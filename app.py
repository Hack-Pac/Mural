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
from user_data import user_data_manager
from challenges import challenge_manager
from shop import shop
from functools import wraps
import hashlib

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

# Debug logging for cooldown configuration
logger.info(f"Environment: {config_name}")
logger.info(f"PIXEL_COOLDOWN from config: {PIXEL_COOLDOWN}")
logger.info(f"PIXEL_COOLDOWN from env: {os.environ.get('PIXEL_COOLDOWN', 'Not set')}")

# Rate limiting decorator
rate_limit_data = {}

def rate_limit(max_requests=60, window_seconds=60):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user_id = session.get('user_id', request.remote_addr)
            now = datetime.now()
            
            # Clean old entries
            global rate_limit_data
            rate_limit_data = {k: v for k, v in rate_limit_data.items() 
                             if (now - v['first_request']).seconds < window_seconds}
            
            if user_id in rate_limit_data:
                user_data = rate_limit_data[user_id]
                if (now - user_data['first_request']).seconds < window_seconds:
                    if user_data['count'] >= max_requests:
                        return jsonify({'error': 'Rate limit exceeded'}), 429
                    user_data['count'] += 1
                else:
                    rate_limit_data[user_id] = {'first_request': now, 'count': 1}
            else:
                rate_limit_data[user_id] = {'first_request': now, 'count': 1}
            
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
@rate_limit(max_requests=120, window_seconds=60)  # Higher limit for canvas fetching
def get_canvas():
    """Get the current canvas state with caching and compression support"""
    try:
        # Check if client accepts gzip
        accept_encoding = request.headers.get('Accept-Encoding', '')
        
        # Try to get from cache first
        try:
            cached_canvas = MuralCache.get_canvas_data()
            if cached_canvas is not None:
                logger.info("Serving canvas from cache")
                response = jsonify(cached_canvas)
                
                # Add compression if supported
                if 'gzip' in accept_encoding and len(canvas_data) > 1000:
                    import gzip
                    import io
                    
                    json_data = json.dumps(cached_canvas)
                    gzip_buffer = io.BytesIO()
                    with gzip.GzipFile(mode='wb', fileobj=gzip_buffer) as gzip_file:
                        gzip_file.write(json_data.encode('utf-8'))
                    
                    response = app.response_class(
                        gzip_buffer.getvalue(),
                        mimetype='application/json',
                        headers={'Content-Encoding': 'gzip'}
                    )
                
                return response
        except Exception as e:
            logger.error(f"Error getting canvas from cache: {e}")
        
        # Cache miss or error - return current data and try to cache it
        logger.info("Cache miss or error - serving live canvas data")
        
        # Ensure canvas_data is not corrupted
        if not isinstance(canvas_data, dict):
            logger.error(f"Canvas data corrupted, type: {type(canvas_data)}")
            return jsonify({'error': 'Canvas data corrupted'}), 500
        
        try:
            MuralCache.set_canvas_data(canvas_data, expire=app.config.get('CACHE_CANVAS_TTL', 60))
        except Exception as e:
            logger.error(f"There was an error caching canvas data: {e}")
        
        return jsonify(canvas_data)
    except Exception as e:
        logger.error(f"Unexpected error in get_canvas: {e}")
        return jsonify({'error': 'Failed to retrieve canvas data'}), 500

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
        logger.info(f"Cooldown check for user {user_id}: {time_remaining} seconds remaining")
        if time_remaining > 0:
            return jsonify({'cooldown_remaining': int(time_remaining)})
        else:
            del user_cooldowns[user_id]
    
    return jsonify({'cooldown_remaining': 0})

@app.route('/api/connected-count')
def get_connected_count():
    """Get the current number of connected users"""
    return jsonify({'count': len(connected_users)})

