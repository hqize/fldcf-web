# 构建上下文应为 fldcf 仓库根目录：docker build -f backend/Dockerfile .
#
# 国内构建 apt 易 502：--build-arg APT_MIRROR=aliyun|tsinghua|ustc（见 docker.env.example）
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
      ustc) \
        if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
          sed -i 's|http://deb.debian.org/debian|https://mirrors.ustc.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources; \
          sed -i 's|https://deb.debian.org/debian|https://mirrors.ustc.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources; \
          sed -i 's|http://security.debian.org/debian-security|https://mirrors.ustc.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
          sed -i 's|https://security.debian.org/debian-security|https://mirrors.ustc.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
        elif [ -f /etc/apt/sources.list ]; then \
          sed -i 's|deb.debian.org|mirrors.ustc.edu.cn|g' /etc/apt/sources.list; \
          sed -i 's|security.debian.org/debian-security|mirrors.ustc.edu.cn/debian-security|g' /etc/apt/sources.list; \
        fi ;; \
      *) echo "unknown APT_MIRROR=$APT_MIRROR (use official|tsinghua|aliyun|ustc)" >&2; exit 1 ;; \
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

# PYTORCH_VARIANT: cpu（默认）| cu118（CUDA 11.8 轮子）| cu124（CUDA 12.4 轮子）
# PIP_MIRROR: official | aliyun | ustc | tsinghua | tencent
#   ustc/tsinghua 时 torch 也走国内 pytorch-wheels 镜像；aliyun/tencent 仅加速 PyPI 小依赖
# 其余依赖里含 torchvision 行，避免二次安装把 torch 换成 CPU 版，故先装 torch 再 sed 掉该行
ARG PYTORCH_VARIANT=cpu
ARG PIP_MIRROR=official

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt

RUN set -eux; \
    case "$PYTORCH_VARIANT" in \
      cu118) \
        WHEEL_TAG="cu118"; \
        TORCH_VER="2.6.0+cu118"; \
        TV_VER="0.21.0+cu118"; \
        ;; \
      cu124) \
        WHEEL_TAG="cu124"; \
        TORCH_VER="2.6.0+cu124"; \
        TV_VER="0.21.0+cu124"; \
        ;; \
      cpu|*) \
        WHEEL_TAG="cpu"; \
        TORCH_VER="2.6.0+cpu"; \
        TV_VER="0.21.0+cpu"; \
        ;; \
    esac; \
    IDX="https://download.pytorch.org/whl/${WHEEL_TAG}"; \
    case "$PIP_MIRROR" in \
      official) PIP_EXTRA="" ;; \
      aliyun) PIP_EXTRA="https://mirrors.aliyun.com/pypi/simple/" ;; \
      ustc) \
        PIP_EXTRA="https://mirrors.ustc.edu.cn/pypi/web/simple"; \
        IDX="https://mirrors.ustc.edu.cn/pytorch-wheels/whl/${WHEEL_TAG}"; \
        ;; \
      tsinghua) \
        PIP_EXTRA="https://pypi.tuna.tsinghua.edu.cn/simple"; \
        IDX="https://mirrors.tuna.tsinghua.edu.cn/pytorch-wheels/whl/${WHEEL_TAG}"; \
        ;; \
      tencent) PIP_EXTRA="https://mirrors.cloud.tencent.com/pypi/simple" ;; \
      *) echo "unknown PIP_MIRROR=$PIP_MIRROR (use official|aliyun|ustc|tsinghua|tencent)" >&2; exit 1 ;; \
    esac; \
    PIP_OPTS="--no-cache-dir --default-timeout=300 --retries 10"; \
    if [ -n "$PIP_EXTRA" ]; then PIP_EXTRA_FLAG="--extra-index-url $PIP_EXTRA"; else PIP_EXTRA_FLAG=""; fi; \
    pip install $PIP_OPTS $PIP_EXTRA_FLAG \
      "torch==${TORCH_VER}" "torchvision==${TV_VER}" \
      --index-url "$IDX"; \
    sed '/^torchvision/d' /app/backend/requirements.txt > /tmp/req.txt; \
    if [ -n "$PIP_EXTRA" ]; then \
      pip install $PIP_OPTS -i "$PIP_EXTRA" --extra-index-url "$IDX" -r /tmp/req.txt; \
    else \
      pip install $PIP_OPTS --extra-index-url "$IDX" -r /tmp/req.txt; \
    fi

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
