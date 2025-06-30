from typing import Dict, List, Any, Optional

class ShopItem:
    """Represents an item in the shop"""
    def __init__(self, item_id: str, name: str, description: str, 
                 cost: int, item_type: str, value: Any, max_level: int = 1):
        self.id = item_id
        self.name = name
        self.description = description
        self.cost = cost
        self.type = item_type
        self.value = value
        self.max_level = max_level
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'cost': self.cost,
            'type': self.type,
            'value': self.value,
            'max_level': self.max_level
        }

class Shop:
    """Manages the shop and available upgrades"""
    
    def __init__(self):
        self.items = {
            # Brush upgrades
            'brush_2x2': ShopItem(
                'brush_2x2',
                '2x2 Brush',
                'Place 4 pixels at once in a 2x2 pattern',
                500,
                'brush_size',
                2,
                max_level=1
            ),
            'brush_3x3': ShopItem(
                'brush_3x3',
                '3x3 Brush',
                'Place 9 pixels at once in a 3x3 pattern',
                2000,
                'brush_size',
                3,
                max_level=1
            ),
            'brush_cross': ShopItem(
                'brush_cross',
                'Cross Brush',
                'Place 5 pixels in a cross pattern',
                1000,
                'brush_pattern',
                'cross',
                max_level=1
            ),
            
            # Cooldown reductions
            'cooldown_10': ShopItem(
                'cooldown_10',
                'Quick Painter I',
                'Reduce cooldown by 10%',
                300,
                'cooldown_reduction',
                10,
                max_level=1
            ),
            'cooldown_25': ShopItem(
                'cooldown_25',
                'Quick Painter II',
                'Reduce cooldown by 25%',
                1000,
                'cooldown_reduction',
                25,
                max_level=1
            ),
            'cooldown_50': ShopItem(
                'cooldown_50',
                'Quick Painter III',
                'Reduce cooldown by 50%',
                5000,
                'cooldown_reduction',
                50,
                max_level=1
            ),
            
            # Special features
            'rainbow_mode': ShopItem(
                'rainbow_mode',
                'Rainbow Mode',
                'Each pixel placed cycles through rainbow colors',
                3000,
                'special_mode',
                'rainbow',
                max_level=1
            ),
            'pixel_protect': ShopItem(
                'pixel_protect',
                'Pixel Shield',
                'Your pixels are 50% harder to overwrite for 1 hour',
                2500,
                'temporary_boost',
                'protection',
                max_level=1
            ),
            'double_rewards': ShopItem(
                'double_rewards',
                'Double Rewards',
                'Double paint bucket rewards for 1 hour',
                4000,
                'temporary_boost',
                'double_rewards',
                max_level=1
            ),
            
            # Color unlocks
            'special_colors': ShopItem(
                'special_colors',
                'Special Colors',
                'Unlock gradient and metallic colors',
                1500,
                'color_unlock',
                ['gradient', 'metallic'],
                max_level=1
            ),
            'neon_colors': ShopItem(
                'neon_colors',
                'Neon Colors',
                'Unlock bright neon color palette',
                2000,
                'color_unlock',
                'neon',
                max_level=1
            ),
            
            # Utility items
            'undo_token': ShopItem(
                'undo_token',
                'Undo Token',
                'Undo your last pixel placement',
                100,
                'consumable',
                'undo',
                max_level=99
            ),
            'instant_cooldown': ShopItem(
                'instant_cooldown',
                'Instant Refresh',
                'Skip current cooldown instantly',
                200,
                'consumable',
                'skip_cooldown',
                max_level=99
            ),
        }
        
        # Define upgrade paths (what needs to be bought first)
        self.prerequisites = {
            'brush_3x3': ['brush_2x2'],
            'cooldown_25': ['cooldown_10'],
            'cooldown_50': ['cooldown_25'],
            'neon_colors': ['special_colors']
        }
    
    def get_available_items(self, user_purchases: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get list of items available for purchase based on user's current upgrades"""
        available = []
        
        for item_id, item in self.items.items():
            # Check prerequisites
            if item_id in self.prerequisites:
                prereqs = self.prerequisites[item_id]
                if not all(p in user_purchases for p in prereqs):
                    continue
            
            # Check if already at max level
            if item.type in ['brush_size', 'cooldown_reduction']:
                # These are exclusive - can only have one
                if item.type == 'brush_size' and user_purchases.get('brush_size', 1) >= item.value:
                    continue
                if item.type == 'cooldown_reduction' and user_purchases.get('cooldown_reduction', 0) >= item.value:
                    continue
            elif item.type not in ['consumable', 'temporary_boost']:
                # Non-consumables can only be bought once
                if item_id in user_purchases:
                    continue
            
            available.append(item.to_dict())
        
        return available
    
    def purchase_item(self, item_id: str, user_data: Dict[str, Any]) -> Optional[str]:
        """
        Attempt to purchase an item
        Returns error message if failed, None if successful
        """
        if item_id not in self.items:
            return "Item not found"
        
        item = self.items[item_id]
        
        # Check if user has enough currency
        if user_data['paint_buckets'] < item.cost:
            return "Insufficient paint buckets"
        
        # Check prerequisites
        if item_id in self.prerequisites:
            prereqs = self.prerequisites[item_id]
            for prereq in prereqs:
                if prereq not in user_data['purchases']:
                    return f"Requires {self.items[prereq].name} first"
        
        # Check if already owned (for non-consumables)
        if item.type not in ['consumable', 'temporary_boost']:
            if item_id in user_data['purchases']:
                return "Already owned"
        
        return None  # Purchase is valid
    
    def apply_purchase(self, item_id: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the effects of a purchase"""
        item = self.items[item_id]
        
        if item.type == 'brush_size':
            user_data['purchases']['brush_size'] = item.value
        elif item.type == 'cooldown_reduction':
            user_data['purchases']['cooldown_reduction'] = item.value
        elif item.type == 'color_unlock':
            if 'unlocked_colors' not in user_data['purchases']:
                user_data['purchases']['unlocked_colors'] = []
            if isinstance(item.value, list):
                user_data['purchases']['unlocked_colors'].extend(item.value)
            else:
                user_data['purchases']['unlocked_colors'].append(item.value)
        elif item.type == 'special_mode':
            if 'special_modes' not in user_data['purchases']:
                user_data['purchases']['special_modes'] = []
            user_data['purchases']['special_modes'].append(item.value)
        elif item.type == 'consumable':
            if 'consumables' not in user_data['purchases']:
                user_data['purchases']['consumables'] = {}
            if item_id not in user_data['purchases']['consumables']:
                user_data['purchases']['consumables'][item_id] = 0
            user_data['purchases']['consumables'][item_id] += 1
        elif item.type == 'temporary_boost':
            if 'active_boosts' not in user_data:
                user_data['active_boosts'] = {}
            from datetime import datetime, timedelta
            user_data['active_boosts'][item.value] = {
                'expires': (datetime.now() + timedelta(hours=1)).isoformat()
            }
        
        # Mark as purchased (except consumables)
        if item.type not in ['consumable', 'temporary_boost']:
            if item_id not in user_data['purchases']:
                user_data['purchases'][item_id] = True
        
        return user_data

# Global instance
shop = Shop()