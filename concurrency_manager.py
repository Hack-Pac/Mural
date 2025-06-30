"""
Concurrency manager for safe concurrent access to data
"""
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable, List
from contextlib import contextmanager
from collections import defaultdict
import asyncio
from datetime import datetime, timedelta
logger = logging.getLogger(__name__)
class OptimisticLockManager:
    """
    Implements optimistic concurrency control with version tracking
    """

    def __init__(self):
        self.versions = {}  # Track version numbers for each resource
        self.lock = threading.Lock()
    def get_version(self, resource_id: str) -> int:
        """Get current version of a resource"""
        with self.lock:
            return self.versions.get(resource_id, 0)
    def check_and_update(self, resource_id: str, expected_version: int) -> bool:
        """Check version and update if it matches expected"""
        with self.lock:
            current_version = self.versions.get(resource_id, 0)
            if current_version == expected_version:
                self.versions[resource_id] = current_version + 1
                return True
            return False
    def force_update(self, resource_id: str) -> int:
        """Force update version and return new version"""
        with self.lock:
            new_version = self.versions.get(resource_id, 0) + 1
            self.versions[resource_id] = new_version
            return new_version
class ReadWriteLockManager:
    """
    Implements reader-writer locks for better concurrent read performance
    """

    def __init__(self):
        self.locks = {}
        self.lock_creation_lock = threading.Lock()
    def _get_lock(self, resource_id: str) -> 'ReadWriteLock':
        """Get or create a lock for a resource"""
        with self.lock_creation_lock:
            if resource_id not in self.locks:
                self.locks[resource_id] = ReadWriteLock()
            return self.locks[resource_id]
    @contextmanager
    def read_lock(self, resource_id: str):
        """Acquire read lock for a resource"""
        lock = self._get_lock(resource_id)
        lock.acquire_read()
        try:
            yield
        finally:
            lock.release_read()
    @contextmanager
    def write_lock(self, resource_id: str):
        """Acquire write lock for a resource"""
        lock = self._get_lock(resource_id)
        lock.acquire_write()
        try:
            yield
        finally:
            lock.release_write()
class ReadWriteLock:
    """
    A reader-writer lock implementation
    Allows multiple readers or a single writer
    """

    def __init__(self):
        self.readers = 0
        self.writers = 0
        self.read_ready = threading.Condition(threading.Lock())
        self.write_ready = threading.Condition(threading.Lock())
    def acquire_read(self):
        """Acquire lock for reading"""
        self.read_ready.acquire()
        while self.writers > 0:
            self.read_ready.wait()
        self.readers += 1
        self.read_ready.release()

    def release_read(self):
        """Release read lock"""
        self.read_ready.acquire()
        self.readers -= 1
        if self.readers == 0:
            self.read_ready.notify_all()
        self.read_ready.release()
    def acquire_write(self):
        """Acquire lock for writing"""
        self.write_ready.acquire()
        while self.writers > 0:
            self.write_ready.wait()
        self.writers += 1
        self.write_ready.release()

        self.read_ready.acquire()
        while self.readers > 0:
            self.read_ready.wait()
        self.read_ready.release()
    def release_write(self):
        """Release write lock"""
        self.write_ready.acquire()
        self.writers -= 1
        self.write_ready.notify_all()
        self.write_ready.release()

        self.read_ready.acquire()
        self.read_ready.notify_all()
        self.read_ready.release()
class TransactionManager:
    """
    Manages transactions with rollback capability
    """

    def __init__(self):
        self.transactions = {}
        self.lock = threading.Lock()
    def begin_transaction(self, transaction_id: str) -> 'Transaction':
        """Begin a new transaction"""
        with self.lock:
            if transaction_id in self.transactions:
                raise ValueError(f"Transaction {transaction_id} already exists")
            transaction = Transaction(transaction_id)
            self.transactions[transaction_id] = transaction
            return transaction

    def get_transaction(self, transaction_id: str) -> Optional['Transaction']:
        """Get an existing transaction"""
        with self.lock:
            return self.transactions.get(transaction_id)
    def commit_transaction(self, transaction_id: str) -> bool:
        """Commit a transaction"""
        with self.lock:
            transaction = self.transactions.get(transaction_id)
            if not transaction:
                return False

            success = transaction.commit()
            del self.transactions[transaction_id]
            return success
    def rollback_transaction(self, transaction_id: str) -> bool:
        """Rollback a transaction"""
        with self.lock:
            transaction = self.transactions.get(transaction_id)
            if not transaction:
                return False
            success = transaction.rollback()
            del self.transactions[transaction_id]
            return success
