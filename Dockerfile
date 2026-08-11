# Dockerfile for CampusLink Web Application
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Environment variables
ENV PORT=5000
ENV USE_MYSQL=true
ENV MYSQL_HOST=db
ENV MYSQL_PORT=3306
ENV MYSQL_USER=campus_user
ENV MYSQL_PASSWORD=campus_pass
ENV MYSQL_DB=campuslink_umat

EXPOSE 5000

# Run with Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