@app.route('/api/user-progress')
def get_user_progress():
    """Get user's progress, challenges, and achievements"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_data = user_data_manager.get_user_data(user_id)
    
    # Check for new achievements
    unlocked_achievements = challenge_manager.check_achievements(user_data)
    new_achievements = []
    for achievement_id, achievement_data in unlocked_achievements:
        if user_data_manager.unlock_achievement(user_id, achievement_id):
            # Award paint buckets for new achievement
            user_data_manager.add_paint_buckets(user_id, achievement_data['reward'])
            new_achievements.append({
                'id': achievement_id,
                **achievement_data
            })
    
    # Get or generate active challenges
    if not user_data['active_challenges'] or len(user_data['active_challenges']) == 0:
        # Generate new challenges
        new_challenges = challenge_manager.generate_challenges(
            user_data['challenges_completed'],
            user_data.get('completed_challenge_ids', [])
        )
        challenge_ids = [c.id for c in new_challenges]
        user_data_manager.set_active_challenges(user_id, challenge_ids)
        
        # Store challenge details in user data for persistence
        if 'challenge_details' not in user_data:
            user_data['challenge_details'] = {}
        for challenge in new_challenges:
            challenge_dict = challenge.to_dict()
            user_data['challenge_details'][challenge.id] = challenge_dict
            # Also update the user data directly
            user_data_manager.user_data[user_id]['challenge_details'][challenge.id] = challenge_dict
        user_data_manager.save_data()
        
        active_challenges = []
        for challenge in new_challenges:
            challenge_dict = challenge.to_dict()
            challenge_dict['progress'] = 0
            active_challenges.append(challenge_dict)
    else:
        # Return existing challenges with progress
        active_challenges = []
        for challenge_id in user_data['active_challenges']:
            progress = user_data['challenge_progress'].get(challenge_id, 0)
            
            # Get stored challenge details
            if 'challenge_details' in user_data and challenge_id in user_data['challenge_details']:
                challenge_data = user_data['challenge_details'][challenge_id].copy()
                challenge_data['progress'] = progress
            else:
                # Fallback if details not stored - regenerate based on current progress
                logger.warning(f"Challenge {challenge_id} missing details, regenerating...")
                # Generate a single challenge as fallback
                temp_challenges = challenge_manager.generate_challenges(
                    user_data['challenges_completed'], 
                    [challenge_id]
                )
                if temp_challenges:
                    challenge_data = temp_challenges[0].to_dict()
                    challenge_data['progress'] = progress
                    # Store for future use
                    if 'challenge_details' not in user_data:
                        user_data['challenge_details'] = {}
                    user_data['challenge_details'][challenge_id] = challenge_data
                    user_data_manager.save_data()
                else:
                    # Last resort fallback
                    challenge_data = {
                        'id': challenge_id,
                        'name': 'Mystery Challenge',
                        'description': 'Complete the mystery challenge',
                        'requirement': 10,
                        'reward': 50,
                        'progress': progress
                    }
            active_challenges.append(challenge_data)
    
    return jsonify({
        'paint_buckets': user_data['paint_buckets'],
        'total_pixels': user_data['total_pixels_placed'],
        'challenges_completed': user_data['challenges_completed'],
        'achievements': user_data['achievements'],
        'active_challenges': active_challenges,
        'new_achievements': new_achievements,
        'statistics': user_data['statistics'],
        'purchases': user_data['purchases']
    })

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
    
    return jsonify({
        'user_pixels': user_pixels,
        'total_pixels': total_pixels
    })

@app.route('/api/shop')
def get_shop_items():
    """Get available shop items for the user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'items': shop.get_available_items({})})
    
    user_data = user_data_manager.get_user_data(user_id)
    available_items = shop.get_available_items(user_data['purchases'])
    
    return jsonify({
        'items': available_items,
        'paint_buckets': user_data['paint_buckets']
    })

