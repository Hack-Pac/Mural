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
        specialThemes: {
            christmas: {
                startMonth: 12,
                startDay: 20,
                endMonth: 12,
                endDay: 31,
                hasEffects: true
            }
        },
        
        init: function() {
            // Check if we're in a special date range
            const specialTheme = this.getSpecialTheme();
            
            if (specialTheme) {
                // Add special theme to available themes if not already there
                if (!this.themes.includes(specialTheme)) {
                    this.themes.push(specialTheme);
                }
                
                // Check for saved theme preference or default to special theme
                const savedTheme = localStorage.getItem('mural-theme');
                const defaultTheme = savedTheme && this.themes.includes(savedTheme) ? savedTheme : specialTheme;
                this.setTheme(defaultTheme);
                
                // Initialize special effects if applicable
                if (this.specialThemes[specialTheme].hasEffects) {
                    this.initSpecialEffects(specialTheme);
                }
            } else {
                // Remove special themes from available themes
                this.themes = this.themes.filter(theme => !this.specialThemes[theme]);
                
                // Check for saved theme preference or default to dark mode
                const savedTheme = localStorage.getItem('mural-theme');
                const defaultTheme = savedTheme && this.themes.includes(savedTheme) ? savedTheme : 'dark';
                this.setTheme(defaultTheme);
            }
            
            this.setupToggle();
        },
        
        getSpecialTheme: function() {
            const now = new Date();
            const month = now.getMonth() + 1; // JavaScript months are 0-indexed
            const day = now.getDate();
            
            for (const [themeName, config] of Object.entries(this.specialThemes)) {
                // Check if we're within the date range
                if (config.startMonth === config.endMonth) {
                    // Same month range
                    if (month === config.startMonth && day >= config.startDay && day <= config.endDay) {
                        return themeName;
                    }
                } else {
                    // Cross-month range (e.g., Dec 20 - Jan 5)
                    if ((month === config.startMonth && day >= config.startDay) || 
                        (month === config.endMonth && day <= config.endDay)) {
                        return themeName;
                    }
                }
            }
            
            return null;
        },

        // Set the theme and update the UI accordingly
        setTheme: function(theme) {
            if (!this.themes.includes(theme)) {
                theme = 'dark'; // fallback to dark if invalid theme
            }
            
            const htmlElement = document.documentElement;
            const bodyElement = document.body;
            
            // Remove all theme classes
            htmlElement.classList.remove('dark', 'coffee', 'christmas');
            
            // Add appropriate theme class
            if (theme === 'dark') {
                htmlElement.classList.add('dark');
            } else if (theme === 'coffee') {
                htmlElement.classList.add('coffee');
            } else if (theme === 'christmas') {
                htmlElement.classList.add('christmas');
            }
            // light theme has no class (default)
            
            // Update body data attribute for additional styling hooks
            if (bodyElement) {
                bodyElement.setAttribute('data-theme', theme);
            }
            
            localStorage.setItem('mural-theme', theme);
            this.updateToggleButton(theme);
            
            // Update accessibility announcement
            if (window.muralInstance && window.muralInstance.accessibility) {
                window.muralInstance.accessibility.updateThemeAnnouncement(theme);
            }
        },

        toggleTheme: function() {
            const currentTheme = localStorage.getItem('mural-theme') || 'dark';
            const currentIndex = this.themes.indexOf(currentTheme);
            const nextIndex = (currentIndex + 1) % this.themes.length;
            const newTheme = this.themes[nextIndex];
            
            // Handle special effects when switching themes
            if (currentTheme === 'christmas' && newTheme !== 'christmas') {
                // Switching away from Christmas theme
                this.stopSnowEffect();
                const effectsToggle = document.getElementById('effects-toggle');
                if (effectsToggle) {
                    effectsToggle.classList.add('hidden');
                }
            } else if (currentTheme !== 'christmas' && newTheme === 'christmas') {
                // Switching to Christmas theme
                this.initSpecialEffects('christmas');
            }
            
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
                const currentThemeCapitalized = theme.charAt(0).toUpperCase() + theme.slice(1);
                const nextThemeCapitalized = nextTheme.charAt(0).toUpperCase() + nextTheme.slice(1);
                toggleButton.title = `Switch to ${nextThemeCapitalized} Theme`;
                toggleButton.setAttribute('aria-label', `Change theme. Current theme: ${currentThemeCapitalized}`);
            }
        },

        getCurrentTheme: function() {
            return localStorage.getItem('mural-theme') || 'dark';
        },
        
        initSpecialEffects: function(theme) {
            if (theme === 'christmas') {
                // Show effects toggle button
                const effectsToggle = document.getElementById('effects-toggle');
                if (effectsToggle) {
                    effectsToggle.classList.remove('hidden');
                    effectsToggle.addEventListener('click', () => {
                        this.toggleEffects();
                    });
                }
                
                // Check if effects are enabled (default: true)
                const effectsEnabled = localStorage.getItem('mural-effects') !== 'false';
                if (effectsEnabled) {
                    this.startSnowEffect();
                }
            }
        },
        
        toggleEffects: function() {
            const snowContainer = document.getElementById('snow-container');
            const effectsEnabled = localStorage.getItem('mural-effects') !== 'false';
            
            if (effectsEnabled) {
                // Disable effects
                localStorage.setItem('mural-effects', 'false');
                this.stopSnowEffect();
            } else {
                // Enable effects
                localStorage.setItem('mural-effects', 'true');
                this.startSnowEffect();
            }
        },
        
        startSnowEffect: function() {
            const snowContainer = document.getElementById('snow-container');
            if (!snowContainer) return;
            
            snowContainer.classList.remove('hidden');
            
            // Create snowflakes
            const snowflakeCount = 50;
            for (let i = 0; i < snowflakeCount; i++) {
                this.createSnowflake();
            }
        },
        
        stopSnowEffect: function() {
            const snowContainer = document.getElementById('snow-container');
            if (!snowContainer) return;
            
            snowContainer.classList.add('hidden');
            snowContainer.innerHTML = '';
        },
        
        createSnowflake: function() {
            const snowContainer = document.getElementById('snow-container');
            if (!snowContainer) return;
            
            const snowflake = document.createElement('div');
            snowflake.className = 'snowflake';
            snowflake.innerHTML = '❄';
            
            // Random properties
            const startPosition = Math.random() * 100;
            const animationDuration = 10 + Math.random() * 20; // 10-30 seconds
            const size = 0.5 + Math.random() * 1.5; // 0.5-2em
            const delay = Math.random() * animationDuration;
            
            snowflake.style.left = `${startPosition}%`;
            snowflake.style.fontSize = `${size}em`;
            snowflake.style.animationDuration = `${animationDuration}s`;
            snowflake.style.animationDelay = `${delay}s`;
            
            snowContainer.appendChild(snowflake);
            
            // Remove and recreate snowflake when animation ends
            snowflake.addEventListener('animationend', () => {
                snowflake.remove();
                if (localStorage.getItem('mural-effects') !== 'false') {
                    this.createSnowflake();
                }
            });
        }
    }
};

