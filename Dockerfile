FROM python:3.14-slim

WORKDIR /app

# Set Python to run in unbuffered mode (print statements flush immediately)
ENV PYTHONUNBUFFERED=1

# Install git and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY config.yaml ./
COPY cache/aw2_atlas.npz ./cache/aw2_atlas.npz
COPY src ./src

CMD ["uv", "run", "--no-sync", "python", "-m", "src.main"]
