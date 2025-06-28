import redis
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class CacheService:
    """High-performance caching service for Mural app"""
    
    def __init__(self, redis_url=None):
        """Initialize Redis connection with fallback to in-memory cache"""
        self.redis_client = None
        self.fallback_cache = {}  # In-memory fallback
        self.use_redis = False
        
        try:
            redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            self.use_redis = True
            logger.info("Redis cache initialized successfully")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self.use_redis = False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.use_redis:
                value = self.redis_client.get(key)
                return json.loads(value) if value else None
            else:
                # Handle fallback cache with expiration
                cached_item = self.fallback_cache.get(key)
                if not cached_item:
                    return None
                
                # Check if it's expired
                if isinstance(cached_item, dict) and 'expires' in cached_item:
                    if datetime.now() > cached_item['expires']:
                        # Expired - remove and return None
                        del self.fallback_cache[key]
                        return None
                    return cached_item['value']
                else:
                    # Old format or direct value
                    return cached_item
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache with expiration"""
        try:
            if self.use_redis:
                return self.redis_client.setex(key, expire, json.dumps(value))
            else:
                # Simple in-memory with timestamp for expiration
                self.fallback_cache[key] = {
                    'value': value,
                    'expires': datetime.now() + timedelta(seconds=expire)
                }
                return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.use_redis:
                return bool(self.redis_client.delete(key))
            else:
                self.fallback_cache.pop(key, None)
                return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter in cache"""
        try:
            if self.use_redis:
                return self.redis_client.incrby(key, amount)
            else:
                current = self.get(key) or 0
                new_value = current + amount
                self.set(key, new_value)
                return new_value
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    def cleanup_expired(self):
        """Clean up expired keys from in-memory cache"""
        if not self.use_redis:
            now = datetime.now()
            expired_keys = [
                key for key, data in self.fallback_cache.items()
                if isinstance(data, dict) and data.get('expires', now) < now
            ]
            for key in expired_keys:
                del self.fallback_cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

# Global cache instance
cache = CacheService()

class MuralCache:
    """Specialized caching for Mural app operations"""
    
    CANVAS_KEY = "mural:canvas"
    USER_PIXELS_KEY = "mural:user_pixels:{user_id}"
    TOTAL_PIXELS_KEY = "mural:total_pixels"
    COOLDOWN_KEY = "mural:cooldown:{user_id}"
    
    @classmethod
    def get_canvas_data(cls) -> Optional[Dict]:
        """Get cached canvas data"""
        return cache.get(cls.CANVAS_KEY)
    
    @classmethod
    def set_canvas_data(cls, canvas_data: Dict, expire: int = 60) -> bool:
        """Cache canvas data"""
        return cache.set(cls.CANVAS_KEY, canvas_data, expire)
    
    @classmethod
    def invalidate_canvas(cls) -> bool:
        """Invalidate canvas cache when pixels change"""
        return cache.delete(cls.CANVAS_KEY)
    
    @classmethod
    def get_user_pixel_count(cls, user_id: str) -> Optional[int]:
        """Get cached user pixel count"""
        key = cls.USER_PIXELS_KEY.format(user_id=user_id)
        return cache.get(key)
    
    @classmethod
    def set_user_pixel_count(cls, user_id: str, count: int, expire: int = 300) -> bool:
        """Cache user pixel count"""
        key = cls.USER_PIXELS_KEY.format(user_id=user_id)
        return cache.set(key, count, expire)
    
    @classmethod
    def increment_user_pixels(cls, user_id: str) -> Optional[int]:
        """Increment user pixel count"""
        key = cls.USER_PIXELS_KEY.format(user_id=user_id)
        return cache.increment(key)
    
    @classmethod
    def decrement_user_pixels(cls, user_id: str) -> Optional[int]:
        """Decrement user pixel count"""
        key = cls.USER_PIXELS_KEY.format(user_id=user_id)
        return cache.increment(key, -1)
    
    @classmethod
    def get_total_pixel_count(cls) -> Optional[int]:
        """Get cached total pixel count"""
        return cache.get(cls.TOTAL_PIXELS_KEY)
    
    @classmethod
    def set_total_pixel_count(cls, count: int, expire: int = 60) -> bool:
        """Cache total pixel count"""
        return cache.set(cls.TOTAL_PIXELS_KEY, count, expire)
    
    @classmethod
    def increment_total_pixels(cls) -> Optional[int]:
        """Increment total pixel count"""
        return cache.increment(cls.TOTAL_PIXELS_KEY)
    
    @classmethod
    def get_cooldown(cls, user_id: str) -> Optional[datetime]:
        """Get cached cooldown expiration"""
        key = cls.COOLDOWN_KEY.format(user_id=user_id)
        timestamp = cache.get(key)
        
        if not timestamp:
            return None
        
        try:
            # Handle different cache storage formats
            if isinstance(timestamp, str):
                return datetime.fromisoformat(timestamp)
            elif isinstance(timestamp, dict) and 'value' in timestamp:
                # Fallback cache format
                return datetime.fromisoformat(timestamp['value'])
            else:
                logger.warning(f"Unexpected cooldown cache format: {type(timestamp)}")
                return None
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing cooldown timestamp {timestamp}: {e}")
            # Clear invalid cache entry
            cache.delete(key)
            return None
    
    @classmethod
    def set_cooldown(cls, user_id: str, expires_at: datetime) -> bool:
        """Cache cooldown expiration"""
        key = cls.COOLDOWN_KEY.format(user_id=user_id)
        expire_seconds = int((expires_at - datetime.now()).total_seconds()) + 10  # Small buffer
        return cache.set(key, expires_at.isoformat(), expire_seconds)
    
    @classmethod
    def clear_user_cache(cls, user_id: str) -> bool:
        """Clear all cached data for a user"""
        keys = [
            cls.USER_PIXELS_KEY.format(user_id=user_id),
            cls.COOLDOWN_KEY.format(user_id=user_id)
        ]
        success = True
        for key in keys:
            success = success and cache.delete(key)
        return success