// Mural - Collaborative Pixel Art Application with Optimized Rendering
class Mural {
    constructor() {
        // Add error boundary for constructor
        try {
            this.canvas = document.getElementById('canvas');
            if (!this.canvas) {
                throw new Error('Canvas element not found');
            }
            
            this.ctx = this.canvas.getContext('2d');
            if (!this.ctx) {
                throw new Error('Failed to get 2D context');
            }
            
            // Initialize WebSocket with connection state tracking
            this.socketConnected = false;
            this.socketReconnectAttempts = 0;
            this.maxReconnectAttempts = 10;
            this.reconnectDelay = 1000; // Start with 1 second
            this.messageBuffer = []; // Buffer messages when disconnected
            this.initializeSocket();
            
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
            
            // Track all event listeners for cleanup
            this.eventListeners = [];
            this.boundHandlers = {};
        
        // User progress data
        this.paintBuckets = 0;
        this.achievements = [];
        this.challenges = [];
        this.userPurchases = {};
        
        // Performance optimizations
        this.debouncedUpdateCoords = MuralUtils.debounce(this.updateCoordinateDisplay.bind(this), 16); // 60fps is sufficient
        this.debouncedSaveState = MuralUtils.debounce(this.saveStateToHash.bind(this), 250); // Less frequent state saves
        this.throttledLoadProgress = this.throttle(this.loadUserProgress.bind(this), 5000); // Throttle progress loading
        
        // Cache for performance
        this.canvasRect = null;
        this.lastDisplayedX = null;
        this.lastDisplayedY = null;
        this.lastDisplayedValid = null;
        
        // Pre-rendered canvas system with optimizations
        this.pixelData = new Map(); // Store pixel data efficiently
        this.needsRedraw = true;
        this.isRendering = false;
        
        // Dirty rectangle tracking for optimized rendering
        this.dirtyRects = [];
        this.fullRedrawNeeded = true;
        
        // WebSocket message batching
        this.messageQueue = [];
        this.messageBatchTimer = null;
        
        // Activity feed optimization
        this.activityBuffer = [];
        this.activityFlushTimer = null;
        
        // Viewport settings - will be set dynamically
        this.viewportWidth = 600; // initial fallback
        this.viewportHeight = 600; // initial fallback
        this.originalWidth = 500;
        this.originalHeight = 500;
        
        // Performance monitoring
        this.perfMonitor = null;
        
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
        } catch (error) {
            console.error('Failed to initialize Mural:', error);
            this.showCriticalError('Failed to initialize the application. Please refresh the page.');
        }
    }
    
