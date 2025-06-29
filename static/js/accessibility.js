// Accessibility enhancements for Mural application

class AccessibilityManager {
    constructor(mural) {
        this.mural = mural;
        this.cursorX = 250; // Start at center
        this.cursorY = 250;
        this.keyboardMode = false;
        this.helpVisible = false;
        
        // Initialize accessibility features
        this.init();
    }
    
    init() {
        this.setupKeyboardNavigation();
        this.setupAnnouncements();
        this.setupFocusManagement();
        this.setupColorPaletteAccessibility();
        this.setupModalAccessibility();
        this.setupLiveRegions();
    }
    
    // Keyboard navigation for canvas
    setupKeyboardNavigation() {
        const canvas = document.getElementById('canvas');
        
        // Add keyboard event listeners
        canvas.addEventListener('keydown', (e) => {
            this.keyboardMode = true;
            
            switch(e.key) {
                // Arrow keys for navigation
                case 'ArrowUp':
                    e.preventDefault();
                    this.moveCursor(0, -1);
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    this.moveCursor(0, 1);
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    this.moveCursor(-1, 0);
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.moveCursor(1, 0);
                    break;
                    
                // Enter or Space to place pixel
                case 'Enter':
                case ' ':
                    e.preventDefault();
                    this.placePixelAtCursor();
                    break;
                // Number keys for color selection
                case '1':
                case '2':
                case '3':
                case '4':
                case '5':
                case '6':
                case '7':
                case '8':
                case '9':
                    e.preventDefault();
                    this.selectColorByNumber(parseInt(e.key));
                    break;
                // Zoom controls
                case '+':
                case '=':
                    e.preventDefault();
                    document.getElementById('zoom-in').click();
                    break;
                case '-':
                case '_':
                    e.preventDefault();
                    document.getElementById('zoom-out').click();
                    break;
                case '0':
                    e.preventDefault();
                    document.getElementById('reset-view').click();
                    break;
                    
                // Center view
                case 'c':
                case 'C':
                    e.preventDefault();
                    this.mural.centerCanvas();
                    this.announce('Canvas centered');
                    break;
                // Help toggle
                case 'h':
                case 'H':
                    e.preventDefault();
                    this.toggleHelp();
                    break;
                    
                // Export canvas
                case 'e':
                case 'E':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        document.getElementById('export-canvas').click();
                        this.announce('Exporting canvas as PNG');
                    }
                    break;
                    
                // Open shop
                case 's':
                case 'S':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        document.getElementById('open-shop').click();
                    }
                    break;
                // View achievements
                case 'a':
                case 'A':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        document.getElementById('view-all-achievements').click();
                    }
                    break;
                // Escape to exit keyboard mode
                case 'Escape':
                    e.preventDefault();
                    this.exitKeyboardMode();
                    break;
            }
        });
        
        // Track when canvas loses focus
        canvas.addEventListener('blur', () => {
            this.keyboardMode = false;
        });
    }
    
    moveCursor(dx, dy) {
        // Calculate new position
        let newX = this.cursorX + dx;
        let newY = this.cursorY + dy;
        
        // Clamp to canvas bounds
        newX = Math.max(0, Math.min(499, newX));
        newY = Math.max(0, Math.min(499, newY));
        
        // Update cursor position
        this.cursorX = newX;
        this.cursorY = newY;
        // Update coordinate display
        document.getElementById('cursor-coords').textContent = `${newX}, ${newY}`;
        
        // Announce position periodically
        if ((newX % 10 === 0 && dx !== 0) || (newY % 10 === 0 && dy !== 0)) {
            this.announce(`Position ${newX}, ${newY}`, 'polite');
        }
        // Visual indicator for keyboard mode
        if (this.keyboardMode) {
            this.drawCursorIndicator();
        }
    }
    
    drawCursorIndicator() {
        // Draw a visual cursor indicator on the canvas
        const ctx = this.mural.ctx;
        const zoom = this.mural.zoom;
        const panX = this.mural.panX;
        const panY = this.mural.panY;
        // Save context state
        ctx.save();
        // Calculate screen position
        const screenX = panX + this.cursorX * zoom;
        const screenY = panY + this.cursorY * zoom;
        // Draw cursor outline
        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = 2;
        ctx.strokeRect(screenX, screenY, zoom, zoom);
        // Restore context
        ctx.restore();
        
        // Request redraw
        this.mural.needsRedraw = true;
    }
    placePixelAtCursor() {
        this.mural.placePixel(this.cursorX, this.cursorY, this.mural.selectedColor);
        this.announce(`Placed ${this.getColorName(this.mural.selectedColor)} pixel at ${this.cursorX}, ${this.cursorY}`);
    }
    
    selectColorByNumber(num) {
        const colors = document.querySelectorAll('.color-picker');
        if (num > 0 && num <= colors.length) {
            colors[num - 1].click();
            this.announce(`Selected color ${num}: ${this.getColorName(this.mural.selectedColor)}`);
        }
    }
    
    exitKeyboardMode() {
        this.keyboardMode = false;
        this.announce('Exited keyboard mode');
        this.mural.needsRedraw = true;
    }
    toggleHelp() {
        const helpDiv = document.getElementById('keyboard-help');
        this.helpVisible = !this.helpVisible;
        if (this.helpVisible) {
            helpDiv.classList.remove('hidden');
            this.announce('Keyboard help opened. Press H to close.');
        } else {
            helpDiv.classList.add('hidden');
            this.announce('Keyboard help closed');
        }
    }
    // Screen reader announcements
    setupAnnouncements() {
        // Create announcement containers if they don't exist
        if (!document.getElementById('sr-announcements')) {
            const politeAnnouncer = document.createElement('div');
            politeAnnouncer.id = 'sr-announcements';
            politeAnnouncer.setAttribute('aria-live', 'polite');
            politeAnnouncer.setAttribute('aria-atomic', 'true');
            politeAnnouncer.className = 'sr-only';
            document.body.appendChild(politeAnnouncer);
        }
        
        if (!document.getElementById('sr-alerts')) {
            const assertiveAnnouncer = document.createElement('div');
            assertiveAnnouncer.id = 'sr-alerts';
            assertiveAnnouncer.setAttribute('aria-live', 'assertive');
            assertiveAnnouncer.setAttribute('aria-atomic', 'true');
            assertiveAnnouncer.className = 'sr-only';
            document.body.appendChild(assertiveAnnouncer);
        }
    }
    
    announce(message, priority = 'polite') {
        const announcer = priority === 'assertive' 
            ? document.getElementById('sr-alerts')
            : document.getElementById('sr-announcements');
        if (announcer) {
            // Clear previous announcement
            announcer.textContent = '';
            
            // Set new announcement after a brief delay
            setTimeout(() => {
                announcer.textContent = message;
            }, 100);
        }
    }
    // Focus management
    setupFocusManagement() {
        // Track focus for modals
        this.lastFocusedElement = null;
        // Add focus trap for modals
        ['shop-modal', 'achievements-modal'].forEach(modalId => {
            const modal = document.getElementById(modalId);
            if (modal) {
                this.setupModalFocusTrap(modal);
            }
        });
    }
    setupModalFocusTrap(modal) {
        const focusableElements = modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        if (focusableElements.length === 0) return;
        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements[focusableElements.length - 1];
        
        modal.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    // Shift + Tab
                    if (document.activeElement === firstFocusable) {
                        e.preventDefault();
                        lastFocusable.focus();
                    }
                } else {
                    // Tab
                    if (document.activeElement === lastFocusable) {
                        e.preventDefault();
                        firstFocusable.focus();
                    }
                }
            }
            
            if (e.key === 'Escape') {
                this.closeModal(modal);
            }
        });
    }
    
    openModal(modal) {
        this.lastFocusedElement = document.activeElement;
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden', 'false');
        // Focus first focusable element
        const firstFocusable = modal.querySelector(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (firstFocusable) {
            firstFocusable.focus();
        }
        this.announce(`${modal.getAttribute('aria-labelledby')} dialog opened`);
    }
    
    closeModal(modal) {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
        
        // Restore focus
        if (this.lastFocusedElement) {
            this.lastFocusedElement.focus();
        }
        
        this.announce('Dialog closed');
    }
    // Color palette accessibility
    setupColorPaletteAccessibility() {
        const palette = document.getElementById('color-palette-grid');
        if (!palette) return;
        
        // Make color selection work with keyboard
        palette.addEventListener('keydown', (e) => {
            const colors = Array.from(palette.querySelectorAll('.color-picker'));
            const currentIndex = colors.findIndex(el => el === document.activeElement);
            
            let newIndex = currentIndex;
            switch(e.key) {
                case 'ArrowRight':
                    newIndex = (currentIndex + 1) % colors.length;
                    break;
                case 'ArrowLeft':
                    newIndex = currentIndex - 1;
                    if (newIndex < 0) newIndex = colors.length - 1;
                    break;
                case 'ArrowDown':
                    newIndex = currentIndex + 4; // Assuming 4 columns
                    if (newIndex >= colors.length) newIndex = currentIndex;
                    break;
                case 'ArrowUp':
                    newIndex = currentIndex - 4;
                    if (newIndex < 0) newIndex = currentIndex;
                    break;
            }
            
            if (newIndex !== currentIndex && colors[newIndex]) {
                e.preventDefault();
                colors[newIndex].focus();
            }
        });
    }
    
    // Modal accessibility
    setupModalAccessibility() {
        // Shop modal
        const shopButton = document.getElementById('open-shop');
        const shopModal = document.getElementById('shop-modal');
        const closeShop = document.getElementById('close-shop');
        
        if (shopButton && shopModal) {
            shopButton.addEventListener('click', () => this.openModal(shopModal));
            closeShop.addEventListener('click', () => this.closeModal(shopModal));
        }
        // Achievements modal
        const achievementsButton = document.getElementById('view-all-achievements');
        const achievementsModal = document.getElementById('achievements-modal');
        const closeAchievements = document.getElementById('close-achievements');
        
        if (achievementsButton && achievementsModal) {
            achievementsButton.addEventListener('click', () => this.openModal(achievementsModal));
            closeAchievements.addEventListener('click', () => this.closeModal(achievementsModal));
        }
    }
    // Live regions for dynamic content
    setupLiveRegions() {
        // Monitor activity feed
        const activityFeed = document.getElementById('activity-feed');
        if (activityFeed) {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                        const newActivity = mutation.addedNodes[0];
                        if (newActivity.textContent) {
                            // Announce new activity with a delay to avoid overwhelming
                            setTimeout(() => {
                                this.announce(newActivity.textContent, 'polite');
                            }, 500);
                        }
                    }
                });
            });
            
            observer.observe(activityFeed, { childList: true });
        }
    }
    // Helper function to get color names
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
    
    // Update theme announcement
    updateThemeAnnouncement(theme) {
        const button = document.getElementById('theme-toggle');
        if (button) {
            button.setAttribute('aria-label', `Change theme. Current theme: ${theme}`);
            this.announce(`Theme changed to ${theme}`);
        }
    }
}
// Export for use in main mural.js
window.AccessibilityManager = AccessibilityManager;








































