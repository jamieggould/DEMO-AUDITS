FROM python:3.11-slim
 
WORKDIR /app
 
# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy all app files
COPY . .
 
EXPOSE 10000
 
# Render injects $PORT — default 10000 if not set
# timeout 120s to allow OpenAI generation to complete
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --workers 2 --timeout 120
 
