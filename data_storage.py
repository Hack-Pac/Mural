"""
Optimized data storage with compression, versioning, and backup strategies
"""
import json
import gzip
import os
import shutil
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
import threading
import msgpack
import lz4.frame
from pathlib import Path

logger = logging.getLogger(__name__)

class OptimizedDataStorage:
    """
    Efficient file-based storage with:
    - Multiple compression algorithms
    - Atomic writes
    - Automatic backups
    - Data versioning
    - Corruption detection
    """

    def __init__(self, base_dir: str = 'data', backup_dir: str = 'backups'):
        self.base_dir = Path(base_dir)
        self.backup_dir = Path(backup_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)

        # Compression settings
        self.compression_threshold = 1024  # Compress files larger than 1KB
        self.compression_method = 'lz4'  # Options: 'gzip', 'lz4', 'none'

        # Backup settings
        self.backup_retention_days = 7
        self.max_backups_per_file = 10

        # Write lock for thread safety
        self._write_locks = {}
        self._lock_manager = threading.Lock()

    def _get_write_lock(self, filename: str) -> threading.Lock:
        """Get or create a write lock for a file"""
        with self._lock_manager:
            if filename not in self._write_locks:
                self._write_locks[filename] = threading.Lock()
            return self._write_locks[filename]

    def _compress_data(self, data: bytes) -> tuple[bytes, str]:
        """Compress data using configured method"""
        if len(data) < self.compression_threshold:
            return data, 'none'

        if self.compression_method == 'lz4':
            compressed = lz4.frame.compress(data, compression_level=1)  # Fast compression
            return compressed, 'lz4'
        elif self.compression_method == 'gzip':
            compressed = gzip.compress(data, compresslevel=6)
            return compressed, 'gzip'
        else:
            return data, 'none'
    def _decompress_data(self, data: bytes, method: str) -> bytes:
        """Decompress data based on method used"""
        if method == 'lz4':
            return lz4.frame.decompress(data)
        elif method == 'gzip':
            return gzip.decompress(data)
        else:
            return data
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA256 checksum for data integrity"""
        return hashlib.sha256(data).hexdigest()

    def save(self, filename: str, data: Any, create_backup: bool = True) -> bool:
        """Save data with compression and backup"""
        filepath = self.base_dir / filename
        lock = self._get_write_lock(filename)

        with lock:
            try:
                # Serialize data
                if filename.endswith('.json'):
                    serialized = json.dumps(data, indent=2, sort_keys=True).encode('utf-8')
                else:
                    # Use msgpack for better performance
                    serialized = msgpack.packb(data, use_bin_type=True)

                # Compress if needed
                compressed_data, compression_method = self._compress_data(serialized)

                # Calculate checksum
                checksum = self._calculate_checksum(compressed_data)

                # Create metadata
                metadata = {
                    'version': 2,
                    'compression': compression_method,
                    'checksum': checksum,
                    'original_size': len(serialized),
                    'compressed_size': len(compressed_data),
                    'timestamp': datetime.now().isoformat()
                }

                # Create backup if file exists
                if create_backup and filepath.exists():
                    self._create_backup(filename)

                # Write to temporary file first (atomic write)
                temp_filepath = filepath.with_suffix('.tmp')

                with open(temp_filepath, 'wb') as f:
                    # Write metadata header
                    metadata_bytes = json.dumps(metadata).encode('utf-8')
                    f.write(len(metadata_bytes).to_bytes(4, 'little'))
                    f.write(metadata_bytes)
                    # Write compressed data
                    f.write(compressed_data)
                # Atomic rename
                temp_filepath.replace(filepath)
                logger.info(f"Saved {filename}: {len(serialized)} bytes -> {len(compressed_data)} bytes "
                          f"({compression_method}, {100 * len(compressed_data) / len(serialized):.1f}% ratio)")

                return True

            except Exception as e:
                logger.error(f"Error saving {filename}: {e}")
                # Clean up temp file if exists
                temp_filepath = filepath.with_suffix('.tmp')
                if temp_filepath.exists():
                    temp_filepath.unlink()
                return False

    def load(self, filename: str, validate_checksum: bool = True) -> Optional[Any]:
        """Load data with decompression and validation"""
        filepath = self.base_dir / filename

        if not filepath.exists():
            return None

        try:
            with open(filepath, 'rb') as f:
                # Read metadata header
                metadata_size = int.from_bytes(f.read(4), 'little')
                metadata_bytes = f.read(metadata_size)
                metadata = json.loads(metadata_bytes.decode('utf-8'))

                # Read compressed data
                compressed_data = f.read()

            # Validate checksum
            if validate_checksum:
                calculated_checksum = self._calculate_checksum(compressed_data)
                if calculated_checksum != metadata['checksum']:
                    logger.error(f"Checksum mismatch for {filename}! Data may be corrupted.")
                    # Try to restore from backup
                    return self._restore_from_backup(filename)

            # Decompress data
            decompressed_data = self._decompress_data(compressed_data, metadata['compression'])

            # Deserialize
            if filename.endswith('.json'):
                return json.loads(decompressed_data.decode('utf-8'))
            else:
                return msgpack.unpackb(decompressed_data, raw=False)

        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            # Try to restore from backup
            return self._restore_from_backup(filename)

    def _create_backup(self, filename: str):
        """Create a backup of the file"""
        try:
            source = self.base_dir / filename
            if not source.exists():
                return
            # Create timestamped backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{filename}.{timestamp}.bak"
            backup_path = self.backup_dir / backup_name

            shutil.copy2(source, backup_path)
            # Clean up old backups
            self._cleanup_old_backups(filename)

            logger.info(f"Created backup: {backup_name}")

        except Exception as e:
            logger.error(f"Error creating backup for {filename}: {e}")

    def _cleanup_old_backups(self, filename: str):
        """Remove old backups based on retention policy"""
        try:
            # Get all backups for this file
            backups = sorted([
                f for f in self.backup_dir.glob(f"{filename}.*.bak")
            ], key=lambda f: f.stat().st_mtime, reverse=True)

            # Keep only recent backups
            cutoff_date = datetime.now() - timedelta(days=self.backup_retention_days)

            for i, backup in enumerate(backups):
                # Keep max number of backups
                if i >= self.max_backups_per_file:
                    backup.unlink()
                    continue

                # Remove old backups
                if datetime.fromtimestamp(backup.stat().st_mtime) < cutoff_date:
                    backup.unlink()

        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")

    def _restore_from_backup(self, filename: str) -> Optional[Any]:
        """Restore data from the most recent backup"""
        try:
            # Find most recent backup
            backups = sorted([
                f for f in self.backup_dir.glob(f"{filename}.*.bak")
            ], key=lambda f: f.stat().st_mtime, reverse=True)

            if not backups:
                logger.error(f"No backups found for {filename}")
                return None

            latest_backup = backups[0]
            logger.info(f"Restoring from backup: {latest_backup.name}")

            # Copy backup to main file
            shutil.copy2(latest_backup, self.base_dir / filename)

            # Try loading again
            return self.load(filename, validate_checksum=False)

        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return None

    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get information about a stored file"""
        filepath = self.base_dir / filename

        if not filepath.exists():
            return None

        try:
            with open(filepath, 'rb') as f:
                # Read metadata header
                metadata_size = int.from_bytes(f.read(4), 'little')
                metadata_bytes = f.read(metadata_size)
                metadata = json.loads(metadata_bytes.decode('utf-8'))

            # Add file size info
            metadata['file_size'] = filepath.stat().st_size
            metadata['compression_ratio'] = metadata['compressed_size'] / metadata['original_size']

            return metadata

        except Exception as e:
            logger.error(f"Error getting file info for {filename}: {e}")
            return None

    def list_backups(self, filename: str) -> List[Dict[str, Any]]:
        """List all backups for a file"""
        backups = []

        for backup_file in self.backup_dir.glob(f"{filename}.*.bak"):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        return sorted(backups, key=lambda b: b['modified'], reverse=True)

