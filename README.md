# 构建镜像

```bash
docker build -t kechangdev/t2t:latest .

```

> 这会根据 Dockerfile 构建镜像，并命名为 kechangdev/t2t:latest。
> 

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
# 环境变量
- `INBOUND_PORT=25565`: 容器内脚本监听在 25565
- `FORWARD_TARGET="100.82.235.46:25565"`: 把所有请求转发到该IP+端口
