from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import json
import os
import uuid
from datetime import datetime, timedelta
from config import config
from dotenv import load_dotenv

load_dotenv()

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
    """Get the current canvas state"""
    return jsonify(canvas_data)

@app.route('/api/cooldown')
def get_cooldown():
    """Get user's current cooldown status"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'cooldown_remaining': 0})
    
    if user_id in user_cooldowns:
        time_remaining = (user_cooldowns[user_id] - datetime.now()).total_seconds()
        if time_remaining > 0:
            return jsonify({'cooldown_remaining': int(time_remaining)})
        else:
            del user_cooldowns[user_id]
    
    return jsonify({'cooldown_remaining': 0})

@app.route('/api/place-pixel', methods=['POST'])
def place_pixel():
    """Place a pixel on the canvas"""
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
    
    # Check cooldown
    if user_id in user_cooldowns:
        time_remaining = (user_cooldowns[user_id] - datetime.now()).total_seconds()
        if time_remaining > 0:
            return jsonify({
                'error': 'Cooldown active',
                'cooldown_remaining': int(time_remaining)
            }), 429  # Too Many Requests
    
    pixel_key = f"{x},{y}"
    canvas_data[pixel_key] = {
        'color': color,
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id
    }
    
    user_cooldowns[user_id] = datetime.now() + timedelta(seconds=PIXEL_COOLDOWN)
    
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

if __name__ == '__main__':
    config_name = os.environ.get('FLASK_ENV', 'development')
    config_obj = config[config_name]
    socketio.run(app, 
                debug=config_obj.DEBUG, 
                host=config_obj.HOST, 
                port=config_obj.PORT,
                allow_unsafe_werkzeug=True)  
