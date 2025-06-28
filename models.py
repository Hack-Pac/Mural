from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Cached pixel count for performance
    pixel_count = db.Column(db.Integer, default=0)
    
    # Relationship to pixels
    pixels = db.relationship('Pixel', backref='user', lazy='dynamic')

class Pixel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(7), nullable=False)  # Hex color
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    placed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Composite index for fast lookups
    __table_args__ = (
        db.Index('idx_pixel_coords', 'x', 'y'),
        db.Index('idx_pixel_user', 'user_id'),
    )

class Cooldown(db.Model):
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), primary_key=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    @classmethod
    def is_user_on_cooldown(cls, user_id):
        cooldown = cls.query.filter_by(user_id=user_id).first()
        if cooldown and cooldown.expires_at > datetime.utcnow():
            return True
        elif cooldown:
            # Clean up expired cooldown
            db.session.delete(cooldown)
            db.session.commit()
        return False
    
    @classmethod
    def set_user_cooldown(cls, user_id, seconds):
        cooldown = cls.query.filter_by(user_id=user_id).first()
        if not cooldown:
            cooldown = cls(user_id=user_id)
        
        cooldown.expires_at = datetime.utcnow() + timedelta(seconds=seconds)
        db.session.add(cooldown)
        db.session.commit()