@app.route('/api/shop/purchase', methods=['POST'])
def purchase_item():
    """Purchase an item from the shop"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    item_id = data.get('item_id')
    
    if not item_id:
        return jsonify({'error': 'No item specified'}), 400
    
    user_data = user_data_manager.get_user_data(user_id)
    
    # Check if purchase is valid
    error = shop.purchase_item(item_id, user_data)
    if error:
        return jsonify({'error': error}), 400
    
    # Deduct cost and apply purchase
    item = shop.items[item_id]
    if not user_data_manager.spend_paint_buckets(user_id, item.cost):
        return jsonify({'error': 'Insufficient paint buckets'}), 400
    
    # Apply the purchase effects
    updated_data = shop.apply_purchase(item_id, user_data)
    user_data_manager.user_data[user_id] = updated_data
    user_data_manager.save_data()
    
    return jsonify({
        'success': True,
        'paint_buckets': updated_data['paint_buckets'],
        'purchase': item.to_dict()
    })

@app.route('/api/complete-challenges', methods=['POST'])
def complete_challenges():
    """Complete finished challenges and get new ones"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    completed_ids = data.get('completed_challenge_ids', [])
    
    if not completed_ids:
        return jsonify({'error': 'No challenges to complete'}), 400
    
    user_data = user_data_manager.get_user_data(user_id)
    total_reward = 0
    
    # Complete each challenge and award rewards
    for challenge_id in completed_ids:
        if challenge_id in user_data['active_challenges']:
            # Get challenge reward from stored details
            challenge_reward = 50  # Default
            if 'challenge_details' in user_data and challenge_id in user_data['challenge_details']:
                challenge_reward = user_data['challenge_details'][challenge_id].get('reward', 50)
            
            # Award paint buckets
            total_reward += challenge_reward
            user_data_manager.complete_challenge(user_id, challenge_id)
    
    # Add total rewards
    if total_reward > 0:
        user_data_manager.add_paint_buckets(user_id, total_reward)
    
    # Generate new challenges if all are completed
    user_data = user_data_manager.get_user_data(user_id)
    if len(user_data['active_challenges']) == 0:
        new_challenges = challenge_manager.generate_challenges(
            user_data['challenges_completed']
        )
        challenge_ids = [c.id for c in new_challenges]
        user_data_manager.set_active_challenges(user_id, challenge_ids)
        
        # Store new challenge details
        if 'challenge_details' not in user_data:
            user_data['challenge_details'] = {}
        for challenge in new_challenges:
            challenge_dict = challenge.to_dict()
            user_data['challenge_details'][challenge.id] = challenge_dict
            # Also update the user data directly
            user_data_manager.user_data[user_id]['challenge_details'][challenge.id] = challenge_dict
        user_data_manager.save_data()
        
        # Return full challenge details with initial progress
        active_challenges = []
        for challenge in new_challenges:
            challenge_dict = challenge.to_dict()
            challenge_dict['progress'] = 0
            active_challenges.append(challenge_dict)
    else:
        # Return remaining challenges with details
        active_challenges = []
        for challenge_id in user_data['active_challenges']:
            if 'challenge_details' in user_data and challenge_id in user_data['challenge_details']:
                challenge_data = user_data['challenge_details'][challenge_id].copy()
                challenge_data['progress'] = user_data['challenge_progress'].get(challenge_id, 0)
                active_challenges.append(challenge_data)
    
    return jsonify({
        'success': True,
        'total_reward': total_reward,
        'paint_buckets': user_data['paint_buckets'],
        'active_challenges': active_challenges,
        'challenges_completed': user_data['challenges_completed']
    })

