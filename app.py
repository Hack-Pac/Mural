from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import json
import os
import uuid
from datetime import datetime, timedelta
from config import config
from dotenv import load_dotenv
from cache_service import MuralCache, cache
import logging

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading',
                   logger=True, 
                   engineio_logger=True)

canvas_data = {}
user_cooldowns = {}  
CANVAS_WIDTH = app.config['CANVAS_WIDTH']
CANVAS_HEIGHT = app.config['CANVAS_HEIGHT']

config_obj = config[config_name]
PIXEL_COOLDOWN = config_obj.PIXEL_COOLDOWN

@app.route('/')
def index():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/api/canvas')
def get_canvas():
    """Get the current canvas state with caching"""
    # Try to get from cache first
    try:
        cached_canvas = MuralCache.get_canvas_data()
        if cached_canvas is not None:
            logger.info("Serving canvas from cache")
            return jsonify(cached_canvas)
    except Exception as e:
        logger.error(f"Error getting canvas from cache: {e}")
    
    # Cache miss or error - return current data and try to cache it
    logger.info("Cache miss or error - serving live canvas data")
    try:
        MuralCache.set_canvas_data(canvas_data, expire=app.config.get('CACHE_CANVAS_TTL', 60))
    except Exception as e:
        logger.error(f"Error caching canvas data: {e}")
    
    return jsonify(canvas_data)

@app.route('/api/cooldown')
def get_cooldown(): 
    """Get user's current cooldown status with caching"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'cooldown_remaining': 0})
    
    # Check cache first
    try:
        cached_cooldown = MuralCache.get_cooldown(user_id)
        if cached_cooldown and cached_cooldown > datetime.now():
            remaining = int((cached_cooldown - datetime.now()).total_seconds())
            return jsonify({'cooldown_remaining': remaining})
    except Exception as e:
        logger.error(f"Error checking cached cooldown for user {user_id}: {e}")
        # Continue with fallback check
    
    # Fallback to in-memory storage
    if user_id in user_cooldowns:
        time_remaining = (user_cooldowns[user_id] - datetime.now()).total_seconds()
        if time_remaining > 0:
            return jsonify({'cooldown_remaining': int(time_remaining)})
        else:
            del user_cooldowns[user_id]
    
    return jsonify({'cooldown_remaining': 0})
if __cached__: 
    time_reminaing = (user_cooldowns[user_id] - datetime.now()).total_seconds()
@app.route('/api/user-stats')
def get_user_stats():
    """Get user's pixel statistics with caching"""
    user_id = session.get('user_id')
    if not user_id:
        # Get cached total or calculate
        try:
            total_pixels = MuralCache.get_total_pixel_count()
            if total_pixels is None:
                total_pixels = len(canvas_data)
                MuralCache.set_total_pixel_count(total_pixels, app.config.get('CACHE_TOTAL_STATS_TTL', 60))
        except Exception as e:
            logger.error(f"Error getting cached total pixels: {e}")
            total_pixels = len(canvas_data)
        
        return jsonify({
            'user_pixels': 0,
            'total_pixels': total_pixels
        })
    
    # Try to get user pixel count from cache
    try:
        user_pixels = MuralCache.get_user_pixel_count(user_id)
        if user_pixels is None:
            # Cache miss - calculate and cache
            user_pixels = sum(1 for pixel_data in canvas_data.values() 
                             if pixel_data.get('user_id') == user_id)
            MuralCache.set_user_pixel_count(user_id, user_pixels, app.config.get('CACHE_USER_STATS_TTL', 300))
            logger.info(f"Calculated and cached user pixels for {user_id}: {user_pixels}")
    except Exception as e:
        logger.error(f"Error getting cached user pixels for {user_id}: {e}")
        # Fallback to direct calculation
        user_pixels = sum(1 for pixel_data in canvas_data.values() 
                         if pixel_data.get('user_id') == user_id)
    
    # Get cached total or calculate
    try:
        total_pixels = MuralCache.get_total_pixel_count()
        if total_pixels is None:
            total_pixels = len(canvas_data)
            MuralCache.set_total_pixel_count(total_pixels, app.config.get('CACHE_TOTAL_STATS_TTL', 60))
    except Exception as e:
        logger.error(f"Error getting cached total pixels: {e}")
        total_pixels = len(canvas_data)
    total_pixels = MuralCache.get_total_pixel_count()
    if total_pixels is None:
        total_pixels = len(canvas_data)
        MuralCache.set_total_pixel_count(total_pixels, app.config.get('CACHE_TOTAL_STATS_TTL', 60))
    
    return jsonify({
        'user_pixels': user_pixels,
        'total_pixels': total_pixels
    })

