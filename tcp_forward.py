import os
import sys
import socket
import logging
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 读取环境变量
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


def forward_data(src_socket: socket.socket, dst_socket: socket.socket):
    """从 src_socket 读数据发到 dst_socket, 读到空则停止。"""
    try:
        while True:
            data = src_socket.recv(4096)
            if not data:
                break
            dst_socket.sendall(data)
    except Exception as e:
        # 可在调试时打印: logging.debug(f"Forward error: {e}")
        pass
    finally:
        src_socket.close()
        dst_socket.close()


def handle_client(client_socket: socket.socket, client_addr):
    """处理单个客户端连接，将其转发到目标地址。"""
    ip_str, port = client_addr
    logging.info(f"收到来自 {ip_str}:{port} 的连接请求")

    # 连接目标服务器
    try:
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((target_host, target_port))
    except Exception as e:
        logging.error(f"连接目标 {target_host}:{target_port} 失败: {e}")
        client_socket.close()
        return

    # 开启两个线程做双向转发
    t1 = threading.Thread(target=forward_data, args=(client_socket, remote_socket), daemon=True)
    t2 = threading.Thread(target=forward_data, args=(remote_socket, client_socket), daemon=True)
    t1.start()
    t2.start()

    # 等待线程结束（或可不 join，让主线程继续 accept）
    t1.join()
    t2.join()


def start_server():
    """启动TCP服务器，监听INBOUND_PORT，把连接转发到FORWARD_TARGET"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", INBOUND_PORT))
    server_socket.listen(128)

    logging.info(f"TCP Forward 启动: 监听 0.0.0.0:{INBOUND_PORT}, 转发到 {target_host}:{target_port}")

    while True:
        client_socket, client_addr = server_socket.accept()
        # 为每个客户端启动新线程进行处理
        t = threading.Thread(target=handle_client, args=(client_socket, client_addr), daemon=True)
        t.start()


if __name__ == "__main__":
    start_server()
