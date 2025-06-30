// Performance Monitoring Module for Mural
class PerformanceMonitor {
    constructor() {
        this.metrics = {
            renderTime: [],
            fps: [],
            messageQueue: [],
            memoryUsage: []
        };
        this.maxSamples = 60; // Keep last 60 samples
        this.enabled = false;
        this.lastFrameTime = 0;
        // Create performance overlay
        this.createOverlay();
    }
    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.id = 'perf-monitor';
        this.overlay.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.8);
            color: #00ff00;
            font-family: monospace;
            font-size: 12px;
            padding: 10px;
            border-radius: 5px;
            z-index: 10000;
            display: none;
            min-width: 200px;
        `;
        document.body.appendChild(this.overlay);
    }
    toggle() {
        this.enabled = !this.enabled;
        this.overlay.style.display = this.enabled ? 'block' : 'none';
        if (this.enabled) {
            this.startMonitoring();
        } else {
            this.stopMonitoring();
        }
    }
    startMonitoring() {
        this.monitoringInterval = setInterval(() => {
            this.updateMetrics();
        }, 1000);
        // Start FPS monitoring
        this.measureFPS();
    }
    stopMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
        }
    }
    measureFPS() {
        if (!this.enabled) return;
        const currentTime = performance.now();
        if (this.lastFrameTime > 0) {
            const fps = 1000 / (currentTime - this.lastFrameTime);
            this.addMetric('fps', fps);
        }
        this.lastFrameTime = currentTime;
        requestAnimationFrame(() => this.measureFPS());
    }
    addMetric(type, value) {
        if (!this.metrics[type]) {
            this.metrics[type] = [];
        }
        this.metrics[type].push(value);
        // Keep only last N samples
        if (this.metrics[type].length > this.maxSamples) {
            this.metrics[type].shift();
        }
    }
    recordRenderTime(time) {
        this.addMetric('renderTime', time);
    }
    recordMessageQueueSize(size) {
        this.addMetric('messageQueue', size);
    }
    updateMetrics() {
        // Get memory usage if available
        if (performance.memory) {
            const memoryMB = performance.memory.usedJSHeapSize / (1024 * 1024);
            this.addMetric('memoryUsage', memoryMB);
        }
        // Calculate averages
        const avgFPS = this.getAverage('fps');
        const avgRenderTime = this.getAverage('renderTime');
        const avgQueueSize = this.getAverage('messageQueue');
        const currentMemory = this.metrics.memoryUsage[this.metrics.memoryUsage.length - 1] || 0;
        // Update overlay
        this.overlay.innerHTML = `
            <div><strong>Performance Monitor</strong></div>
            <div>FPS: ${avgFPS.toFixed(1)}</div>
            <div>Render: ${avgRenderTime.toFixed(2)}ms</div>
            <div>Queue: ${avgQueueSize.toFixed(0)} msgs</div>
            <div>Memory: ${currentMemory.toFixed(1)}MB</div>
            <div style="margin-top: 5px; font-size: 10px;">Press P to toggle</div>
        `;
    }
    getAverage(type) {
        const values = this.metrics[type];
        if (!values || values.length === 0) return 0;
        const sum = values.reduce((a, b) => a + b, 0);
        return sum / values.length;
    }
}
// Export for use in main application
window.PerformanceMonitor = PerformanceMonitor;
// Extended performance monitoring
class PerformanceMonitor {
    constructor() {
        this.metrics = new Map();
        this.observers = new Map();
        this.init();
    }
    
    init() {
        this.setupPerformanceObserver();
        this.setupResourceTimingObserver();
        this.setupLongTaskObserver();
        this.setupMemoryMonitoring();
    }
    
    setupPerformanceObserver() {
        if ('PerformanceObserver' in window) {
            // Monitor navigation timing
            const navigationObserver = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    this.recordMetric('navigation', {
                        domContentLoaded: entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart,
                        loadComplete: entry.loadEventEnd - entry.loadEventStart,
                        totalTime: entry.loadEventEnd - entry.fetchStart
                    });
                }
            });
            navigationObserver.observe({ entryTypes: ['navigation'] });
            this.observers.set('navigation', navigationObserver);
        }
    }
    setupResourceTimingObserver() {
        if ('PerformanceObserver' in window) {
            const resourceObserver = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    this.recordMetric('resource', {
                        name: entry.name,
                        duration: entry.duration,
                        size: entry.transferSize,
                        type: entry.initiatorType
                    });
                }
            });
            resourceObserver.observe({ entryTypes: ['resource'] });
            this.observers.set('resource', resourceObserver);
        }
    }
    setupLongTaskObserver() {
        if ('PerformanceObserver' in window && 'PerformanceLongTaskTiming' in window) {
            const longTaskObserver = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    this.recordMetric('longTask', {
                        duration: entry.duration,
                        startTime: entry.startTime,
                        attribution: entry.attribution
                    });
                    
                    // Warn about long tasks
                    if (entry.duration > 100) {
                        console.warn(`Long task detected: ${entry.duration}ms`);
                    }
                }
            });
            longTaskObserver.observe({ entryTypes: ['longtask'] });
            this.observers.set('longtask', longTaskObserver);
        }
    }
    setupMemoryMonitoring() {
        if ('memory' in performance) {
            setInterval(() => {
                const memory = performance.memory;
                this.recordMetric('memory', {
                    usedJSHeapSize: memory.usedJSHeapSize,
                    totalJSHeapSize: memory.totalJSHeapSize,
                    jsHeapSizeLimit: memory.jsHeapSizeLimit
                });
            }, 10000); // Check every 10 seconds
        }
    }
    recordMetric(type, data) {
        if (!this.metrics.has(type)) {
            this.metrics.set(type, []);
        }
        const metric = {
            timestamp: Date.now(),
            ...data
        };
        
        this.metrics.get(type).push(metric);
        
        // Keep only last 100 entries per type
        const metrics = this.metrics.get(type);
        if (metrics.length > 100) {
            metrics.shift();
        }
    }
    getMetrics(type) {
        return this.metrics.get(type) || [];
    }
    
    getAllMetrics() {
        const result = {};
        for (const [type, metrics] of this.metrics) {
            result[type] = metrics;
        }
        return result;
    }
    generateReport() {
        const report = {
            timestamp: new Date().toISOString(),
            metrics: this.getAllMetrics(),
            summary: this.generateSummary()
        };
        
        return report;
    }
    generateSummary() {
        const summary = {};
        // Navigation summary
        const navigationMetrics = this.getMetrics('navigation');
        if (navigationMetrics.length > 0) {
            const latest = navigationMetrics[navigationMetrics.length - 1];
            summary.navigation = {
                totalLoadTime: latest.totalTime,
                domContentLoaded: latest.domContentLoaded
            };
        }
        
        // Resource summary
        const resourceMetrics = this.getMetrics('resource');
        if (resourceMetrics.length > 0) {
            const totalSize = resourceMetrics.reduce((sum, r) => sum + (r.size || 0), 0);
            const avgDuration = resourceMetrics.reduce((sum, r) => sum + r.duration, 0) / resourceMetrics.length;
            summary.resources = {
                count: resourceMetrics.length,
                totalSize: totalSize,
                averageDuration: avgDuration
            };
        }
        // Memory summary
        const memoryMetrics = this.getMetrics('memory');
        if (memoryMetrics.length > 0) {
            const latest = memoryMetrics[memoryMetrics.length - 1];
            summary.memory = {
                used: latest.usedJSHeapSize,
                total: latest.totalJSHeapSize,
                limit: latest.jsHeapSizeLimit,
                usagePercent: (latest.usedJSHeapSize / latest.jsHeapSizeLimit) * 100
            };
        }
        
        return summary;
    }
}
// Initialize performance monitor
const performanceMonitor = new PerformanceMonitor();

































