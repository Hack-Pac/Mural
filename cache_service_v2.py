"""
Enhanced cache service with tiered caching, compression, and advanced features
"""
import redis
import json
import logging
import gzip
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache
from threading import Lock
import os
import msgpack
import time

logger = logging.getLogger(__name__)
class CacheMetrics:
    """Track cache performance metrics"""
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.response_times = []
        self._lock = Lock()
        self.start_time = time.time()

    def record_hit(self):
        with self._lock:
            self.hits += 1

    def record_miss(self):
        with self._lock:
            self.misses += 1

    def record_set(self):
        with self._lock:
            self.sets += 1
    def record_delete(self):
        with self._lock:
            self.deletes += 1

    def record_error(self):
        with self._lock:
            self.errors += 1

    def record_response_time(self, duration: float):
        with self._lock:
            self.response_times.append(duration)
            # Keep only last 1000 response times
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
    def get_stats(self) -> Dict[str, Any]:
        """Get current cache statistics"""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

            avg_response_time = 0
            if self.response_times:
                avg_response_time = sum(self.response_times) / len(self.response_times)

            uptime = time.time() - self.start_time
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': round(hit_rate, 2),
                'sets': self.sets,
                'deletes': self.deletes,
                'errors': self.errors,
                'total_requests': total_requests,
                'avg_response_time_ms': round(avg_response_time * 1000, 2),
                'uptime_seconds': round(uptime, 2)
            }

