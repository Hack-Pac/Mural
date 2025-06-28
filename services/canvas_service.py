from models import db, User, Pixel
from datetime import datetime
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class CanvasService:
    _canvas_cache = None
    _cache_timestamp = None
    _cache_duration = 30  # seconds
    
    @classmethod
    def get_canvas_data(cls, force_refresh=False):
        """Get canvas data with intelligent caching"""
        now = datetime.utcnow()
        
        # Check if cache is valid
        if (not force_refresh and 
            cls._canvas_cache is not None and 
            cls._cache_timestamp is not None and
            (now - cls._cache_timestamp).total_seconds() < cls._cache_duration):
            return cls._canvas_cache
        
        # Rebuild cache
        pixels = Pixel.query.all()
        canvas_data = {}
        
        for pixel in pixels:
            key = f"{pixel.x},{pixel.y}"
            canvas_data[key] = {
                'color': pixel.color,
                'timestamp': pixel.placed_at.isoformat(),
                'user_id': pixel.user_id
            }
        
        cls._canvas_cache = canvas_data
        cls._cache_timestamp = now
        return canvas_data
    
    @classmethod
    def place_pixel(cls, x, y, color, user_id):
        """Place or replace a pixel"""
        # Check if pixel already exists at this position
        existing_pixel = Pixel.query.filter_by(x=x, y=y).first()
        
        if existing_pixel:
            # Update existing pixel
            old_user_id = existing_pixel.user_id
            existing_pixel.color = color
            existing_pixel.user_id = user_id
            existing_pixel.placed_at = datetime.utcnow()
            
            # Update user pixel counts
            if old_user_id != user_id:
                # Decrement old user's count
                old_user = User.query.get(old_user_id)
                if old_user:
                    old_user.pixel_count = max(0, old_user.pixel_count - 1)
                
                # Increment new user's count
                new_user = User.query.get(user_id)
                if new_user:
                    new_user.pixel_count += 1
            
            pixel = existing_pixel
        else:
            # Create new pixel
            pixel = Pixel(x=x, y=y, color=color, user_id=user_id)
            db.session.add(pixel)
            
            # Increment user's pixel count
            user = User.query.get(user_id)
            if user:
                user.pixel_count += 1
        
        db.session.commit()
        
        # Invalidate cache
        cls._canvas_cache = None
        
        return pixel
    
    @classmethod
    def get_total_pixel_count(cls):
        """Get total number of pixels with caching"""
        return Pixel.query.count()
    
    @classmethod
    def get_user_pixel_count(cls, user_id):
        """Get accurate pixel count for a user"""
        # Use cached count from user model
        user = User.query.get(user_id)
        return user.pixel_count if user else 0
    
    @classmethod
    def rebuild_user_pixel_counts(cls):
        """Rebuild all user pixel counts (maintenance function)"""
        users = User.query.all()
        for user in users:
            count = Pixel.query.filter_by(user_id=user.id).count()
            user.pixel_count = count
        
        db.session.commit()
        logger.info("Rebuilt pixel counts for all users")
