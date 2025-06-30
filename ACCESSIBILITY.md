# Mural Accessibility Features

## Overview
The Mural collaborative pixel art application has been enhanced with comprehensive accessibility features to ensure it is fully usable by people with disabilities. This document outlines all accessibility improvements and how to use them.

## Screen Reader Support

### ARIA Implementation
- **Live Regions**: Dynamic content updates are announced through ARIA live regions
  - Polite announcements for general updates (pixel placements, activity feed)
  - Assertive announcements for important alerts (errors, achievements)
- **Landmarks**: Semantic HTML5 landmarks for easy navigation
  - `<header>`, `<main>`, `<aside>`, and `<section>` elements properly labeled
- **Labels and Descriptions**: All interactive elements have descriptive ARIA labels
- **Roles**: Appropriate ARIA roles for complex widgets (radiogroup for color palette)

### Announcements
- Activity feed updates are announced to screen readers
- Achievement notifications are read aloud
- Canvas position changes are announced periodically
- Color selections are announced with color names

## Keyboard Navigation

### Skip Links
- Skip to canvas
- Skip to color palette  
- Skip to statistics
- Visible on focus for keyboard users

### Canvas Controls
| Key | Action |
|-----|--------|
| Arrow Keys | Navigate canvas pixel by pixel |
| Enter/Space | Place pixel at current position |
| 1-9 | Select color from palette |
| +/- | Zoom in/out |
| 0 | Reset zoom to 100% |
| C | Center canvas view |
| H | Toggle keyboard help |
| Escape | Exit keyboard mode |

### Color Palette Navigation
- Arrow keys navigate between colors
- Enter/Space selects a color
- Tab moves through color options

### Modal Navigation
- Focus trapped within modals when open
- Escape key closes modals
- Tab cycles through focusable elements
- Focus returns to trigger element on close

## Visual Accessibility

### Focus Indicators
- High contrast 2px blue outline on all focused elements
- 2px offset for better visibility
- Consistent across all interactive elements

### High Contrast Mode Support
- Enhanced borders in high contrast mode
- Increased border widths for better visibility
- Better separation between UI elements

### Reduced Motion Support
- Animations disabled when `prefers-reduced-motion` is set
- Instant transitions for users sensitive to motion

### Color and Contrast
- WCAG AA compliant color contrast ratios
- Theme toggle supports:
  - Light mode for better readability
  - Dark mode for reduced eye strain
  - Coffee theme with warm tones
- Non-color indicators for all states

## Alternative Interactions

### Voice Command Structure
The application is structured to support voice command software:
- Clear, unique button labels
- Consistent naming conventions
- Logical grouping of controls

### Touch Accessibility
- Minimum 44x44px touch targets
- Adequate spacing between interactive elements
- No hover-only interactions

## Assistive Technology Compatibility

### Semantic HTML
- Proper heading hierarchy (h1 → h2 → h3)
- Form elements with associated labels
- Lists for grouped items
- Buttons vs links used appropriately

### Screen Reader Testing
Optimized for compatibility with:
- NVDA (Windows)
- JAWS (Windows)
- VoiceOver (macOS/iOS)
- TalkBack (Android)

## Implementation Details

### AccessibilityManager Class
The `accessibility.js` file contains the main accessibility manager that handles:
- Keyboard navigation state
- Screen reader announcements
- Focus management
- Modal dialog accessibility

### Integration Points
- Canvas drawing events announce pixel placements
- Activity feed updates are announced
- Achievement unlocks trigger audio announcements
- Theme changes are announced

## Testing Accessibility

### Keyboard Testing
1. Tab through all interactive elements
2. Verify focus indicators are visible
3. Test all keyboard shortcuts
4. Ensure no keyboard traps

### Screen Reader Testing
1. Enable screen reader
2. Navigate using landmarks
3. Verify all content is announced
4. Check dynamic updates are read

### Automated Testing
Use tools like:
- axe DevTools
- WAVE
- Lighthouse (Chrome DevTools)

## Future Enhancements

### Planned Features
- Customizable keyboard shortcuts
- Sound effects toggle
- Alternative color indicators (patterns/shapes)
- Magnification support
- Voice control integration

### Known Limitations
- Canvas pixel selection requires arrow key navigation (no direct coordinate input yet)
- Some complex animations may still play in reduced motion mode
- Voice commands require third-party software

## Contributing

When adding new features, ensure:
1. All interactive elements have keyboard support
2. Dynamic content updates use ARIA live regions
3. Focus management is maintained
4. Color is not the only indicator
5. Touch targets meet minimum size requirements

## Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [WebAIM Resources](https://webaim.org/resources/)