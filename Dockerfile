FROM python:3.15-slim

WORKDIR /app

# Set Python to run in unbuffered mode (print statements flush immediately)
ENV PYTHONUNBUFFERED=1

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
