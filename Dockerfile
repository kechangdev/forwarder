FROM python:3.9-slim

# 将工作目录设置为 /app
WORKDIR /app

# 将 forward.py 拷贝进入容器
COPY forward.py /app/forward.py

# 默认执行的命令（启动 Python 脚本）
CMD ["python", "/app/forward.py"]
