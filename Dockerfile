# 使用官方 uv 镜像（已包含 Python 3.13 和 uv）
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# 设置工作目录
WORKDIR /app

# 拷贝项目文件
# 仅拷贝 pyproject.toml 和 uv.lock 用于依赖缓存
COPY pyproject.toml uv.lock* ./

# 安装依赖（生产模式，不安装 dev）
RUN uv sync --frozen --no-dev

# 拷贝源码
COPY api ./api
COPY templates ./templates
RUN mkdir -p static/uploads

# 设置 Flask 环境变量
ENV FLASK_APP=api/app.py \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000 \
    PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 5000

# 启动应用
CMD ["uv", "run", "python", "api/app.py"]
