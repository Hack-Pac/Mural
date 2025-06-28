import os
from datetime import timedelta

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    
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
    PIXEL_COOLDOWN = int(os.environ.get('PIXEL_COOLDOWN', 60))  # 1 minute for development

class ProductionConfig(Config):
    DEBUG = False
    HOST = '0.0.0.0'
    PORT = int(os.environ.get('PORT', 5000))
    PIXEL_COOLDOWN = int(os.environ.get('PIXEL_COOLDOWN', 300))  # 5 minutes for production
    
    # Production-specific settings
    RATE_LIMIT_PIXELS_PER_MINUTE = 10  # Stricter rate limiting
    CORS_ORIGINS = []  # Add your production domains

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