class Transaction:
    """
    Represents a transaction with operations log
    """
    def __init__(self, transaction_id: str):
        self.id = transaction_id
        self.operations = []
        self.state = 'active'
        self.timestamp = datetime.now()

    def add_operation(self, operation: Dict[str, Any]):
        """Add an operation to the transaction"""
        if self.state != 'active':
            raise ValueError(f"Cannot add operation to {self.state} transaction")
        self.operations.append({
            'timestamp': datetime.now(),
            **operation
        })
    def commit(self) -> bool:
        """Commit the transaction"""
        if self.state != 'active':
            return False
        self.state = 'committed'
        logger.info(f"Transaction {self.id} committed with {len(self.operations)} operations")
        return True
    def rollback(self) -> bool:
        """Rollback the transaction"""
        if self.state != 'active':
            return False

        self.state = 'rolled_back'
        logger.info(f"Transaction {self.id} rolled back, {len(self.operations)} operations discarded")
        return True

class ConcurrentCanvasManager:
    """
    Manages concurrent access to canvas data with optimistic locking
    """
    def __init__(self, storage):
        self.storage = storage
        self.optimistic_lock = OptimisticLockManager()
        self.rw_lock = ReadWriteLockManager()
        self.transaction_manager = TransactionManager()
        # Pixel update queue for batching
        self.update_queue = []
        self.queue_lock = threading.Lock()
        self.batch_size = 50
        self.batch_interval = 0.1  # seconds
        # Start batch processor
        self._start_batch_processor()
    def read_canvas(self, chunk_id: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """Read canvas data with version"""
        resource_id = f"canvas:{chunk_id}" if chunk_id else "canvas:full"

        with self.rw_lock.read_lock(resource_id):
            data = self.storage.load(f"canvas_{chunk_id}.dat" if chunk_id else "canvas.dat")
            version = self.optimistic_lock.get_version(resource_id)
            return data or {}, version
    def update_pixel(self, x: int, y: int, pixel_data: Dict[str, Any],
                    expected_version: Optional[int] = None) -> bool:
        """Update a pixel with optimistic locking"""
        pixel_key = f"{x},{y}"
        chunk_id = f"{x // 50}_{y // 50}"
        resource_id = f"canvas:{chunk_id}"
        # If version provided, check it
        if expected_version is not None:
            if not self.optimistic_lock.check_and_update(resource_id, expected_version):
                logger.warning(f"Version mismatch for pixel {pixel_key}")
                return False
        else:
            # Force update version
            self.optimistic_lock.force_update(resource_id)
        # Add to update queue
        with self.queue_lock:
            self.update_queue.append({
                'pixel_key': pixel_key,
                'chunk_id': chunk_id,
                'data': pixel_data,
                'timestamp': datetime.now()
            })
        return True
    def _start_batch_processor(self):
        """Start background thread for processing batched updates"""
        def process_batches():
            while True:
                time.sleep(self.batch_interval)
                self._process_update_batch()
        thread = threading.Thread(target=process_batches, daemon=True)
        thread.start()

    def _process_update_batch(self):
        """Process a batch of pixel updates"""
        with self.queue_lock:
            if not self.update_queue:
                return
            # Take up to batch_size updates
            batch = self.update_queue[:self.batch_size]
            self.update_queue = self.update_queue[self.batch_size:]
        # Group updates by chunk
        chunks_to_update = defaultdict(list)
        for update in batch:
            chunks_to_update[update['chunk_id']].append(update)
        # Update each chunk
        for chunk_id, updates in chunks_to_update.items():
            resource_id = f"canvas:{chunk_id}"
            with self.rw_lock.write_lock(resource_id):
                # Load chunk data
                chunk_data, _ = self.read_canvas(chunk_id)
                # Apply updates
                for update in updates:
                    chunk_data[update['pixel_key']] = update['data']
                # Save chunk
                self.storage.save(f"canvas_{chunk_id}.dat", chunk_data)
                logger.debug(f"Processed {len(updates)} updates for chunk {chunk_id}")
class ConcurrentUserDataManager:
    """
    Manages concurrent access to user data with transactions
    """
    def __init__(self, storage):
        self.storage = storage
        self.rw_lock = ReadWriteLockManager()
        self.transaction_manager = TransactionManager()
        self.user_locks = {}
        self.lock_creation_lock = threading.Lock()
    def _get_user_lock(self, user_id: str) -> threading.Lock:
        """Get or create a lock for a user"""
        with self.lock_creation_lock:
            if user_id not in self.user_locks:
                self.user_locks[user_id] = threading.Lock()
            return self.user_locks[user_id]
    @contextmanager
    def user_transaction(self, user_id: str, transaction_id: str):
        """Create a transaction context for user operations"""
        transaction = self.transaction_manager.begin_transaction(transaction_id)
        user_lock = self._get_user_lock(user_id)
        user_lock.acquire()
        try:
            yield transaction
            self.transaction_manager.commit_transaction(transaction_id)
        except Exception as e:
            logger.error(f"Transaction {transaction_id} failed: {e}")
            self.transaction_manager.rollback_transaction(transaction_id)
            raise
        finally:
            user_lock.release()
    def update_user_data(self, user_id: str, updates: Dict[str, Any],
                        transaction: Optional[Transaction] = None) -> bool:
        """Update user data within a transaction"""
        resource_id = f"user:{user_id}"
        with self.rw_lock.write_lock(resource_id):
            # Load current data
            user_data = self.storage.load(f"user_{user_id}.dat") or {}
            # Record operation in transaction
            if transaction:
                transaction.add_operation({
                    'type': 'update_user',
                    'user_id': user_id,
                    'old_data': user_data.copy(),
                    'updates': updates
                })
            # Apply updates
            user_data.update(updates)

            # Save data
            return self.storage.save(f"user_{user_id}.dat", user_data)
    def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """Get user data with read lock"""
        resource_id = f"user:{user_id}"
        with self.rw_lock.read_lock(resource_id):
            return self.storage.load(f"user_{user_id}.dat") or {}
# Global instances
optimistic_lock_manager = OptimisticLockManager()
rw_lock_manager = ReadWriteLockManager()
transaction_manager = TransactionManager()

    def get_lock_statistics(self) -> Dict[str, Any]:
        """Get detailed lock statistics"""
        stats = {
            'total_locks': len(self.locks),
            'active_locks': sum(1 for lock in self.locks.values() if lock.is_locked()),
            'deadlock_detections': self.deadlock_detections,
            'lock_contentions': self.lock_contentions
        }
        return stats

# Extended concurrency utilities
class ConcurrencyMetrics:
    """Track concurrency metrics"""
    
    def __init__(self):
        self.metrics = {
            'locks_acquired': 0,
            'locks_released': 0,
            'deadlocks_prevented': 0,
            'transactions_completed': 0,
            'transactions_rolled_back': 0
        }
        self.start_time = datetime.now()
    
    def record_lock_acquired(self, resource_id: str):
        """Record lock acquisition"""
        self.metrics['locks_acquired'] += 1
    
    def record_lock_released(self, resource_id: str):
        """Record lock release"""
        self.metrics['locks_released'] += 1
    
    def record_deadlock_prevented(self):
        """Record deadlock prevention"""
        self.metrics['deadlocks_prevented'] += 1
    
    def record_transaction_completed(self, transaction_id: str):
        """Record transaction completion"""
        self.metrics['transactions_completed'] += 1
    
    def record_transaction_rollback(self, transaction_id: str):
        """Record transaction rollback"""
        self.metrics['transactions_rolled_back'] += 1
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            **self.metrics,
            'uptime_seconds': uptime,
            'locks_per_second': self.metrics['locks_acquired'] / uptime if uptime > 0 else 0,
            'transaction_success_rate': (
                self.metrics['transactions_completed'] / 
                (self.metrics['transactions_completed'] + self.metrics['transactions_rolled_back'])
                if (self.metrics['transactions_completed'] + self.metrics['transactions_rolled_back']) > 0
                else 1.0
            )
        }
# Global metrics instance
concurrency_metrics = ConcurrencyMetrics()