@app.route('/api/place-pixel', methods=['POST'])
@rate_limit(max_requests=app.config.get('RATE_LIMIT_PIXELS_PER_MINUTE', 60), window_seconds=60)
def place_pixel():
    """Place a pixel on the canvas with enhanced validation"""
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
    
    # Get user data for upgrades
    user_data = user_data_manager.get_user_data(user_id)
    
    # Apply cooldown reduction from upgrades
    base_cooldown = PIXEL_COOLDOWN
    cooldown_reduction = user_data['purchases'].get('cooldown_reduction', 0)
    actual_cooldown = int(base_cooldown * (1 - cooldown_reduction / 100))
    
    # Update cooldowns
    logger.info(f"Setting cooldown for user {user_id} to {actual_cooldown} seconds (base: {base_cooldown}, reduction: {cooldown_reduction}%)")
    cooldown_time = datetime.now() + timedelta(seconds=actual_cooldown)
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
    
    # Save canvas data to file for persistence
    save_canvas_to_file()
    
    # Update user progress
    user_data_manager.increment_pixels_placed(user_id)
    
    # Award paint buckets for placing pixels (base reward)
    base_reward = 1
    
    # Check for active double rewards boost
    active_boosts = user_data.get('active_boosts', {})
    if 'double_rewards' in active_boosts:
        expires = datetime.fromisoformat(active_boosts['double_rewards']['expires'])
        if expires > datetime.now():
            base_reward *= 2
    
    paint_buckets_earned = user_data_manager.add_paint_buckets(user_id, base_reward)
    
    # Check challenge progress
    # This is simplified - in production you'd have more sophisticated challenge tracking
    for challenge_id in user_data['active_challenges']:
        if 'place_pixels' in challenge_id:
            current_progress = user_data['challenge_progress'].get(challenge_id, 0) + 1
            user_data_manager.update_challenge_progress(user_id, challenge_id, current_progress)
    
    # Hash user ID for privacy in broadcasts
    hashed_user_id = hashlib.sha256(user_id.encode()).hexdigest()[:8]
    
    # Add to batch queue instead of immediate emit
    pixel_update = {
        'x': x,
        'y': y,
        'color': color,
        'user_id': hashed_user_id  # Send hashed ID for privacy
    }
    
    # Use batching for better performance
    batch_pixel_update(pixel_update)
    
    return jsonify({
        'success': True,
        'cooldown_remaining': actual_cooldown,
        'paint_buckets_earned': base_reward,
        'total_paint_buckets': paint_buckets_earned
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
        
        # Send canvas data with rate limiting
        if len(canvas_data) > 10000:  # Large canvas
            # Send a message to fetch via API instead
            emit('canvas_large', {'message': 'Please fetch canvas via API'})
        else:
            # Send a sanitized copy of canvas data
            safe_canvas = {k: v for k, v in canvas_data.items() if isinstance(v, dict) and 'color' in v}
            emit('canvas_update', safe_canvas)
        
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
                # Also save canvas data periodically for extra safety
                save_canvas_to_file()
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    logger.info("Started periodic cleanup worker")

def generate_initial_pixel_art():
    """Generate some initial pixel art with holes for users to fill in"""
    designs = []
    
    # Design 1: Smiley face with missing features (centered around 100, 100)
    smiley = [
        # Face outline (circle)
        (95, 90), (96, 90), (97, 90), (98, 90), (99, 90), (100, 90), (101, 90), (102, 90), (103, 90), (104, 90), (105, 90),
        (93, 91), (94, 91), (106, 91), (107, 91),
        (92, 92), (108, 92),
        (91, 93), (109, 93),
        (90, 94), (110, 94),
        (90, 95), (110, 95),
        (89, 96), (111, 96),
        (89, 97), (111, 97),
        (89, 98), (111, 98),
        (89, 99), (111, 99),
        (89, 100), (111, 100),
        (89, 101), (111, 101),
        (89, 102), (111, 102),
        (90, 103), (110, 103),
        (90, 104), (110, 104),
        (91, 105), (109, 105),
        (92, 106), (108, 106),
        (93, 107), (94, 107), (106, 107), (107, 107),
        (95, 108), (96, 108), (97, 108), (98, 108), (99, 108), (100, 108), (101, 108), (102, 108), (103, 108), (104, 108), (105, 108),
        # Left eye (missing pupil)
        (95, 95), (96, 95), (97, 95),
        (94, 96), (98, 96),
        (94, 97), (98, 97),
        (95, 98), (96, 98), (97, 98),
        # Right eye (missing pupil)
        (103, 95), (104, 95), (105, 95),
        (102, 96), (106, 96),
        (102, 97), (106, 97),
        (103, 98), (104, 98), (105, 98),
        # Mouth outline (missing middle)
        (96, 103), (97, 103), (103, 103), (104, 103),
        (95, 104), (105, 104),
        (96, 105), (97, 105), (103, 105), (104, 105),
    ]
    designs.append(('smiley', smiley, '#FFD700'))  # Gold color
    
    # Design 2: Heart with missing center (around 250, 150)
    heart = [
        # Left heart bump
        (245, 145), (246, 145), (247, 145),
        (244, 146), (245, 146), (246, 146), (247, 146), (248, 146),
        (243, 147), (244, 147), (245, 147), (246, 147), (247, 147), (248, 147), (249, 147),
        (243, 148), (244, 148), (245, 148), (246, 148), (247, 148), (248, 148), (249, 148),
        # Right heart bump
        (251, 145), (252, 145), (253, 145),
        (250, 146), (251, 146), (252, 146), (253, 146), (254, 146),
        (249, 147), (250, 147), (251, 147), (252, 147), (253, 147), (254, 147), (255, 147),
        (249, 148), (250, 148), (251, 148), (252, 148), (253, 148), (254, 148), (255, 148),
        # Heart body outline (missing center)
        (243, 149), (255, 149),
        (244, 150), (254, 150),
        (245, 151), (253, 151),
        (246, 152), (252, 152),
        (247, 153), (251, 153),
        (248, 154), (250, 154),
        (249, 155),
    ]
    designs.append(('heart', heart, '#FF69B4'))  # Hot pink
    
    # Design 3: Simple house with missing windows and door (around 150, 300)
    house = [
        # Roof
        (155, 290),
        (154, 291), (156, 291),
        (153, 292), (157, 292),
        (152, 293), (158, 293),
        (151, 294), (159, 294),
        (150, 295), (160, 295),
        # House walls (outline only)
        (145, 296), (146, 296), (147, 296), (148, 296), (149, 296), (150, 296), (151, 296), (152, 296), (153, 296), (154, 296), (155, 296), (156, 296), (157, 296), (158, 296), (159, 296), (160, 296), (161, 296), (162, 296), (163, 296), (164, 296), (165, 296),
        (145, 297), (165, 297),
        (145, 298), (165, 298),
        (145, 299), (165, 299),
        (145, 300), (165, 300),
        (145, 301), (165, 301),
        (145, 302), (165, 302),
        (145, 303), (165, 303),
        (145, 304), (165, 304),
        (145, 305), (165, 305),
        (145, 306), (146, 306), (147, 306), (148, 306), (149, 306), (150, 306), (151, 306), (152, 306), (153, 306), (154, 306), (155, 306), (156, 306), (157, 306), (158, 306), (159, 306), (160, 306), (161, 306), (162, 306), (163, 306), (164, 306), (165, 306),
        # Window frames (missing glass)
        (149, 299), (150, 299), (151, 299), (152, 299),
        (149, 300), (152, 300),
        (149, 301), (152, 301),
        (149, 302), (150, 302), (151, 302), (152, 302),
        (158, 299), (159, 299), (160, 299), (161, 299),
        (158, 300), (161, 300),
        (158, 301), (161, 301),
        (158, 302), (159, 302), (160, 302), (161, 302),
        # Door frame (missing door)
        (154, 303), (155, 303), (156, 303),
        (154, 304), (156, 304),
        (154, 305), (156, 305),
    ]
    designs.append(('house', house, '#8B4513'))  # Saddle brown
    
    # Design 4: Flower with missing petals (around 350, 200)
    flower = [
        # Flower center
        (349, 199), (350, 199), (351, 199),
        (349, 200), (350, 200), (351, 200),
        (349, 201), (350, 201), (351, 201),
        # Partial petals (some missing)
        (347, 197), (348, 197),  # Top left petal (partial)
        (352, 197), (353, 197),  # Top right petal (partial)
        (347, 203), (348, 203),  # Bottom left petal (partial)
        (352, 203), (353, 203),  # Bottom right petal (partial)
        # Stem
        (350, 202), (350, 203), (350, 204), (350, 205), (350, 206), (350, 207), (350, 208), (350, 209), (350, 210),
        # Leaves (partial)
        (348, 206), (349, 207),  # Left leaf (partial)
        (351, 206), (352, 207),  # Right leaf (partial)
    ]
    designs.append(('flower', flower, '#32CD32'))  # Lime green
    
    # Design 5: Star with missing points (around 400, 100)
    star = [
        # Star center
        (399, 99), (400, 99), (401, 99),
        (398, 100), (399, 100), (400, 100), (401, 100), (402, 100),
        (399, 101), (400, 101), (401, 101),
        # Partial star points (some missing)
        (400, 95), (400, 96), (400, 97),  # Top point (partial)
        (395, 102), (396, 103),  # Left point (partial)
        (404, 102), (405, 103),  # Right point (partial)
        (398, 104), (399, 105),  # Bottom left point (partial)
        (401, 104), (402, 105),  # Bottom right point (partial)
    ]
    designs.append(('star', star, '#FFD700'))  # Gold
    
    return designs

def populate_canvas_with_initial_art():
    """Populate the canvas with initial pixel art designs"""
    if canvas_data:  # Don't overwrite if canvas already has data
        logger.info("Canvas already has data, skipping initial art generation")
        return
    
    designs = generate_initial_pixel_art()
    pixels_added = 0
    
    for design_name, coordinates, color in designs:
        for x, y in coordinates:
            # Make sure coordinates are within bounds
            if 0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT:
                pixel_key = f"{x},{y}"
                canvas_data[pixel_key] = {
                    'color': color,
                    'timestamp': datetime.now().isoformat(),
                    'user_id': 'system'  # Mark as system-generated
                }
                pixels_added += 1
    
    logger.info(f"Generated initial pixel art: {pixels_added} pixels across {len(designs)} designs")
    
    # Save the initial art to file for persistence
    save_canvas_to_file()
    
    # Update cache with the new data
    try:
        MuralCache.set_canvas_data(canvas_data)
        MuralCache.set_total_pixel_count(len(canvas_data))
    except Exception as e:
        logger.error(f"Error caching initial canvas data: {e}")

# Persistent storage configuration
CANVAS_DATA_FILE = 'canvas_data.json'

def save_canvas_to_file():
    """Save canvas data to JSON file with atomic write"""
    try:
        # Write to temporary file first
        temp_file = f"{CANVAS_DATA_FILE}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(canvas_data, f, indent=2)
        
        # Atomic rename
        os.replace(temp_file, CANVAS_DATA_FILE)
        logger.info(f"Canvas data saved to {CANVAS_DATA_FILE}")
    except Exception as e:
        logger.error(f"Error saving canvas data: {e}")
        # Clean up temp file if it exists
        try:
            if os.path.exists(f"{CANVAS_DATA_FILE}.tmp"):
                os.remove(f"{CANVAS_DATA_FILE}.tmp")
        except:
            pass

def load_canvas_from_file():
    """Load canvas data from JSON file with validation"""
    global canvas_data
    try:
        if os.path.exists(CANVAS_DATA_FILE):
            with open(CANVAS_DATA_FILE, 'r') as f:
                loaded_data = json.load(f)
            
            # Validate loaded data
            if not isinstance(loaded_data, dict):
                logger.error(f"Invalid canvas data format in file: {type(loaded_data)}")
                canvas_data = {}
                return
            
            # Validate each pixel entry
            valid_pixels = 0
            for key, value in loaded_data.items():
                if isinstance(value, dict) and 'color' in value:
                    # Validate coordinate format
                    if re.match(r'^\d+,\d+$', key):
                        x, y = map(int, key.split(','))
                        if 0 <= x < CANVAS_WIDTH and 0 <= y < CANVAS_HEIGHT:
                            valid_pixels += 1
                        else:
                            logger.warning(f"Pixel out of bounds: {key}")
                            del loaded_data[key]
                    else:
                        logger.warning(f"Invalid pixel key format: {key}")
                        del loaded_data[key]
                else:
                    logger.warning(f"Invalid pixel data for key {key}: {value}")
                    del loaded_data[key]
            
            canvas_data = loaded_data
            logger.info(f"Canvas data loaded from {CANVAS_DATA_FILE} - {valid_pixels} valid pixels")
        else:
            logger.info("No existing canvas data file found, starting with empty canvas")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error loading canvas data: {e}")
        canvas_data = {}
    except Exception as e:
        logger.error(f"Error loading canvas data: {e}")
        canvas_data = {}

if __name__ == '__main__':
    config_name = os.environ.get('FLASK_ENV', 'development')
    config_obj = config[config_name]
    
    # Start periodic cleanup
    setup_periodic_cleanup()
    
    # Load existing canvas data from file first
    load_canvas_from_file()
    
    # Initialize cache with canvas data if it exists
    if canvas_data:
        MuralCache.set_canvas_data(canvas_data)
        MuralCache.set_total_pixel_count(len(canvas_data))
        logger.info("Initialized cache with existing canvas data")
    
    # Only populate with initial art if canvas is empty
    if not canvas_data:
        populate_canvas_with_initial_art()
        logger.info("Populated empty canvas with initial pixel art")
    
    socketio.run(app, 
                debug=config_obj.DEBUG, 
                host=config_obj.HOST, 
                port=config_obj.PORT,
                allow_unsafe_werkzeug=True)
