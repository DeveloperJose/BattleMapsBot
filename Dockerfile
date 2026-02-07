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
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml README.md uv.lock config.yaml ./
COPY src/ ./src/
COPY cache/ ./cache/

# Install dependencies using uv
RUN uv sync --no-dev

# Create directories for data and cache
RUN mkdir -p data

# Run the bot
CMD ["uv", "run", "src/main.py"]
