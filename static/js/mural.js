// Optimized utilities inspired by the provided implementation
const MuralUtils = {
    // Enhanced fetch wrapper with better error handling
    ajax: {
        request: function(url, options = {}, showError = true) {
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                },
                ...options
            };

            return fetch(url, defaultOptions)
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(data => {
                            throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
                        }).catch(() => {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                        });
                    }
                    return response.json();
                })
                .catch(error => {
                    if (showError) {
                        this.showError(error.message || 'An unknown error occurred');
                    }
                    throw error;
                });
        },

        get: function(url, showError = true) {
            return this.request(url, { method: 'GET' }, showError);
        },

        post: function(url, data = null, showError = true) {
            return this.request(url, {
                method: 'POST',
                body: data ? JSON.stringify(data) : null
            }, showError);
        },

        showError: function(message) {
            // Create a toast-style error notification
            const errorDiv = document.createElement('div');
            errorDiv.className = 'fixed top-4 right-4 bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 transform translate-x-full transition-transform duration-300';
            errorDiv.innerHTML = `
                <div class="flex items-center space-x-2">
                    <span>❌</span>
                    <span>${message}</span>
                    <button class="ml-2 text-white hover:text-gray-200" onclick="this.parentElement.parentElement.remove()">✕</button>
                </div>
            `;
            
            document.body.appendChild(errorDiv);
            
            // Slide in
            setTimeout(() => {
                errorDiv.classList.remove('translate-x-full');
            }, 10);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (errorDiv.parentElement) {
                    errorDiv.classList.add('translate-x-full');
                    setTimeout(() => errorDiv.remove(), 300);
                }
            }, 5000);
        }
    },

    // Hash management for state persistence
    hash: {
        get: function() {
            return this.decode(window.location.hash);
        },

        set: function(hash) {
            const encoded = this.encode(hash);
            if (window.history) {
                window.history.replaceState(undefined, undefined, '#' + encoded);
            } else {
                location.replace('#' + encoded);
            }
        },

        modify: function(newHash) {
            this.set(Object.assign(this.get(), newHash));
        },

        remove: function(keys) {
            const keysArray = Array.isArray(keys) ? keys : [keys];
            const hash = this.get();
            keysArray.forEach(key => delete hash[key]);
            this.set(hash);
        },

        decode: function(hashString) {
            if (hashString.indexOf('#') === 0) hashString = hashString.substring(1);
            if (hashString.length <= 0) return {};
            
            const params = new URLSearchParams(hashString);
            const decoded = {};
            for (const [key, value] of params) {
                decoded[key] = decodeURIComponent(value);
            }
            return decoded;
        },

        encode: function(hash) {
            return new URLSearchParams(hash).toString();
        }
    },

    // Enhanced DOM utilities
    dom: {
        create: function(tag, className = '', attributes = {}) {
            const element = document.createElement(tag);
            if (className) element.className = className;
            Object.entries(attributes).forEach(([key, value]) => {
                element.setAttribute(key, value);
            });
            return element;
        },

        animate: function(element, className, duration = 300) {
            return new Promise(resolve => {
                element.classList.add(className);
                setTimeout(() => {
                    element.classList.remove(className);
                    resolve();
                }, duration);
            });
        }
    },

    // Debounce utility for performance
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Mural - Collaborative Pixel Art Application with Optimized Rendering
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
        this.dragStartTime = 0;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.lastMouseX = 0;
        this.lastMouseY = 0;
        this.userPixelCount = 0;
        this.totalPixelCount = 0;
        this.cooldownTimer = null;
        this.cooldownRemaining = 0;
        
        // Performance optimizations
        this.debouncedUpdateCoords = MuralUtils.debounce(this.updateCoordinateDisplay.bind(this), 16); // ~60fps
        
        // Pre-rendered canvas system
        this.pixelData = new Map(); // Store pixel data efficiently
        this.needsRedraw = true;
        this.isRendering = false;
        
        // Viewport settings - will be set dynamically
        this.viewportWidth = 600; // initial fallback
        this.viewportHeight = 600; // initial fallback
        this.originalWidth = 500;
        this.originalHeight = 500;
        
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
        
        // Start with 1:1 zoom
        this.zoom = 1;
        this.updateZoomDisplay();
        this.centerCanvas(); // Center the canvas on initialization
        
        // Restore state from URL hash if available
        this.restoreStateFromHash();
        
        // Handle browser back/forward
        window.addEventListener('hashchange', () => this.restoreStateFromHash());
    }
    
    setupCanvas() {
        // Get actual container size
        const container = this.canvas.parentElement;
        this.viewportWidth = container.clientWidth;
        this.viewportHeight = container.clientHeight;
        
        // Set canvas to match viewport size
        this.canvas.width = this.viewportWidth;
        this.canvas.height = this.viewportHeight;
        
        // Set pixel art rendering
        this.ctx.imageSmoothingEnabled = false;
        
        // Set initial zoom and position
        this.zoom = 1;
        this.panX = 0;
        this.panY = 0;
        
        // Center the view initially
        this.centerCanvas();
        
        // Start render loop
        this.startRenderLoop();
    }
    
    centerCanvas() {
        // Calculate the best fit zoom that ensures the 500x500 canvas fills the viewport
        const zoomX = this.viewportWidth / this.originalWidth;
        const zoomY = this.viewportHeight / this.originalHeight;
        const minZoom = Math.max(zoomX, zoomY); // Use the larger zoom to ensure full coverage
        
        // Set zoom to at least the minimum required to fill viewport
        if (this.zoom < minZoom) {
            this.zoom = minZoom;
        }
        
        // Center the view on the middle of the canvas
        this.panX = (this.viewportWidth - this.originalWidth * this.zoom) / 2;
        this.panY = (this.viewportHeight - this.originalHeight * this.zoom) / 2;
        
        // Apply clamping to ensure no out-of-bounds is visible
        this.panX = this.clampPan(this.panX, 'x');
        this.panY = this.clampPan(this.panY, 'y');
        
        this.needsRedraw = true;
    }
    
    startRenderLoop() {
        const render = () => {
            if (this.needsRedraw && !this.isRendering) {
                this.renderCanvas();
            }
            requestAnimationFrame(render);
        };
        requestAnimationFrame(render);
    }
    
    renderCanvas() {
        this.isRendering = true;
        this.needsRedraw = false;
        
        // Clear canvas with white background
        this.ctx.fillStyle = '#FFFFFF';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Calculate visible region
        const startX = Math.max(0, Math.floor(-this.panX / this.zoom));
        const startY = Math.max(0, Math.floor(-this.panY / this.zoom));
        const endX = Math.min(this.originalWidth, Math.ceil((this.viewportWidth - this.panX) / this.zoom));
        const endY = Math.min(this.originalHeight, Math.ceil((this.viewportHeight - this.panY) / this.zoom));
        
        // Only render visible pixels for performance
        for (let x = startX; x < endX; x++) {
            for (let y = startY; y < endY; y++) {
                const pixelKey = `${x},${y}`;
                const pixelColor = this.pixelData.get(pixelKey);
                
                if (pixelColor) {
                    const screenX = Math.floor(this.panX + x * this.zoom);
                    const screenY = Math.floor(this.panY + y * this.zoom);
                    const pixelSize = Math.ceil(this.zoom);
                    
                    this.ctx.fillStyle = pixelColor;
                    this.ctx.fillRect(screenX, screenY, pixelSize, pixelSize);
                }
            }
        }
        
        this.isRendering = false;
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
                
                // Save color selection to hash
                this.saveStateToHash();
            });
            
            palette.appendChild(colorDiv);
        });
    }
    
    updateSelectedColor(color) {
        document.getElementById('selected-color').style.backgroundColor = color;
        document.getElementById('selected-color-hex').textContent = color;
    }
    
    setupEventListeners() {
        // Canvas click event - Optimized for direct coordinate calculation
        this.canvas.addEventListener('click', (e) => {
            // Only place pixel if we're not in the middle of a drag operation
            // and the click wasn't generated by the drag detection logic
            if (!this.isDragging && !e.isTrusted) {
                const rect = this.canvas.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                
                // Convert screen coordinates to canvas coordinates
                const x = Math.floor((mouseX - this.panX) / this.zoom);
                const y = Math.floor((mouseY - this.panY) / this.zoom);
                
                // Only place pixel if coordinates are valid
                if (x >= 0 && x < this.originalWidth && y >= 0 && y < this.originalHeight) {
                    this.placePixel(x, y, this.selectedColor);
                }
            }
        });
        
        // Mouse move for coordinates display - Optimized
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            
            // Convert screen coordinates to canvas coordinates
            const x = Math.floor((mouseX - this.panX) / this.zoom);
            const y = Math.floor((mouseY - this.panY) / this.zoom);
            
            // Use debounced coordinate update for better performance
            const isValid = x >= 0 && x < this.originalWidth && y >= 0 && y < this.originalHeight;
            this.debouncedUpdateCoords(x, y, isValid);

            if (this.isDragging) {
                const deltaX = e.clientX - this.lastMouseX;
                const deltaY = e.clientY - this.lastMouseY;
                
                // Apply delta directly without clamping for smooth movement
                this.panX += deltaX;
                this.panY += deltaY;
                
                // Clamp after movement
                this.panX = this.clampPan(this.panX, 'x');
                this.panY = this.clampPan(this.panY, 'y');
                
                this.needsRedraw = true;
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
                
                // Save state when panning
                this.saveStateToHash();
            }
        });
        
        // Pan functionality - Enhanced to support regular click and drag
        this.canvas.addEventListener('mousedown', (e) => {
            // Allow panning with left click, middle click, or Ctrl+click
            if (e.button === 0 || e.button === 1 || e.ctrlKey) {
                e.preventDefault();
                this.isDragging = true;
                this.dragStartTime = Date.now();
                this.dragStartX = e.clientX;
                this.dragStartY = e.clientY;
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
                this.canvas.style.cursor = 'grabbing';
                
                // Prevent text selection while dragging
                document.body.style.userSelect = 'none';
            }
        });
        
        document.addEventListener('mouseup', (e) => {
            if (this.isDragging) {
                const dragEndTime = Date.now();
                const dragDuration = dragEndTime - this.dragStartTime;
                const dragDistance = Math.sqrt(
                    Math.pow(e.clientX - this.dragStartX, 2) + 
                    Math.pow(e.clientY - this.dragStartY, 2)
                );
                
                this.isDragging = false;
                document.body.style.userSelect = '';
                
                // If it was a very short drag (< 200ms) and small distance (< 5px), 
                // treat it as a click for pixel placement
                if (dragDuration < 200 && dragDistance < 5) {
                    // Trigger a click event for pixel placement
                    const clickEvent = new MouseEvent('click', {
                        clientX: this.dragStartX,
                        clientY: this.dragStartY,
                        bubbles: true
                    });
                    this.canvas.dispatchEvent(clickEvent);
                }
                
                // Reset cursor based on current mouse position
                const moveEvent = new MouseEvent('mousemove', {
                    clientX: e.clientX,
                    clientY: e.clientY
                });
                this.canvas.dispatchEvent(moveEvent);
            }
        });
        
        // Zoom controls
        document.getElementById('zoom-in').addEventListener('click', () => {
            this.zoomAt(1.2);
        });
        
        document.getElementById('zoom-out').addEventListener('click', () => {
            this.zoomAt(1/1.2);
        });
        
        document.getElementById('reset-view').addEventListener('click', () => {
            // Calculate the minimum zoom needed to fill the viewport
            const zoomX = this.viewportWidth / this.originalWidth;
            const zoomY = this.viewportHeight / this.originalHeight;
            this.zoom = Math.max(zoomX, zoomY); // Ensure no out-of-bounds is visible
            
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
        
        // Window resize handler to update viewport and maintain centering
        window.addEventListener('resize', () => {
            // Update viewport size and re-center the canvas when window is resized
            setTimeout(() => {
                const container = this.canvas.parentElement;
                this.viewportWidth = container.clientWidth;
                this.viewportHeight = container.clientHeight;
                
                // Resize canvas to match new container size
                this.canvas.width = this.viewportWidth;
                this.canvas.height = this.viewportHeight;
                
                this.centerCanvas();
                this.needsRedraw = true;
            }, 100); // Small delay to ensure layout has updated
        });
    }
    
    updateCanvasTransform() {
        // No longer needed - we use direct rendering
        this.needsRedraw = true;
    }
    
    clampPan(panValue, axis) {
        const containerSize = axis === 'x' ? this.viewportWidth : this.viewportHeight;
        const canvasDisplaySize = axis === 'x' ? 
            (this.originalWidth * this.zoom) : 
            (this.originalHeight * this.zoom);
        
        // Calculate the maximum and minimum pan values to prevent showing out-of-bounds
        const maxPan = 0; // Can't pan beyond the top-left (0,0)
        const minPan = containerSize - canvasDisplaySize; // Can't pan beyond bottom-right
        
        // Always clamp to prevent showing any white space/out-of-bounds
        return Math.max(minPan, Math.min(maxPan, panValue));
    }
    
    updateZoomDisplay() {
        document.getElementById('zoom-level').textContent = `${Math.round(this.zoom * 100)}%`;
    }
    
    zoomAt(factor) {
        // Calculate minimum zoom to prevent showing out-of-bounds
        const zoomX = this.viewportWidth / this.originalWidth;
        const zoomY = this.viewportHeight / this.originalHeight;
        const minZoom = Math.max(zoomX, zoomY);
        
        // Zoom centered around the center of the container
        const newZoom = Math.max(minZoom, Math.min(10, this.zoom * factor));
        
        if (newZoom !== this.zoom) {
            const containerCenterX = this.viewportWidth / 2;
            const containerCenterY = this.viewportHeight / 2;
            
            // Calculate the canvas point that's currently at the center
            const canvasPointX = (containerCenterX - this.panX) / this.zoom;
            const canvasPointY = (containerCenterY - this.panY) / this.zoom;
            
            // Update zoom
            this.zoom = newZoom;
            
            // Calculate new pan to keep the same canvas point at the center
            const newPanX = containerCenterX - (canvasPointX * this.zoom);
            const newPanY = containerCenterY - (canvasPointY * this.zoom);
            
            // Apply boundary constraints
            this.panX = this.clampPan(newPanX, 'x');
            this.panY = this.clampPan(newPanY, 'y');
            
            this.needsRedraw = true;
            this.updateZoomDisplay();
            
            // Save state to hash
            this.saveStateToHash();
        }
    }
    
    zoomAtPoint(factor, mouseX, mouseY) {
        // Calculate minimum zoom to prevent showing out-of-bounds
        const zoomX = this.viewportWidth / this.originalWidth;
        const zoomY = this.viewportHeight / this.originalHeight;
        const minZoom = Math.max(zoomX, zoomY);
        
        // Zoom at a specific point (for mouse wheel)
        const newZoom = Math.max(minZoom, Math.min(10, this.zoom * factor));
        
        if (newZoom !== this.zoom) {
            // Calculate canvas coordinates of the mouse position
            const canvasX = (mouseX - this.panX) / this.zoom;
            const canvasY = (mouseY - this.panY) / this.zoom;
            
            // Update zoom
            this.zoom = newZoom;
            
            // Calculate new pan to keep the same point under the mouse
            const newPanX = mouseX - (canvasX * this.zoom);
            const newPanY = mouseY - (canvasY * this.zoom);
            
            // Apply boundary constraints
            this.panX = this.clampPan(newPanX, 'x');
            this.panY = this.clampPan(newPanY, 'y');
            
            this.needsRedraw = true;
            this.updateZoomDisplay();
        }
    }
    
    // State management methods
    saveStateToHash() {
        MuralUtils.hash.modify({
            zoom: this.zoom.toFixed(2),
            panX: Math.round(this.panX),
            panY: Math.round(this.panY),
            color: this.selectedColor
        });
    }

    restoreStateFromHash() {
        const state = MuralUtils.hash.get();
        
        if (state.zoom) {
            this.zoom = parseFloat(state.zoom);
            this.updateZoomDisplay();
        }
        
        if (state.panX !== undefined && state.panY !== undefined) {
            this.panX = parseInt(state.panX);
            this.panY = parseInt(state.panY);
        }
        
        if (state.color && this.colors.includes(state.color)) {
            this.selectedColor = state.color;
            this.updateSelectedColor(state.color);
            // Update UI to show selected color
            document.querySelectorAll('.color-picker').forEach(el => {
                el.classList.remove('selected');
                if (el.dataset.color === state.color) {
                    el.classList.add('selected');
                }
            });
        }
        
        this.needsRedraw = true;
    }

    // Optimized coordinate display update
    updateCoordinateDisplay(x, y, isValid) {
        const coordsElement = document.getElementById('cursor-coords');
        if (isValid) {
            coordsElement.textContent = `${x}, ${y}`;
            coordsElement.className = 'text-green-400';
            // Set cursor based on drag state
            this.canvas.style.cursor = this.isDragging ? 'grabbing' : 'crosshair';
        } else {
            coordsElement.textContent = 'Outside canvas';
            coordsElement.className = 'text-gray-500';
            this.canvas.style.cursor = this.isDragging ? 'grabbing' : 'grab';
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
            const canvasData = await MuralUtils.ajax.get('/api/canvas', false);
            this.loadCanvasData(canvasData);
        } catch (error) {
            console.error('Failed to load canvas:', error);
            this.addActivity('Failed to load canvas', 'error');
        }
    }
    
    loadCanvasData(canvasData) {
        // Clear pixel data
        this.pixelData.clear();
        
        // Store pixels in our efficient map
        Object.entries(canvasData).forEach(([key, pixelData]) => {
            this.pixelData.set(key, pixelData.color);
        });
        
        this.totalPixelCount = Object.keys(canvasData).length;
        this.updateStats();
        this.needsRedraw = true;
    }
    
    drawPixel(x, y, color) {
        // Store pixel in our map
        const key = `${x},${y}`;
        this.pixelData.set(key, color);
        this.needsRedraw = true;
    }
    
    async placePixel(x, y, color) {
        // At this point, coordinates should already be validated, but double-check
        if (!Number.isInteger(x) || !Number.isInteger(y) || 
            x < 0 || x >= this.originalWidth || y < 0 || y >= this.originalHeight) {
            return; // Silently ignore invalid coordinates
        }
        
        // Check if cooldown is active
        if (this.cooldownRemaining > 0) {
            MuralUtils.ajax.showError(`Cooldown active! Wait ${this.formatTime(this.cooldownRemaining)}`);
            return;
        }
        
        try {
            const result = await MuralUtils.ajax.post('/api/place-pixel', { x, y, color }, false);
            
            this.userPixelCount++;
            this.addActivity(`You placed a pixel at (${x}, ${y})`, 'user');
            this.startCooldown(result.cooldown_remaining);
            
        } catch (error) {
            if (error.message.includes('429')) {
                // Extract cooldown from error if available
                const match = error.message.match(/(\d+)/);
                const cooldown = match ? parseInt(match[1]) : 60;
                this.startCooldown(cooldown);
            }
            // Error is already displayed by MuralUtils.ajax
            console.error('Failed to place pixel:', error);
        }
    }
    
    async checkCooldown() {
        try {
            const result = await MuralUtils.ajax.get('/api/cooldown', false);
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
