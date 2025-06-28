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
