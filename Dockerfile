# Dockerfile
FROM python:3.9-slim

# 将工作目录设置为 /app
WORKDIR /app

# 将 tcp_forward.py 拷贝进入容器
COPY tcp_forward.py /app/tcp_forward.py

# 启动容器时默认执行的命令
CMD ["python", "/app/tcp_forward.py"]
