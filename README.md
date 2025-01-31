# kechangdev/t2t
该容器可以根据环境变量实现 TCP 转发...

# 环境变量
- `INBOUND_PORT=25565`: 容器内脚本监听在 25565
- `FORWARD_TARGET="100.82.235.46:25565"`: 把所有请求转发到该IP+端口

# 运行容器

例如：

```bash
docker run -d \
    --name tcp_forward \
    --restart=unless-stopped \
    -p 25565:25565 \
    -e INBOUND_PORT=25565 \
    -e FORWARD_TARGET="100.82.235.46:25565" \
    kechangdev/t2t:latest

```
