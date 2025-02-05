# kechangdev/forwarder

[![Docker Pulls](https://img.shields.io/docker/pulls/kechangdev/s2s?style=flat-square)](https://hub.docker.com/r/kechangdev/forwarder)


该项目是一个通用的 TCP/UDP 转发器，可以满足各种网络层/应用层协议的端口转发需求（例如 HTTP、SOCKS5、私有协议等均可）。

## 功能

1. **TCP 转发**：监听某个 TCP 端口，把所有数据转发到目标服务器与端口，再把目标服务器的响应回发给客户端。
2. **UDP 转发**：类似地，监听某个 UDP 端口，把数据转发到目标服务器与端口；为多个并发客户端分别创建相应的 UDP 会话。

通过环境变量 `FORWARD_PROTOCOL` 来选择只启用 TCP、只启用 UDP，或者同时启用二者。只要是使用对应端口的协议，转发器都可以通透传递数据。

## 环境变量

- `INBOUND_PORT`：容器内脚本监听的端口，默认 `25565`
- `FORWARD_TARGET`：转发目标，例如 `100.82.235.46:25565`
- `FORWARD_PROTOCOL`：可选 `tcp` / `udp` / `both`，默认 `tcp`
  - `tcp` 只开 TCP 转发
  - `udp` 只开 UDP 转发
  - `both` 同时开 TCP 与 UDP 转发

## 运行容器示例

```bash
docker run -d \
    --name tcp_forward \
    --restart=unless-stopped \
    -p 25565:25565/tcp \
    -p 25565:25565/udp \
    -e INBOUND_PORT=25565 \
    -e FORWARD_TARGET="100.82.235.46:25565" \
    -e FORWARD_PROTOCOL=both \
    kechangdev/forwarder:latest
```

<img src="https://github.com/kechangdev/forwarder/blob/main/Preview.jpeg?raw=true" alt="Preview" width="600">
