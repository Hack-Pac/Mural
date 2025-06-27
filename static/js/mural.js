// Mural - Collaborative Pixel Art Application
class Mural {
    constructor() {
        this.canvas = document.getElementById('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.socket = io();
        this.selectedColor = '#000000';
        this.zoom = 1;
        this.panX = 0;
        this.panY = 0;
        this.isDragging = false;
        this.lastMouseX = 0;
        this.lastMouseY = 0;
        this.userPixelCount = 0;
        this.totalPixelCount = 0;
        this.cooldownTimer = null;
        this.cooldownRemaining = 0;
        
        // Color palette
        this.colors = [
            '#000000', '#FFFFFF', '#FF0000', '#00FF00',
            '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
            '#800000', '#008000', '#000080', '#808000',
            '#800080', '#008080', '#C0C0C0', '#808080',
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
            '#BB8FCE', '#85C1E9', '#F8C471', '#82E0AA',
            '#F1948A', '#85929E', '#D2B4DE', '#AED6F1'
        ];
        
        this.init();
    }
    
    init() {
        this.setupCanvas();
        this.setupColorPalette();
        this.setupEventListeners();
        this.setupSocketEvents();
        this.loadCanvas();
        this.checkCooldown();
        this.centerCanvas(); // Center the canvas on initialization
    }
    
    setupCanvas() {
        // Set canvas size
        this.canvas.width = 1000;
        this.canvas.height = 1000;
        
        // Fill with white background
        this.ctx.fillStyle = '#FFFFFF';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Set pixel art rendering
        this.ctx.imageSmoothingEnabled = false;
    }
    
    centerCanvas() {
        // Center the canvas so that pixel (500, 500) is in the center of the viewport
        const container = this.canvas.parentElement;
        
        // Get actual container dimensions
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;
        
        // Calculate the center of the container
        const centerX = containerWidth / 2;
        const centerY = containerHeight / 2;
        
        // Calculate pan offset to center (500, 500)
        // We want canvas pixel (500, 500) to be at the center of the container
        this.panX = centerX - (500 * this.zoom);
        this.panY = centerY - (500 * this.zoom);
        
        this.updateCanvasTransform();
    }
    
    setupColorPalette() {
        const palette = document.getElementById('color-palette');
        
        this.colors.forEach((color, index) => {
            const colorDiv = document.createElement('div');
            colorDiv.className = 'color-picker w-8 h-8 rounded cursor-pointer border-2 border-gray-600';
            colorDiv.style.backgroundColor = color;
            colorDiv.dataset.color = color;
            
            if (index === 0) {
                colorDiv.classList.add('selected');
                this.updateSelectedColor(color);
            }
            
            colorDiv.addEventListener('click', () => {
                // Remove selected class from all colors
                document.querySelectorAll('.color-picker').forEach(el => {
                    el.classList.remove('selected');
                });
                
                // Add selected class to clicked color
                colorDiv.classList.add('selected');
                this.selectedColor = color;
                this.updateSelectedColor(color);
            });
            
            palette.appendChild(colorDiv);
        });
    }
    
    updateSelectedColor(color) {
        document.getElementById('selected-color').style.backgroundColor = color;
        document.getElementById('selected-color-hex').textContent = color;
    }
    
    setupEventListeners() {
        // Canvas click event
        this.canvas.addEventListener('click', (e) => {
            if (!this.isDragging) {
                const rect = this.canvas.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                
                // Convert screen coordinates to canvas coordinates
                const x = Math.floor((mouseX - this.panX) / this.zoom);
                const y = Math.floor((mouseY - this.panY) / this.zoom);
                
                this.placePixel(x, y, this.selectedColor);
            }
        });
        
        // Mouse move for coordinates display
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            
            // Convert screen coordinates to canvas coordinates
            const x = Math.floor((mouseX - this.panX) / this.zoom);
            const y = Math.floor((mouseY - this.panY) / this.zoom);
            
            document.getElementById('cursor-coords').textContent = `${x}, ${y}`;
            
            if (this.isDragging) {
                const deltaX = e.clientX - this.lastMouseX;
                const deltaY = e.clientY - this.lastMouseY;
                this.panX += deltaX;
                this.panY += deltaY;
                this.updateCanvasTransform();
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
            }
        });
        