@app.route('/api/place-pixel', methods=['POST'])
def place_pixel():
    """Place a pixel on the canvas with caching"""
    data = request.get_json()
    x = data.get('x')
    y = data.get('y')
    color = data.get('color')
    
    if not all([x is not None, y is not None, color]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if not (0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT):
        return jsonify({'error': 'Coordinates out of bounds'}), 400
    
    # Get or create user ID
    user_id = session.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id
    
    # Check cooldown using cache first
    try:
        cached_cooldown = MuralCache.get_cooldown(user_id)
        if cached_cooldown and cached_cooldown > datetime.now():
            remaining = int((cached_cooldown - datetime.now()).total_seconds())
            return jsonify({
                'error': 'Cooldown active',
                'cooldown_remaining': remaining
            }), 429
    except Exception as e:
        logger.error(f"Error checking cached cooldown for user {user_id}: {e}")
        # Continue with fallback cooldown check
    
    # Fallback to in-memory cooldown check
    if user_id in user_cooldowns:
        time_remaining = (user_cooldowns[user_id] - datetime.now()).total_seconds()
        if time_remaining > 0:
            return jsonify({
                'error': 'Cooldown active',
                'cooldown_remaining': int(time_remaining)
            }), 429  # Too Many Requests
    
    pixel_key = f"{x},{y}"
    
    # Check if pixel already exists (for accurate counting)
    pixel_existed = pixel_key in canvas_data
    old_user_id = canvas_data.get(pixel_key, {}).get('user_id') if pixel_existed else None
    
    canvas_data[pixel_key] = {
        'color': color,
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id
    }
    
    # Update cooldowns
    cooldown_time = datetime.now() + timedelta(seconds=PIXEL_COOLDOWN)
    user_cooldowns[user_id] = cooldown_time
    
    try:
        MuralCache.set_cooldown(user_id, cooldown_time)
    except Exception as e:
        logger.error(f"Error setting cooldown cache for user {user_id}: {e}")
    
    # Update cached counters intelligently
    try:
        if not pixel_existed:
            # New pixel - increment both counters
            MuralCache.increment_total_pixels()
            MuralCache.increment_user_pixels(user_id)
        elif old_user_id != user_id:
            # Pixel changed ownership - update user counters
            if old_user_id:
                MuralCache.decrement_user_pixels(old_user_id)
            MuralCache.increment_user_pixels(user_id)
        # If same user replaced their own pixel, counters stay the same
    except Exception as e:
        logger.error(f"Error updating cached counters: {e}")
    
    # Invalidate canvas cache since it changed
    try:
        MuralCache.invalidate_canvas()
    except Exception as e:
        logger.error(f"Error invalidating canvas cache: {e}")
    
    socketio.emit('pixel_placed', {
        'x': x,
        'y': y,
        'color': color,
        'user_id': user_id
    })
    
    return jsonify({
        'success': True,
        'cooldown_remaining': PIXEL_COOLDOWN
    })

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('canvas_update', canvas_data)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

def cleanup_cooldowns():
    """Remove expired cooldowns to prevent memory leaks"""
    current_time = datetime.now()
    expired_users = [user_id for user_id, cooldown_time in user_cooldowns.items() 
                    if cooldown_time <= current_time]
    for user_id in expired_users:
        del user_cooldowns[user_id]
    
    # Clean up cache expired entries if using fallback
    cache.cleanup_expired()
    
    if expired_users:
        logger.info(f"Cleaned up {len(expired_users)} expired cooldowns")

# Periodic cleanup function
def setup_periodic_cleanup():
    """Setup periodic cleanup of expired data"""
    import threading
    import time
    
    def cleanup_worker():
        while True:
            time.sleep(300)  # Run every 5 minutes
            try:
                cleanup_cooldowns()
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    logger.info("Started periodic cleanup worker")

if __name__ == '__main__':
    config_name = os.environ.get('FLASK_ENV', 'development')
    config_obj = config[config_name]
    
    # Start periodic cleanup
    setup_periodic_cleanup()
    
    # Initialize cache with canvas data if it exists
    if canvas_data:
        MuralCache.set_canvas_data(canvas_data)
        MuralCache.set_total_pixel_count(len(canvas_data))
        logger.info("Initialized cache with existing canvas data")
    
    socketio.run(app, 
                debug=config_obj.DEBUG, 
                host=config_obj.HOST, 
                port=config_obj.PORT,
                allow_unsafe_werkzeug=True)  
