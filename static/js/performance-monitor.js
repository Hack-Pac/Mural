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




