    initializeSocket() {
        try {
            // Create socket with explicit options
            this.socket = io({
                reconnection: true,
                reconnectionAttempts: this.maxReconnectAttempts,
                reconnectionDelay: this.reconnectDelay,
                reconnectionDelayMax: 10000,
                timeout: 20000,
                transports: ['websocket', 'polling'] // Fallback to polling if WebSocket fails
            });
            
            // Add connection event handlers
            this.socket.on('connect', () => {
                this.socketConnected = true;
                this.socketReconnectAttempts = 0;
                this.reconnectDelay = 1000;
                console.log('WebSocket connected');
                
                // Flush any buffered messages
                this.flushMessageBuffer();
            });
            
            this.socket.on('disconnect', (reason) => {
                this.socketConnected = false;
                console.log('WebSocket disconnected:', reason);
                this.addActivity('Connection lost. Attempting to reconnect...', 'error');
            });
            
            this.socket.on('connect_error', (error) => {
                console.error('WebSocket connection error:', error);
                this.socketReconnectAttempts++;
                
                if (this.socketReconnectAttempts >= this.maxReconnectAttempts) {
                    this.addActivity('Failed to connect to server. Please refresh the page.', 'error');
                }
            });
            
            this.socket.on('reconnect_attempt', (attemptNumber) => {
                this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 10000);
                this.addActivity(`Reconnecting... (attempt ${attemptNumber})`, 'system');
            });
            
            this.socket.on('reconnect', (attemptNumber) => {
                this.addActivity('Reconnected to server', 'system');
                // Reload canvas state after reconnection
                this.loadCanvas();
                this.loadUserStats();
            });
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
            this.socketConnected = false;
        }
    }
    
    flushMessageBuffer() {
        if (this.messageBuffer.length > 0 && this.socketConnected) {
            const messages = [...this.messageBuffer];
            this.messageBuffer = [];
            
            messages.forEach(({ event, data }) => {
                this.socket.emit(event, data);
            });
        }
    }
    
    emitWithBuffer(event, data) {
        if (this.socketConnected && this.socket.connected) {
            this.socket.emit(event, data);
        } else {
            // Buffer the message for later
            this.messageBuffer.push({ event, data });
            console.warn('Socket not connected, buffering message:', event);
        }
    }
    
    showCriticalError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50';
        errorDiv.innerHTML = `
            <div class="bg-red-600 text-white p-8 rounded-lg max-w-md">
                <h2 class="text-2xl font-bold mb-4">Error</h2>
                <p class="mb-4">${message}</p>
                <button onclick="location.reload()" class="bg-white text-red-600 px-4 py-2 rounded hover:bg-gray-100">
                    Refresh Page
                </button>
            </div>
        `;
        document.body.appendChild(errorDiv);
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
        
        // Initialize accessibility features
        if (window.AccessibilityManager) {
            this.accessibility = new window.AccessibilityManager(this);
        }
        
        // Start with 1:1 zoom
        this.zoom = 1;
        this.updateZoomDisplay();
        this.centerCanvas(); // Center the canvas on initialization
        
        // Restore state from URL hash if available
        this.restoreStateFromHash();
        
        // Handle browser back/forward
        this.addEventListener(window, 'hashchange', () => this.restoreStateFromHash());
        
        // Initialize performance monitor
        if (window.PerformanceMonitor) {
            this.perfMonitor = new window.PerformanceMonitor();
            
            // Add keyboard shortcut for performance monitor
            this.addEventListener(document, 'keydown', (e) => {
                if (e.key === 'p' || e.key === 'P') {
                    this.perfMonitor.toggle();
                }
            });
        }
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
        
        // Set pixel art rendering with vendor prefixes
        this.ctx.imageSmoothingEnabled = false;
        this.ctx.webkitImageSmoothingEnabled = false;
        this.ctx.mozImageSmoothingEnabled = false;
        this.ctx.msImageSmoothingEnabled = false;
        
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
        // Add validation for screenX and screenY
        if (typeof screenX !== 'number' || typeof screenY !== 'number' ||
            !isFinite(screenX) || !isFinite(screenY)) {
            console.warn('Invalid screen coordinates:', screenX, screenY);
            return { x: -1, y: -1 }; // Return invalid coordinates
        }
        
        // Ensure zoom is valid
        if (!this.zoom || this.zoom <= 0) {
            console.warn('Invalid zoom level:', this.zoom);
            this.zoom = 1; // Reset to default
        }
        
        const x = Math.floor((screenX - this.panX) / this.zoom);
        const y = Math.floor((screenY - this.panY) / this.zoom);
        
        // Clamp to integer values to prevent floating point errors
        return { 
            x: Math.floor(x), 
            y: Math.floor(y) 
        };
    }
    
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }
    
    startRenderLoop() {
        let lastRenderTime = 0;
        const targetFPS = 60;
        const frameTime = 1000 / targetFPS;
        
        const render = (timestamp) => {
            // Limit to target FPS
            if (timestamp - lastRenderTime >= frameTime) {
                if (this.needsRedraw && !this.isRendering) {
                    if (this.fullRedrawNeeded) {
                        this.renderCanvas();
                    } else if (this.dirtyRects.length > 0) {
                        this.renderDirtyRects();
                    }
                }
                lastRenderTime = timestamp;
            }
            requestAnimationFrame(render);
        };
        requestAnimationFrame(render);
    }

    renderCanvas() {
        const startTime = performance.now();
        
        this.isRendering = true;
        this.needsRedraw = false;
        this.fullRedrawNeeded = false;
        
        // Use save/restore for better performance
        this.ctx.save();
        
        // Clear canvas with white background
        this.ctx.fillStyle = '#FFFFFF';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Calculate visible region
        const startX = Math.max(0, Math.floor(-this.panX / this.zoom));
        const startY = Math.max(0, Math.floor(-this.panY / this.zoom));
        const endX = Math.min(this.originalWidth, Math.ceil((this.viewportWidth - this.panX) / this.zoom));
        const endY = Math.min(this.originalHeight, Math.ceil((this.viewportHeight - this.panY) / this.zoom));
        
        // Batch similar color pixels for better performance
        const colorBatches = new Map();
        
        // Group pixels by color
        for (let x = startX; x < endX; x++) {
            for (let y = startY; y < endY; y++) {
                const pixelKey = `${x},${y}`;
                const pixelColor = this.pixelData.get(pixelKey);
                
                if (pixelColor) {
                    if (!colorBatches.has(pixelColor)) {
                        colorBatches.set(pixelColor, []);
                    }
                    colorBatches.get(pixelColor).push({ x, y });
                }
            }
        }
        
        // Render batched by color to reduce state changes
        const pixelSize = Math.ceil(this.zoom);
        colorBatches.forEach((pixels, color) => {
            this.ctx.fillStyle = color;
            pixels.forEach(({ x, y }) => {
                const screenX = Math.floor(this.panX + x * this.zoom);
                const screenY = Math.floor(this.panY + y * this.zoom);
                this.ctx.fillRect(screenX, screenY, pixelSize, pixelSize);
            });
        });
        
        this.ctx.restore();
        this.isRendering = false;
        this.dirtyRects = [];
        
        // Track render performance
        if (this.perfMonitor) {
            const renderTime = performance.now() - startTime;
            this.perfMonitor.recordRenderTime(renderTime);
        }
    }
    
    renderDirtyRects() {
        this.isRendering = true;
        this.needsRedraw = false;
        
        this.ctx.save();
        const pixelSize = Math.ceil(this.zoom);
        
        // Process dirty rectangles
        this.dirtyRects.forEach(rect => {
            // Clear the dirty area
            const screenX = Math.floor(this.panX + rect.x * this.zoom);
            const screenY = Math.floor(this.panY + rect.y * this.zoom);
            
            this.ctx.fillStyle = '#FFFFFF';
            this.ctx.fillRect(screenX, screenY, pixelSize, pixelSize);
            
            // Redraw the pixel if it exists
            const pixelKey = `${rect.x},${rect.y}`;
            const pixelColor = this.pixelData.get(pixelKey);
            
            if (pixelColor) {
                this.ctx.fillStyle = pixelColor;
                this.ctx.fillRect(screenX, screenY, pixelSize, pixelSize);
            }
        });
        
        this.ctx.restore();
        this.dirtyRects = [];
        this.isRendering = false;
    }
    
    setupColorPalette() {
        const palette = document.getElementById('color-palette-grid');
        
        this.colors.forEach((color, index) => {
            const colorDiv = document.createElement('div');
            colorDiv.className = 'color-picker w-8 h-8 rounded cursor-pointer border-2 border-gray-600';
            colorDiv.style.backgroundColor = color;
            colorDiv.dataset.color = color;
            
            // Add accessibility attributes
            colorDiv.setAttribute('role', 'radio');
            colorDiv.setAttribute('aria-label', `Color ${index + 1}: ${this.getColorName(color)}`);
            colorDiv.setAttribute('tabindex', index === 0 ? '0' : '-1');
            colorDiv.setAttribute('aria-checked', index === 0 ? 'true' : 'false');
            
            if (index === 0) {
                colorDiv.classList.add('selected');
                this.updateSelectedColor(color);
            }
            
            // Click handler
            colorDiv.addEventListener('click', () => {
                this.selectColor(colorDiv, color);
            });
            
            // Keyboard handler
            colorDiv.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.selectColor(colorDiv, color);
                }
            });
            
            palette.appendChild(colorDiv);
        });
    }
    
    selectColor(colorDiv, color) {
        // Remove selected class and aria attributes from all colors
        document.querySelectorAll('.color-picker').forEach(el => {
            el.classList.remove('selected');
            el.setAttribute('aria-checked', 'false');
            el.setAttribute('tabindex', '-1');
        });
        
        // Add selected class to clicked color
        colorDiv.classList.add('selected');
        colorDiv.setAttribute('aria-checked', 'true');
        colorDiv.setAttribute('tabindex', '0');
        this.selectedColor = color;
        this.updateSelectedColor(color);
        
        // Save color selection to hash
        this.saveStateToHash();
        
        // Announce selection for screen readers
        if (this.accessibility) {
            this.accessibility.announce(`Selected ${this.getColorName(color)}`);
        }
    }
    
    getColorName(hex) {
        const colorNames = {
            '#000000': 'black',
            '#FFFFFF': 'white',
            '#FF0000': 'red',
            '#00FF00': 'green',
            '#0000FF': 'blue',
            '#FFFF00': 'yellow',
            '#FF00FF': 'magenta',
            '#00FFFF': 'cyan',
            '#FFA500': 'orange',
            '#800080': 'purple',
            '#FFC0CB': 'pink',
            '#A52A2A': 'brown',
            '#808080': 'gray',
            '#FFD700': 'gold',
            '#C0C0C0': 'silver',
            '#000080': 'navy'
        };
        
        return colorNames[hex.toUpperCase()] || hex;
    }
    
    updateSelectedColor(color) {
        document.getElementById('selected-color').style.backgroundColor = color;
        document.getElementById('selected-color-hex').textContent = color;
    }
    
    addEventListener(element, event, handler, options = false) {
        // Safely add event listener and track it
        if (!element) {
            console.warn('Attempted to add event listener to null element');
            return;
        }
        
        const boundHandler = handler.bind(this);
        element.addEventListener(event, boundHandler, options);
        
        // Track for cleanup
        this.eventListeners.push({
            element,
            event,
            handler: boundHandler,
            options
        });
        
        return boundHandler;
    }
    
    removeAllEventListeners() {
        // Clean up all tracked event listeners
        this.eventListeners.forEach(({ element, event, handler, options }) => {
            try {
                element.removeEventListener(event, handler, options);
            } catch (error) {
                console.warn('Failed to remove event listener:', error);
            }
        });
        this.eventListeners = [];
    }
    
    setupEventListeners() {
        // Canvas click event - Optimized for direct coordinate calculation
        this.addEventListener(this.canvas, 'click', (e) => {
            // Only place pixel if we're not in the middle of a drag operation
            if (!this.isDragging) {
                // Update canvas rect in case window was resized or scrolled
                this.updateCanvasRect();
                
                const mouseX = e.clientX - this.canvasRect.left;
                const mouseY = e.clientY - this.canvasRect.top;
                
                // Validate mouse coordinates
                if (!isFinite(mouseX) || !isFinite(mouseY)) {
                    console.warn('Invalid mouse coordinates');
                    return;
                }
                
                // Convert screen coordinates to canvas coordinates
                const coords = this.screenToCanvas(mouseX, mouseY);
                
                // Only place pixel if coordinates are valid (strict integer check)
                if (Number.isInteger(coords.x) && Number.isInteger(coords.y) &&
                    coords.x >= 0 && coords.x < this.originalWidth && 
                    coords.y >= 0 && coords.y < this.originalHeight) {
                    this.placePixel(coords.x, coords.y, this.selectedColor);
                } else {
                    console.debug('Click outside canvas bounds:', coords);
                }
            }
        });
        
        // Mouse move for coordinates display - Highly optimized
        this.addEventListener(this.canvas, 'mousemove', (e) => {
            // Validate event object
            if (!e || typeof e.clientX !== 'number' || typeof e.clientY !== 'number') {
                return;
            }
            
            const mouseX = e.clientX - this.canvasRect.left;
            const mouseY = e.clientY - this.canvasRect.top;
            
            // Convert screen coordinates to canvas coordinates
            const coords = this.screenToCanvas(mouseX, mouseY);
            const isValid = Number.isInteger(coords.x) && Number.isInteger(coords.y) &&
                           coords.x >= 0 && coords.x < this.originalWidth && 
                           coords.y >= 0 && coords.y < this.originalHeight;
            
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
                this.fullRedrawNeeded = true; // Panning requires full redraw
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
                
                // Use debounced state saving for better performance
                this.debouncedSaveState();
            }
        });
        
        // Pan functionality - Enhanced to support regular click and drag
        this.addEventListener(this.canvas, 'mousedown', (e) => {
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
        
        this.addEventListener(document, 'mouseup', (e) => {
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
        
        // Zoom controls with null checks
        const zoomInBtn = document.getElementById('zoom-in');
        const zoomOutBtn = document.getElementById('zoom-out');
        const resetViewBtn = document.getElementById('reset-view');
        
        if (zoomInBtn) {
            this.addEventListener(zoomInBtn, 'click', () => {
                this.zoomAt(1.2);
            });
        }
        
        if (zoomOutBtn) {
            this.addEventListener(zoomOutBtn, 'click', () => {
                this.zoomAt(1/1.2);
            });
        }
        
        if (resetViewBtn) {
            this.addEventListener(resetViewBtn, 'click', () => {
                // Calculate the minimum zoom needed to fill the viewport
                const zoomX = this.viewportWidth / this.originalWidth;
                const zoomY = this.viewportHeight / this.originalHeight;
                this.zoom = Math.max(zoomX, zoomY); // Ensure no out-of-bounds is visible
                
                this.centerCanvas();
                this.updateZoomDisplay();
            });
        }
        
        // Export canvas as PNG
        const exportBtn = document.getElementById('export-canvas');
        if (exportBtn) {
            this.addEventListener(exportBtn, 'click', () => {
                this.exportCanvasAsPNG();
            });
        }
        
        // Mouse wheel zoom
        this.addEventListener(this.canvas, 'wheel', (e) => {
            e.preventDefault();
            const mouseX = e.clientX - this.canvasRect.left;
            const mouseY = e.clientY - this.canvasRect.top;
            
            const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
            this.zoomAtPoint(zoomFactor, mouseX, mouseY);
        });
        
        // Window resize handler to update viewport and maintain centering
        this.addEventListener(window, 'resize', () => {
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
                this.fullRedrawNeeded = true;
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
            
            this.fullRedrawNeeded = true;
            this.needsRedraw = true;
            this.updateZoomDisplay();
            
            // Use debounced state saving
            this.debouncedSaveState();
        }
    }
    
    zoomAtPoint(factor, mouseX, mouseY) {
        // Validate inputs
        if (!isFinite(factor) || !isFinite(mouseX) || !isFinite(mouseY)) {
            console.warn('Invalid zoom parameters');
            return;
        }
        
        // Calculate minimum zoom to prevent showing out-of-bounds
        const zoomX = this.viewportWidth / this.originalWidth;
        const zoomY = this.viewportHeight / this.originalHeight;
        const minZoom = Math.max(zoomX, zoomY);
        
        // Zoom at a specific point (for mouse wheel)
        const newZoom = Math.max(minZoom, Math.min(10, this.zoom * factor));
        
        if (Math.abs(newZoom - this.zoom) > 0.001) { // Avoid floating point precision issues
            // Calculate canvas coordinates of the mouse position
            const canvasX = (mouseX - this.panX) / this.zoom;
            const canvasY = (mouseY - this.panY) / this.zoom;
            
            // Validate calculated coordinates
            if (!isFinite(canvasX) || !isFinite(canvasY)) {
                console.warn('Invalid canvas coordinates during zoom');
                return;
            }
            
            // Update zoom
            this.zoom = newZoom;
            
            // Calculate new pan to keep the same point under the mouse
            const newPanX = mouseX - (canvasX * this.zoom);
            const newPanY = mouseY - (canvasY * this.zoom);
            
            // Apply boundary constraints
            this.panX = this.clampPan(newPanX, 'x');
            this.panY = this.clampPan(newPanY, 'y');
            
            this.fullRedrawNeeded = true;
            this.needsRedraw = true;
            this.updateZoomDisplay();
            
            // Save state with debouncing
            this.debouncedSaveState();
        }
    }
    
    // Export canvas as PNG
    exportCanvasAsPNG() {
        // Create a temporary canvas to render the full image at actual size
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = this.originalWidth;
        tempCanvas.height = this.originalHeight;
        const tempCtx = tempCanvas.getContext('2d');
        
        // Fill with white background
        tempCtx.fillStyle = '#FFFFFF';
        tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);
        
        // Draw all pixels at original size with vendor prefixes
        tempCtx.imageSmoothingEnabled = false;
        tempCtx.webkitImageSmoothingEnabled = false;
        tempCtx.mozImageSmoothingEnabled = false;
        tempCtx.msImageSmoothingEnabled = false;
        this.pixelData.forEach((color, key) => {
            const [x, y] = key.split(',').map(Number);
            tempCtx.fillStyle = color;
            tempCtx.fillRect(x, y, 1, 1);
        });
        
        // Convert to blob and download
        tempCanvas.toBlob((blob) => {
            if (blob) {
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                
                // Create filename with timestamp
                const now = new Date();
                const timestamp = now.getFullYear() + 
                    String(now.getMonth() + 1).padStart(2, '0') +
                    String(now.getDate()).padStart(2, '0') + '_' +
                    String(now.getHours()).padStart(2, '0') +
                    String(now.getMinutes()).padStart(2, '0') +
                    String(now.getSeconds()).padStart(2, '0');
                
                link.download = `mural_canvas_${timestamp}.png`;
                
                // Trigger download
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                // Cleanup
                URL.revokeObjectURL(url);
                
                // Show success notification
                this.showNotification('Canvas exported successfully!', 'success');
            } else {
                MuralUtils.ajax.showError('Failed to export canvas');
            }
        }, 'image/png');
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
        if (!coordsElement) return; // Null check
        
        if (isValid) {
            coordsElement.textContent = `${x}, ${y}`;
            coordsElement.className = 'text-green-400';
            // Set cursor based on drag state
            if (this.canvas) {
                this.canvas.style.cursor = this.isDragging ? 'grabbing' : 'crosshair';
            }
        } else {
            coordsElement.textContent = 'Outside canvas';
            coordsElement.className = 'text-gray-500';
            if (this.canvas) {
                this.canvas.style.cursor = this.isDragging ? 'grabbing' : 'grab';
            }
        }
    }
    
    setupSocketEvents() {
        // Avoid duplicate event handlers
        if (this.socketEventsSetup) {
            return;
        }
        this.socketEventsSetup = true;
        
        // Already handled in initializeSocket, but add additional handlers here
        
        this.socket.on('pixel_placed', (data) => {
            try {
                // Validate incoming data
                if (!data || typeof data.x !== 'number' || typeof data.y !== 'number' || !data.color) {
                    console.warn('Invalid pixel data received:', data);
                    return;
                }
                this.drawPixel(data.x, data.y, data.color);
                this.addActivity(`Pixel placed at (${data.x}, ${data.y})`, 'pixel');
                // Update total pixel count for any pixel placed
                this.totalPixelCount++;
                // Debounce stats update
                if (!this.statsUpdateTimer) {
                    this.statsUpdateTimer = setTimeout(() => {
                        this.updateStats();
                        this.statsUpdateTimer = null;
                    }, 50);
                }
            } catch (error) {
                console.error('Error handling pixel_placed:', error);
            }
        });
        
        this.socket.on('pixel_batch', (pixelBatch) => {
            try {
                // Validate batch data
                if (!Array.isArray(pixelBatch)) {
                    console.warn('Invalid pixel batch received:', pixelBatch);
                    return;
                }
                
                // Handle batched pixel updates with validation
                let validPixels = 0;
                pixelBatch.forEach(data => {
                    if (data && typeof data.x === 'number' && typeof data.y === 'number' && data.color) {
                        this.drawPixel(data.x, data.y, data.color);
                        validPixels++;
                    }
                });
                
                if (validPixels > 0) {
                    this.addActivity(`${validPixels} pixels updated`, 'pixel');
                    this.totalPixelCount += validPixels;
                    this.updateStats();
                }
            } catch (error) {
                console.error('Error handling pixel_batch:', error);
            }
        });
        
        this.socket.on('canvas_update', (canvasData) => {
            try {
                if (canvasData && typeof canvasData === 'object') {
                    this.loadCanvasData(canvasData);
                }
            } catch (error) {
                console.error('Error handling canvas_update:', error);
            }
        });
        
        this.socket.on('canvas_large', (data) => {
            try {
                // Fetch large canvas via API to avoid WebSocket size limits
                this.loadCanvas();
            } catch (error) {
                console.error('Error handling canvas_large:', error);
            }
        });
        
        this.socket.on('user_count', (data) => {
            try {
                if (data && typeof data.count === 'number') {
                    this.updateConnectedCount(data.count);
                }
            } catch (error) {
                console.error('Error handling user_count:', error);
            }
        });
    }
    
    async loadCanvas() {
        try {
            const canvasData = await MuralUtils.ajax.get('/api/canvas', false);
            if (canvasData && typeof canvasData === 'object') {
                this.loadCanvasData(canvasData);
            } else {
                throw new Error('Invalid canvas data received');
            }
        } catch (error) {
            console.error('Failed to load canvas:', error);
            this.addActivity('Failed to load canvas. Retrying...', 'error');
            
            // Retry logic
            if (!this.canvasRetryCount) this.canvasRetryCount = 0;
            this.canvasRetryCount++;
            
            if (this.canvasRetryCount < 3) {
                setTimeout(() => this.loadCanvas(), 2000 * this.canvasRetryCount);
            } else {
                this.addActivity('Failed to load canvas after multiple attempts', 'error');
            }
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
        // Validate canvas data
        if (!canvasData || typeof canvasData !== 'object') {
            console.error('Invalid canvas data');
            return;
        }
        
        // Clear pixel data
        this.pixelData.clear();
        
        // For large canvases, process in chunks to avoid blocking
        const entries = Object.entries(canvasData);
        const chunkSize = 1000;
        let index = 0;
        
        const processChunk = () => {
            const chunk = entries.slice(index, index + chunkSize);
            chunk.forEach(([key, pixelData]) => {
                // Validate pixel data
                if (pixelData && pixelData.color) {
                    // Validate coordinate key format
                    const coordMatch = key.match(/^(\d+),(\d+)$/);
                    if (coordMatch) {
                        const x = parseInt(coordMatch[1], 10);
                        const y = parseInt(coordMatch[2], 10);
                        
                        // Validate coordinates are within bounds
                        if (x >= 0 && x < this.originalWidth && y >= 0 && y < this.originalHeight) {
                            this.pixelData.set(key, pixelData.color);
                        } else {
                            console.warn('Pixel coordinates out of bounds:', key);
                        }
                    } else {
                        console.warn('Invalid pixel key format:', key);
                    }
                }
            });
            
            index += chunkSize;
            
            if (index < entries.length) {
                // Process next chunk in next frame
                requestAnimationFrame(processChunk);
            } else {
                // All done
                this.totalPixelCount = entries.length;
                this.updateStats();
                this.fullRedrawNeeded = true;
                this.needsRedraw = true;
            }
        };
        
        if (entries.length > chunkSize) {
            // Process in chunks for large data
            processChunk();
        } else {
            // Small dataset, process immediately with validation
            entries.forEach(([key, pixelData]) => {
                if (pixelData && pixelData.color) {
                    const coordMatch = key.match(/^(\d+),(\d+)$/);
                    if (coordMatch) {
                        const x = parseInt(coordMatch[1], 10);
                        const y = parseInt(coordMatch[2], 10);
                        
                        if (x >= 0 && x < this.originalWidth && y >= 0 && y < this.originalHeight) {
                            this.pixelData.set(key, pixelData.color);
                        }
                    }
                }
            });
            this.totalPixelCount = entries.length;
            this.updateStats();
            this.fullRedrawNeeded = true;
            this.needsRedraw = true;
        }
    }
    
    drawPixel(x, y, color) {
        // Validate coordinates
        if (!Number.isInteger(x) || !Number.isInteger(y) ||
            x < 0 || x >= this.originalWidth || y < 0 || y >= this.originalHeight) {
            console.warn('Invalid pixel coordinates:', x, y);
            return;
        }
        
        // Validate color
        const hexColorRegex = /^#[0-9A-Fa-f]{6}$/;
        if (!hexColorRegex.test(color)) {
            console.warn('Invalid color format:', color);
            return;
        }
        
        // Store pixel in our map
        const key = `${x},${y}`;
        this.pixelData.set(key, color);
        
        // Add to dirty rectangles for optimized rendering
        this.dirtyRects.push({ x, y });
        this.needsRedraw = true;
        
        // If too many dirty rects, switch to full redraw
        if (this.dirtyRects.length > 100) {
            this.fullRedrawNeeded = true;
            this.dirtyRects = [];
        }
    }
    
    async placePixel(x, y, color) {
        // Validate coordinates with strict type checking
        if (!Number.isInteger(x) || !Number.isInteger(y) || 
            x < 0 || x >= this.originalWidth || y < 0 || y >= this.originalHeight) {
            console.warn('Invalid coordinates attempted:', x, y);
            return; // Silently ignore invalid coordinates
        }
        
        // Validate color format (must be hex color)
        const hexColorRegex = /^#[0-9A-Fa-f]{6}$/;
        if (!hexColorRegex.test(color)) {
            console.warn('Invalid color format attempted:', color);
            MuralUtils.ajax.showError('Invalid color format');
            return;
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
        // Validate input
        if (typeof seconds !== 'number' || seconds < 0) {
            console.warn('Invalid cooldown seconds:', seconds);
            return;
        }
        
        this.cooldownRemaining = Math.floor(seconds);
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
        // Add to buffer for batching
        this.activityBuffer.push({ message, type, timestamp: new Date() });
        
        // Track queue size for performance monitoring
        if (this.perfMonitor) {
            this.perfMonitor.recordMessageQueueSize(this.activityBuffer.length);
        }
        
        // Announce important activities to screen readers
        if (this.accessibility && (type === 'pixel' || type === 'system' || type === 'error')) {
            // Format message for screen reader announcement
            const announcement = this.formatActivityForScreenReader(message, type);
            this.accessibility.announce(announcement, type === 'error' ? 'assertive' : 'polite');
        }
        
        // Flush buffer if it gets too large
        if (this.activityBuffer.length >= 10) {
            this.flushActivityBuffer();
        } else {
            // Schedule flush if not already scheduled
            if (!this.activityFlushTimer) {
                this.activityFlushTimer = setTimeout(() => {
                    this.flushActivityBuffer();
                }, 100);
            }
        }
    }
    
    flushActivityBuffer() {
        if (this.activityBuffer.length === 0) return;
        
        const feed = document.getElementById('activity-feed');
        const fragment = document.createDocumentFragment();
        
        const typeIcon = {
            'system': '🔗',
            'pixel': '🎨',
            'user': '👤',
            'error': '❌',
            'info': 'ℹ️'
        };
        
        // Process all buffered activities
        this.activityBuffer.forEach(({ message, type, timestamp }) => {
            const activity = document.createElement('div');
            activity.className = 'flex items-center space-x-2 text-xs';
            
            const timestampSpan = document.createElement('span');
            timestampSpan.className = 'text-gray-500';
            timestampSpan.textContent = timestamp.toLocaleTimeString();
            
            const iconSpan = document.createElement('span');
            iconSpan.textContent = typeIcon[type] || typeIcon['info'];
            
            const messageSpan = document.createElement('span');
            messageSpan.className = 'flex-1';
            messageSpan.textContent = message;
            
            activity.appendChild(timestampSpan);
            activity.appendChild(iconSpan);
            activity.appendChild(messageSpan);
            
            fragment.appendChild(activity);
        });
        
        // Insert all at once
        feed.insertBefore(fragment, feed.firstChild);
        
        // Clear buffer
        this.activityBuffer = [];
        clearTimeout(this.activityFlushTimer);
        this.activityFlushTimer = null;
        
        // Keep only the last 50 activities
        while (feed.children.length > 50) {
            feed.removeChild(feed.lastChild);
        }
    }
    
    updateStats() {
        const totalPixelsEl = document.getElementById('total-pixels');
        const userPixelsEl = document.getElementById('user-pixels');
        
        if (totalPixelsEl) {
            totalPixelsEl.textContent = this.totalPixelCount.toLocaleString();
        }
        if (userPixelsEl) {
            userPixelsEl.textContent = this.userPixelCount.toLocaleString();
        }
    }
    
    updateConnectedCount(count) {
        const element = document.getElementById('connected-count');
        const userCountEl = document.getElementById('user-count');
        
        if (element) {
            element.textContent = count.toLocaleString();
        }
        if (userCountEl) {
            userCountEl.textContent = count.toLocaleString();
        }
    }
    
    formatActivityForScreenReader(message, type) {
        // Remove emojis and format message for clear screen reader announcement
        const cleanMessage = message.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]/gu, '').trim();
        
        // Add context based on type
        switch(type) {
            case 'pixel':
                return `Pixel placed: ${cleanMessage}`;
            case 'system':
                return `System: ${cleanMessage}`;
            case 'error':
                return `Error: ${cleanMessage}`;
            case 'user':
                return `User joined: ${cleanMessage}`;
            default:
                return cleanMessage;
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
        const element = document.getElementById('paint-buckets-count');
        if (element) {
            element.textContent = this.paintBuckets.toLocaleString();
        }
    }
    
    updateAchievementsDisplay() {
        // Update achievement count
        const totalAchievements = 19; // Total number of achievements defined
        const achievementsCountEl = document.getElementById('achievements-count');
        if (achievementsCountEl) {
            achievementsCountEl.textContent = `${this.achievements.length}/${totalAchievements}`;
        }
        
        // Update preview badges
        const preview = document.getElementById('achievements-preview');
        if (!preview) return;
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
        if (!challengesList) return;
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
            
            // Create elements safely to prevent XSS
            const headerDiv = document.createElement('div');
            headerDiv.className = 'flex justify-between items-start mb-2';
            
            const titleH4 = document.createElement('h4');
            titleH4.className = `font-medium ${isCompleted ? 'text-green-800 dark:text-green-200' : 'text-gray-900 dark:text-white'}`;
            titleH4.textContent = `${challenge.name || 'Challenge'} ${isCompleted ? '✓' : ''}`;
            
            const rewardSpan = document.createElement('span');
            rewardSpan.className = `text-xs ${isCompleted ? 'text-green-600 dark:text-green-400' : 'text-yellow-600 dark:text-yellow-400'}`;
            rewardSpan.textContent = `🪣 ${challenge.reward || 0}`;
            
            headerDiv.appendChild(titleH4);
            headerDiv.appendChild(rewardSpan);
            
            const descP = document.createElement('p');
            descP.className = `text-xs ${isCompleted ? 'text-green-700 dark:text-green-300' : 'text-gray-600 dark:text-gray-400'} mb-2`;
            descP.textContent = challenge.description || '';
            
            const progressDiv = document.createElement('div');
            progressDiv.className = 'relative bg-gray-200 dark:bg-gray-600 rounded-full h-2';
            
            const progressBar = document.createElement('div');
            progressBar.className = `absolute inset-0 ${
                isCompleted 
                    ? 'bg-gradient-to-r from-green-400 to-green-600' 
                    : 'bg-gradient-to-r from-blue-400 to-blue-600'
            } rounded-full transition-all duration-300`;
            progressBar.style.width = `${percentage}%`;
            progressDiv.appendChild(progressBar);
            
            const statusP = document.createElement('p');
            statusP.className = `text-xs ${isCompleted ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'} mt-1`;
            statusP.textContent = `${progress}/${requirement} ${isCompleted ? 'Complete!' : ''}`;
            
            challengeDiv.appendChild(headerDiv);
            challengeDiv.appendChild(descP);
            challengeDiv.appendChild(progressDiv);
            challengeDiv.appendChild(statusP);
            
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
        notification.setAttribute('role', 'alert');
        notification.setAttribute('aria-live', 'assertive');
        document.body.appendChild(notification);
        
        // Announce to screen readers
        if (this.accessibility) {
            this.accessibility.announce(message, 'assertive');
        }
        
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
    
    showNotification(message, type = 'info') {
        // Create a temporary notification with appropriate styling
        const notification = document.createElement('div');
        const bgColor = type === 'success' ? 'bg-green-600' : type === 'error' ? 'bg-red-600' : 'bg-blue-600';
        notification.className = `fixed top-20 left-1/2 transform -translate-x-1/2 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-all duration-500 translate-y-[-20px] opacity-0`;
        notification.textContent = message;
        notification.setAttribute('role', 'alert');
        notification.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');
        document.body.appendChild(notification);
        
        // Announce to screen readers
        if (this.accessibility) {
            this.accessibility.announce(message, type === 'error' ? 'assertive' : 'polite');
        }
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translate(-50%, 0)';
            notification.style.opacity = '1';
        }, 10);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translate(-50%, -20px)';
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
        
        // Update aria-hidden attribute for visibility
        notification.setAttribute('aria-hidden', 'false');
        
        // Show notification
        notification.classList.remove('translate-x-full');
        
        // Announce to screen readers
        if (this.accessibility) {
            this.accessibility.announce(
                `Achievement unlocked: ${achievement.name}. You earned ${achievement.reward} paint buckets!`,
                'assertive'
            );
        }
        
        // Hide after 5 seconds
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            notification.setAttribute('aria-hidden', 'true');
        }, 5000);
        
        // Update displays
        this.paintBuckets += achievement.reward;
        this.updatePaintBucketsDisplay();
        this.achievements.push(achievement.id);
        this.updateAchievementsDisplay();
    }
    
    setupModals() {
        // Shop modal
        const openShopBtn = document.getElementById('open-shop');
        const closeShopBtn = document.getElementById('close-shop');
        const shopModal = document.getElementById('shop-modal');
        
        if (openShopBtn) {
            this.addEventListener(openShopBtn, 'click', () => this.openShop());
        }
        if (closeShopBtn) {
            this.addEventListener(closeShopBtn, 'click', () => this.closeShop());
        }
        
        // Achievements modal
        const viewAchievementsBtn = document.getElementById('view-all-achievements');
        const closeAchievementsBtn = document.getElementById('close-achievements');
        const achievementsModal = document.getElementById('achievements-modal');
        
        if (viewAchievementsBtn) {
            this.addEventListener(viewAchievementsBtn, 'click', () => this.openAchievements());
        }
        if (closeAchievementsBtn) {
            this.addEventListener(closeAchievementsBtn, 'click', () => this.closeAchievements());
        }
        
        // Help modal
        const helpBtn = document.getElementById('help-button');
        const closeHelpBtn = document.getElementById('close-help');
        const helpModal = document.getElementById('help-modal');
        
        if (helpBtn) {
            this.addEventListener(helpBtn, 'click', () => this.openHelp());
        }
        if (closeHelpBtn) {
            this.addEventListener(closeHelpBtn, 'click', () => this.closeHelp());
        }
        
        // Close modals on background click
        if (shopModal) {
            this.addEventListener(shopModal, 'click', (e) => {
                if (e.target.id === 'shop-modal') this.closeShop();
            });
        }
        if (achievementsModal) {
            this.addEventListener(achievementsModal, 'click', (e) => {
                if (e.target.id === 'achievements-modal') this.closeAchievements();
            });
        }
        if (helpModal) {
            this.addEventListener(helpModal, 'click', (e) => {
                if (e.target.id === 'help-modal') this.closeHelp();
            });
        }
        
        // Refresh challenges button
        const refreshChallengesBtn = document.getElementById('refresh-challenges');
        if (refreshChallengesBtn) {
            this.addEventListener(refreshChallengesBtn, 'click', () => this.refreshChallenges());
        }
    }
    
    async openShop() {
        const modal = document.getElementById('shop-modal');
        if (!modal) return;
        modal.classList.remove('hidden');
        
        // Update paint buckets display
        const shopPaintBucketsEl = document.getElementById('shop-paint-buckets');
        if (shopPaintBucketsEl) {
            shopPaintBucketsEl.textContent = this.paintBuckets.toLocaleString();
        }
        
        // Load shop items
        try {
            const shopData = await MuralUtils.ajax.get('/api/shop');
            this.displayShopItems(shopData.items);
        } catch (error) {
            console.error('Failed to load shop items:', error);
        }
    }
    
    closeShop() {
        const modal = document.getElementById('shop-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }
    
    displayShopItems(items) {
        const container = document.getElementById('shop-items');
        if (!container) return;
        container.innerHTML = '';
        
        items.forEach(item => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600';
            
            const canAfford = this.paintBuckets >= item.cost;
            const buttonClass = canAfford 
                ? 'bg-green-600 hover:bg-green-500 text-white' 
                : 'bg-gray-400 text-gray-200 cursor-not-allowed';
            
            // Create elements safely
            const titleH4 = document.createElement('h4');
            titleH4.className = 'font-bold text-gray-900 dark:text-white mb-2';
            titleH4.textContent = item.name;
            
            const descP = document.createElement('p');
            descP.className = 'text-sm text-gray-600 dark:text-gray-400 mb-3';
            descP.textContent = item.description;
            
            const footerDiv = document.createElement('div');
            footerDiv.className = 'flex justify-between items-center';
            
            const costSpan = document.createElement('span');
            costSpan.className = 'text-lg font-bold text-orange-500';
            costSpan.textContent = `🪣 ${item.cost}`;
            
            const purchaseBtn = document.createElement('button');
            purchaseBtn.className = `px-4 py-2 rounded text-sm font-medium ${buttonClass}`;
            purchaseBtn.textContent = 'Purchase';
            purchaseBtn.disabled = !canAfford;
            if (canAfford) {
                // Use bound handler to avoid memory leaks
                const handler = () => this.purchaseItem(item.id);
                purchaseBtn.addEventListener('click', handler);
                // Store handler reference for potential cleanup
                purchaseBtn._clickHandler = handler;
            }
            
            footerDiv.appendChild(costSpan);
            footerDiv.appendChild(purchaseBtn);
            
            itemDiv.appendChild(titleH4);
            itemDiv.appendChild(descP);
            itemDiv.appendChild(footerDiv);
            
            container.appendChild(itemDiv);
        });
    }
    
    async purchaseItem(itemId) {
        try {
            const result = await MuralUtils.ajax.post('/api/shop/purchase', { item_id: itemId });
            
            // Update paint buckets
            this.paintBuckets = result.paint_buckets;
            this.updatePaintBucketsDisplay();
            const shopPaintBucketsEl = document.getElementById('shop-paint-buckets');
            if (shopPaintBucketsEl) {
                shopPaintBucketsEl.textContent = this.paintBuckets.toLocaleString();
            }
            
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
        if (!modal) return;
        modal.classList.remove('hidden');
        this.displayAllAchievements();
    }
    
    closeAchievements() {
        const modal = document.getElementById('achievements-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }
    
    openHelp() {
        const modal = document.getElementById('help-modal');
        if (!modal) return;
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden', 'false');
        
        // Announce to screen readers
        if (this.accessibility) {
            this.accessibility.announce('Help dialog opened', 'polite');
        }
    }
    
    closeHelp() {
        const modal = document.getElementById('help-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
        }
    }
    
    displayAllAchievements() {
        const grid = document.getElementById('achievements-grid');
        if (!grid) return;
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
            
            // Create elements safely
            const iconDiv = document.createElement('div');
            iconDiv.className = 'text-3xl mb-2';
            iconDiv.textContent = achievement.icon;
            
            const nameH4 = document.createElement('h4');
            nameH4.className = `font-bold text-sm ${unlocked ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-gray-400'}`;
            nameH4.textContent = achievement.name;
            
            const descP = document.createElement('p');
            descP.className = `text-xs mt-1 ${unlocked ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500'}`;
            descP.textContent = achievement.description;
            
            achievementDiv.appendChild(iconDiv);
            achievementDiv.appendChild(nameH4);
            achievementDiv.appendChild(descP);
            
            grid.appendChild(achievementDiv);
        });
        
        // Update progress
        const progressEl = document.getElementById('achievements-progress');
        if (progressEl) {
            progressEl.textContent = `${this.achievements.length}/${Object.keys(allAchievements).length}`;
        }
    }
    
    async refreshChallenges() {
        // This would normally complete the current challenges and get new ones
        // For now, just reload progress
        await this.loadUserProgress();
    }
    
    destroy() {
        // Clean up all resources to prevent memory leaks
        console.log('Destroying Mural instance...');
        
        // Clear all timers
        if (this.cooldownTimer) {
            clearInterval(this.cooldownTimer);
            this.cooldownTimer = null;
        }
        if (this.statsUpdateTimer) {
            clearTimeout(this.statsUpdateTimer);
            this.statsUpdateTimer = null;
        }
        if (this.activityFlushTimer) {
            clearTimeout(this.activityFlushTimer);
            this.activityFlushTimer = null;
        }
        
        // Remove all event listeners
        this.removeAllEventListeners();
        
        // Disconnect socket
        if (this.socket) {
            this.socket.removeAllListeners();
            this.socket.disconnect();
            this.socket = null;
        }
        
        // Clear data structures
        if (this.pixelData) {
            this.pixelData.clear();
        }
        this.messageBuffer = [];
        this.activityBuffer = [];
        this.dirtyRects = [];
        
        // Remove canvas context reference
        this.ctx = null;
        this.canvas = null;
        
        // Clear any remaining references
        this.perfMonitor = null;
        
        console.log('Mural instance destroyed');
    }
}

// Browser compatibility checks
const BrowserCompat = {
    checkRequirements: function() {
        const requirements = {
            canvas: !!document.createElement('canvas').getContext,
            websocket: 'WebSocket' in window,
            localStorage: function() {
                try {
                    const test = '__test__';
                    localStorage.setItem(test, test);
                    localStorage.removeItem(test);
                    return true;
                } catch(e) {
                    return false;
                }
            }(),
            requestAnimationFrame: !!window.requestAnimationFrame,
            fetch: !!window.fetch,
            promise: !!window.Promise,
            map: !!window.Map,
            set: !!window.Set,
            isInteger: !!Number.isInteger,
            isFinite: !!Number.isFinite
        };
        
        const missing = [];
        for (const [feature, supported] of Object.entries(requirements)) {
            if (!supported) {
                missing.push(feature);
            }
        }
        
        return { supported: missing.length === 0, missing };
    },
    
    addPolyfills: function() {
        // Number.isInteger polyfill
        if (!Number.isInteger) {
            Number.isInteger = function(value) {
                return typeof value === 'number' && 
                       isFinite(value) && 
                       Math.floor(value) === value;
            };
        }
        
        // Number.isFinite polyfill
        if (!Number.isFinite) {
            Number.isFinite = function(value) {
                return typeof value === 'number' && isFinite(value);
            };
        }
        
        // Array.isArray polyfill
        if (!Array.isArray) {
            Array.isArray = function(arg) {
                return Object.prototype.toString.call(arg) === '[object Array]';
            };
        }
        
        // Object.entries polyfill
        if (!Object.entries) {
            Object.entries = function(obj) {
                var ownProps = Object.keys(obj),
                    i = ownProps.length,
                    resArray = new Array(i);
                while (i--)
                    resArray[i] = [ownProps[i], obj[ownProps[i]]];
                return resArray;
            };
        }
        
        // requestAnimationFrame polyfill
        if (!window.requestAnimationFrame) {
            window.requestAnimationFrame = (function() {
                return window.webkitRequestAnimationFrame ||
                       window.mozRequestAnimationFrame ||
                       window.oRequestAnimationFrame ||
                       window.msRequestAnimationFrame ||
                       function(callback) {
                           window.setTimeout(callback, 1000 / 60);
                       };
            })();
        }
    },
    
    showCompatibilityError: function(missing) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center z-50 p-4';
        errorDiv.innerHTML = `
            <div class="bg-white rounded-lg p-8 max-w-md text-center">
                <h2 class="text-2xl font-bold mb-4 text-red-600">Browser Not Supported</h2>
                <p class="mb-4 text-gray-700">Your browser is missing required features:</p>
                <ul class="text-left mb-6 text-gray-600">
                    ${missing.map(f => `<li>• ${f}</li>`).join('')}
                </ul>
                <p class="text-gray-700">Please update your browser or use a modern browser like Chrome, Firefox, Safari, or Edge.</p>
            </div>
        `;
        document.body.appendChild(errorDiv);
    }
};

// Initialize the application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Add polyfills first
    BrowserCompat.addPolyfills();
    
    // Check browser compatibility
    const compat = BrowserCompat.checkRequirements();
    if (!compat.supported) {
        console.error('Browser missing required features:', compat.missing);
        BrowserCompat.showCompatibilityError(compat.missing);
        return; // Don't initialize the app
    }
    
    // Initialize theme before creating Mural instance
    MuralUtils.theme.init();
    
    try {
        // Create instance
        window.muralInstance = new Mural();
        
        // Clean up on page unload
        window.addEventListener('beforeunload', () => {
            if (window.muralInstance && window.muralInstance.destroy) {
                window.muralInstance.destroy();
            }
        });
    } catch (error) {
        console.error('Failed to initialize Mural:', error);
        // Show user-friendly error
        const errorDiv = document.createElement('div');
        errorDiv.className = 'fixed top-4 right-4 bg-red-600 text-white p-4 rounded-lg';
        errorDiv.textContent = 'Failed to initialize the application. Please refresh the page.';
        document.body.appendChild(errorDiv);
    }
});
