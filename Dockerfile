FROM python:3.11-slim

# Set working directory
WORKDIR /app

ARG GIT_TOKEN

# Install dependencies
COPY requirements.txt .

RUN apt-get update && apt-get install -y git g++ && \
    pip install uv && \
    uv pip install --force-reinstall --no-cache "draup_packages[email, llm_manager] @ git+https://$GIT_TOKEN@github.com/Draup/draup-services.git@main#subdirectory=draup_packages" --system && \
    uv pip install -r requirements.txt --system && \
    apt-get remove -y git g++ && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*
    
# Copy all source code
COPY . .

# Run FastAPI app via Uvicorn with timeout settings
CMD ["uvicorn", "settings.server:etter_app", "--host", "0.0.0.0", "--port", "7071", "--timeout-keep-alive", "600", "--timeout-graceful-shutdown", "600", "--workers", "5"]