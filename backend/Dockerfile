# 构建上下文应为 fldcf 仓库根目录：docker build -f backend/Dockerfile .
#
# 国内构建 apt 易 502：加 --build-arg APT_MIRROR=tsinghua 或 aliyun（见 docker.env.example）
FROM python:3.12-slim-bookworm

ARG APT_MIRROR=official

RUN set -eux; \
    case "$APT_MIRROR" in \
      official) ;; \
      tsinghua) \
        if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
          sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources; \
          sed -i 's|https://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources; \
          sed -i 's|http://security.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
          sed -i 's|https://security.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
        elif [ -f /etc/apt/sources.list ]; then \
          sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list; \
          sed -i 's|security.debian.org/debian-security|mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list; \
        fi ;; \
      aliyun) \
        codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"; \
        rm -f /etc/apt/sources.list.d/debian.sources; \
        { \
          echo "deb https://mirrors.aliyun.com/debian/ ${codename} main contrib non-free non-free-firmware"; \
          echo "deb https://mirrors.aliyun.com/debian/ ${codename}-updates main contrib non-free non-free-firmware"; \
          echo "deb https://mirrors.aliyun.com/debian-security ${codename}-security main contrib non-free non-free-firmware"; \
        } > /etc/apt/sources.list ;; \
      *) echo "unknown APT_MIRROR=$APT_MIRROR (use official|tsinghua|aliyun)" >&2; exit 1 ;; \
    esac; \
    apt-get -o Acquire::Retries=6 \
        -o Acquire::http::Timeout=120 \
        -o Acquire::https::Timeout=120 \
        update; \
    apt-get -o Acquire::Retries=6 \
        -o Acquire::http::Timeout=120 \
        -o Acquire::https::Timeout=120 \
        install -y --no-install-recommends \
        gcc g++; \
    rm -rf /var/lib/apt/lists/*

# PYTORCH_VARIANT: cpu（默认，镜像小）| cu124（NVIDIA CUDA 12.4 轮子；需主机驱动支持）
# 其余依赖里含 torchvision 行，避免二次安装把 torch 换成 CPU 版，故先装 torch 再 sed 掉该行
ARG PYTORCH_VARIANT=cpu

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt

RUN set -eux; \
    case "$PYTORCH_VARIANT" in \
      cu124) IDX="https://download.pytorch.org/whl/cu124" ;; \
      cpu|*) IDX="https://download.pytorch.org/whl/cpu" ;; \
    esac; \
    pip install --no-cache-dir torch torchvision --index-url "$IDX"; \
    sed '/^torchvision/d' /app/backend/requirements.txt > /tmp/req.txt; \
    pip install --no-cache-dir -r /tmp/req.txt

COPY backend /app/backend
COPY FLDCF_raw /app/FLDCF_raw

WORKDIR /app/backend
ENV PYTHONPATH=/app/backend
ENV FLDCF_ROOT=/app/FLDCF_raw
# 运行时可用 FLDCF_CPU=0 尝试 GPU（需 CUDA 版 torch + 容器可见 GPU）；默认仍偏 CPU 安全
ENV FLDCF_CPU=1

EXPOSE 8000
# 应用定义在 src/main.py
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
