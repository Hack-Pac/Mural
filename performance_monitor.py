"""
Performance monitoring system for database and caching operations
"""
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict, deque
import psutil
import json
from dataclasses import dataclass, asdict
import statistics
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Represents a single performance measurement"""
    operation: str
    duration_ms: float
    timestamp: datetime
    success: bool
    metadata: Dict[str, Any] = None
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

class PerformanceMonitor:
    """
    Comprehensive performance monitoring for all data operations
    """

    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.metrics = defaultdict(lambda: deque(maxlen=max_history))
        self.counters = defaultdict(int)
        self.lock = threading.Lock()

        # System resource monitoring
        self.system_metrics = deque(maxlen=1000)
        self._start_system_monitoring()

        # Alert thresholds
        self.thresholds = {
            'cache_hit_rate': 0.8,  # Alert if hit rate < 80%
            'avg_response_time_ms': 100,  # Alert if avg response > 100ms
            'error_rate': 0.05,  # Alert if error rate > 5%
            'memory_usage_percent': 80,  # Alert if memory > 80%
        }

        # Alert callbacks
        self.alert_callbacks = []

    def record_operation(self, operation: str, duration_ms: float,
                        success: bool = True, metadata: Dict[str, Any] = None):
        """Record a single operation metric"""
        metric = PerformanceMetric(
            operation=operation,
            duration_ms=duration_ms,
            timestamp=datetime.now(),
            success=success,
            metadata=metadata or {}
        )

        with self.lock:
            self.metrics[operation].append(metric)
            self.counters[f"{operation}_total"] += 1
            if success:
                self.counters[f"{operation}_success"] += 1
            else:
                self.counters[f"{operation}_error"] += 1
    def time_operation(self, operation: str):
        """Context manager to time an operation"""
        class OperationTimer:
            def __init__(self, monitor, operation):
                self.monitor = monitor
                self.operation = operation
                self.start_time = None
                self.metadata = {}
            def __enter__(self):
                self.start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                duration_ms = (time.time() - self.start_time) * 1000
                success = exc_type is None
                self.monitor.record_operation(
                    self.operation,
                    duration_ms,
                    success,
                    self.metadata
                )
        return OperationTimer(self, operation)

    def get_operation_stats(self, operation: str,
                           time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get statistics for a specific operation"""
        with self.lock:
            metrics = list(self.metrics[operation])

        if not metrics:
            return {
                'operation': operation,
                'count': 0,
                'success_rate': 0.0,
                'avg_duration_ms': 0.0,
                'percentiles': {}
            }

        # Filter by time window if specified
        if time_window:
            cutoff = datetime.now() - time_window
            metrics = [m for m in metrics if m.timestamp > cutoff]

        if not metrics:
            return {
                'operation': operation,
                'count': 0,
                'success_rate': 0.0,
                'avg_duration_ms': 0.0,
                'percentiles': {}
            }

        # Calculate statistics
        durations = [m.duration_ms for m in metrics]
        success_count = sum(1 for m in metrics if m.success)

        stats = {
            'operation': operation,
            'count': len(metrics),
            'success_count': success_count,
            'error_count': len(metrics) - success_count,
            'success_rate': success_count / len(metrics),
            'avg_duration_ms': statistics.mean(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'std_dev_ms': statistics.stdev(durations) if len(durations) > 1 else 0,
            'percentiles': {
                'p50': statistics.median(durations),
                'p90': self._percentile(durations, 90),
                'p95': self._percentile(durations, 95),
                'p99': self._percentile(durations, 99)
            }
        }
        return stats
    def get_all_stats(self, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get statistics for all operations"""
        operations = list(self.metrics.keys())
        stats = {}
        for operation in operations:
            stats[operation] = self.get_operation_stats(operation, time_window)

        # Add system metrics
        stats['system'] = self.get_system_metrics()
        # Check for alerts
        alerts = self.check_alerts(stats)
        if alerts:
            stats['alerts'] = alerts
        return stats

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = (len(sorted_values) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1

        if upper >= len(sorted_values):
            return sorted_values[lower]
        weight = index - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

    def _start_system_monitoring(self):
        """Start monitoring system resources"""
        def monitor_system():
            while True:
                try:
                    # Get system metrics
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    disk = psutil.disk_usage('/')
                    metric = {
                        'timestamp': datetime.now().isoformat(),
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'memory_used_mb': memory.used / 1024 / 1024,
                        'memory_available_mb': memory.available / 1024 / 1024,
                        'disk_percent': disk.percent,
                        'disk_free_gb': disk.free / 1024 / 1024 / 1024
                    }

                    with self.lock:
                        self.system_metrics.append(metric)

                    time.sleep(10)  # Monitor every 10 seconds
                except Exception as e:
                    logger.error(f"System monitoring error: {e}")
                    time.sleep(60)  # Wait longer on error
        thread = threading.Thread(target=monitor_system, daemon=True)
        thread.start()
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        with self.lock:
            if not self.system_metrics:
                return {}
            recent_metrics = list(self.system_metrics)[-10:]  # Last 10 samples

        if not recent_metrics:
            return {}

        # Calculate averages
        return {
            'current': recent_metrics[-1],
            'avg_cpu_percent': statistics.mean(m['cpu_percent'] for m in recent_metrics),
            'avg_memory_percent': statistics.mean(m['memory_percent'] for m in recent_metrics),
            'max_cpu_percent': max(m['cpu_percent'] for m in recent_metrics),
            'max_memory_percent': max(m['memory_percent'] for m in recent_metrics)
        }
    def check_alerts(self, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for performance alerts based on thresholds"""
        alerts = []

        # Check cache hit rate
        cache_stats = stats.get('cache_get', {})
        if cache_stats and cache_stats.get('count', 0) > 100:  # Enough samples
            hit_rate = cache_stats.get('success_rate', 1.0)
            if hit_rate < self.thresholds['cache_hit_rate']:
                alerts.append({
                    'type': 'cache_hit_rate',
                    'severity': 'warning',
                    'message': f'Cache hit rate {hit_rate:.2%} below threshold {self.thresholds["cache_hit_rate"]:.0%}',
                    'value': hit_rate,
                    'threshold': self.thresholds['cache_hit_rate']
                })

        # Check average response times
        for operation, op_stats in stats.items():
            if isinstance(op_stats, dict) and 'avg_duration_ms' in op_stats:
                avg_time = op_stats['avg_duration_ms']
                if avg_time > self.thresholds['avg_response_time_ms']:
                    alerts.append({
                        'type': 'slow_operation',
                        'severity': 'warning',
                        'operation': operation,
                        'message': f'{operation} avg response time {avg_time:.1f}ms exceeds threshold',
                        'value': avg_time,
                        'threshold': self.thresholds['avg_response_time_ms']
                    })
        # Check system resources
        system_metrics = stats.get('system', {})
        current = system_metrics.get('current', {})
        if current.get('memory_percent', 0) > self.thresholds['memory_usage_percent']:
            alerts.append({
                'type': 'high_memory',
                'severity': 'critical',
                'message': f'Memory usage {current["memory_percent"]:.1f}% exceeds threshold',
                'value': current['memory_percent'],
                'threshold': self.thresholds['memory_usage_percent']
            })
        # Notify alert callbacks
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")
        return alerts

    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add a callback to be notified of alerts"""
        self.alert_callbacks.append(callback)
    def export_metrics(self, filepath: str, time_window: Optional[timedelta] = None):
        """Export metrics to a JSON file"""
        stats = self.get_all_stats(time_window)

        # Convert to serializable format
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'time_window': str(time_window) if time_window else 'all',
            'stats': stats
        }

        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        logger.info(f"Metrics exported to {filepath}")

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get performance optimization recommendations"""
        recommendations = []
        stats = self.get_all_stats(timedelta(hours=1))  # Last hour
        # Cache recommendations
        cache_stats = stats.get('cache_get', {})
        if cache_stats:
            hit_rate = cache_stats.get('success_rate', 1.0)
            if hit_rate < 0.7:
                recommendations.append({
                    'category': 'caching',
                    'priority': 'high',
                    'recommendation': 'Increase cache TTL or implement cache warming',
                    'reason': f'Low cache hit rate: {hit_rate:.2%}'
                })
        # Operation performance recommendations
        slow_operations = []
        for operation, op_stats in stats.items():
            if isinstance(op_stats, dict) and op_stats.get('count', 0) > 10:
                p95 = op_stats.get('percentiles', {}).get('p95', 0)
                if p95 > 200:  # 200ms
                    slow_operations.append((operation, p95))
        if slow_operations:
            slow_operations.sort(key=lambda x: x[1], reverse=True)
            for operation, p95 in slow_operations[:3]:  # Top 3 slowest
                recommendations.append({
                    'category': 'performance',
                    'priority': 'medium',
                    'recommendation': f'Optimize {operation} operation',
                    'reason': f'95th percentile response time: {p95:.1f}ms'
                })

        # Memory recommendations
        system_metrics = stats.get('system', {})
        if system_metrics:
            avg_memory = system_metrics.get('avg_memory_percent', 0)
            if avg_memory > 70:
                recommendations.append({
                    'category': 'resources',
                    'priority': 'high',
                    'recommendation': 'Implement memory optimization or increase resources',
                    'reason': f'High average memory usage: {avg_memory:.1f}%'
                })
        return recommendations
# Global performance monitor instance
performance_monitor = PerformanceMonitor()
# Decorator for automatic performance monitoring
def monitor_performance(operation_name: Optional[str] = None):
    """Decorator to automatically monitor function performance"""
    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__name__}"
        def wrapper(*args, **kwargs):
            with performance_monitor.time_operation(operation_name) as timer:
                result = func(*args, **kwargs)
                # Add metadata if available
                if hasattr(result, '__len__'):
                    timer.metadata['result_size'] = len(result)
                return result
        return wrapper
    return decorator


# Additional performance monitoring utilities

class PerformanceAnalyzer:
    """Advanced performance analysis tools"""
    
    def __init__(self):
        self.analysis_cache = {}
        self.trend_data = defaultdict(list)
    
    def analyze_trends(self, metric_name: str, window_size: int = 100):
        """Analyze performance trends over time"""
        if metric_name not in self.trend_data:
            return None
        
        data = self.trend_data[metric_name]
        if len(data) < window_size:
            return None
        
        # Calculate moving average
        recent_data = data[-window_size:]
        avg = sum(recent_data) / len(recent_data)
        
        # Calculate trend direction
        first_half = sum(recent_data[:window_size//2]) / (window_size//2)
        second_half = sum(recent_data[window_size//2:]) / (window_size//2)
        
        trend = "improving" if second_half < first_half else "degrading"
        
        return {
            'average': avg,
            'trend': trend,
            'change_percent': ((second_half - first_half) / first_half) * 100
        }
    
    def get_bottlenecks(self):
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Analyze each metric
        for metric_name, values in self.trend_data.items():
            if not values:
                continue
            
            # Check if this metric is consistently high
            avg = sum(values[-100:]) / min(100, len(values))
            if avg > self.get_threshold(metric_name):
                bottlenecks.append({
                    'metric': metric_name,
                    'average': avg,
                    'severity': self.calculate_severity(avg, metric_name)
                })
        
        return sorted(bottlenecks, key=lambda x: x['severity'], reverse=True)
    
    def get_threshold(self, metric_name: str) -> float:
        """Get performance threshold for a metric"""
        thresholds = {
            'response_time': 1000,  # 1 second
            'memory_usage': 500,    # 500 MB
            'cpu_usage': 80,        # 80%
            'cache_miss_rate': 0.3  # 30%
        }
        return thresholds.get(metric_name, float('inf'))
    
    def calculate_severity(self, value: float, metric_name: str) -> int:
        """Calculate severity score (1-10)"""
        threshold = self.get_threshold(metric_name)
        if value <= threshold:
            return 1
        
        # Calculate how much over threshold
        over_threshold = value / threshold
        severity = min(10, int(over_threshold * 5))
        
        return severity