class DeltaCompressionStorage:
    """
    Storage optimized for incremental updates using delta compression
    """

    def __init__(self, storage: OptimizedDataStorage):
        self.storage = storage
        self.base_snapshots = {}
        self.delta_threshold = 0.3  # Create new snapshot if deltas > 30% of base

    def save_with_delta(self, filename: str, data: Dict[str, Any]) -> bool:
        """Save data using delta compression"""
        base_key = f"{filename}_base"
        delta_key = f"{filename}_delta"

        # Load or create base snapshot
        if base_key not in self.base_snapshots:
            base_data = self.storage.load(base_key)
            if base_data:
                self.base_snapshots[base_key] = base_data
            else:
                # First save - create base snapshot
                self.storage.save(base_key, data)
                self.base_snapshots[base_key] = data.copy()
                return True

        base_data = self.base_snapshots[base_key]

        # Calculate delta
        delta = self._calculate_delta(base_data, data)

        # Check if we should create a new snapshot
        delta_size = len(json.dumps(delta))
        base_size = len(json.dumps(base_data))

        if delta_size > base_size * self.delta_threshold:
            # Delta is too large - create new base snapshot
            self.storage.save(base_key, data)
            self.base_snapshots[base_key] = data.copy()
            # Clear old deltas
            self.storage.save(delta_key, {})
        else:
            # Save delta
            self.storage.save(delta_key, delta)

        return True

    def load_with_delta(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load data by applying deltas to base snapshot"""
        base_key = f"{filename}_base"
        delta_key = f"{filename}_delta"

        # Load base snapshot
        base_data = self.storage.load(base_key)
        if not base_data:
            return None
        # Load and apply delta
        delta = self.storage.load(delta_key)
        if delta:
            return self._apply_delta(base_data, delta)

        return base_data

    def _calculate_delta(self, base: Dict, current: Dict) -> Dict[str, Any]:
        """Calculate differences between base and current data"""
        delta = {
            'added': {},
            'modified': {},
            'deleted': []
        }

        # Find added and modified entries
        for key, value in current.items():
            if key not in base:
                delta['added'][key] = value
            elif base[key] != value:
                delta['modified'][key] = value

        # Find deleted entries
        for key in base:
            if key not in current:
                delta['deleted'].append(key)

        return delta
    def _apply_delta(self, base: Dict, delta: Dict) -> Dict[str, Any]:
        """Apply delta to base data"""
        result = base.copy()

        # Apply additions
        for key, value in delta.get('added', {}).items():
            result[key] = value

        # Apply modifications
        for key, value in delta.get('modified', {}).items():
            result[key] = value

        # Apply deletions
        for key in delta.get('deleted', []):
            result.pop(key, None)

        return result

# Global storage instances
storage = OptimizedDataStorage()
delta_storage = DeltaCompressionStorage(storage)


    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get detailed migration status"""
        return {
            'version': self.version,
            'last_migration': self.last_migration_time,
            'pending_migrations': self._get_pending_migrations(),
            'migration_history': self.migration_history[-10:]  # Last 10 migrations
        }
    
    def _get_pending_migrations(self) -> List[str]:
        """Get list of pending migrations"""
        # Implementation depends on migration system
        return []


# Storage utilities
class StorageMonitor:
    """Monitor storage operations"""
    
    def __init__(self):
        self.operation_counts = defaultdict(int)
        self.operation_times = defaultdict(list)
    
    def record_operation(self, operation: str, duration: float):
        """Record a storage operation"""
        self.operation_counts[operation] += 1
        self.operation_times[operation].append(duration)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage operation statistics"""
        stats = {}
        for op, times in self.operation_times.items():
            if times:
                stats[op] = {
                    'count': self.operation_counts[op],
                    'avg_time': sum(times) / len(times),
                    'max_time': max(times),
                    'min_time': min(times)
                }
        return stats
