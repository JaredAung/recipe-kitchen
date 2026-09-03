FROM python:3.14-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_TORCH_BACKEND=cpu \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# PyPI Linux torch is CUDA. Skip that stack, then install CPU wheels for Silero VAD.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev \
        --no-install-package torch \
        --no-install-package torchaudio \
        --no-install-package triton \
        --no-install-package cuda-bindings \
        --no-install-package cuda-pathfinder \
        --no-install-package cuda-toolkit \
        --no-install-package nvidia-cublas \
        --no-install-package nvidia-cuda-cupti \
        --no-install-package nvidia-cuda-nvrtc \
        --no-install-package nvidia-cuda-runtime \
        --no-install-package nvidia-cudnn-cu13 \
        --no-install-package nvidia-cufft \
        --no-install-package nvidia-cufile \
        --no-install-package nvidia-curand \
        --no-install-package nvidia-cusolver \
        --no-install-package nvidia-cusparse \
        --no-install-package nvidia-cusparselt-cu13 \
        --no-install-package nvidia-nccl-cu13 \
        --no-install-package nvidia-nvjitlink \
        --no-install-package nvidia-nvshmem-cu13 \
        --no-install-package nvidia-nvtx \
    && uv pip install torch==2.14.0 torchaudio==2.11.0 --torch-backend=cpu

EXPOSE 80

CMD ["uvicorn", "recipe_kitchen.main:app", "--host", "0.0.0.0", "--port", "80"]
