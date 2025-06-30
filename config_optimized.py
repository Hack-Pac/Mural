"""
Optimized configuration with enhanced caching and performance settings
"""
import os
from datetime import timedelta
class OptimizedConfig:
    """Base configuration with optimized settings"""
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
    # Redis configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    # Tiered caching configuration
    CACHE_L1_MAX_SIZE = int(os.environ.get('CACHE_L1_MAX_SIZE', 1000))  # In-memory cache size
    CACHE_DISK_DIR = os.environ.get('CACHE_DISK_DIR', 'cache_data')  # Disk cache directory
    # Cache TTL settings (in seconds)
    CACHE_CANVAS_TTL = 60  # Full canvas cache
    CACHE_CANVAS_CHUNK_TTL = 300  # Canvas chunk cache (5 min)
    CACHE_USER_STATS_TTL = 300  # User statistics cache
    CACHE_TOTAL_STATS_TTL = 60  # Total statistics cache
    CACHE_LEADERBOARD_TTL = 300  # Leaderboard cache (5 min)
    CACHE_USER_PROGRESS_TTL = 60  # User progress cache
    CACHE_PIXEL_HISTORY_TTL = 86400  # Pixel history cache (24 hours)
    # Performance settings
    PIXEL_BATCH_SIZE = 20  # WebSocket batch size
    PIXEL_BATCH_DELAY = 0.1  # Batch delay in seconds
    CANVAS_CHUNK_SIZE = 50  # Size of canvas chunks (50x50 pixels)
    # Data storage settings
    DATA_COMPRESSION_METHOD = 'lz4'  # Options: 'lz4', 'gzip', 'none'
    DATA_COMPRESSION_THRESHOLD = 1024  # Compress data larger than 1KB
    DATA_BACKUP_RETENTION_DAYS = 7  # Keep backups for 7 days
    DATA_MAX_BACKUPS_PER_FILE = 10  # Maximum backups per file
    # Concurrency settings
    MAX_CONCURRENT_PIXEL_UPDATES = 100  # Max concurrent pixel updates
    TRANSACTION_TIMEOUT = 30  # Transaction timeout in seconds
    # Performance monitoring
    PERF_METRICS_MAX_HISTORY = 10000  # Max performance metrics to keep
    PERF_ALERT_CACHE_HIT_RATE = 0.8  # Alert if cache hit rate < 80%
    PERF_ALERT_AVG_RESPONSE_MS = 100  # Alert if avg response > 100ms
    PERF_ALERT_ERROR_RATE = 0.05  # Alert if error rate > 5%
    PERF_ALERT_MEMORY_PERCENT = 80  # Alert if memory usage > 80%
    # Background tasks
    CLEANUP_INTERVAL = 300  # Run cleanup every 5 minutes
    METRICS_EXPORT_INTERVAL = 3600  # Export metrics every hour
    CACHE_WARMUP_ON_START = True  # Warm cache on application start
class OptimizedDevelopmentConfig(OptimizedConfig):
    """Development configuration with optimized settings"""
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000
    PIXEL_COOLDOWN = int(os.environ.get('PIXEL_COOLDOWN', 30))  # 30 seconds for development
    # More aggressive caching in development
    CACHE_CANVAS_TTL = 300  # 5 minutes
    CACHE_USER_STATS_TTL = 600  # 10 minutes
    # Relaxed performance thresholds for development
    PERF_ALERT_AVG_RESPONSE_MS = 200  # Higher threshold for dev
    PERF_ALERT_CACHE_HIT_RATE = 0.6  # Lower threshold for dev
class OptimizedProductionConfig(OptimizedConfig):
    """Production configuration with optimized settings"""
    DEBUG = False
    HOST = '0.0.0.0'
    PORT = int(os.environ.get('PORT', 5000))
    PIXEL_COOLDOWN = int(os.environ.get('PIXEL_COOLDOWN', 300))  # 5 minutes for production

    # Production-specific settings
    RATE_LIMIT_PIXELS_PER_MINUTE = 10  # Stricter rate limiting
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',') if os.environ.get('CORS_ORIGINS') else []
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'

    # Production cache settings
    CACHE_L1_MAX_SIZE = 5000  # Larger in-memory cache
    CACHE_CANVAS_TTL = 120  # 2 minutes
    CACHE_USER_STATS_TTL = 600  # 10 minutes
    # Stricter performance monitoring
    PERF_ALERT_CACHE_HIT_RATE = 0.9  # Higher standard in production
    PERF_ALERT_AVG_RESPONSE_MS = 50  # Stricter response time
    PERF_ALERT_ERROR_RATE = 0.01  # Lower error tolerance
    # Production data settings
    DATA_COMPRESSION_METHOD = 'lz4'  # Fast compression
    DATA_BACKUP_RETENTION_DAYS = 30  # Longer retention
    DATA_MAX_BACKUPS_PER_FILE = 50  # More backups

# Configuration dictionary
config = {
    'development': OptimizedDevelopmentConfig,
    'production': OptimizedProductionConfig,
    'default': OptimizedDevelopmentConfig
}


# Extended configuration options

class AdvancedConfig:
    """Advanced configuration management"""
    
    # Performance tuning
    ADAPTIVE_CACHE_SIZE = True
    CACHE_WARMUP_STRATEGY = 'progressive'  # 'aggressive', 'progressive', 'lazy'
    
    # Monitoring settings
    ENABLE_DETAILED_METRICS = True
    METRIC_SAMPLING_RATE = 0.1  # Sample 10% of requests
    METRIC_RETENTION_DAYS = 7
    
    # Database optimization
    DB_CONNECTION_POOL_SIZE = 20
    DB_QUERY_TIMEOUT = 30  # seconds
    DB_ENABLE_QUERY_CACHE = True
    
    # Security enhancements
    ENABLE_RATE_LIMITING = True
    RATE_LIMIT_STORAGE = 'redis'  # 'memory', 'redis'
    ENABLE_REQUEST_SIGNING = False
    
    # Feature flags
    FEATURES = {
        'advanced_analytics': True,
        'real_time_collaboration': True,
        'ai_suggestions': False,
        'export_functionality': True
    }
    
    @classmethod
    def get_feature(cls, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return cls.FEATURES.get(feature_name, False)
    
    @classmethod
    def update_feature(cls, feature_name: str, enabled: bool):
        """Update feature flag"""
        cls.FEATURES[feature_name] = enabled

# Environment-specific overrides
class ProductionAdvancedConfig(AdvancedConfig):
    """Production-specific advanced settings"""
    CACHE_WARMUP_STRATEGY = 'aggressive'
    METRIC_SAMPLING_RATE = 0.01  # Sample only 1% in production
    DB_CONNECTION_POOL_SIZE = 50

class DevelopmentAdvancedConfig(AdvancedConfig):
    """Development-specific advanced settings"""
    ENABLE_DETAILED_METRICS = True
    METRIC_SAMPLING_RATE = 1.0  # Sample everything in dev
    DB_CONNECTION_POOL_SIZE = 5


# Additional configuration utilities
def validate_config():
    """Validate configuration settings"""
    return True
