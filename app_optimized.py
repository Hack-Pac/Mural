"""
Optimized version of app.py with enhanced caching and database performance
"""
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import json
import os
import uuid
from datetime import datetime, timedelta
from config import config
from dotenv import load_dotenv
import logging
from user_data import user_data_manager
from challenges import challenge_manager
from shop import shop
from functools import wraps
import hashlib
import asyncio
from concurrent.futures import ThreadPoolExecutor
# Import optimized components
from cache_service_v2 import tiered_cache, MuralCacheV2
from data_storage import storage, delta_storage
from concurrency_manager import ConcurrentCanvasManager, ConcurrentUserDataManager
from performance_monitor import performance_monitor, monitor_performance

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

# Initialize optimized components
canvas_manager = ConcurrentCanvasManager(storage)
user_manager = ConcurrentUserDataManager(storage)
thread_pool = ThreadPoolExecutor(max_workers=10)

# Global data structures (kept for compatibility)
canvas_data = {}
user_cooldowns = {}
connected_users = set()
CANVAS_WIDTH = app.config['CANVAS_WIDTH']
CANVAS_HEIGHT = app.config['CANVAS_HEIGHT']
# Message batching for WebSocket
pixel_update_queue = []
pixel_batch_timer = None
PIXEL_BATCH_SIZE = 20
PIXEL_BATCH_DELAY = 0.1  # 100ms
config_obj = config[config_name]
PIXEL_COOLDOWN = app.config['PIXEL_COOLDOWN']
# Enhanced rate limiting with caching
rate_limit_data = {}

