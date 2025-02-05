import os
import sys
import socket
import logging
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ========== 读取环境变量 ==========

# 监听端口（默认 25565）
INBOUND_PORT = int(os.getenv("INBOUND_PORT", "25565"))

# 目标服务器（IP或域名）和端口（默认 127.0.0.1:25565）
FORWARD_TARGET = os.getenv("FORWARD_TARGET", "127.0.0.1:25565")

# 解析目标
try:
    if ":" not in FORWARD_TARGET:
        raise ValueError(f"FORWARD_TARGET={FORWARD_TARGET} 格式不正确，请写成 HOST:PORT")
    target_host, target_port_str = FORWARD_TARGET.split(":", 1)
    target_port = int(target_port_str)
except Exception as e:
    logging.error(f"无法解析 FORWARD_TARGET={FORWARD_TARGET}: {e}")
    sys.exit(1)

# 决定转发协议，可选值: tcp / udp / both
FORWARD_PROTOCOL = os.getenv("FORWARD_PROTOCOL", "tcp").lower()
if FORWARD_PROTOCOL not in ["tcp", "udp", "both"]:
    logging.warning(f"FORWARD_PROTOCOL={FORWARD_PROTOCOL} 不合法，将使用 tcp")
    FORWARD_PROTOCOL = "tcp"


# ========== TCP 转发 ==========

def forward_data(src_socket: socket.socket, dst_socket: socket.socket):
    """从 src_socket 读数据发到 dst_socket, 读到空则停止。"""
    try:
        while True:
            data = src_socket.recv(4096)
            if not data:
                break
            dst_socket.sendall(data)
    except Exception:
        pass
    finally:
        src_socket.close()
        dst_socket.close()


def handle_client_tcp(client_socket: socket.socket, client_addr):
    """处理单个TCP客户端连接，将其转发到目标地址。"""
    ip_str, port = client_addr
    logging.info(f"[TCP] 收到来自 {ip_str}:{port} 的连接请求")

    # 连接目标服务器
    try:
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((target_host, target_port))
    except Exception as e:
        logging.error(f"[TCP] 连接目标 {target_host}:{target_port} 失败: {e}")
        client_socket.close()
        return

    # 开启两个线程做双向转发
    t1 = threading.Thread(target=forward_data, args=(client_socket, remote_socket), daemon=True)
    t2 = threading.Thread(target=forward_data, args=(remote_socket, client_socket), daemon=True)
    t1.start()
    t2.start()
    # 阻塞等待两个线程结束
    t1.join()
    t2.join()


def start_tcp_server():
    """启动TCP服务器，监听INBOUND_PORT，把连接转发到FORWARD_TARGET"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", INBOUND_PORT))
    server_socket.listen(128)

    logging.info(f"[TCP] 启动: 监听 0.0.0.0:{INBOUND_PORT}, 转发到 {target_host}:{target_port}")

    while True:
        client_socket, client_addr = server_socket.accept()
        # 为每个TCP客户端启动新线程进行处理
        t = threading.Thread(target=handle_client_tcp, args=(client_socket, client_addr), daemon=True)
        t.start()


# ========== UDP 转发 ==========

def start_udp_server():
    """
    启动 UDP 服务器:
    1. 在 INBOUND_PORT 上监听来自客户端的数据；
    2. 为每个新的 client_addr 创建一个远程 socket，并启动线程把远程的数据再发回给 client_addr；
    3. 把客户端的请求发给目标服务器，再把目标服务器响应转发给客户端。
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(("0.0.0.0", INBOUND_PORT))
    logging.info(f"[UDP] 启动: 监听 0.0.0.0:{INBOUND_PORT}, 转发到 {target_host}:{target_port}")

    # 客户端地址 -> 远程Socket 的映射表
    client_map = {}
    lock = threading.Lock()

    def forward_remote_to_local(remote_sock: socket.socket, client_addr):
        """
        从远程服务器拿到数据后，发送给 client_addr。
        当出现异常(如远程关闭等)时，清理映射表。
        """
        while True:
            try:
                data = remote_sock.recv(65535)
                if not data:
                    break
                with lock:
                    # 如果已不在映射表, 说明会话已结束
                    if client_map.get(client_addr) != remote_sock:
                        break
                server_socket.sendto(data, client_addr)
            except Exception:
                break

        # 清理
        with lock:
            if client_map.get(client_addr) == remote_sock:
                del client_map[client_addr]
        remote_sock.close()
        logging.info(f"[UDP] 远程到 {client_addr} 的线程退出, 会话关闭.")

    while True:
        try:
            data, client_addr = server_socket.recvfrom(65535)
        except Exception as e:
            logging.error(f"[UDP] recvfrom 异常: {e}")
            continue

        with lock:
            if client_addr not in client_map:
                # 与目标服务器建立一个UDP“伪连接”
                remote_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # 对 UDP socket 执行 connect，后续可以直接使用 send/recv 而不用 sendto/recvfrom
                remote_sock.connect((target_host, target_port))
                client_map[client_addr] = remote_sock

                # 启动线程，把远程服务器的数据读出来发回给客户端
                t = threading.Thread(target=forward_remote_to_local, args=(remote_sock, client_addr), daemon=True)
                t.start()

            else:
                remote_sock = client_map[client_addr]

        # 把客户端数据发给目标服务器
        try:
            remote_sock.send(data)
        except Exception as e:
            logging.error(f"[UDP] send 异常: {e}")
            # 如果发送失败，可以选择删除映射或忽略
            with lock:
                if client_map.get(client_addr) == remote_sock:
                    del client_map[client_addr]
            remote_sock.close()


if __name__ == "__main__":
    # 根据 FORWARD_PROTOCOL 的值分别启动 TCP/UDP 服务器
    threads = []
    if FORWARD_PROTOCOL in ["tcp", "both"]:
        t_tcp = threading.Thread(target=start_tcp_server, daemon=True)
        threads.append(t_tcp)
        t_tcp.start()

    if FORWARD_PROTOCOL in ["udp", "both"]:
        t_udp = threading.Thread(target=start_udp_server, daemon=True)
        threads.append(t_udp)
        t_udp.start()

    # 在主线程等待所有子线程(服务器)运行
    for t in threads:
        t.join()
