FROM python:3.12-slim

WORKDIR /app

# Install build dependencies and cleanup
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Disable Python output buffering for real-time logs
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Run with the builtin server (sufficient for simple testing). For production, replace with gunicorn or another WSGI server.
CMD ["python", "app.py"]
