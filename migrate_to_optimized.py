"""
Migration script to transition from current system to optimized database/caching
"""
import json
import os
import logging
from datetime import datetime
import shutil
from pathlib import Path
from data_storage import storage, delta_storage
from cache_service_v2 import MuralCacheV2, tiered_cache
from concurrency_manager import ConcurrentCanvasManager, ConcurrentUserDataManager
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class DataMigration:
    """Handles migration from old to new data storage format"""
    
    def __init__(self):
        self.backup_dir = Path('migration_backup')
        self.backup_dir.mkdir(exist_ok=True)
    def backup_existing_data(self):
        """Create backups of existing data files"""
        logger.info("Creating backups of existing data...")
        
        files_to_backup = [
            'canvas_data.json',
            'user_data.json'
        ]
        
        for filename in files_to_backup:
            if os.path.exists(filename):
                backup_path = self.backup_dir / f"{filename}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(filename, backup_path)
                logger.info(f"Backed up {filename} to {backup_path}")
    def migrate_canvas_data(self):
        """Migrate canvas data to optimized format"""
        logger.info("Migrating canvas data...")
        if not os.path.exists('canvas_data.json'):
            logger.warning("No canvas_data.json found")
            return False
        try:
            # Load existing canvas data
            with open('canvas_data.json', 'r') as f:
                canvas_data = json.load(f)
            logger.info(f"Loaded {len(canvas_data)} pixels from canvas_data.json")
            # Save to optimized storage with delta compression
            success = delta_storage.save_with_delta('canvas', canvas_data)
            
            if success:
                logger.info("Canvas data migrated to optimized storage")
                # Warm up the cache
                MuralCacheV2.warm_cache(canvas_data)
                logger.info("Cache warmed with canvas data")
                # Initialize concurrent canvas manager
                canvas_manager = ConcurrentCanvasManager(storage)
                for pixel_key, pixel_data in canvas_data.items():
                    x, y = map(int, pixel_key.split(','))
                    canvas_manager.update_pixel(x, y, pixel_data)
                
                logger.info("Canvas data loaded into concurrent manager")
                return True
            else:
                logger.error("Failed to save canvas data to optimized storage")
                return False
                
        except Exception as e:
            logger.error(f"Error migrating canvas data: {e}")
            return False
    def migrate_user_data(self):
        """Migrate user data to optimized format"""
        logger.info("Migrating user data...")
        
        if not os.path.exists('user_data.json'):
            logger.warning("No user_data.json found")
            return False
        
        try:
            # Load existing user data
            with open('user_data.json', 'r') as f:
                all_user_data = json.load(f)
            logger.info(f"Loaded data for {len(all_user_data)} users")
            # Initialize concurrent user manager
            user_manager = ConcurrentUserDataManager(storage)
            
            # Migrate each user's data
            for user_id, user_data in all_user_data.items():
                # Save to optimized storage
                success = storage.save(f"user_{user_id}.dat", user_data)
                
                if success:
                    # Cache frequently accessed data
                    cache_key = f"user_progress:{user_id}"
                    progress_data = {
                        'paint_buckets': user_data.get('paint_buckets', 0),
                        'total_pixels': user_data.get('total_pixels_placed', 0),
                        'challenges_completed': user_data.get('challenges_completed', 0),
                        'achievements': user_data.get('achievements', []),
                        'statistics': user_data.get('statistics', {}),
                        'purchases': user_data.get('purchases', {})
                    }
                    tiered_cache.set(cache_key, progress_data, expire=3600)
                else:
                    logger.error(f"Failed to migrate user {user_id}")
            logger.info("User data migration completed")
            return True
        except Exception as e:
            logger.error(f"Error migrating user data: {e}")
            return False
    def verify_migration(self):
        """Verify that migration was successful"""
        logger.info("Verifying migration...")
        # Check canvas data
        canvas_from_storage = delta_storage.load_with_delta('canvas')
        if canvas_from_storage:
            logger.info(f"✓ Canvas data verified: {len(canvas_from_storage)} pixels")
        else:
            logger.error("✗ Canvas data verification failed")
            return False
        # Check if original files match migrated data
        if os.path.exists('canvas_data.json'):
            with open('canvas_data.json', 'r') as f:
                original_canvas = json.load(f)
            if len(original_canvas) == len(canvas_from_storage):
                logger.info("✓ Canvas pixel count matches")
            else:
                logger.warning(f"⚠ Canvas pixel count mismatch: {len(original_canvas)} vs {len(canvas_from_storage)}")
        # Check cache
        cached_canvas = MuralCacheV2.get_canvas_data()
        if cached_canvas:
            logger.info("✓ Canvas cache is working")
        else:
            logger.warning("⚠ Canvas cache is empty")
        
        # Check user data files
        user_files = list(Path('data').glob('user_*.dat'))
        logger.info(f"✓ Found {len(user_files)} user data files")
        
        # Test performance metrics
        from performance_monitor import performance_monitor
        metrics = performance_monitor.get_all_stats()
        logger.info("✓ Performance monitoring is active")
        return True
    
    def create_indexes(self):
        """Create indexes for optimized lookups"""
        logger.info("Creating lookup indexes...")
        # Create user pixel index
        canvas_data = delta_storage.load_with_delta('canvas')
        if canvas_data:
            user_pixel_index = {}
            for pixel_key, pixel_data in canvas_data.items():
                user_id = pixel_data.get('user_id')
                if user_id:
                    if user_id not in user_pixel_index:
                        user_pixel_index[user_id] = []
                    user_pixel_index[user_id].append(pixel_key)
            
            # Save index
            storage.save('user_pixel_index.dat', user_pixel_index)
            logger.info(f"Created user pixel index for {len(user_pixel_index)} users")
        # Create spatial index for chunks
        chunk_index = {}
        if canvas_data:
            for pixel_key, pixel_data in canvas_data.items():
                x, y = map(int, pixel_key.split(','))
                chunk_id = f"{x // 50}_{y // 50}"
                
                if chunk_id not in chunk_index:
                    chunk_index[chunk_id] = []
                chunk_index[chunk_id].append(pixel_key)
            storage.save('chunk_index.dat', chunk_index)
            logger.info(f"Created chunk index with {len(chunk_index)} chunks")
        return True
def main():
    """Run the migration process"""
    logger.info("Starting migration to optimized database and caching system...")
    migration = DataMigration()
    # Step 1: Backup existing data
    migration.backup_existing_data()
    # Step 2: Migrate canvas data
    if not migration.migrate_canvas_data():
        logger.error("Canvas data migration failed. Aborting.")
        return False
    # Step 3: Migrate user data
    if not migration.migrate_user_data():
        logger.error("User data migration failed. Aborting.")
        return False
    # Step 4: Create indexes
    migration.create_indexes()
    # Step 5: Verify migration
    if migration.verify_migration():
        logger.info("✅ Migration completed successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Test the application with app_optimized.py")
        logger.info("2. Monitor performance metrics at /api/performance-metrics")
        logger.info("3. Check cache metrics at /api/cache-metrics")
        logger.info("4. Once verified, replace app.py with app_optimized.py")
        logger.info(f"\nBackups are stored in: {migration.backup_dir}")
        return True
    else:
        logger.error("❌ Migration verification failed")
        logger.info("Original files have been preserved. Check the logs for errors.")
        return False

if __name__ == '__main__':
    main()


















































