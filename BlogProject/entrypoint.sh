#!/bin/bash

# Chờ cơ sở dữ liệu sẵn sàng
echo "Waiting for the database to be ready..."
while ! nc -z db 3306; do
  sleep 1
done

echo "Database is ready. Running migrations..."

# Áp dụng migrations
python manage.py migrate

# Áp dụng migrations
python manage.py initialize

# Khởi động ứng dụng với Gunicorn
exec gunicorn --bind 0.0.0.0:8000 BlogProject.wsgi:application
