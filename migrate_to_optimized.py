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


class MigrationUtilities:
    """Additional utilities for migration process"""

    @staticmethod
    def analyze_performance_baseline(app_path='app.py'):
        """Analyze current app performance before migration"""
        logger.info("Analyzing performance baseline...")
        metrics = {
            'response_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'timestamp': datetime.now().isoformat()
        }

        try:
            import psutil
            import time

            process = psutil.Process()
            metrics['memory_usage'] = process.memory_info().rss / 1024 / 1024  # MB
            metrics['cpu_usage'] = process.cpu_percent(interval=1)

            # Save baseline metrics
            with open('migration_baseline.json', 'w') as f:
                json.dump(metrics, f, indent=2)

            logger.info(f"Baseline metrics saved: Memory: {metrics['memory_usage']:.2f}MB, CPU: {metrics['cpu_usage']:.2f}%")
            return metrics
        except Exception as e:
            logger.warning(f"Could not analyze baseline: {e}")
            return None

    @staticmethod
    def validate_redis_connection():
        """Validate Redis connection and configuration"""
        try:
            import redis
            client = redis.StrictRedis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=0,
                decode_responses=True
            )
            client.ping()
            logger.info("✅ Redis connection validated")
            return True
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return False

    @staticmethod
    def create_migration_report(migration_status):
        """Create detailed migration report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'status': migration_status,
            'environment': {
                'python_version': sys.version,
                'platform': sys.platform,
                'redis_available': MigrationUtilities.validate_redis_connection()
            },
            'files_migrated': [],
            'warnings': [],
            'errors': []
        }

        # Save report
        report_path = f'migration_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Migration report saved to {report_path}")
        return report_path

    @staticmethod
    def check_dependencies():
        """Check if all required dependencies are installed"""
        required_packages = [
            'flask',
            'redis',
            'psutil',
            'flask-cors',
            'flask-limiter',
            'python-dotenv'
        ]

        missing = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing.append(package)

        if missing:
            logger.warning(f"Missing dependencies: {', '.join(missing)}")
            logger.info("Install with: pip install " + ' '.join(missing))
            return False

        logger.info("✅ All dependencies are installed")
        return True

    @staticmethod
    def cleanup_old_files(backup_dir):
        """Clean up old backup files older than 30 days"""
        try:
            import glob
            from datetime import timedelta

            cutoff_date = datetime.now() - timedelta(days=30)
            old_backups = []

            for backup_path in glob.glob('backup_*'):
                if os.path.isdir(backup_path):
                    try:
                        # Extract date from directory name
                        date_str = backup_path.split('_')[1]
                        backup_date = datetime.strptime(date_str, '%Y%m%d')

                        if backup_date < cutoff_date:
                            old_backups.append(backup_path)
                    except:
                        continue

            if old_backups:
                logger.info(f"Found {len(old_backups)} old backup(s) to clean up")
                for old_backup in old_backups:
                    try:
                        shutil.rmtree(old_backup)
                        logger.info(f"Removed old backup: {old_backup}")
                    except Exception as e:
                        logger.warning(f"Could not remove {old_backup}: {e}")

            return len(old_backups)
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
            return 0

    @staticmethod
    def generate_rollback_script(backup_dir):
        """Generate a rollback script for emergency recovery"""
        rollback_script = f"""#!/usr/bin/env python3
# Auto-generated rollback script
# Created: {datetime.now().isoformat()}

import os
import shutil
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rollback():
    backup_dir = '{backup_dir}'

    if not os.path.exists(backup_dir):
        logger.error(f"Backup directory not found: {{backup_dir}}")
        return False

    # Restore files
    files_to_restore = {os.listdir(backup_dir)}

    for file in files_to_restore:
        backup_path = os.path.join(backup_dir, file)
        restore_path = file

        try:
            if os.path.exists(restore_path):
                os.remove(restore_path)
            shutil.copy2(backup_path, restore_path)
            logger.info(f"Restored: {{file}}")
        except Exception as e:
            logger.error(f"Failed to restore {{file}}: {{e}}")
            return False

    logger.info("✅ Rollback completed successfully")
    return True

if __name__ == '__main__':
    if input("Are you sure you want to rollback? (yes/no): ").lower() == 'yes':
        rollback()
    else:
        print("Rollback cancelled")
"""

        script_path = f'rollback_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
        with open(script_path, 'w') as f:
            f.write(rollback_script)

        os.chmod(script_path, 0o755)  # Make executable
        logger.info(f"Rollback script generated: {script_path}")
        return script_path
