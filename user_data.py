import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class UserDataManager:
    """Manages user progress, achievements, challenges, and currency"""
    
    def __init__(self, data_file='user_data.json'):
        self.data_file = data_file
        self.user_data = {}
        self.load_data()
        
    def load_data(self):
        """Load user data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    self.user_data = json.load(f)
                logger.info(f"Loaded user data for {len(self.user_data)} users")
            else:
                logger.info("No existing user data file found")
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
            self.user_data = {}
    
    def save_data(self):
        """Save user data to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.user_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
    
    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get or create user data"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'paint_buckets': 100,  # Starting currency
                'total_pixels_placed': 0,
                'challenges_completed': 0,
                'achievements': [],
                'active_challenges': [],
                'challenge_progress': {},
                'challenge_details': {},  # Store full challenge details
                'purchases': {
                    'brush_size': 1,
                    'cooldown_reduction': 0,  # Percentage reduction
                    'special_colors_unlocked': False
                },
                'statistics': {
                    'first_pixel_time': None,
                    'last_pixel_time': None,
                    'favorite_color': None,
                    'streak_days': 0,
                    'last_active_date': None
                }
            }
            self.save_data()
        return self.user_data[user_id]
    
    def add_paint_buckets(self, user_id: str, amount: int) -> int:
        """Add paint buckets to user's balance"""
        user = self.get_user_data(user_id)
        user['paint_buckets'] += amount
        self.save_data()
        return user['paint_buckets']
    
    def spend_paint_buckets(self, user_id: str, amount: int) -> bool:
        """Spend paint buckets if user has enough"""
        user = self.get_user_data(user_id)
        if user['paint_buckets'] >= amount:
            user['paint_buckets'] -= amount
            self.save_data()
            return True
        return False
    
    def increment_pixels_placed(self, user_id: str):
        """Increment total pixels placed and update statistics"""
        user = self.get_user_data(user_id)
        user['total_pixels_placed'] += 1
        
        now = datetime.now().isoformat()
        if not user['statistics']['first_pixel_time']:
            user['statistics']['first_pixel_time'] = now
        user['statistics']['last_pixel_time'] = now
        
        # Update daily streak
        today = datetime.now().date().isoformat()
        if user['statistics']['last_active_date'] != today:
            last_active = user['statistics']['last_active_date']
            if last_active:
                last_date = datetime.fromisoformat(last_active).date()
                current_date = datetime.now().date()
                if (current_date - last_date).days == 1:
                    user['statistics']['streak_days'] += 1
                elif (current_date - last_date).days > 1:
                    user['statistics']['streak_days'] = 1
            else:
                user['statistics']['streak_days'] = 1
            user['statistics']['last_active_date'] = today
        
        self.save_data()
    
    def unlock_achievement(self, user_id: str, achievement_id: str) -> bool:
        """Unlock an achievement for a user"""
        user = self.get_user_data(user_id)
        if achievement_id not in user['achievements']:
            user['achievements'].append(achievement_id)
            self.save_data()
            return True
        return False
    
    def update_challenge_progress(self, user_id: str, challenge_id: str, progress: int):
        """Update progress on a specific challenge"""
        user = self.get_user_data(user_id)
        user['challenge_progress'][challenge_id] = progress
        self.save_data()
    
    def complete_challenge(self, user_id: str, challenge_id: str):
        """Mark a challenge as completed"""
        user = self.get_user_data(user_id)
        if challenge_id in user['active_challenges']:
            user['active_challenges'].remove(challenge_id)
            user['challenges_completed'] += 1
            if challenge_id in user['challenge_progress']:
                del user['challenge_progress'][challenge_id]
            if challenge_id in user.get('challenge_details', {}):
                del user['challenge_details'][challenge_id]
            self.save_data()
    
    def set_active_challenges(self, user_id: str, challenge_ids: List[str]):
        """Set the active challenges for a user"""
        user = self.get_user_data(user_id)
        user['active_challenges'] = challenge_ids
        # Initialize progress for new challenges
        for challenge_id in challenge_ids:
            if challenge_id not in user['challenge_progress']:
                user['challenge_progress'][challenge_id] = 0
        self.save_data()
    
    def purchase_upgrade(self, user_id: str, upgrade_type: str, value: Any) -> bool:
        """Purchase an upgrade"""
        user = self.get_user_data(user_id)
        if upgrade_type in user['purchases']:
            user['purchases'][upgrade_type] = value
            self.save_data()
            return True
        return False
    
    def update_favorite_color(self, user_id: str, color: str):
        """Update user's most used color"""
        user = self.get_user_data(user_id)
        user['statistics']['favorite_color'] = color
        self.save_data()

# Global instance
user_data_manager = UserDataManager()