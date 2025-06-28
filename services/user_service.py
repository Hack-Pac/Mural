from models import db, User
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class UserService:
    @classmethod
    def get_or_create_user(cls, session):
        """Get existing user or create new one based on session"""
        user_id = session.get('user_id')
        
        if user_id:
            user = User.query.filter_by(session_id=user_id).first()
            if user:
                # Update last active time
                user.last_active = datetime.utcnow()
                db.session.commit()
                return user
        
        # Create new user
        new_user_id = str(uuid.uuid4())
        user = User(session_id=new_user_id)
        db.session.add(user)
        db.session.commit()
        
        # Store in session
        session['user_id'] = new_user_id
        
        logger.info(f"Created new user: {user.id}")
        return user
    
    @classmethod
    def cleanup_inactive_users(cls, days=30):
        """Remove users inactive for specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        inactive_users = User.query.filter(User.last_active < cutoff_date).all()
        
        for user in inactive_users:
            # Note: This will cascade delete pixels due to foreign key
            db.session.delete(user)
        
        db.session.commit()
        logger.info(f"Cleaned up {len(inactive_users)} inactive users")
