# ⚙️ Configuration Guide
Complete configuration reference for Mural, covering all environment variables, settings, and customization options.

## 📋 Table of Contents

- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [Feature Toggles](#feature-toggles)
- [Caching Configuration](#caching-configuration)
- [WebSocket Configuration](#websocket-configuration)
- [Security Settings](#security-settings)
- [Performance Tuning](#performance-tuning)
- [Deployment Configurations](#deployment-configurations)

## 🌍 Environment Variables
### Core Application Settings

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| `FLASK_ENV` | Flask environment | `production` | No | `development` |
| `SECRET_KEY` | Flask secret key | Auto-generated | **Yes** | `your-secret-key-here` |
| `DEBUG` | Debug mode | `False` | No | `True` |
| `HOST` | Server host | `0.0.0.0` | No | `127.0.0.1` |
| `PORT` | Server port | `5000` | No | `8080` |

### Canvas Configuration
| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| `CANVAS_WIDTH` | Canvas width in pixels | `500` | No | `1000` |
| `CANVAS_HEIGHT` | Canvas height in pixels | `500` | No | `1000` |
| `PIXEL_COOLDOWN` | Cooldown in seconds | `300` (prod), `60` (dev) | No | `120` |
| `MAX_PIXELS_PER_USER` | Max pixels per user | `unlimited` | No | `1000` |

### Caching Configuration

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| `REDIS_URL` | Redis connection URL | None | No | `redis://localhost:6379/0` |
| `CACHE_TYPE` | Cache backend type | `redis_memory_fallback` | No | `redis` |
| `CACHE_TTL` | Cache TTL in seconds | `3600` | No | `1800` |
| `MEMORY_CACHE_SIZE` | Max memory cache items | `10000` | No | `5000` |

### WebSocket Configuration

| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| `SOCKETIO_CORS_ORIGINS` | Allowed CORS origins | `*` | No | `https://yourdomain.com` |
| `SOCKETIO_PING_TIMEOUT` | Ping timeout (seconds) | `60` | No | `30` |
| `SOCKETIO_PING_INTERVAL` | Ping interval (seconds) | `25` | No | `15` |
| `MAX_CONNECTIONS` | Max WebSocket connections | `1000` | No | `500` |

### Logging Configuration
| Variable | Description | Default | Required | Example |
|----------|-------------|---------|----------|---------|
| `LOG_LEVEL` | Logging level | `INFO` | No | `DEBUG` |
| `LOG_FILE` | Log file path | None | No | `/var/log/mural.log` |
| `LOG_FORMAT` | Log message format | Standard | No | Custom format |
| `ENABLE_ACCESS_LOG` | Enable access logging | `True` | No | `False` |

## 📁 Configuration Files

### 1. Environment File (.env)

```bash
# .env file for local development
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=True
HOST=127.0.0.1
PORT=5000

# Canvas settings
CANVAS_WIDTH=500
CANVAS_HEIGHT=500
PIXEL_COOLDOWN=60

# Caching
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# WebSocket
SOCKETIO_CORS_ORIGINS=*
SOCKETIO_PING_TIMEOUT=60
# Logging
LOG_LEVEL=DEBUG
ENABLE_ACCESS_LOG=True
```

### 2. Production Environment (.env.production)

```bash
# Production environment configuration
FLASK_ENV=production
SECRET_KEY=your-super-secure-secret-key-here
DEBUG=False
HOST=0.0.0.0
PORT=5000

# Canvas settings
CANVAS_WIDTH=500
CANVAS_HEIGHT=500
PIXEL_COOLDOWN=300

# Caching
REDIS_URL=redis://redis-server:6379/0
CACHE_TTL=7200
MEMORY_CACHE_SIZE=20000

# WebSocket
SOCKETIO_CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SOCKETIO_PING_TIMEOUT=60
SOCKETIO_PING_INTERVAL=25
MAX_CONNECTIONS=2000

# Security
ENABLE_RATE_LIMITING=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/mural/app.log
ENABLE_ACCESS_LOG=True
```

### 3. Configuration Classes (config.py)

```python
import os
from typing import Type

class Config:
    """Base configuration class."""
    # Flask Core
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    DEBUG = False
    TESTING = False
    
    # Server
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Canvas
    CANVAS_WIDTH = int(os.environ.get('CANVAS_WIDTH', 500))
    CANVAS_HEIGHT = int(os.environ.get('CANVAS_HEIGHT', 500))
    PIXEL_COOLDOWN = int(os.environ.get('PIXEL_COOLDOWN', 300))
    
    # Caching
    REDIS_URL = os.environ.get('REDIS_URL')
    CACHE_TTL = int(os.environ.get('CACHE_TTL', 3600))
    MEMORY_CACHE_SIZE = int(os.environ.get('MEMORY_CACHE_SIZE', 10000))
    
    # WebSocket
    SOCKETIO_CORS_ORIGINS = os.environ.get('SOCKETIO_CORS_ORIGINS', '*')
    SOCKETIO_PING_TIMEOUT = int(os.environ.get('SOCKETIO_PING_TIMEOUT', 60))
    SOCKETIO_PING_INTERVAL = int(os.environ.get('SOCKETIO_PING_INTERVAL', 25))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    PIXEL_COOLDOWN = int(os.environ.get('PIXEL_COOLDOWN', 60))
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    PIXEL_COOLDOWN = int(os.environ.get('PIXEL_COOLDOWN', 300))
    # Enhanced security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    PIXEL_COOLDOWN = 1  # Fast testing
    REDIS_URL = None  # Use memory cache only
    LOG_LEVEL = 'WARNING'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name: str = None) -> Type[Config]:
    """Get configuration class by name."""
    config_name = config_name or os.environ.get('FLASK_ENV', 'default')
    return config.get(config_name, DevelopmentConfig)
```

## 🔧 Feature Toggles

### Canvas Features

```bash
# Canvas size configuration
CANVAS_WIDTH=500
CANVAS_HEIGHT=500

# Enable/disable canvas features
ENABLE_ZOOM=True
ENABLE_PAN=True
ENABLE_GRID=False
MAX_ZOOM_LEVEL=10
MIN_ZOOM_LEVEL=0.1

# Color palette
CUSTOM_COLORS_ENABLED=False
TOTAL_COLORS=32
ALLOW_COLOR_PICKER=False
```
### User Features

```bash
# User session features
ENABLE_USER_STATS=True
ENABLE_ACTIVITY_FEED=True
SHOW_USER_COUNT=True
ENABLE_USER_IDENTIFICATION=False

# Rate limiting
ENABLE_RATE_LIMITING=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# Cooldown system
ENABLE_COOLDOWN=True
PIXEL_COOLDOWN=300
COOLDOWN_BYPASS_ROLES=admin,moderator
```

### UI Features

```bash
# Theme system
ENABLE_THEMES=True
DEFAULT_THEME=auto
AVAILABLE_THEMES=light,dark,auto

# Interface elements
SHOW_COORDINATES=True
SHOW_COLOR_HISTORY=True
ENABLE_KEYBOARD_SHORTCUTS=True
SHOW_TOOLTIPS=True

# Mobile optimizations
ENABLE_TOUCH_GESTURES=True
MOBILE_UI_SCALE=1.2
TOUCH_SENSITIVITY=1.0
```

## 🗄️ Caching Configuration
### Redis Configuration

```bash
# Redis connection
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-redis-password
# Redis SSL (for cloud providers)
REDIS_SSL=True
REDIS_SSL_CERT_REQS=required

# Connection pooling
REDIS_MAX_CONNECTIONS=50
REDIS_CONNECTION_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5

# Advanced Redis settings
REDIS_HEALTH_CHECK_INTERVAL=30
REDIS_RETRY_ON_TIMEOUT=True
```

### Cache Strategy

```python
# cache_config.py
CACHE_CONFIG = {
    'canvas_data': {
        'ttl': 3600,  # 1 hour
        'strategy': 'write_through'
    },
    'user_sessions': {
        'ttl': 1800,  # 30 minutes
        'strategy': 'write_behind'
    },
    'cooldowns': {
        'ttl': 300,   # 5 minutes
        'strategy': 'write_through'
    },
    'statistics': {
        'ttl': 300,   # 5 minutes
        'strategy': 'lazy_loading'
    }
}
```

### Memory Cache Fallback

```bash
# Memory cache settings
MEMORY_CACHE_SIZE=10000
MEMORY_CACHE_TTL=1800
MEMORY_CACHE_CLEANUP_INTERVAL=300

# Cache eviction policy
CACHE_EVICTION_POLICY=lru  # lru, lfu, random

# Cache monitoring
ENABLE_CACHE_METRICS=True
CACHE_HIT_RATE_THRESHOLD=0.8
```

## 🔌 WebSocket Configuration

### Socket.IO Settings

```python
# socketio_config.py
SOCKETIO_CONFIG = {
    'cors_allowed_origins': os.environ.get('SOCKETIO_CORS_ORIGINS', '*'),
    'ping_timeout': int(os.environ.get('SOCKETIO_PING_TIMEOUT', 60)),
    'ping_interval': int(os.environ.get('SOCKETIO_PING_INTERVAL', 25)),
    'max_http_buffer_size': int(os.environ.get('SOCKETIO_MAX_BUFFER_SIZE', 1024 * 1024)),
    'allow_upgrades': True,
    'compression': True,
    'cookie': 'io',
    'engineio_logger': False,
    'logger': False
}
```

### Connection Management
```bash
# Connection limits
MAX_CONNECTIONS=1000
MAX_CONNECTIONS_PER_IP=10
CONNECTION_TIMEOUT=60

# WebSocket transport
ALLOWED_TRANSPORTS=websocket,polling
PREFERRED_TRANSPORT=websocket

# Broadcasting
ENABLE_BROADCAST_ALL=True
BROADCAST_BATCH_SIZE=100
BROADCAST_INTERVAL=50  # milliseconds
```

### Room Management

```bash
# Room configuration
ENABLE_ROOMS=False
DEFAULT_ROOM=canvas
MAX_ROOM_SIZE=100
AUTO_JOIN_DEFAULT_ROOM=True

# Room-based features
ENABLE_ROOM_STATS=True
ROOM_INACTIVITY_TIMEOUT=3600
```

## 🔒 Security Settings

### Session Security

```bash
# Session configuration
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_MAX_AGE=86400  # 24 hours

# Session storage
SESSION_TYPE=redis
SESSION_REDIS_URL=redis://localhost:6379/1
SESSION_USE_SIGNER=True
SESSION_KEY_PREFIX=mural:session:
```

### CORS Configuration

```bash
# CORS settings
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_METHODS=GET,POST,OPTIONS
CORS_ALLOW_HEADERS=Content-Type,Authorization
CORS_EXPOSE_HEADERS=X-RateLimit-Remaining,X-RateLimit-Reset
CORS_MAX_AGE=86400
```

### Rate Limiting

```bash
# Global rate limits
GLOBAL_RATE_LIMIT=1000/hour
API_RATE_LIMIT=100/minute
WEBSOCKET_RATE_LIMIT=60/minute

# Per-endpoint limits
CANVAS_GET_RATE_LIMIT=10/minute
PIXEL_PLACE_RATE_LIMIT=1/5minutes
COOLDOWN_CHECK_RATE_LIMIT=30/minute

# Rate limit storage
RATELIMIT_STORAGE_URL=redis://localhost:6379/2
RATELIMIT_KEY_PREFIX=mural:ratelimit:
```

### Input Validation

```python
# validation_config.py
VALIDATION_CONFIG = {
    'pixel_coordinates': {
        'x_min': 0,
        'x_max': 499,
        'y_min': 0,
        'y_max': 499
    },
    'color_values': {
        'min': 0,
        'max': 31
    },
    'user_input': {
        'max_length': 1000,
        'allowed_chars': r'^[a-zA-Z0-9\s\-_\.]+$'
    }
}
```

## ⚡ Performance Tuning
### Application Performance

```bash
# Flask performance
FLASK_SKIP_DOTENV=True
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000

# Gunicorn settings
GUNICORN_WORKERS=4
GUNICORN_WORKER_CLASS=eventlet
GUNICORN_WORKER_CONNECTIONS=1000
GUNICORN_MAX_REQUESTS=1000
GUNICORN_MAX_REQUESTS_JITTER=100
GUNICORN_TIMEOUT=60
GUNICORN_KEEPALIVE=5
```

### Database Performance

```bash
# Redis performance
REDIS_MAX_MEMORY=512mb
REDIS_MAX_MEMORY_POLICY=allkeys-lru
REDIS_SAVE_ENABLED=True
REDIS_SAVE_INTERVAL=60

# Connection pooling
DB_POOL_SIZE=20
DB_POOL_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

### Caching Performance
```bash
# Cache optimization
CACHE_PREFETCH_ENABLED=True
CACHE_COMPRESSION_ENABLED=True
CACHE_SERIALIZATION_FORMAT=msgpack  # json, pickle, msgpack

# Cache warming
CACHE_WARM_ON_STARTUP=True
CACHE_BACKGROUND_REFRESH=True
CACHE_REFRESH_INTERVAL=300
```
## 🚀 Deployment Configurations

### Docker Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  mural:
    image: mural:latest
    environment:
      - FLASK_ENV=${FLASK_ENV:-production}
      - SECRET_KEY=${SECRET_KEY}
      - REDIS_URL=redis://redis:6379/0
      - PIXEL_COOLDOWN=${PIXEL_COOLDOWN:-300}
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s
```

### Kubernetes Configuration

```yaml
# k8s-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mural-config
data:
  FLASK_ENV: "production"
  PIXEL_COOLDOWN: "300"
  CANVAS_WIDTH: "500"
  CANVAS_HEIGHT: "500"
  LOG_LEVEL: "INFO"
  CACHE_TTL: "3600"
  SOCKETIO_PING_TIMEOUT: "60"
---
apiVersion: v1
kind: Secret
metadata:
  name: mural-secrets
type: Opaque
stringData:
  SECRET_KEY: "your-secret-key-here"
  REDIS_URL: "redis://redis:6379/0"
```

### Load Balancer Configuration

```nginx
# nginx.conf
upstream mural_app {
    least_conn;
    server mural1:5000 max_fails=3 fail_timeout=30s;
    server mural2:5000 max_fails=3 fail_timeout=30s;
    server mural3:5000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name yourdomain.com;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=pixel:10m rate=1r/5s;
    
    location / {
        proxy_pass http://mural_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    location /api/place-pixel {
        limit_req zone=pixel burst=1 nodelay;
        proxy_pass http://mural_app;
    }
    
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://mural_app;
    }
}
```

## 🔧 Configuration Validation
### Environment Validation Script

```python
#!/usr/bin/env python3
# validate_config.py

import os
import sys
from typing import Dict, Any

def validate_config() -> Dict[str, Any]:
    """Validate configuration and return status."""
    errors = []
    warnings = []
    # Required variables
    required_vars = ['SECRET_KEY']
    for var in required_vars:
        if not os.environ.get(var):
            errors.append(f"Missing required environment variable: {var}")
    
    # Validate numeric values
    numeric_vars = {
        'PORT': (1, 65535),
        'PIXEL_COOLDOWN': (0, 86400),
        'CANVAS_WIDTH': (100, 2000),
        'CANVAS_HEIGHT': (100, 2000)
    }
    
    for var, (min_val, max_val) in numeric_vars.items():
        value = os.environ.get(var)
        if value:
            try:
                num_value = int(value)
                if not (min_val <= num_value <= max_val):
                    warnings.append(f"{var}={num_value} outside recommended range [{min_val}, {max_val}]")
            except ValueError:
                errors.append(f"Invalid numeric value for {var}: {value}")
    
    # Check Redis connectivity
    redis_url = os.environ.get('REDIS_URL')
    if redis_url:
        try:
            import redis
            r = redis.from_url(redis_url)
            r.ping()
        except Exception as e:
            warnings.append(f"Redis connection failed: {e}")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }

if __name__ == '__main__':
    result = validate_config()
    
    if result['errors']:
        print("❌ Configuration errors:")
        for error in result['errors']:
            print(f"  • {error}")
    
    if result['warnings']:
        print("⚠️  Configuration warnings:")
        for warning in result['warnings']:
            print(f"  • {warning}")
    if result['valid']:
        print("✅ Configuration is valid!")
        sys.exit(0)
    else:
        sys.exit(1)
```

### Usage
```bash
# Validate configuration
python validate_config.py

# Load configuration and start app
python app.py
```

---

This configuration guide covers all aspects of customizing and tuning Mural for your specific needs. For deployment-specific configurations, refer to the [Setup Guide](SETUP.md).




















































