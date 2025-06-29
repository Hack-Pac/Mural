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
                            const error = new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
                            error.status = response.status;
                            error.data = data;
                            throw error;
                        }).catch(() => {
                            const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
                            error.status = response.status;
                            throw error;
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
            // Create a toast-style error notification with theme awareness
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
    },

    // Theme management
    theme: {
        themes: ['dark', 'light', 'coffee'],
        
        init: function() {
            // Check for saved theme preference or default to dark mode
            const savedTheme = localStorage.getItem('mural-theme') || 'dark';
            this.setTheme(savedTheme);
            this.setupToggle();
        },

        // Set the theme and update the UI accordingly
        setTheme: function(theme) {
            if (!this.themes.includes(theme)) {
                theme = 'dark'; // fallback to dark if invalid theme
            }
            
            const htmlElement = document.documentElement;
            const bodyElement = document.body;
            
            // Remove all theme classes
            htmlElement.classList.remove('dark', 'coffee');
            
            // Add appropriate theme class
            if (theme === 'dark') {
                htmlElement.classList.add('dark');
            } else if (theme === 'coffee') {
                htmlElement.classList.add('coffee');
            }
            // light theme has no class (default)
            
            // Update body data attribute for additional styling hooks
            if (bodyElement) {
                bodyElement.setAttribute('data-theme', theme);
            }
            
            localStorage.setItem('mural-theme', theme);
            this.updateToggleButton(theme);
        },

        toggleTheme: function() {
            const currentTheme = localStorage.getItem('mural-theme') || 'dark';
            const currentIndex = this.themes.indexOf(currentTheme);
            const nextIndex = (currentIndex + 1) % this.themes.length;
            const newTheme = this.themes[nextIndex];
            this.setTheme(newTheme);
        },

        setupToggle: function() {
            const toggleButton = document.getElementById('theme-toggle');
            if (toggleButton) {
                toggleButton.addEventListener('click', () => {
                    this.toggleTheme();
                });
            }
        },

        updateToggleButton: function(theme) {
            // Icons will be handled by CSS classes automatically
            // due to the theme-specific classes in the HTML
            // Update the title to show next theme
            const toggleButton = document.getElementById('theme-toggle');
            if (toggleButton) {
                const currentIndex = this.themes.indexOf(theme);
                const nextIndex = (currentIndex + 1) % this.themes.length;
                const nextTheme = this.themes[nextIndex];
                const nextThemeCapitalized = nextTheme.charAt(0).toUpperCase() + nextTheme.slice(1);
                toggleButton.title = `Switch to ${nextThemeCapitalized} Theme`;
            }
        },

        getCurrentTheme: function() {
            return localStorage.getItem('mural-theme') || 'dark';
        }
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
        
        // User progress data
        this.paintBuckets = 0;
        this.achievements = [];
        this.challenges = [];
        this.userPurchases = {};
        
        // Performance optimizations
        this.debouncedUpdateCoords = MuralUtils.debounce(this.updateCoordinateDisplay.bind(this), 8); // ~120fps for smoother updates
        this.debouncedSaveState = MuralUtils.debounce(this.saveStateToHash.bind(this), 100); // Debounce state saving
        
        // Cache for performance
        this.canvasRect = null;
        this.lastDisplayedX = null;
        this.lastDisplayedY = null;
        this.lastDisplayedValid = null;
        
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
        this.loadUserStats(); // Load user statistics
        this.loadConnectedCount(); // Load connected users count
        this.loadUserProgress(); // Load achievements and challenges
        this.checkCooldown();
        this.setupModals(); // Setup modal interactions
        
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
        
        // Cache the canvas bounding rect for performance
        this.updateCanvasRect();
        
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
    
    updateCanvasRect() {
        // Cache the canvas bounding rect for performance
        this.canvasRect = this.canvas.getBoundingClientRect();
    }
    
    // Fast coordinate conversion without DOM queries
    screenToCanvas(screenX, screenY) {
        const x = Math.floor((screenX - this.panX) / this.zoom);
        const y = Math.floor((screenY - this.panY) / this.zoom);
        return { x, y };
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
            if (!this.isDragging) {
                // Update canvas rect in case window was resized or scrolled
                this.updateCanvasRect();
                
                const mouseX = e.clientX - this.canvasRect.left;
                const mouseY = e.clientY - this.canvasRect.top;
                
                // Convert screen coordinates to canvas coordinates
                const coords = this.screenToCanvas(mouseX, mouseY);
                
                // Only place pixel if coordinates are valid
                if (coords.x >= 0 && coords.x < this.originalWidth && coords.y >= 0 && coords.y < this.originalHeight) {
                    this.placePixel(coords.x, coords.y, this.selectedColor);
                }
            }
        });
        
        // Mouse move for coordinates display - Highly optimized
        this.canvas.addEventListener('mousemove', (e) => {
            const mouseX = e.clientX - this.canvasRect.left;
            const mouseY = e.clientY - this.canvasRect.top;
            
            // Convert screen coordinates to canvas coordinates
            const coords = this.screenToCanvas(mouseX, mouseY);
            const isValid = coords.x >= 0 && coords.x < this.originalWidth && coords.y >= 0 && coords.y < this.originalHeight;
            
            // Only update display if coordinates actually changed
            if (coords.x !== this.lastDisplayedX || coords.y !== this.lastDisplayedY || isValid !== this.lastDisplayedValid) {
                this.lastDisplayedX = coords.x;
                this.lastDisplayedY = coords.y;
                this.lastDisplayedValid = isValid;
                this.debouncedUpdateCoords(coords.x, coords.y, isValid);
            }

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
                
                // Use debounced state saving for better performance
                this.debouncedSaveState();
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
            const mouseX = e.clientX - this.canvasRect.left;
            const mouseY = e.clientY - this.canvasRect.top;
            
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
                
                // Update cached rect after resize
                this.updateCanvasRect();
                
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
            
            // Use debounced state saving
            this.debouncedSaveState();
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

    // Highly optimized coordinate display update
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
            // Update total pixel count for any pixel placed
            this.totalPixelCount++;
            this.updateStats();
        });
        
        this.socket.on('canvas_update', (canvasData) => {
            this.loadCanvasData(canvasData);
        });
        
        this.socket.on('user_count', (data) => {
            this.updateConnectedCount(data.count);
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
    
    async loadUserStats() {
        try {
            const stats = await MuralUtils.ajax.get('/api/user-stats', false);
            this.userPixelCount = stats.user_pixels;
            this.totalPixelCount = stats.total_pixels;
            this.updateStats();
        } catch (error) {
            console.error('Failed to load user stats:', error);
            this.addActivity('Failed to load user statistics', 'error');
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
        // Don't update user pixel count here - it's loaded separately from server
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
            this.updateStats(); // Update the display immediately
            
            // Update paint buckets if earned
            if (result.paint_buckets_earned) {
                this.paintBuckets = result.total_paint_buckets;
                this.updatePaintBucketsDisplay();
                this.addActivity(`You placed a pixel at (${x}, ${y}) +${result.paint_buckets_earned}🪣`, 'user');
            } else {
                this.addActivity(`You placed a pixel at (${x}, ${y})`, 'user');
            }
            
            this.startCooldown(result.cooldown_remaining);
            
            // Reload progress to check for completed challenges and achievements
            // Use a small delay to ensure server has processed the pixel
            setTimeout(() => {
                this.loadUserProgress();
            }, 500);
            
        } catch (error) {
            if (error.status === 429 && error.data && error.data.cooldown_remaining) {
                // Use the actual cooldown remaining from the server
                this.startCooldown(error.data.cooldown_remaining);
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
    
    updateConnectedCount(count) {
        const element = document.getElementById('connected-count');
        if (element) {
            element.textContent = count.toLocaleString();
        }
    }
    
    async loadConnectedCount() {
        try {
            const result = await MuralUtils.ajax.get('/api/connected-count', false);
            this.updateConnectedCount(result.count);
        } catch (error) {
            console.error('Failed to load connected count:', error);
        }
    }
    
    async loadUserProgress() {
        try {
            const progress = await MuralUtils.ajax.get('/api/user-progress', false);
            
            // Update paint buckets
            this.paintBuckets = progress.paint_buckets;
            this.updatePaintBucketsDisplay();
            
            // Update achievements
            this.achievements = progress.achievements;
            this.updateAchievementsDisplay();
            
            // Update challenges
            this.challenges = progress.active_challenges;
            this.updateChallengesDisplay();
            
            // Store purchases
            this.userPurchases = progress.purchases;
            
            // Show new achievements
            if (progress.new_achievements && progress.new_achievements.length > 0) {
                progress.new_achievements.forEach(achievement => {
                    this.showAchievementNotification(achievement);
                });
            }
        } catch (error) {
            console.error('Failed to load user progress:', error);
        }
    }
    
    updatePaintBucketsDisplay() {
        document.getElementById('paint-buckets-count').textContent = this.paintBuckets.toLocaleString();
    }
    
    updateAchievementsDisplay() {
        // Update achievement count
        const totalAchievements = 19; // Total number of achievements defined
        document.getElementById('achievements-count').textContent = `${this.achievements.length}/${totalAchievements}`;
        
        // Update preview badges
        const preview = document.getElementById('achievements-preview');
        preview.innerHTML = '';
        
        // Show first 6 achievements as preview
        const achievementIcons = {
            'first_pixel': '🎨',
            'pixel_10': '🖌️',
            'pixel_100': '🎭',
            'pixel_1000': '👨‍🎨',
            'pixel_10000': '🏆',
            'challenge_1': '✅',
            'challenge_10': '💪',
            'challenge_50': '🔥',
            'challenge_100': '⚡',
            'challenge_500': '👑',
            'early_bird': '🌅',
            'night_owl': '🦉',
            'speed_demon': '⚡',
            'patient_artist': '⏳',
            'color_master': '🌈',
            'survivor': '🛡️',
            'architect': '🏗️',
            'week_streak': '📅',
            'month_streak': '📆'
        };
        
        for (let i = 0; i < Math.min(6, this.achievements.length); i++) {
            const achievementId = this.achievements[i];
            const icon = achievementIcons[achievementId] || '🏅';
            const badge = document.createElement('div');
            badge.className = 'w-8 h-8 bg-yellow-100 dark:bg-yellow-900 rounded flex items-center justify-center text-lg';
            badge.textContent = icon;
            badge.title = achievementId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            preview.appendChild(badge);
        }
        
        // Fill remaining slots with empty badges
        for (let i = this.achievements.length; i < 6; i++) {
            const badge = document.createElement('div');
            badge.className = 'w-8 h-8 bg-gray-100 dark:bg-gray-700 rounded flex items-center justify-center text-gray-400';
            badge.textContent = '?';
            preview.appendChild(badge);
        }
    }
    
    updateChallengesDisplay() {
        const challengesList = document.getElementById('challenges-list');
        challengesList.innerHTML = '';
        
        let hasCompletedChallenges = false;
        
        this.challenges.forEach(challenge => {
            const challengeDiv = document.createElement('div');
            const progress = challenge.progress || 0;
            const requirement = challenge.requirement || 1;
            const percentage = Math.min(100, (progress / requirement) * 100);
            const isCompleted = progress >= requirement;
            
            if (isCompleted) {
                hasCompletedChallenges = true;
            }
            
            challengeDiv.className = `rounded-lg p-3 transition-all duration-300 ${
                isCompleted 
                    ? 'bg-green-100 dark:bg-green-900 border-2 border-green-400' 
                    : 'bg-gray-50 dark:bg-gray-700'
            }`;
            
            challengeDiv.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <h4 class="font-medium ${isCompleted ? 'text-green-800 dark:text-green-200' : 'text-gray-900 dark:text-white'}">
                        ${challenge.name || 'Challenge'} ${isCompleted ? '✓' : ''}
                    </h4>
                    <span class="text-xs ${isCompleted ? 'text-green-600 dark:text-green-400' : 'text-yellow-600 dark:text-yellow-400'}">
                        🪣 ${challenge.reward || 0}
                    </span>
                </div>
                <p class="text-xs ${isCompleted ? 'text-green-700 dark:text-green-300' : 'text-gray-600 dark:text-gray-400'} mb-2">
                    ${challenge.description || ''}
                </p>
                <div class="relative bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                    <div class="absolute inset-0 ${
                        isCompleted 
                            ? 'bg-gradient-to-r from-green-400 to-green-600' 
                            : 'bg-gradient-to-r from-blue-400 to-blue-600'
                    } rounded-full transition-all duration-300" 
                         style="width: ${percentage}%"></div>
                </div>
                <p class="text-xs ${isCompleted ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'} mt-1">
                    ${progress}/${requirement} ${isCompleted ? 'Complete!' : ''}
                </p>
            `;
            
            challengesList.appendChild(challengeDiv);
        });
        
        // Auto-complete challenges if any are finished
        if (hasCompletedChallenges) {
            this.checkAndCompleteChallenges();
        }
        
        // Show refresh button if all challenges are completed
        const allCompleted = this.challenges.every(c => c.progress >= c.requirement);
        document.getElementById('refresh-challenges').classList.toggle('hidden', !allCompleted);
    }
    
    async checkAndCompleteChallenges() {
        const completedChallenges = this.challenges.filter(c => c.progress >= c.requirement);
        if (completedChallenges.length === 0) return;
        
        const completedIds = completedChallenges.map(c => c.id);
        
        try {
            const result = await MuralUtils.ajax.post('/api/complete-challenges', {
                completed_challenge_ids: completedIds
            }, false);
            
            if (result.success) {
                // Update paint buckets
                this.paintBuckets = result.paint_buckets;
                this.updatePaintBucketsDisplay();
                
                // Show reward notification
                if (result.total_reward > 0) {
                    this.showRewardNotification(`Challenges Complete! +${result.total_reward} 🪣`);
                }
                
                // Update challenges
                this.challenges = result.active_challenges;
                this.updateChallengesDisplay();
                
                // Play a success sound or animation
                this.addActivity(`Completed ${completedIds.length} challenge(s)!`, 'info');
            }
        } catch (error) {
            console.error('Failed to complete challenges:', error);
        }
    }
    
    showRewardNotification(message) {
        // Create a temporary notification
        const notification = document.createElement('div');
        notification.className = 'fixed top-20 left-1/2 transform -translate-x-1/2 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-all duration-500';
        notification.textContent = message;
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translate(-50%, 0)';
        }, 10);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }
    
    showAchievementNotification(achievement) {
        const notification = document.getElementById('achievement-notification');
        const icon = document.getElementById('achievement-icon');
        const name = document.getElementById('achievement-name');
        const reward = document.getElementById('achievement-reward');
        
        icon.textContent = achievement.icon || '🏆';
        name.textContent = achievement.name;
        reward.textContent = `+${achievement.reward} Paint Buckets`;
        
        // Show notification
        notification.classList.remove('translate-x-full');
        
        // Hide after 5 seconds
        setTimeout(() => {
            notification.classList.add('translate-x-full');
        }, 5000);
        
        // Update displays
        this.paintBuckets += achievement.reward;
        this.updatePaintBucketsDisplay();
        this.achievements.push(achievement.id);
        this.updateAchievementsDisplay();
    }
    
    setupModals() {
        // Shop modal
        document.getElementById('open-shop').addEventListener('click', () => this.openShop());
        document.getElementById('close-shop').addEventListener('click', () => this.closeShop());
        
        // Achievements modal
        document.getElementById('view-all-achievements').addEventListener('click', () => this.openAchievements());
        document.getElementById('close-achievements').addEventListener('click', () => this.closeAchievements());
        
        // Close modals on background click
        document.getElementById('shop-modal').addEventListener('click', (e) => {
            if (e.target.id === 'shop-modal') this.closeShop();
        });
        document.getElementById('achievements-modal').addEventListener('click', (e) => {
            if (e.target.id === 'achievements-modal') this.closeAchievements();
        });
        
        // Refresh challenges button
        document.getElementById('refresh-challenges').addEventListener('click', () => this.refreshChallenges());
    }
    
    async openShop() {
        const modal = document.getElementById('shop-modal');
        modal.classList.remove('hidden');
        
        // Update paint buckets display
        document.getElementById('shop-paint-buckets').textContent = this.paintBuckets.toLocaleString();
        
        // Load shop items
        try {
            const shopData = await MuralUtils.ajax.get('/api/shop');
            this.displayShopItems(shopData.items);
        } catch (error) {
            console.error('Failed to load shop items:', error);
        }
    }
    
    closeShop() {
        document.getElementById('shop-modal').classList.add('hidden');
    }
    
    displayShopItems(items) {
        const container = document.getElementById('shop-items');
        container.innerHTML = '';
        
        items.forEach(item => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600';
            
            const canAfford = this.paintBuckets >= item.cost;
            const buttonClass = canAfford 
                ? 'bg-green-600 hover:bg-green-500 text-white' 
                : 'bg-gray-400 text-gray-200 cursor-not-allowed';
            
            itemDiv.innerHTML = `
                <h4 class="font-bold text-gray-900 dark:text-white mb-2">${item.name}</h4>
                <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">${item.description}</p>
                <div class="flex justify-between items-center">
                    <span class="text-lg font-bold text-orange-500">🪣 ${item.cost}</span>
                    <button class="px-4 py-2 rounded text-sm font-medium ${buttonClass}" 
                            ${!canAfford ? 'disabled' : ''}
                            onclick="window.muralInstance.purchaseItem('${item.id}')">
                        Purchase
                    </button>
                </div>
            `;
            
            container.appendChild(itemDiv);
        });
    }
    
    async purchaseItem(itemId) {
        try {
            const result = await MuralUtils.ajax.post('/api/shop/purchase', { item_id: itemId });
            
            // Update paint buckets
            this.paintBuckets = result.paint_buckets;
            this.updatePaintBucketsDisplay();
            document.getElementById('shop-paint-buckets').textContent = this.paintBuckets.toLocaleString();
            
            // Refresh shop display
            this.openShop();
            
            // Show success message
            this.addActivity(`Purchased ${result.purchase.name}!`, 'info');
            
            // Update user purchases
            this.userPurchases = { ...this.userPurchases, [itemId]: true };
        } catch (error) {
            console.error('Failed to purchase item:', error);
        }
    }
    
    openAchievements() {
        const modal = document.getElementById('achievements-modal');
        modal.classList.remove('hidden');
        this.displayAllAchievements();
    }
    
    closeAchievements() {
        document.getElementById('achievements-modal').classList.add('hidden');
    }
    
    displayAllAchievements() {
        const grid = document.getElementById('achievements-grid');
        grid.innerHTML = '';
        
        const allAchievements = {
            'first_pixel': { name: 'First Pixel', description: 'Place your first pixel', icon: '🎨' },
            'pixel_10': { name: 'Apprentice', description: 'Place 10 pixels', icon: '🖌️' },
            'pixel_100': { name: 'Artist', description: 'Place 100 pixels', icon: '🎭' },
            'pixel_1000': { name: 'Master Artist', description: 'Place 1,000 pixels', icon: '👨‍🎨' },
            'pixel_10000': { name: 'Legendary Artist', description: 'Place 10,000 pixels', icon: '🏆' },
            'challenge_1': { name: 'Challenger', description: 'Complete your first challenge', icon: '✅' },
            'challenge_10': { name: 'Dedicated', description: 'Complete 10 challenges', icon: '💪' },
            'challenge_50': { name: 'Persistent', description: 'Complete 50 challenges', icon: '🔥' },
            'challenge_100': { name: 'Unstoppable', description: 'Complete 100 challenges', icon: '⚡' },
            'challenge_500': { name: 'Challenge Master', description: 'Complete 500 challenges', icon: '👑' },
            'early_bird': { name: 'Early Bird', description: 'Place a pixel before 6 AM', icon: '🌅' },
            'night_owl': { name: 'Night Owl', description: 'Place a pixel after midnight', icon: '🦉' },
            'speed_demon': { name: 'Speed Demon', description: 'Place 10 pixels in 1 minute', icon: '⚡' },
            'patient_artist': { name: 'Patient Artist', description: 'Wait for full cooldown 10 times', icon: '⏳' },
            'color_master': { name: 'Color Master', description: 'Use all available colors', icon: '🌈' },
            'survivor': { name: 'Survivor', description: 'Have a pixel survive for 1 hour', icon: '🛡️' },
            'architect': { name: 'Architect', description: 'Create a 5x5 square of the same color', icon: '🏗️' },
            'week_streak': { name: 'Dedicated Week', description: '7-day streak', icon: '📅' },
            'month_streak': { name: 'Monthly Master', description: '30-day streak', icon: '📆' }
        };
        
        Object.entries(allAchievements).forEach(([id, achievement]) => {
            const unlocked = this.achievements.includes(id);
            const achievementDiv = document.createElement('div');
            achievementDiv.className = `rounded-lg p-4 text-center ${
                unlocked 
                    ? 'bg-yellow-100 dark:bg-yellow-900 border-2 border-yellow-400' 
                    : 'bg-gray-100 dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-600 opacity-50'
            }`;
            
            achievementDiv.innerHTML = `
                <div class="text-3xl mb-2">${achievement.icon}</div>
                <h4 class="font-bold text-sm ${unlocked ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}">${achievement.name}</h4>
                <p class="text-xs mt-1 ${unlocked ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500'}">${achievement.description}</p>
            `;
            
            grid.appendChild(achievementDiv);
        });
        
        // Update progress
        document.getElementById('achievements-progress').textContent = `${this.achievements.length}/${Object.keys(allAchievements).length}`;
    }
    
    async refreshChallenges() {
        // This would normally complete the current challenges and get new ones
        // For now, just reload progress
        await this.loadUserProgress();
    }
}

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Initialize theme before creating Mural instance
    MuralUtils.theme.init();
    window.muralInstance = new Mural();
});
