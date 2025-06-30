# 🛠️ Setup Guide

This comprehensive guide covers installation, configuration, and deployment of the Mural collaborative pixel art platform.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Configuration](#configuration)
- [Production Deployment](#production-deployment)
- [Docker Setup](#docker-setup)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### System Requirements

- **Python**: 3.8 or higher
- **pip**: Latest version (comes with Python)
- **Git**: For version control
- **Redis**: Optional but recommended for production

### Recommended Tools

- **Virtual Environment**: venv or conda
- **Code Editor**: VS Code, PyCharm, or similar
- **Browser**: Modern browser with WebSocket support

### Hardware Requirements

- **Development**: 4GB RAM, 1GB disk space
- **Production**: 8GB+ RAM, 5GB+ disk space (depends on usage)

## 💻 Development Setup

### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/your-username/Mural.git
cd Mural

# Verify the clone
ls -la
```

### 2. Set Up Python Environment

#### Option A: Using venv (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Verify activation (should show virtual environment path)
which python
```

#### Option B: Using conda

```bash
# Create conda environment
conda create -n mural python=3.9

# Activate environment
conda activate mural

# Verify activation
python --version
```

### 3. Install Dependencies

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
pip list
```

### 4. Set Up Configuration

#### Create Environment File

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration (use your preferred editor)
nano .env
```

#### Basic Development Configuration

```bash
# .env file content
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
PIXEL_COOLDOWN=60
HOST=127.0.0.1
PORT=5000
DEBUG=True
```

### 5. Run the Application

```bash
# Start the development server
python app.py

# Alternative: Using Flask CLI
flask run
```

### 6. Verify Installation

Open your browser and navigate to:
- **Main Application**: http://localhost:5000
- **API Health Check**: http://localhost:5000/api/canvas

You should see the Mural interface with a blank canvas ready for pixel art!

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FLASK_ENV` | Flask environment | `production` | No |
| `SECRET_KEY` | Flask secret key | Generated | **Yes** |
| `PIXEL_COOLDOWN` | Cooldown in seconds | `300` (prod), `60` (dev) | No |
| `HOST` | Server host | `0.0.0.0` | No |
| `PORT` | Server port | `5000` | No |
| `REDIS_URL` | Redis connection URL | None | No |
| `DEBUG` | Debug mode | `False` | No |

### Advanced Configuration

#### Redis Configuration

```bash
# Redis URL formats
REDIS_URL=redis://localhost:6379/0
REDIS_URL=redis://username:password@host:port/db
REDIS_URL=rediss://ssl-enabled-redis.com:6380/0
```

#### Production Security

```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Use the generated key
SECRET_KEY=your-generated-secure-key-here
```

#### Performance Tuning

```bash
# Longer cooldown for production
PIXEL_COOLDOWN=300

# Enable production optimizations
FLASK_ENV=production
DEBUG=False
```

## 🚀 Production Deployment

### Method 1: Direct Deployment

#### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx redis-server

# Create application user
sudo useradd -m -s /bin/bash mural
sudo su - mural
```

#### 2. Application Setup

```bash
# Clone and setup application
git clone https://github.com/your-username/Mural.git
cd Mural

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn
```

#### 3. Production Configuration

```bash
# Create production environment file
cat > .env << EOF
FLASK_ENV=production
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
PIXEL_COOLDOWN=300
HOST=0.0.0.0
PORT=5000
REDIS_URL=redis://localhost:6379/0
DEBUG=False
EOF
```

#### 4. Gunicorn Setup

```bash
# Create Gunicorn configuration
cat > gunicorn.conf.py << EOF
bind = "0.0.0.0:5000"
workers = 1
worker_class = "eventlet"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 60
keepalive = 5
EOF

# Test Gunicorn
gunicorn -c gunicorn.conf.py app:app
```

#### 5. Systemd Service

```bash
# Create systemd service file
sudo tee /etc/systemd/system/mural.service << EOF
[Unit]
Description=Mural Collaborative Pixel Art
After=network.target

[Service]
User=mural
Group=mural
WorkingDirectory=/home/mural/Mural
Environment=PATH=/home/mural/Mural/venv/bin
ExecStart=/home/mural/Mural/venv/bin/gunicorn -c gunicorn.conf.py app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable mural
sudo systemctl start mural
sudo systemctl status mural
```

#### 6. Nginx Configuration

```bash
# Create Nginx configuration
sudo tee /etc/nginx/sites-available/mural << EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/mural /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Method 2: Docker Deployment

#### 1. Create Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash mural
RUN chown -R mural:mural /app
USER mural

# Expose port
EXPOSE 5000

# Run command
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "app:app"]
```

#### 2. Create docker-compose.yml

```yaml
version: '3.8'

services:
  redis:
    image: redis:alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  mural:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
      - PIXEL_COOLDOWN=300
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    restart: unless-stopped
    volumes:
      - ./canvas_data:/app/canvas_data

volumes:
  redis_data:
```

#### 3. Deploy with Docker

```bash
# Create environment file
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env

# Build and start
docker-compose up --build -d

# Check status
docker-compose ps
docker-compose logs mural
```

## 🐳 Docker Setup

### Development with Docker

```bash
# Build development image
docker build -t mural:dev .

# Run with development settings
docker run -p 5000:5000 -e FLASK_ENV=development -e DEBUG=True mural:dev
```

### Production with Docker Swarm

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  redis:
    image: redis:alpine
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
    volumes:
      - redis_data:/data

  mural:
    image: mural:latest
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SECRET_KEY_FILE=/run/secrets/secret_key
      - REDIS_URL=redis://redis:6379/0
    secrets:
      - secret_key
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure
    depends_on:
      - redis

secrets:
  secret_key:
    external: true

volumes:
  redis_data:
```

## 🔐 SSL/HTTPS Setup

### Using Certbot (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

### Manual SSL Configuration

```bash
# Update Nginx configuration for SSL
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # Your existing location blocks here
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## 🔍 Health Checks and Monitoring

### Basic Health Check Endpoint

```python
# Add to your Flask app
@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }
```

### System Monitoring

```bash
# Monitor application logs
sudo journalctl -u mural -f

# Monitor system resources
htop

# Monitor Redis
redis-cli info
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find process using port 5000
lsof -i :5000

# Kill process if needed
kill -9 <PID>

# Or use different port
export PORT=8080
python app.py
```

#### 2. Permission Denied

```bash
# Fix file permissions
chmod +x app.py
chown -R $USER:$USER .

# Fix virtual environment permissions
chmod -R 755 venv
```

#### 3. Redis Connection Issues

```bash
# Check Redis status
redis-cli ping

# Start Redis if not running
sudo systemctl start redis-server

# Check Redis logs
sudo journalctl -u redis-server
```

#### 4. WebSocket Connection Failures

```bash
# Check firewall settings
sudo ufw allow 5000

# Test WebSocket connection
curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
     -H "Sec-WebSocket-Version: 13" \
     http://localhost:5000/socket.io/
```

### Performance Issues

#### 1. High Memory Usage

```bash
# Monitor memory usage
free -h
ps aux | grep python

# Optimize Python memory
export PYTHONOPTIMIZE=1
```

#### 2. Slow Response Times

```bash
# Check system load
uptime
iostat 1

# Profile Flask application
pip install flask-profiler
# Add profiling to your app
```

### Logging and Debugging

#### Enable Debug Logging

```python
# Add to app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Application Logs

```bash
# View application logs
tail -f /var/log/mural/app.log

# Rotate logs
sudo logrotate /etc/logrotate.d/mural
```

## 📊 Performance Tuning

### Gunicorn Optimization

```python
# gunicorn.conf.py
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "eventlet"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True
timeout = 60
keepalive = 5
```

### Redis Optimization

```bash
# Redis configuration optimization
echo "maxmemory 256mb" >> /etc/redis/redis.conf
echo "maxmemory-policy allkeys-lru" >> /etc/redis/redis.conf
sudo systemctl restart redis-server
```

### Nginx Optimization

```nginx
# nginx.conf optimizations
worker_processes auto;
worker_connections 1024;

gzip on;
gzip_types text/plain text/css application/json application/javascript;

client_max_body_size 10M;
```

---

This setup guide should get you up and running with Mural in both development and production environments. For additional help, refer to the [Troubleshooting Guide](TROUBLESHOOTING.md) or open an issue on GitHub.
