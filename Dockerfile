FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies using uv
RUN uv sync --no-dev

# Create directories for data and cache
RUN mkdir -p data cache

# Run the bot
CMD ["uv", "run", "src/main.py"]