def rate_limit(max_requests=60, window_seconds=60):
    def decorator(f):
        @wraps(f)
        @monitor_performance(f"rate_limit.{f.__name__}")
        def wrapped(*args, **kwargs):
            user_id = session.get('user_id', request.remote_addr)
            rate_key = f"rate_limit:{user_id}:{f.__name__}"
            # Try to get from cache first
            rate_info = tiered_cache.get(rate_key)
            if rate_info:
                if rate_info['count'] >= max_requests:
                    return jsonify({'error': 'Rate limit exceeded'}), 429
                rate_info['count'] += 1
                tiered_cache.set(rate_key, rate_info, expire=window_seconds)
            else:
                # Initialize rate limit
                rate_info = {
                    'count': 1,
                    'window_start': datetime.now().isoformat()
                }
                tiered_cache.set(rate_key, rate_info, expire=window_seconds)

            return f(*args, **kwargs)
        return wrapped
    return decorator
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "font-src 'self' data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none';"
    )
    # Other security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # HSTS for production
    if app.config.get('SESSION_COOKIE_SECURE'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response
@app.route('/')
def index():
    if 'user_id' not in session:
        # Generate a new user ID server-side
        session['user_id'] = str(uuid.uuid4())
        session['created_at'] = datetime.now().isoformat()
        session.permanent = True  # Use permanent session with configured lifetime
    else:
        # Validate existing session
        if 'created_at' not in session:
            # Regenerate session if it's missing metadata
            session.clear()
            session['user_id'] = str(uuid.uuid4())
            session['created_at'] = datetime.now().isoformat()
            session.permanent = True
    return render_template('index.html')
@app.route('/favicon.ico')
def favicon():
    return '', 204
@app.route('/api/canvas')
@rate_limit(max_requests=120, window_seconds=60)
@monitor_performance('api.get_canvas')
def get_canvas():
    """Get the current canvas state with enhanced caching"""
    try:
        # Check request headers for chunk support
        supports_chunks = request.headers.get('X-Canvas-Chunks', 'false').lower() == 'true'
        requested_chunks = request.args.getlist('chunks')
        if supports_chunks and requested_chunks:
            # Return specific chunks
            chunks_data = {}
            for chunk_id in requested_chunks:
                chunk_data = MuralCacheV2.get_canvas_data(chunk_id=chunk_id)
                if chunk_data:
                    chunks_data[chunk_id] = chunk_data

            return jsonify({
                'type': 'chunks',
                'chunks': chunks_data
            })

        # Try to get full canvas from cache
        cached_canvas = MuralCacheV2.get_canvas_data()
        if cached_canvas is not None:
            logger.info("Serving canvas from tiered cache")

            # Check if client accepts compression
            accept_encoding = request.headers.get('Accept-Encoding', '')
            if 'gzip' in accept_encoding:
                # Response will be compressed by Flask/nginx
                response = jsonify(cached_canvas)
                response.headers['X-Cache-Hit'] = 'true'
                return response

            return jsonify(cached_canvas)

        # Cache miss - rebuild from storage
        logger.info("Cache miss - rebuilding canvas data")
        canvas_data, _ = canvas_manager.read_canvas()
        # Warm the cache
        MuralCacheV2.warm_cache(canvas_data)

        response = jsonify(canvas_data)
        response.headers['X-Cache-Hit'] = 'false'
        return response

    except Exception as e:
        logger.error(f"Unexpected error in get_canvas: {e}")
        performance_monitor.record_operation('api.get_canvas', 0, success=False)
        return jsonify({'error': 'Failed to retrieve canvas data'}), 500
@app.route('/api/cooldown')
@monitor_performance('api.get_cooldown')
def get_cooldown():
    """Get user's current cooldown status with caching"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'cooldown_remaining': 0})

    # Check tiered cache first
    cooldown_key = f"mural:cooldown:{user_id}"
    cached_cooldown = tiered_cache.get(cooldown_key)
    if cached_cooldown:
        cooldown_time = datetime.fromisoformat(cached_cooldown)
        if cooldown_time > datetime.now():
            remaining = int((cooldown_time - datetime.now()).total_seconds())
            return jsonify({'cooldown_remaining': remaining})

    return jsonify({'cooldown_remaining': 0})

@app.route('/api/connected-count')
def get_connected_count():
    """Get the current number of connected users"""
    # Use cache for connected count
    count = tiered_cache.get('connected_users_count')
    if count is None:
        count = len(connected_users)
        tiered_cache.set('connected_users_count', count, expire=5)

    return jsonify({'count': count})
@app.route('/api/user-progress')
@monitor_performance('api.user_progress')
def get_user_progress():
    """Get user's progress with caching"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    # Try cache first
    cache_key = f"user_progress:{user_id}"
    cached_progress = tiered_cache.get(cache_key)

    if cached_progress:
        return jsonify(cached_progress)

    # Build progress data
    user_data = user_manager.get_user_data(user_id)
    # Check for new achievements
    unlocked_achievements = challenge_manager.check_achievements(user_data)
    new_achievements = []

    with user_manager.user_transaction(user_id, f"achievements_{user_id}_{datetime.now().timestamp()}") as transaction:
        for achievement_id, achievement_data in unlocked_achievements:
            if user_data_manager.unlock_achievement(user_id, achievement_id):
                # Award paint buckets for new achievement
                user_data_manager.add_paint_buckets(user_id, achievement_data['reward'])
                new_achievements.append({
                    'id': achievement_id,
                    **achievement_data
                })
                transaction.add_operation({
                    'type': 'unlock_achievement',
                    'achievement_id': achievement_id,
                    'reward': achievement_data['reward']
                })
    # Get or generate active challenges
    if not user_data.get('active_challenges'):
        # Generate new challenges
        new_challenges = challenge_manager.generate_challenges(
            user_data.get('challenges_completed', 0),
            user_data.get('completed_challenge_ids', [])
        )
        challenge_ids = [c.id for c in new_challenges]
        user_data_manager.set_active_challenges(user_id, challenge_ids)
        active_challenges = []
        for challenge in new_challenges:
            challenge_dict = challenge.to_dict()
            challenge_dict['progress'] = 0
            active_challenges.append(challenge_dict)
    else:
        # Return existing challenges with progress
        active_challenges = []
        for challenge_id in user_data['active_challenges']:
            progress = user_data.get('challenge_progress', {}).get(challenge_id, 0)

            # Get stored challenge details
            if 'challenge_details' in user_data and challenge_id in user_data['challenge_details']:
                challenge_data = user_data['challenge_details'][challenge_id].copy()
                challenge_data['progress'] = progress
                active_challenges.append(challenge_data)

    progress_data = {
        'paint_buckets': user_data.get('paint_buckets', 0),
        'total_pixels': user_data.get('total_pixels_placed', 0),
        'challenges_completed': user_data.get('challenges_completed', 0),
        'achievements': user_data.get('achievements', []),
        'active_challenges': active_challenges,
        'new_achievements': new_achievements,
        'statistics': user_data.get('statistics', {}),
        'purchases': user_data.get('purchases', {})
    }
    # Cache the result
    tiered_cache.set(cache_key, progress_data, expire=60)

    return jsonify(progress_data)

@app.route('/api/user-stats')
@monitor_performance('api.user_stats')
def get_user_stats():
    """Get user's pixel statistics with enhanced caching"""
    user_id = session.get('user_id')

    # Get total pixels (cached)
    total_pixels = tiered_cache.get('mural:total_pixels')
    if total_pixels is None:
        canvas_data, _ = canvas_manager.read_canvas()
        total_pixels = len(canvas_data)
        tiered_cache.set('mural:total_pixels', total_pixels, expire=60)

    if not user_id:
        return jsonify({
            'user_pixels': 0,
            'total_pixels': total_pixels
        })

    # Get user pixel count (cached)
    user_pixels_key = f"mural:user_pixels:{user_id}"
    user_pixels = tiered_cache.get(user_pixels_key)

    if user_pixels is None:
        # Calculate from canvas data
        canvas_data, _ = canvas_manager.read_canvas()
        user_pixels = sum(1 for pixel_data in canvas_data.values()
                         if pixel_data.get('user_id') == user_id)
        tiered_cache.set(user_pixels_key, user_pixels, expire=300)

    return jsonify({
        'user_pixels': user_pixels,
        'total_pixels': total_pixels
    })

@app.route('/api/shop')
@monitor_performance('api.get_shop')
def get_shop_items():
    """Get available shop items for the user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'items': shop.get_available_items({})})
    user_data = user_manager.get_user_data(user_id)
    available_items = shop.get_available_items(user_data.get('purchases', {}))
    return jsonify({
        'items': available_items,
        'paint_buckets': user_data.get('paint_buckets', 0)
    })

@app.route('/api/shop/purchase', methods=['POST'])
@monitor_performance('api.shop_purchase')
def purchase_item():
    """Purchase an item from the shop"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    item_id = data.get('item_id')
    if not item_id:
        return jsonify({'error': 'No item specified'}), 400

    with user_manager.user_transaction(user_id, f"purchase_{user_id}_{datetime.now().timestamp()}") as transaction:
        user_data = user_manager.get_user_data(user_id)
        # Check if purchase is valid
        error = shop.purchase_item(item_id, user_data)
        if error:
            return jsonify({'error': error}), 400
        # Deduct cost and apply purchase
        item = shop.items[item_id]
        if user_data.get('paint_buckets', 0) < item.cost:
            return jsonify({'error': 'Insufficient paint buckets'}), 400
        # Update user data
        user_data['paint_buckets'] -= item.cost
        updated_data = shop.apply_purchase(item_id, user_data)

        # Save with transaction
        user_manager.update_user_data(user_id, updated_data, transaction)
        transaction.add_operation({
            'type': 'shop_purchase',
            'item_id': item_id,
            'cost': item.cost
        })

        # Invalidate user progress cache
        tiered_cache.delete(f"user_progress:{user_id}")
        return jsonify({
            'success': True,
            'paint_buckets': updated_data['paint_buckets'],
            'purchase': item.to_dict()
        })
@app.route('/api/complete-challenges', methods=['POST'])
@monitor_performance('api.complete_challenges')
def complete_challenges():
    """Complete finished challenges and get new ones"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json()
    completed_ids = data.get('completed_challenge_ids', [])

    if not completed_ids:
        return jsonify({'error': 'No challenges to complete'}), 400
    with user_manager.user_transaction(user_id, f"challenges_{user_id}_{datetime.now().timestamp()}") as transaction:
        user_data = user_manager.get_user_data(user_id)
        total_reward = 0
        # Complete each challenge and award rewards
        for challenge_id in completed_ids:
            if challenge_id in user_data.get('active_challenges', []):
                # Get challenge reward from stored details
                challenge_details = user_data.get('challenge_details', {})
                challenge_reward = challenge_details.get(challenge_id, {}).get('reward', 50)

                # Award paint buckets
                total_reward += challenge_reward
                user_data_manager.complete_challenge(user_id, challenge_id)
                transaction.add_operation({
                    'type': 'complete_challenge',
                    'challenge_id': challenge_id,
                    'reward': challenge_reward
                })
        # Add total rewards
        if total_reward > 0:
            user_data['paint_buckets'] = user_data.get('paint_buckets', 0) + total_reward
            user_manager.update_user_data(user_id, user_data, transaction)
        # Generate new challenges if needed
        user_data = user_manager.get_user_data(user_id)
        if len(user_data.get('active_challenges', [])) == 0:
            new_challenges = challenge_manager.generate_challenges(
                user_data.get('challenges_completed', 0)
            )
            challenge_ids = [c.id for c in new_challenges]
            user_data_manager.set_active_challenges(user_id, challenge_ids)

            active_challenges = []
            for challenge in new_challenges:
                challenge_dict = challenge.to_dict()
                challenge_dict['progress'] = 0
                active_challenges.append(challenge_dict)
        else:
            active_challenges = []

        # Invalidate user progress cache
        tiered_cache.delete(f"user_progress:{user_id}")
        return jsonify({
            'success': True,
            'total_reward': total_reward,
            'paint_buckets': user_data.get('paint_buckets', 0),
            'active_challenges': active_challenges,
            'challenges_completed': user_data.get('challenges_completed', 0)
        })

@app.route('/api/place-pixel', methods=['POST'])
@rate_limit(max_requests=app.config.get('RATE_LIMIT_PIXELS_PER_MINUTE', 60), window_seconds=60)
@monitor_performance('api.place_pixel')
def place_pixel():
    """Place a pixel with enhanced performance"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    x = data.get('x')
    y = data.get('y')
    color = data.get('color')

    # Validate all fields are present
    if not all([x is not None, y is not None, color]):
        return jsonify({'error': 'Missing required fields'}), 400
    # Validate coordinate types
    if not isinstance(x, int) or not isinstance(y, int):
        return jsonify({'error': 'Coordinates must be integers'}), 400

    # Validate coordinate bounds
    if not (0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT):
        return jsonify({'error': 'Coordinates out of bounds'}), 400

    # Validate color format
    import re
    if not isinstance(color, str) or not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        return jsonify({'error': 'Invalid color format. Must be hex color (#RRGGBB)'}), 400
    # Get or create user ID
    user_id = session.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id

    # Check cooldown using enhanced cache
    cooldown_key = f"mural:cooldown:{user_id}"
    cached_cooldown = tiered_cache.get(cooldown_key)

    if cached_cooldown:
        cooldown_time = datetime.fromisoformat(cached_cooldown)
        if cooldown_time > datetime.now():
            remaining = int((cooldown_time - datetime.now()).total_seconds())
            return jsonify({
                'error': 'Cooldown active',
                'cooldown_remaining': remaining
            }), 429

    # Prepare pixel data
    pixel_data = {
        'color': color,
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id
    }
    # Update pixel using concurrent manager
    success = canvas_manager.update_pixel(x, y, pixel_data)

    if not success:
        return jsonify({'error': 'Failed to place pixel'}), 500

    # Update cache
    MuralCacheV2.update_pixel(x, y, pixel_data)
    # Get user data for upgrades
    user_data = user_manager.get_user_data(user_id)

    # Apply cooldown reduction from upgrades
    base_cooldown = PIXEL_COOLDOWN
    cooldown_reduction = user_data.get('purchases', {}).get('cooldown_reduction', 0)
    actual_cooldown = int(base_cooldown * (1 - cooldown_reduction / 100))

    # Set cooldown in cache
    cooldown_time = datetime.now() + timedelta(seconds=actual_cooldown)
    tiered_cache.set(cooldown_key, cooldown_time.isoformat(), expire=actual_cooldown + 10)

    # Update user progress asynchronously
    def update_user_progress():
        with user_manager.user_transaction(user_id, f"pixel_{user_id}_{datetime.now().timestamp()}") as transaction:
            # Increment pixels placed
            user_data = user_manager.get_user_data(user_id)
            user_data['total_pixels_placed'] = user_data.get('total_pixels_placed', 0) + 1
            # Award paint buckets
            base_reward = 1
            active_boosts = user_data.get('active_boosts', {})
            if 'double_rewards' in active_boosts:
                expires = datetime.fromisoformat(active_boosts['double_rewards']['expires'])
                if expires > datetime.now():
                    base_reward *= 2
            user_data['paint_buckets'] = user_data.get('paint_buckets', 0) + base_reward

            # Update challenge progress
            for challenge_id in user_data.get('active_challenges', []):
                if 'place_pixels' in challenge_id:
                    progress = user_data.get('challenge_progress', {}).get(challenge_id, 0) + 1
                    user_data['challenge_progress'][challenge_id] = progress

            user_manager.update_user_data(user_id, user_data, transaction)
            transaction.add_operation({
                'type': 'place_pixel',
                'x': x,
                'y': y,
                'color': color,
                'reward': base_reward
            })

    # Execute user update in background
    thread_pool.submit(update_user_progress)

    # Hash user ID for privacy in broadcasts
    hashed_user_id = hashlib.sha256(user_id.encode()).hexdigest()[:8]
    # Add to batch queue for WebSocket broadcast
    pixel_update = {
        'x': x,
        'y': y,
        'color': color,
        'user_id': hashed_user_id
    }

    batch_pixel_update(pixel_update)

    return jsonify({
        'success': True,
        'cooldown_remaining': actual_cooldown,
        'paint_buckets_earned': 1,  # Base reward
        'total_paint_buckets': user_data.get('paint_buckets', 0) + 1
    })
@app.route('/api/leaderboard')
@monitor_performance('api.leaderboard')
def get_leaderboard():
    """Get pixel leaderboard with caching"""
    leaderboard_type = request.args.get('type', 'pixels')
    # Check cache first
    cached_leaderboard = MuralCacheV2.get_leaderboard(leaderboard_type)
    if cached_leaderboard:
        return jsonify({'leaderboard': cached_leaderboard})
    # Build leaderboard
    if leaderboard_type == 'pixels':
        # Get all users and their pixel counts
        canvas_data, _ = canvas_manager.read_canvas()
        user_pixels = {}
        for pixel_data in canvas_data.values():
            user_id = pixel_data.get('user_id')
            if user_id and user_id != 'system':
                user_pixels[user_id] = user_pixels.get(user_id, 0) + 1
        # Sort and limit
        leaderboard = sorted(
            [(user_id, count) for user_id, count in user_pixels.items()],
            key=lambda x: x[1],
            reverse=True
        )[:100]
        # Cache the result
        MuralCacheV2.set_leaderboard(leaderboard_type, leaderboard, expire=300)

        return jsonify({'leaderboard': leaderboard})
    return jsonify({'error': 'Invalid leaderboard type'}), 400

@app.route('/api/pixel-history/<int:x>/<int:y>')
@monitor_performance('api.pixel_history')
def get_pixel_history(x: int, y: int):
    """Get history of changes for a specific pixel"""
    if not (0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT):
        return jsonify({'error': 'Coordinates out of bounds'}), 400

    history = MuralCacheV2.get_pixel_history(x, y)
    return jsonify({'history': history})

@app.route('/api/cache-metrics')
def get_cache_metrics():
    """Get cache performance metrics (admin only)"""
    # In production, add authentication check here
    metrics = MuralCacheV2.get_cache_metrics()
    return jsonify(metrics)
@app.route('/api/performance-metrics')
def get_performance_metrics():
    """Get overall performance metrics (admin only)"""
    # In production, add authentication check here
    time_window = request.args.get('window', 'hour')

    if time_window == 'hour':
        window = timedelta(hours=1)
    elif time_window == 'day':
        window = timedelta(days=1)
    else:
        window = None

    stats = performance_monitor.get_all_stats(window)
    recommendations = performance_monitor.get_recommendations()
    return jsonify({
        'stats': stats,
        'recommendations': recommendations
    })
@socketio.on('connect')
def handle_connect():
    try:
        # Validate session before allowing WebSocket connection
        if 'user_id' not in session:
            logger.warning(f"WebSocket connection attempt without valid session from {request.remote_addr}")
            return False  # Reject connection

        # Validate request.sid
        if not request.sid:
            logger.error("No socket ID provided")
            return False
        print('Client connected')
        connected_users.add(request.sid)

        # Update connected count in cache
        tiered_cache.set('connected_users_count', len(connected_users), expire=5)
        # Send canvas data efficiently
        canvas_data, _ = canvas_manager.read_canvas()
        if len(canvas_data) > 10000:  # Large canvas
            # Send a message to fetch via API instead
            emit('canvas_large', {'message': 'Please fetch canvas via API'})
        else:
            # Send canvas data
            emit('canvas_update', canvas_data)
        # Emit the updated user count to all connected clients
        socketio.emit('user_count', {'count': len(connected_users)})
        logger.info(f"User {session['user_id']} connected. Total users: {len(connected_users)}")
    except Exception as e:
        logger.error(f"Error in handle_connect: {e}")
        return False

@socketio.on('disconnect')
def handle_disconnect():
    try:
        print('Client disconnected')
        if hasattr(request, 'sid') and request.sid:
            connected_users.discard(request.sid)

        # Update connected count in cache
        tiered_cache.set('connected_users_count', len(connected_users), expire=5)
        # Emit the updated user count to all connected clients
        socketio.emit('user_count', {'count': len(connected_users)})
        logger.info(f"User disconnected. Total users: {len(connected_users)}")
    except Exception as e:
        logger.error(f"Error in handle_disconnect: {e}")
def batch_pixel_update(pixel_update):
    """Batch pixel updates for efficient WebSocket transmission"""
    global pixel_update_queue, pixel_batch_timer
    try:
        # Validate pixel update
        if not isinstance(pixel_update, dict) or 'x' not in pixel_update or 'y' not in pixel_update:
            logger.warning(f"Invalid pixel update: {pixel_update}")
            return

        pixel_update_queue.append(pixel_update)
        # If queue is full, send immediately
        if len(pixel_update_queue) >= PIXEL_BATCH_SIZE:
            flush_pixel_batch()
        elif not pixel_batch_timer:
            # Schedule batch send
            import threading
            pixel_batch_timer = threading.Timer(PIXEL_BATCH_DELAY, flush_pixel_batch)
            pixel_batch_timer.start()
    except Exception as e:
        logger.error(f"Error in batch_pixel_update: {e}")
def flush_pixel_batch():
    """Send batched pixel updates"""
    global pixel_update_queue, pixel_batch_timer

    try:
        if pixel_batch_timer:
            pixel_batch_timer.cancel()
            pixel_batch_timer = None
        if not pixel_update_queue:
            return

        # Create a copy to avoid race conditions
        updates_to_send = pixel_update_queue[:]
        pixel_update_queue = []
        # Send as batch if multiple updates, otherwise single
        if len(updates_to_send) > 1:
            socketio.emit('pixel_batch', updates_to_send)
        else:
            socketio.emit('pixel_placed', updates_to_send[0])

    except Exception as e:
        logger.error(f"Error in flush_pixel_batch: {e}")
        # Clear the queue to prevent memory issues
        pixel_update_queue = []
def cleanup_expired_data():
    """Periodic cleanup of expired data"""
    try:
        # Clean up expired cache entries
        tiered_cache.clear_expired()

        # Clean up old performance metrics
        # This could be expanded to archive old metrics to disk
        logger.info("Completed periodic cleanup")
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
def setup_periodic_tasks():
    """Setup all periodic background tasks"""
    import threading
    import time

    def periodic_worker():
        while True:
            try:
                # Run cleanup every 5 minutes
                time.sleep(300)
                cleanup_expired_data()

                # Save canvas data periodically
                canvas_data, _ = canvas_manager.read_canvas()
                delta_storage.save_with_delta('canvas', canvas_data)
                # Export performance metrics periodically
                if datetime.now().minute == 0:  # Every hour
                    performance_monitor.export_metrics(
                        f"metrics/performance_{datetime.now().strftime('%Y%m%d_%H')}.json",
                        timedelta(hours=1)
                    )

            except Exception as e:
                logger.error(f"Error in periodic worker: {e}")
    thread = threading.Thread(target=periodic_worker, daemon=True)
    thread.start()
    logger.info("Started periodic background tasks")

def initialize_data():
    """Initialize or load canvas data on startup"""
    global canvas_data

    try:
        # Try to load from optimized storage
        stored_data = delta_storage.load_with_delta('canvas')

        if stored_data:
            canvas_data = stored_data
            logger.info(f"Loaded canvas data: {len(canvas_data)} pixels")
        else:
            # Load from legacy file if exists
            if os.path.exists('canvas_data.json'):
                with open('canvas_data.json', 'r') as f:
                    canvas_data = json.load(f)
                logger.info(f"Loaded legacy canvas data: {len(canvas_data)} pixels")

                # Save to optimized storage
                delta_storage.save_with_delta('canvas', canvas_data)
            else:
                logger.info("Starting with empty canvas")
                canvas_data = {}
        # Warm up the cache
        if canvas_data:
            MuralCacheV2.warm_cache(canvas_data)
            logger.info("Cache warmed with canvas data")
        # Initialize canvas manager with data
        for pixel_key, pixel_data in canvas_data.items():
            x, y = map(int, pixel_key.split(','))
            canvas_manager.update_pixel(x, y, pixel_data)
    except Exception as e:
        logger.error(f"Error initializing data: {e}")
        canvas_data = {}
# Set up performance alert handler
def handle_performance_alert(alert: Dict[str, Any]):
    """Handle performance alerts"""
    logger.warning(f"Performance Alert: {alert['type']} - {alert['message']}")

    # In production, you might want to:
    # - Send alerts to monitoring service
    # - Trigger auto-scaling
    # - Notify administrators
    # - Adjust cache settings dynamically
performance_monitor.add_alert_callback(handle_performance_alert)
if __name__ == '__main__':
    config_name = os.environ.get('FLASK_ENV', 'development')
    config_obj = config[config_name]

    # Initialize data
    initialize_data()
    # Start periodic tasks
    setup_periodic_tasks()
    # Run the application
    socketio.run(app,
                debug=config_obj.DEBUG,
                host=config_obj.HOST,
                port=config_obj.PORT,
                allow_unsafe_werkzeug=True)


# Extended application utilities and middleware

class RequestContextMiddleware:
    """Middleware for managing request context"""
    
    def __init__(self, app):
        self.app = app
        self.setup_middleware()
    
    def setup_middleware(self):
        """Setup request context middleware"""
        
        @self.app.before_request
        def before_request():
            # Set request start time
            g.request_start_time = time.time()
            
            # Set request ID for tracking
            g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
            
            # Set user context
            g.user_context = self.get_user_context()
        
        @self.app.after_request
        def after_request(response):
            # Add request ID to response
            response.headers['X-Request-ID'] = g.get('request_id', '')
            
            # Add timing header
            if hasattr(g, 'request_start_time'):
                duration = time.time() - g.request_start_time
                response.headers['X-Response-Time'] = f"{duration:.3f}s"
            
            return response
    
    def get_user_context(self):
        """Get user context for the request"""
        return {
            'user_id': session.get('user_id'),
            'ip_address': request.remote_addr,
            'user_agent': request.user_agent.string,
            'timestamp': datetime.now().isoformat()
        }

class HealthCheckEndpoint:
    """Health check endpoint with detailed status"""
    
    def __init__(self, app):
        self.app = app
        self.checks = []
        self.setup_endpoint()
    
    def add_check(self, name: str, check_func: Callable):
        """Add a health check"""
        self.checks.append((name, check_func))
    
    def setup_endpoint(self):
        """Setup health check endpoint"""
        
        @self.app.route('/health')
        def health_check():
            results = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'checks': {}
            }
            
            # Run all checks
            for name, check_func in self.checks:
                try:
                    check_result = check_func()
                    results['checks'][name] = {
                        'status': 'pass',
                        'details': check_result
                    }
                except Exception as e:
                    results['status'] = 'unhealthy'
                    results['checks'][name] = {
                        'status': 'fail',
                        'error': str(e)
                    }
            
            status_code = 200 if results['status'] == 'healthy' else 503
            return jsonify(results), status_code

class MetricsCollector:
    """Collect and expose application metrics"""
    
    def __init__(self, app):
        self.app = app
        self.metrics = defaultdict(lambda: defaultdict(int))
        self.setup_collection()
    
    def setup_collection(self):
        """Setup metrics collection"""
        
        @self.app.before_request
        def collect_request_metrics():
            endpoint = request.endpoint or 'unknown'
            method = request.method
            
            self.metrics['requests'][f"{method}:{endpoint}"] += 1
            self.metrics['requests']['total'] += 1
        
        @self.app.errorhandler(Exception)
        def collect_error_metrics(error):
            error_type = type(error).__name__
            self.metrics['errors'][error_type] += 1
            self.metrics['errors']['total'] += 1
            
            # Re-raise the error
            raise error
    
    def get_metrics(self):
        """Get current metrics"""
        return dict(self.metrics)

# Initialize middleware and utilities
if __name__ == '__main__':
    # This section ensures proper initialization
    pass