class TieredCacheService:
    """
    Tiered caching service with:
    1. L1: In-memory LRU cache (fastest, limited size)
    2. L2: Redis cache (fast, larger capacity)
    3. L3: Disk cache (slowest, largest capacity)
    """
    def __init__(self, redis_url=None, l1_max_size=1000, disk_cache_dir='cache_data'):
        """Initialize tiered cache system"""
        self.metrics = CacheMetrics()
        self.redis_client = None
        self.use_redis = False
        self.l1_max_size = l1_max_size
        self.disk_cache_dir = disk_cache_dir
        self._locks = {}  # Per-key locks for thread safety
        self._global_lock = Lock()
        # L1: In-memory LRU cache
        self._l1_cache = {}
        self._l1_order = []  # Track access order for LRU
        self._l1_lock = Lock()
        # Initialize Redis (L2)
        try:
            redis_url = redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=False,  # We'll handle encoding/decoding
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            # Test connection with timeout
            self.redis_client.ping()
            self.use_redis = True
            logger.info("Redis cache (L2) initialized successfully")
        except Exception as e:
            logger.warning(f"Redis not available for L2 cache: {e}")
            self.use_redis = False
        # Initialize disk cache directory (L3)
        os.makedirs(self.disk_cache_dir, exist_ok=True)
        logger.info(f"Disk cache (L3) initialized at {self.disk_cache_dir}")

    def _get_lock(self, key: str) -> Lock:
        """Get or create a lock for a specific key"""
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = Lock()
            return self._locks[key]

    def _serialize(self, value: Any, compress: bool = True) -> bytes:
        """Serialize and optionally compress data"""
        try:
            # Use msgpack for efficient serialization
            serialized = msgpack.packb(value, use_bin_type=True)

            if compress and len(serialized) > 1000:  # Only compress larger data
                return gzip.compress(serialized, compresslevel=1)  # Fast compression
            return serialized
        except:
            # Fallback to JSON
            serialized = json.dumps(value).encode('utf-8')
            if compress and len(serialized) > 1000:
                return gzip.compress(serialized, compresslevel=1)
            return serialized
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize and decompress data"""
        try:
            # Check if data is gzipped
            if data[:2] == b'\x1f\x8b':  # gzip magic number
                data = gzip.decompress(data)

            # Try msgpack first
            try:
                return msgpack.unpackb(data, raw=False)
            except:
                # Fallback to JSON
                return json.loads(data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            return None
    def _update_l1_lru(self, key: str):
        """Update LRU order for L1 cache"""
        with self._l1_lock:
            if key in self._l1_order:
                self._l1_order.remove(key)
            self._l1_order.append(key)

            # Evict oldest items if cache is full
            while len(self._l1_order) > self.l1_max_size:
                evict_key = self._l1_order.pop(0)
                if evict_key in self._l1_cache:
                    del self._l1_cache[evict_key]
    def _get_disk_path(self, key: str) -> str:
        """Get disk cache file path for a key"""
        # Use hash to avoid filesystem issues with special characters
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.disk_cache_dir, f"{key_hash}.cache")

    def get(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """Get value from cache (checks all tiers)"""
        start_time = time.time()
        lock = self._get_lock(key)
        with lock:
            try:
                # L1: Check in-memory cache
                if key in self._l1_cache:
                    cache_entry = self._l1_cache[key]
                    if isinstance(cache_entry, dict) and 'expires' in cache_entry:
                        if datetime.now() > cache_entry['expires']:
                            del self._l1_cache[key]
                        else:
                            self._update_l1_lru(key)
                            self.metrics.record_hit()
                            self.metrics.record_response_time(time.time() - start_time)
                            return cache_entry['value'] if deserialize else cache_entry['raw']
                    else:
                        self._update_l1_lru(key)
                        self.metrics.record_hit()
                        self.metrics.record_response_time(time.time() - start_time)
                        return cache_entry
                # L2: Check Redis cache
                if self.use_redis:
                    try:
                        raw_data = self.redis_client.get(key)
                        if raw_data:
                            value = self._deserialize(raw_data) if deserialize else raw_data
                            # Promote to L1
                            ttl = self.redis_client.ttl(key)
                            if ttl > 0:
                                expires = datetime.now() + timedelta(seconds=ttl)
                                self._l1_cache[key] = {
                                    'value': value,
                                    'raw': raw_data,
                                    'expires': expires
                                }
                                self._update_l1_lru(key)
                            self.metrics.record_hit()
                            self.metrics.record_response_time(time.time() - start_time)
                            return value
                    except Exception as e:
                        logger.error(f"Redis get error for key {key}: {e}")
                        self.metrics.record_error()

                # L3: Check disk cache
                disk_path = self._get_disk_path(key)
                if os.path.exists(disk_path):
                    try:
                        with open(disk_path, 'rb') as f:
                            cache_data = pickle.load(f)

                        if cache_data['expires'] > datetime.now():
                            raw_data = cache_data['data']
                            value = self._deserialize(raw_data) if deserialize else raw_data
                            # Promote to L1 and L2
                            remaining_ttl = int((cache_data['expires'] - datetime.now()).total_seconds())
                            if remaining_ttl > 0:
                                self._l1_cache[key] = {
                                    'value': value,
                                    'raw': raw_data,
                                    'expires': cache_data['expires']
                                }
                                self._update_l1_lru(key)
                                if self.use_redis:
                                    try:
                                        self.redis_client.setex(key, remaining_ttl, raw_data)
                                    except:
                                        pass
                            self.metrics.record_hit()
                            self.metrics.record_response_time(time.time() - start_time)
                            return value
                        else:
                            # Expired - remove from disk
                            os.remove(disk_path)
                    except Exception as e:
                        logger.error(f"Disk cache read error for key {key}: {e}")
                        self.metrics.record_error()
                self.metrics.record_miss()
                self.metrics.record_response_time(time.time() - start_time)
                return None

            except Exception as e:
                logger.error(f"Cache get error for key {key}: {e}")
                self.metrics.record_error()
                self.metrics.record_response_time(time.time() - start_time)
                return None
    def set(self, key: str, value: Any, expire: int = 3600, compress: bool = True) -> bool:
        """Set value in cache (writes to all tiers)"""
        start_time = time.time()
        lock = self._get_lock(key)
        with lock:
            try:
                # Serialize data
                raw_data = self._serialize(value, compress)
                expires = datetime.now() + timedelta(seconds=expire)

                # L1: Set in memory cache
                self._l1_cache[key] = {
                    'value': value,
                    'raw': raw_data,
                    'expires': expires
                }
                self._update_l1_lru(key)
                # L2: Set in Redis
                if self.use_redis:
                    try:
                        self.redis_client.setex(key, expire, raw_data)
                    except Exception as e:
                        logger.error(f"Redis set error for key {key}: {e}")

                # L3: Set in disk cache (async write for performance)
                disk_path = self._get_disk_path(key)
                cache_data = {
                    'data': raw_data,
                    'expires': expires
                }
                # Write to temporary file first, then rename (atomic operation)
                temp_path = f"{disk_path}.tmp"
                try:
                    with open(temp_path, 'wb') as f:
                        pickle.dump(cache_data, f)
                    os.replace(temp_path, disk_path)
                except Exception as e:
                    logger.error(f"Disk cache write error for key {key}: {e}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                self.metrics.record_set()
                self.metrics.record_response_time(time.time() - start_time)
                return True
            except Exception as e:
                logger.error(f"Cache set error for key {key}: {e}")
                self.metrics.record_error()
                self.metrics.record_response_time(time.time() - start_time)
                return False

    def delete(self, key: str) -> bool:
        """Delete key from all cache tiers"""
        start_time = time.time()
        lock = self._get_lock(key)
        with lock:
            try:
                success = True
                # L1: Remove from memory
                if key in self._l1_cache:
                    del self._l1_cache[key]
                with self._l1_lock:
                    if key in self._l1_order:
                        self._l1_order.remove(key)
                # L2: Remove from Redis
                if self.use_redis:
                    try:
                        self.redis_client.delete(key)
                    except Exception as e:
                        logger.error(f"Redis delete error for key {key}: {e}")
                        success = False
                # L3: Remove from disk
                disk_path = self._get_disk_path(key)
                if os.path.exists(disk_path):
                    try:
                        os.remove(disk_path)
                    except Exception as e:
                        logger.error(f"Disk cache delete error for key {key}: {e}")
                        success = False

                self.metrics.record_delete()
                self.metrics.record_response_time(time.time() - start_time)
                return success
            except Exception as e:
                logger.error(f"Cache delete error for key {key}: {e}")
                self.metrics.record_error()
                self.metrics.record_response_time(time.time() - start_time)
                return False

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys efficiently"""
        result = {}
        # First, check L1 for all keys
        l1_misses = []
        for key in keys:
            if key in self._l1_cache:
                cache_entry = self._l1_cache[key]
                if isinstance(cache_entry, dict) and 'expires' in cache_entry:
                    if datetime.now() <= cache_entry['expires']:
                        result[key] = cache_entry['value']
                        self._update_l1_lru(key)
                        continue
                else:
                    result[key] = cache_entry
                    self._update_l1_lru(key)
                    continue
            l1_misses.append(key)

        # Batch get from Redis for L1 misses
        if l1_misses and self.use_redis:
            try:
                pipe = self.redis_client.pipeline()
                for key in l1_misses:
                    pipe.get(key)
                values = pipe.execute()

                for key, raw_data in zip(l1_misses, values):
                    if raw_data:
                        value = self._deserialize(raw_data)
                        result[key] = value
                        # Promote to L1
                        ttl = self.redis_client.ttl(key)
                        if ttl > 0:
                            expires = datetime.now() + timedelta(seconds=ttl)
                            self._l1_cache[key] = {
                                'value': value,
                                'raw': raw_data,
                                'expires': expires
                            }
                            self._update_l1_lru(key)
            except Exception as e:
                logger.error(f"Redis batch get error: {e}")
        return result

    def set_many(self, items: Dict[str, Any], expire: int = 3600) -> bool:
        """Set multiple keys efficiently"""
        try:
            expires = datetime.now() + timedelta(seconds=expire)

            # Prepare all data
            serialized_items = {}
            for key, value in items.items():
                raw_data = self._serialize(value)
                serialized_items[key] = raw_data
                # Set in L1
                self._l1_cache[key] = {
                    'value': value,
                    'raw': raw_data,
                    'expires': expires
                }
                self._update_l1_lru(key)
            # Batch set in Redis
            if self.use_redis:
                try:
                    pipe = self.redis_client.pipeline()
                    for key, raw_data in serialized_items.items():
                        pipe.setex(key, expire, raw_data)
                    pipe.execute()
                except Exception as e:
                    logger.error(f"Redis batch set error: {e}")
            # Write to disk (can be done asynchronously in production)
            for key, raw_data in serialized_items.items():
                disk_path = self._get_disk_path(key)
                cache_data = {
                    'data': raw_data,
                    'expires': expires
                }
                try:
                    temp_path = f"{disk_path}.tmp"
                    with open(temp_path, 'wb') as f:
                        pickle.dump(cache_data, f)
                    os.replace(temp_path, disk_path)
                except Exception as e:
                    logger.error(f"Disk cache write error for key {key}: {e}")
            return True
        except Exception as e:
            logger.error(f"Batch set error: {e}")
            return False
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Atomic increment operation"""
        lock = self._get_lock(key)
        with lock:
            try:
                if self.use_redis:
                    # Use Redis atomic increment
                    value = self.redis_client.incrby(key, amount)
                    # Update L1
                    self._l1_cache[key] = value
                    self._update_l1_lru(key)
                    return value
                else:
                    # Fallback to get/set
                    current = self.get(key) or 0
                    new_value = current + amount
                    self.set(key, new_value)
                    return new_value
            except Exception as e:
                logger.error(f"Increment error for key {key}: {e}")
                return None
    def clear_expired(self):
        """Clean up expired entries from all tiers"""
        now = datetime.now()

        # Clear L1
        with self._l1_lock:
            expired_keys = [
                key for key, entry in self._l1_cache.items()
                if isinstance(entry, dict) and entry.get('expires', now) < now
            ]
            for key in expired_keys:
                del self._l1_cache[key]
                if key in self._l1_order:
                    self._l1_order.remove(key)

        # Clear L3 (disk)
        try:
            for filename in os.listdir(self.disk_cache_dir):
                if filename.endswith('.cache'):
                    filepath = os.path.join(self.disk_cache_dir, filename)
                    try:
                        with open(filepath, 'rb') as f:
                            cache_data = pickle.load(f)
                        if cache_data['expires'] < now:
                            os.remove(filepath)
                    except:
                        # Remove corrupted cache files
                        os.remove(filepath)
        except Exception as e:
            logger.error(f"Error clearing expired disk cache: {e}")
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        metrics = self.metrics.get_stats()
        # Add tier-specific metrics
        metrics['l1_size'] = len(self._l1_cache)
        metrics['l1_max_size'] = self.l1_max_size
        if self.use_redis:
            try:
                info = self.redis_client.info()
                metrics['l2_used_memory'] = info.get('used_memory_human', 'N/A')
                metrics['l2_connected_clients'] = info.get('connected_clients', 0)
            except:
                pass

        # Disk cache size
        try:
            disk_files = len([f for f in os.listdir(self.disk_cache_dir) if f.endswith('.cache')])
            metrics['l3_files'] = disk_files
        except:
            metrics['l3_files'] = 0

        return metrics
# Global tiered cache instance
tiered_cache = TieredCacheService()

class MuralCacheV2:
    """Enhanced Mural-specific caching with advanced features"""
    # Cache key prefixes
    CANVAS_KEY = "mural:canvas:v2"
    CANVAS_CHUNK_KEY = "mural:canvas:chunk:{chunk_id}"
    USER_PIXELS_KEY = "mural:user_pixels:{user_id}"
    TOTAL_PIXELS_KEY = "mural:total_pixels"
    COOLDOWN_KEY = "mural:cooldown:{user_id}"
    LEADERBOARD_KEY = "mural:leaderboard:{type}"
    PIXEL_HISTORY_KEY = "mural:pixel_history:{x}:{y}"

    # Canvas chunking for better performance
    CHUNK_SIZE = 50  # 50x50 pixel chunks
    @classmethod
    def get_canvas_data(cls, chunk_id: Optional[str] = None) -> Optional[Dict]:
        """Get canvas data (full or specific chunk)"""
        if chunk_id:
            return tiered_cache.get(cls.CANVAS_CHUNK_KEY.format(chunk_id=chunk_id))
        return tiered_cache.get(cls.CANVAS_KEY)
    @classmethod
    def set_canvas_data(cls, canvas_data: Dict, expire: int = 60) -> bool:
        """Set canvas data with intelligent chunking"""
        # Store full canvas
        success = tiered_cache.set(cls.CANVAS_KEY, canvas_data, expire)
        # Also store in chunks for partial updates
        chunks = cls._chunk_canvas(canvas_data)
        chunk_items = {
            cls.CANVAS_CHUNK_KEY.format(chunk_id=chunk_id): chunk_data
            for chunk_id, chunk_data in chunks.items()
        }
        if chunk_items:
            tiered_cache.set_many(chunk_items, expire)

        return success
    @classmethod
    def _chunk_canvas(cls, canvas_data: Dict) -> Dict[str, Dict]:
        """Split canvas into chunks for efficient updates"""
        chunks = {}
        for pixel_key, pixel_data in canvas_data.items():
            x, y = map(int, pixel_key.split(','))
            chunk_x = x // cls.CHUNK_SIZE
            chunk_y = y // cls.CHUNK_SIZE
            chunk_id = f"{chunk_x}_{chunk_y}"
            if chunk_id not in chunks:
                chunks[chunk_id] = {}
            chunks[chunk_id][pixel_key] = pixel_data
        return chunks

    @classmethod
    def update_pixel(cls, x: int, y: int, pixel_data: Dict) -> bool:
        """Update a single pixel efficiently"""
        pixel_key = f"{x},{y}"
        # Update chunk
        chunk_x = x // cls.CHUNK_SIZE
        chunk_y = y // cls.CHUNK_SIZE
        chunk_id = f"{chunk_x}_{chunk_y}"
        chunk_key = cls.CANVAS_CHUNK_KEY.format(chunk_id=chunk_id)

        # Get or create chunk
        chunk = tiered_cache.get(chunk_key) or {}
        old_pixel = chunk.get(pixel_key, {})
        chunk[pixel_key] = pixel_data

        # Update chunk cache
        tiered_cache.set(chunk_key, chunk, expire=300)  # 5 min expiry for chunks

        # Update pixel history
        history_key = cls.PIXEL_HISTORY_KEY.format(x=x, y=y)
        history = tiered_cache.get(history_key) or []
        history.append({
            'timestamp': pixel_data.get('timestamp'),
            'color': pixel_data.get('color'),
            'user_id': pixel_data.get('user_id')
        })
        # Keep last 10 changes
        history = history[-10:]
        tiered_cache.set(history_key, history, expire=86400)  # 24 hour expiry

        # Update user pixel counts
        new_user_id = pixel_data.get('user_id')
        old_user_id = old_pixel.get('user_id')
        if old_user_id and old_user_id != new_user_id:
            tiered_cache.increment(cls.USER_PIXELS_KEY.format(user_id=old_user_id), -1)

        if new_user_id:
            tiered_cache.increment(cls.USER_PIXELS_KEY.format(user_id=new_user_id), 1)

        if not old_pixel:
            tiered_cache.increment(cls.TOTAL_PIXELS_KEY, 1)
        # Invalidate full canvas cache
        tiered_cache.delete(cls.CANVAS_KEY)

        return True

    @classmethod
    def get_pixel_history(cls, x: int, y: int) -> List[Dict]:
        """Get history of changes for a specific pixel"""
        history_key = cls.PIXEL_HISTORY_KEY.format(x=x, y=y)
        return tiered_cache.get(history_key) or []

    @classmethod
    def get_leaderboard(cls, leaderboard_type: str = 'pixels') -> Optional[List]:
        """Get cached leaderboard data"""
        return tiered_cache.get(cls.LEADERBOARD_KEY.format(type=leaderboard_type))
    @classmethod
    def set_leaderboard(cls, leaderboard_type: str, data: List, expire: int = 300) -> bool:
        """Cache leaderboard data"""
        return tiered_cache.set(cls.LEADERBOARD_KEY.format(type=leaderboard_type), data, expire)

    @classmethod
    def warm_cache(cls, canvas_data: Dict):
        """Pre-warm cache with canvas data"""
        logger.info("Warming cache with canvas data...")
        # Set full canvas
        cls.set_canvas_data(canvas_data, expire=3600)  # 1 hour
        # Calculate and cache statistics
        user_pixel_counts = {}
        for pixel_data in canvas_data.values():
            user_id = pixel_data.get('user_id')
            if user_id and user_id != 'system':
                user_pixel_counts[user_id] = user_pixel_counts.get(user_id, 0) + 1
        # Set user pixel counts
        for user_id, count in user_pixel_counts.items():
            tiered_cache.set(cls.USER_PIXELS_KEY.format(user_id=user_id), count, expire=3600)
        # Set total pixel count
        tiered_cache.set(cls.TOTAL_PIXELS_KEY, len(canvas_data), expire=3600)
        # Generate and cache leaderboard
        leaderboard = sorted(
            [(user_id, count) for user_id, count in user_pixel_counts.items()],
            key=lambda x: x[1],
            reverse=True
        )[:100]  # Top 100 users
        cls.set_leaderboard('pixels', leaderboard, expire=600)  # 10 min

        logger.info(f"Cache warmed: {len(canvas_data)} pixels, {len(user_pixel_counts)} users")

    @classmethod
    def get_cache_metrics(cls) -> Dict[str, Any]:
        """Get comprehensive cache metrics"""
        return tiered_cache.get_metrics()


# Extended cache service utilities

class CacheWarmer:
    """Warm cache with frequently accessed data"""
    
    def __init__(self, cache_service):
        self.cache = cache_service
        self.warmup_strategies = {
            'aggressive': self._aggressive_warmup,
            'progressive': self._progressive_warmup,
            'lazy': self._lazy_warmup
        }
    
    def warmup(self, strategy: str = 'progressive'):
        """Warm up the cache using specified strategy"""
        warmup_func = self.warmup_strategies.get(strategy, self._progressive_warmup)
        return warmup_func()
    
    def _aggressive_warmup(self):
        """Load all possible data into cache immediately"""
        logger.info("Starting aggressive cache warmup")
        loaded = 0
        
        # Load all canvas data
        canvas_data = self._load_all_canvas_data()
        for key, value in canvas_data.items():
            self.cache.set(f"canvas:{key}", value)
            loaded += 1
        
        # Load all user data
        user_data = self._load_all_user_data()
        for key, value in user_data.items():
            self.cache.set(f"user:{key}", value)
            loaded += 1
        
        logger.info(f"Aggressive warmup complete: {loaded} items loaded")
        return loaded
    
    def _progressive_warmup(self):
        """Load data progressively based on access patterns"""
        logger.info("Starting progressive cache warmup")
        loaded = 0
        
        # Load most frequently accessed data first
        access_patterns = self._get_access_patterns()
        
        for pattern in access_patterns[:100]:  # Top 100 items
            key = pattern['key']
            data = self._load_data(key)
            if data:
                self.cache.set(key, data)
                loaded += 1
        
        logger.info(f"Progressive warmup complete: {loaded} items loaded")
        return loaded
    
    def _lazy_warmup(self):
        """Minimal warmup, load on demand"""
        logger.info("Lazy warmup - minimal preloading")
        # Only load critical data
        self.cache.set("canvas:metadata", self._get_canvas_metadata())
        return 1
    
    def _load_all_canvas_data(self):
        """Load all canvas data from storage"""
        # Implementation depends on storage backend
        return {}
    
    def _load_all_user_data(self):
        """Load all user data from storage"""
        # Implementation depends on storage backend
        return {}
    
    def _get_access_patterns(self):
        """Get data access patterns"""
        # Implementation depends on monitoring system
        return []
    
    def _load_data(self, key: str):
        """Load specific data by key"""
        # Implementation depends on storage backend
        return None
    
    def _get_canvas_metadata(self):
        """Get canvas metadata"""
        return {
            'version': 1,
            'last_updated': datetime.now().isoformat(),
            'pixel_count': 0
        }

class CacheAnalyzer:
    """Analyze cache performance and usage"""
    
    def __init__(self, cache_service):
        self.cache = cache_service
        self.analysis_history = []
    
    def analyze(self):
        """Perform comprehensive cache analysis"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'hit_rate': self._calculate_hit_rate(),
            'memory_usage': self._get_memory_usage(),
            'key_distribution': self._analyze_key_distribution(),
            'recommendations': self._generate_recommendations()
        }
        
        self.analysis_history.append(analysis)
        return analysis
    
    def _calculate_hit_rate(self):
        """Calculate cache hit rate"""
        stats = self.cache.get_stats()
        hits = stats.get('hits', 0)
        misses = stats.get('misses', 0)
        total = hits + misses
        
        return hits / total if total > 0 else 0
    
    def _get_memory_usage(self):
        """Get cache memory usage"""
        return self.cache.get_memory_usage()
    
    def _analyze_key_distribution(self):
        """Analyze distribution of cache keys"""
        keys = self.cache.get_all_keys()
        distribution = defaultdict(int)
        
        for key in keys:
            prefix = key.split(':')[0]
            distribution[prefix] += 1
        
        return dict(distribution)
    
    def _generate_recommendations(self):
        """Generate cache optimization recommendations"""
        recommendations = []
        
        hit_rate = self._calculate_hit_rate()
        if hit_rate < 0.8:
            recommendations.append("Consider increasing cache size")
        
        memory_usage = self._get_memory_usage()
        if memory_usage > 0.9:
            recommendations.append("Cache is near capacity, consider cleanup")
        
        return recommendations
