FROM python:3.13-slim

# Install git as it's required to run git diff
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install uv to manage dependencies
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Copy the rest of the application
COPY main.py ./

# Run the application
ENTRYPOINT ["uv", "run", "python", "/app/main.py"]