        // Pan functionality
        this.canvas.addEventListener('mousedown', (e) => {
            if (e.button === 1 || e.ctrlKey) { // Middle click or Ctrl+click
                e.preventDefault();
                this.isDragging = true;
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
                this.canvas.style.cursor = 'grabbing';
            }
        });
        
        document.addEventListener('mouseup', () => {
            this.isDragging = false;
            this.canvas.style.cursor = 'crosshair';
        });
        
        // Zoom controls
        document.getElementById('zoom-in').addEventListener('click', () => {
            this.zoomAt(1.2);
        });
        
        document.getElementById('zoom-out').addEventListener('click', () => {
            this.zoomAt(1/1.2);
        });
        
        document.getElementById('reset-view').addEventListener('click', () => {
            this.zoom = 1;
            this.centerCanvas();
            this.updateZoomDisplay();
        });
        
        // Mouse wheel zoom
        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const rect = this.canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            
            const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomAtPoint(zoomFactor, mouseX, mouseY);
        });
        
        // Window resize handler to maintain centering
        window.addEventListener('resize', () => {
            // Re-center the canvas when window is resized
            setTimeout(() => {
                this.centerCanvas();
            }, 100); // Small delay to ensure layout has updated
        });
    }
    
    updateCanvasTransform() {
        this.canvas.style.transform = `scale(${this.zoom}) translate(${this.panX / this.zoom}px, ${this.panY / this.zoom}px)`;
    }
    
    updateZoomDisplay() {
        document.getElementById('zoom-level').textContent = `${Math.round(this.zoom * 100)}%`;
    }
    
    zoomAt(factor) {
        // Zoom centered around (500, 500)
        const newZoom = Math.max(0.1, Math.min(10, this.zoom * factor));
        
        if (newZoom !== this.zoom) {
            // Calculate the center point (500, 500) in screen coordinates
            const container = this.canvas.parentElement;
            const centerX = container.clientWidth / 2;
            const centerY = container.clientHeight / 2;
            
            // Adjust pan to keep (500, 500) centered
            this.panX = centerX - (500 * newZoom);
            this.panY = centerY - (500 * newZoom);
            
            this.zoom = newZoom;
            this.updateCanvasTransform();
            this.updateZoomDisplay();
        }
    }
    
    zoomAtPoint(factor, mouseX, mouseY) {
        // Zoom at a specific point (for mouse wheel)
        const newZoom = Math.max(0.1, Math.min(10, this.zoom * factor));
        
        if (newZoom !== this.zoom) {
            // Calculate canvas coordinates of the mouse position
            const canvasX = (mouseX - this.panX) / this.zoom;
            const canvasY = (mouseY - this.panY) / this.zoom;
            
            // Update zoom
            this.zoom = newZoom;
            
            // Adjust pan to keep the same point under the mouse
            this.panX = mouseX - (canvasX * this.zoom);
            this.panY = mouseY - (canvasY * this.zoom);
            
            this.updateCanvasTransform();
            this.updateZoomDisplay();
        }
    }
    
    setupSocketEvents() {
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.addActivity('Connected to Mural', 'system');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.addActivity('Disconnected from Mural', 'system');
        });
        
        this.socket.on('pixel_placed', (data) => {
            this.drawPixel(data.x, data.y, data.color);
            this.addActivity(`Pixel placed at (${data.x}, ${data.y})`, 'pixel');
            this.updateStats();
        });
        
        this.socket.on('canvas_update', (canvasData) => {
            this.loadCanvasData(canvasData);
        });
    }
    
    async loadCanvas() {
        try {
            const response = await fetch('/api/canvas');
            const canvasData = await response.json();
            this.loadCanvasData(canvasData);
        } catch (error) {
            console.error('Failed to load canvas:', error);
            this.addActivity('Failed to load canvas', 'error');
        }
    }
    
    loadCanvasData(canvasData) {
        // Clear canvas
        this.ctx.fillStyle = '#FFFFFF';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw pixels
        Object.entries(canvasData).forEach(([key, pixelData]) => {
            const [x, y] = key.split(',').map(Number);
            this.drawPixel(x, y, pixelData.color);
        });
        
        this.totalPixelCount = Object.keys(canvasData).length;
        this.updateStats();
    }
    
    drawPixel(x, y, color) {
        this.ctx.fillStyle = color;
        this.ctx.fillRect(x, y, 1, 1);
    }
    
    async placePixel(x, y, color) {
        if (x < 0 || x >= this.canvas.width || y < 0 || y >= this.canvas.height) {
            this.addActivity('Pixel out of bounds!', 'error');
            return;
        }
        
        // Check if cooldown is active
        if (this.cooldownRemaining > 0) {
            this.addActivity(`Cooldown active! Wait ${this.formatTime(this.cooldownRemaining)}`, 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/place-pixel', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ x, y, color })
            });
            
            const result = await response.json();
            
            if (response.status === 429) {
                // Cooldown active
                this.startCooldown(result.cooldown_remaining);
                this.addActivity(`Cooldown active! Wait ${this.formatTime(result.cooldown_remaining)}`, 'error');
            } else if (result.success) {
                this.userPixelCount++;
                this.addActivity(`You placed a pixel at (${x}, ${y})`, 'user');
                this.startCooldown(result.cooldown_remaining);
            } else {
                this.addActivity(`Failed to place pixel: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Failed to place pixel:', error);
            this.addActivity('Failed to place pixel', 'error');
        }
    }
    
    async checkCooldown() {
        try {
            const response = await fetch('/api/cooldown');
            const result = await response.json();
            
            if (result.cooldown_remaining > 0) {
                this.startCooldown(result.cooldown_remaining);
            }
        } catch (error) {
            console.error('Failed to check cooldown:', error);
        }
    }
    
    startCooldown(seconds) {
        this.cooldownRemaining = seconds;
        this.updateCooldownDisplay();
        
        if (this.cooldownTimer) {
            clearInterval(this.cooldownTimer);
        }
        
        this.cooldownTimer = setInterval(() => {
            this.cooldownRemaining--;
            this.updateCooldownDisplay();
            
            if (this.cooldownRemaining <= 0) {
                clearInterval(this.cooldownTimer);
                this.cooldownTimer = null;
                this.addActivity('Cooldown expired! You can place another pixel.', 'info');
            }
        }, 1000);
    }
    
    updateCooldownDisplay() {
        const cooldownElement = document.getElementById('cooldown-status');
        const cooldownSidebarElement = document.getElementById('cooldown-status-sidebar');
        
        if (this.cooldownRemaining > 0) {
            const timeText = this.formatTime(this.cooldownRemaining);
            const cooldownText = `Cooldown: ${timeText}`;
            
            if (cooldownElement) {
                cooldownElement.textContent = cooldownText;
                cooldownElement.className = 'text-red-400 text-sm';
            }
            if (cooldownSidebarElement) {
                cooldownSidebarElement.textContent = timeText;
                cooldownSidebarElement.className = 'text-red-400 text-sm font-medium';
            }
        } else {
            if (cooldownElement) {
                cooldownElement.textContent = 'Ready to place pixel';
                cooldownElement.className = 'text-green-400 text-sm';
            }
            if (cooldownSidebarElement) {
                cooldownSidebarElement.textContent = 'Ready';
                cooldownSidebarElement.className = 'text-green-400 text-sm font-medium';
            }
        }
    }
    
    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`;
    }
    
    addActivity(message, type = 'info') {
        const feed = document.getElementById('activity-feed');
        const activity = document.createElement('div');
        activity.className = 'flex items-center space-x-2 text-xs';
        
        const timestamp = new Date().toLocaleTimeString();
        const typeIcon = {
            'system': '🔗',
            'pixel': '🎨',
            'user': '👤',
            'error': '❌',
            'info': 'ℹ️'
        };
        
        activity.innerHTML = `
            <span class="text-gray-500">${timestamp}</span>
            <span>${typeIcon[type] || typeIcon['info']}</span>
            <span class="flex-1">${message}</span>
        `;
        
        feed.insertBefore(activity, feed.firstChild);
        
        // Keep only the last 50 activities
        while (feed.children.length > 50) {
            feed.removeChild(feed.lastChild);
        }
    }
    
    updateStats() {
        document.getElementById('total-pixels').textContent = this.totalPixelCount.toLocaleString();
        document.getElementById('user-pixels').textContent = this.userPixelCount.toLocaleString();
    }
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new Mural();
});
