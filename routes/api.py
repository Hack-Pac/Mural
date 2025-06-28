from flask import Blueprint, request, jsonify, session
from models import db, User, Pixel, Cooldown
from datetime import datetime, timedelta
from services.canvas_service import CanvasService
from services.user_service import UserService
import logging

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

@api_bp.route('/canvas')
def get_canvas():
    """Get the current canvas state with caching"""
    try:
        canvas_data = CanvasService.get_canvas_data()
        return jsonify(canvas_data)
    except Exception as e:
        logger.error(f"Error getting canvas: {e}")
        return jsonify({'error': 'Failed to load canvas'}), 500

@api_bp.route('/user-stats')
def get_user_stats():
    """Get user's pixel statistics"""
    try:
        user = UserService.get_or_create_user(session)
        stats = {
            'user_pixels': user.pixel_count,
            'total_pixels': CanvasService.get_total_pixel_count()
        }
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return jsonify({'error': 'Failed to load stats'}), 500

@api_bp.route('/cooldown')
def get_cooldown():
    """Get user's current cooldown status"""
    try:
        user = UserService.get_or_create_user(session)
        cooldown = Cooldown.query.filter_by(user_id=user.id).first()
        
        if cooldown and cooldown.expires_at > datetime.utcnow():
            remaining = int((cooldown.expires_at - datetime.utcnow()).total_seconds())
            return jsonify({'cooldown_remaining': remaining})
        
        return jsonify({'cooldown_remaining': 0})
    except Exception as e:
        logger.error(f"Error getting cooldown: {e}")
        return jsonify({'cooldown_remaining': 0})

@api_bp.route('/place-pixel', methods=['POST'])
def place_pixel():
    """Place a pixel on the canvas with improved validation and error handling"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate input
        x, y, color = data.get('x'), data.get('y'), data.get('color')
        if not all([x is not None, y is not None, color]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if not isinstance(x, int) or not isinstance(y, int):
            return jsonify({'error': 'Coordinates must be integers'}), 400
        
        if not (0 <= x < 500 and 0 <= y < 500):  # Use config values
            return jsonify({'error': 'Coordinates out of bounds'}), 400
        
        if not isinstance(color, str) or not color.startswith('#') or len(color) != 7:
            return jsonify({'error': 'Invalid color format'}), 400
        
        # Get or create user
        user = UserService.get_or_create_user(session)
        
        # Check cooldown
        if Cooldown.is_user_on_cooldown(user.id):
            cooldown = Cooldown.query.filter_by(user_id=user.id).first()
            remaining = int((cooldown.expires_at - datetime.utcnow()).total_seconds())
            return jsonify({
                'error': 'Cooldown active',
                'cooldown_remaining': remaining
            }), 429
        
        # Place pixel using service
        pixel = CanvasService.place_pixel(x, y, color, user.id)
        
        # Set cooldown
        from flask import current_app
        cooldown_seconds = current_app.config.get('PIXEL_COOLDOWN', 60)
        Cooldown.set_user_cooldown(user.id, cooldown_seconds)
        
        # Emit socket event
        from app_factory import socketio
        socketio.emit('pixel_placed', {
            'x': x,
            'y': y,
            'color': color,
            'user_id': user.id
        })
        
        return jsonify({
            'success': True,
            'cooldown_remaining': cooldown_seconds
        })
        
    except Exception as e:
        logger.error(f"Error placing pixel: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to place pixel'}), 500
