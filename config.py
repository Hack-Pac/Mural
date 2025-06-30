import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
    # Security configuration
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # CSRF token doesn't expire
    
    # SocketIO configuration
    SOCKETIO_ASYNC_MODE = 'threading'
    
    # Canvas configuration
    CANVAS_WIDTH = 500
    CANVAS_HEIGHT = 500
    
    # Cooldown configuration (in seconds)
    PIXEL_COOLDOWN = int(os.environ.get('PIXEL_COOLDOWN', 300))  # 5 minutes default
    
    # Rate limiting (pixels per minute per user)
    RATE_LIMIT_PIXELS_PER_MINUTE = 60
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_TYPE = 'filesystem'  # Use server-side sessions
    
    # CORS settings
    CORS_ORIGINS = ["*"]  # Change this in production to specific domains
    
    # Caching configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_CANVAS_TTL = 60  # Canvas cache TTL in seconds
    CACHE_USER_STATS_TTL = 300  # User stats cache TTL in seconds
    CACHE_TOTAL_STATS_TTL = 60  # Total stats cache TTL in seconds

class DevelopmentConfig(Config):
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000
    PIXEL_COOLDOWN = int(os.environ.get('PIXEL_COOLDOWN', 30))  # 30 seconds for development

class ProductionConfig(Config):
    DEBUG = False
    HOST = '0.0.0.0'
    PORT = int(os.environ.get('PORT', 5000))
    PIXEL_COOLDOWN = int(os.environ.get('PIXEL_COOLDOWN', 300))  # 5 minutes for production
    
    # Production-specific settings
    RATE_LIMIT_PIXELS_PER_MINUTE = 10  # Stricter rate limiting
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else []  # Whitelist specific domains
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
