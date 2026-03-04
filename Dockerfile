FROM python:3.15-rc-slim

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

# Run the bot, syncing dependencies on startup from the mounted volume
CMD ["sh", "-c", "uv sync --no-dev && uv run src/main.py"]
