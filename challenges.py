from typing import Dict, List, Tuple, Any
import random
from datetime import datetime

class Challenge:
    """Base class for challenges"""
    def __init__(self, challenge_id: str, name: str, description: str, 
                 requirement: int, reward: int, challenge_type: str):
        self.id = challenge_id
        self.name = name
        self.description = description
        self.requirement = requirement
        self.reward = reward
        self.type = challenge_type
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'requirement': self.requirement,
            'reward': self.reward,
            'type': self.type
        }

class ChallengeManager:
    """Manages challenge generation and tracking"""
    
    def __init__(self):
        self.challenge_templates = {
            'beginner': [
                ('place_pixels', 'First Steps', 'Place {req} pixels', 5, 10),
                ('use_color', 'Colorful Start', 'Place {req} pixels using different colors', 3, 15),
                ('place_in_area', 'Local Artist', 'Place {req} pixels in a 10x10 area', 5, 20),
                ('daily_pixel', 'Daily Painter', 'Place at least 1 pixel today', 1, 5),
            ],
            'intermediate': [
                ('place_pixels', 'Pixel Pro', 'Place {req} pixels', 20, 30),
                ('create_line', 'Line Artist', 'Create a line of {req} pixels', 5, 40),
                ('fill_area', 'Area Filler', 'Fill a {req}x{req} square', 3, 50),
                ('use_colors', 'Rainbow Artist', 'Use {req} different colors', 8, 60),
                ('collaborate', 'Team Player', 'Place pixels near {req} other users\' pixels', 10, 70),
            ],
            'advanced': [
                ('place_pixels', 'Pixel Master', 'Place {req} pixels', 100, 150),
                ('create_pattern', 'Pattern Maker', 'Create a checkerboard pattern of {req}x{req}', 5, 200),
                ('pixel_art', 'Artist', 'Complete a {req}x{req} pixel art', 10, 300),
                ('defend_pixels', 'Defender', 'Replace {req} pixels that were overwritten', 20, 250),
                ('marathon', 'Marathon Painter', 'Place {req} pixels in one session', 50, 400),
            ],
            'expert': [
                ('place_pixels', 'Pixel Legend', 'Place {req} pixels', 500, 1000),
                ('create_art', 'Master Artist', 'Create a recognizable {req}x{req} artwork', 20, 1500),
                ('community', 'Community Leader', 'Have {req} of your pixels survive for 24 hours', 100, 2000),
                ('speed_paint', 'Speed Painter', 'Place {req} pixels in 10 minutes', 30, 1200),
                ('precision', 'Precision Master', 'Create perfect circle with {req} pixel radius', 10, 1800),
            ]
        }
        
        self.achievements = {
            # Pixel milestones
            'first_pixel': {'name': 'First Pixel', 'description': 'Place your first pixel', 'reward': 50, 'icon': '🎨'},
            'pixel_10': {'name': 'Apprentice', 'description': 'Place 10 pixels', 'reward': 100, 'icon': '🖌️'},
            'pixel_100': {'name': 'Artist', 'description': 'Place 100 pixels', 'reward': 500, 'icon': '🎭'},
            'pixel_1000': {'name': 'Master Artist', 'description': 'Place 1,000 pixels', 'reward': 2000, 'icon': '👨‍🎨'},
            'pixel_10000': {'name': 'Legendary Artist', 'description': 'Place 10,000 pixels', 'reward': 10000, 'icon': '🏆'},
            
            # Challenge milestones
            'challenge_1': {'name': 'Challenger', 'description': 'Complete your first challenge', 'reward': 100, 'icon': '✅'},
            'challenge_10': {'name': 'Dedicated', 'description': 'Complete 10 challenges', 'reward': 500, 'icon': '💪'},
            'challenge_50': {'name': 'Persistent', 'description': 'Complete 50 challenges', 'reward': 2000, 'icon': '🔥'},
            'challenge_100': {'name': 'Unstoppable', 'description': 'Complete 100 challenges', 'reward': 5000, 'icon': '⚡'},
            'challenge_500': {'name': 'Challenge Master', 'description': 'Complete 500 challenges', 'reward': 20000, 'icon': '👑'},
            
            # Special achievements
            'early_bird': {'name': 'Early Bird', 'description': 'Place a pixel before 6 AM', 'reward': 200, 'icon': '🌅'},
            'night_owl': {'name': 'Night Owl', 'description': 'Place a pixel after midnight', 'reward': 200, 'icon': '🦉'},
            'speed_demon': {'name': 'Speed Demon', 'description': 'Place 10 pixels in 1 minute', 'reward': 300, 'icon': '⚡'},
            'patient_artist': {'name': 'Patient Artist', 'description': 'Wait for full cooldown 10 times', 'reward': 400, 'icon': '⏳'},
            'color_master': {'name': 'Color Master', 'description': 'Use all available colors', 'reward': 600, 'icon': '🌈'},
            'survivor': {'name': 'Survivor', 'description': 'Have a pixel survive for 1 hour', 'reward': 300, 'icon': '🛡️'},
            'architect': {'name': 'Architect', 'description': 'Create a 5x5 square of the same color', 'reward': 800, 'icon': '🏗️'},
            'week_streak': {'name': 'Dedicated Week', 'description': '7-day streak', 'reward': 1000, 'icon': '📅'},
            'month_streak': {'name': 'Monthly Master', 'description': '30-day streak', 'reward': 5000, 'icon': '📆'},
        }
    
    def get_difficulty_tier(self, challenges_completed: int) -> str:
        """Determine difficulty tier based on challenges completed"""
        if challenges_completed < 10:
            return 'beginner'
        elif challenges_completed < 30:
            return 'intermediate'
        elif challenges_completed < 100:
            return 'advanced'
        else:
            return 'expert'
    
    def generate_challenges(self, challenges_completed: int, existing_ids: List[str] = None) -> List[Challenge]:
        """Generate 3 new challenges based on user's progress"""
        tier = self.get_difficulty_tier(challenges_completed)
        templates = self.challenge_templates[tier]
        
        # Ensure we don't repeat recently completed challenges
        if existing_ids is None:
            existing_ids = []
        
        challenges = []
        used_types = set()
        
        # Try to get diverse challenge types
        attempts = 0
        while len(challenges) < 3 and attempts < 20:
            template = random.choice(templates)
            challenge_type, name, desc_template, req, reward = template
            
            # Generate unique ID
            challenge_id = f"{tier}_{challenge_type}_{random.randint(1000, 9999)}"
            
            # Avoid duplicate types and IDs
            if challenge_type not in used_types and challenge_id not in existing_ids:
                # Scale difficulty slightly based on exact progress
                difficulty_multiplier = 1 + (challenges_completed * 0.02)
                adjusted_req = max(1, int(req * difficulty_multiplier))
                adjusted_reward = int(reward * difficulty_multiplier)
                
                description = desc_template.format(req=adjusted_req)
                
                challenge = Challenge(
                    challenge_id=challenge_id,
                    name=name,
                    description=description,
                    requirement=adjusted_req,
                    reward=adjusted_reward,
                    challenge_type=challenge_type
                )
                print(f"DEBUG: Created challenge - Name: {name}, Desc: {description}, Req: {adjusted_req}, Reward: {adjusted_reward}")
                
                challenges.append(challenge)
                used_types.add(challenge_type)
            
            attempts += 1
        
        # Fill remaining slots with any challenges if needed
        while len(challenges) < 3:
            template = random.choice(templates)
            challenge_type, name, desc_template, req, reward = template
            challenge_id = f"{tier}_{challenge_type}_{random.randint(1000, 9999)}"
            
            difficulty_multiplier = 1 + (challenges_completed * 0.02)
            adjusted_req = max(1, int(req * difficulty_multiplier))
            adjusted_reward = int(reward * difficulty_multiplier)
            
            description = desc_template.format(req=adjusted_req)
            
            challenge = Challenge(
                challenge_id=challenge_id,
                name=name,
                description=description,
                requirement=adjusted_req,
                reward=adjusted_reward,
                challenge_type=challenge_type
            )
            
            challenges.append(challenge)
        
        return challenges[:3]
    
    def check_achievements(self, user_stats: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Check which achievements should be unlocked based on user stats"""
        unlocked = []
        
        pixels = user_stats.get('total_pixels_placed', 0)
        challenges = user_stats.get('challenges_completed', 0)
        
        # Pixel milestones
        if pixels >= 1:
            unlocked.append(('first_pixel', self.achievements['first_pixel']))
        if pixels >= 10:
            unlocked.append(('pixel_10', self.achievements['pixel_10']))
        if pixels >= 100:
            unlocked.append(('pixel_100', self.achievements['pixel_100']))
        if pixels >= 1000:
            unlocked.append(('pixel_1000', self.achievements['pixel_1000']))
        if pixels >= 10000:
            unlocked.append(('pixel_10000', self.achievements['pixel_10000']))
        
        # Challenge milestones
        if challenges >= 1:
            unlocked.append(('challenge_1', self.achievements['challenge_1']))
        if challenges >= 10:
            unlocked.append(('challenge_10', self.achievements['challenge_10']))
        if challenges >= 50:
            unlocked.append(('challenge_50', self.achievements['challenge_50']))
        if challenges >= 100:
            unlocked.append(('challenge_100', self.achievements['challenge_100']))
        if challenges >= 500:
            unlocked.append(('challenge_500', self.achievements['challenge_500']))
        
        # Streak achievements
        streak = user_stats.get('statistics', {}).get('streak_days', 0)
        if streak >= 7:
            unlocked.append(('week_streak', self.achievements['week_streak']))
        if streak >= 30:
            unlocked.append(('month_streak', self.achievements['month_streak']))
        
        return unlocked

# Global instance
challenge_manager = ChallengeManager()