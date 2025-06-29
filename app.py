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

# Debug logging for cooldown configuration
logger.info(f"Environment: {config_name}")
logger.info(f"PIXEL_COOLDOWN from config: {PIXEL_COOLDOWN}")
logger.info(f"PIXEL_COOLDOWN from env: {os.environ.get('PIXEL_COOLDOWN', 'Not set')}")

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
        logger.error(f" There was an error caching canvas data: {e}")
    
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
        logger.info(f"Cooldown check for user {user_id}: {time_remaining} seconds remaining")
        if time_remaining > 0:
            return jsonify({'cooldown_remaining': int(time_remaining)})
        else:
            del user_cooldowns[user_id]
    
    return jsonify({'cooldown_remaining': 0})

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
    logger.info(f"Setting cooldown for user {user_id} to {PIXEL_COOLDOWN} seconds")
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
    
    # Save canvas data to file for persistence
    save_canvas_to_file()
    
    socketio.emit('pixel_placed', {
        'x': x,
        'y': y,
        'color': color,
        'user_id': user_id
    })
    
    return jsonify({
        'success': True,
        'cooldown_remaining': PIXEL_COOLDOWN  # This is the total cooldown time in seconds
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
    """Save canvas data to JSON file"""
    try:
        with open(CANVAS_DATA_FILE, 'w') as f:
            json.dump(canvas_data, f, indent=2)
        logger.info(f"Canvas data saved to {CANVAS_DATA_FILE}")
    except Exception as e:
        logger.error(f"Error saving canvas data: {e}")

def load_canvas_from_file():
    """Load canvas data from JSON file"""
    global canvas_data
    try:
        if os.path.exists(CANVAS_DATA_FILE):
            with open(CANVAS_DATA_FILE, 'r') as f:
                canvas_data = json.load(f)
            logger.info(f"Canvas data loaded from {CANVAS_DATA_FILE} - {len(canvas_data)} pixels")
        else:
            logger.info("No existing canvas data file found, starting with empty canvas")
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
