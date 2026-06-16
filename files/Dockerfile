FROM python:3.12-slim

WORKDIR /app

# Cài dependencies trước (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Cloud Run inject PORT, gunicorn listen theo đó
ENV PORT=8080

# Dùng gunicorn thay vì Flask dev server (production-ready)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "300", "main:app"]
