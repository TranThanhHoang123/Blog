# Dockerfile
FROM python:3.11
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y libmagic-dev && apt-get install netcat-traditional
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Sao chép tệp entrypoint vào container
COPY entrypoint.sh /entrypoint.sh

# Đặt quyền thực thi cho tệp entrypoint
RUN chmod +x /entrypoint.sh

# Đặt entrypoint cho container
ENTRYPOINT ["/entrypoint.sh"]
