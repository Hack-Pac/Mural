# Architecture Overview

## System Architecture
Mural is built using a modern web application architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask API     │    │   Data Layer    │
│                 │    │                 │    │                 │
│ • HTML/CSS/JS   │◄──►│ • REST API      │◄──►│ • JSON Files    │
│ • TailwindCSS   │    │ • WebSocket     │    │ • Redis Cache   │
│ • Socket.IO     │    │ • Session Mgmt  │    │ • SQLite (alt)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```
## Core Components

### 1. Application Entry Point (`app.py`)
- **Purpose**: Main Flask application with WebSocket integration
- **Key Features**:
  - Real-time pixel placement via Socket.IO
  - Session management for user tracking
  - Cooldown enforcement (configurable via environment)
  - Canvas persistence to/from JSON files
  - Initial pixel art generation
### 2. Modular Architecture
The application supports both monolithic (`app.py`) and modular architectures:
#### Modular Components:
- **`app_factory.py`**: Application factory pattern
- **`models.py`**: SQLAlchemy data models (User, Pixel, Cooldown)
- **`cache_service.py`**: Redis caching with fallback
- **`services/`**: Business logic services
- **`routes/`**: API route handlers

### 3. Caching System (`cache_service.py`)
```python
# High-performance caching with automatic fallback
class CacheService:
    - Redis primary cache
    - In-memory fallback
    - Automatic expiration handling
    - Error resilience

class MuralCache:
    - Canvas data caching
    - User statistics caching  
    - Cooldown management
    - Cache invalidation strategies
```

### 4. Services Layer

#### Canvas Service (`services/canvas_service.py`)
- Pixel placement and retrieval
- Canvas data caching (30-second TTL)
- User pixel count management
- Maintenance functions

#### User Service (`services/user_service.py`)
- User creation and session management
- Activity tracking
- Cleanup of inactive users

### 5. Frontend Architecture

#### JavaScript (`static/js/mural.js`)
- **MuralUtils**: Utility functions for AJAX, DOM manipulation, debouncing
- **Theme Management**: Light/dark/coffee theme switching with persistence
- **Canvas Rendering**: Optimized pixel-perfect rendering with zoom/pan
- **Real-time Updates**: Socket.IO integration for live pixel placement
- **User Interface**: Responsive controls and statistics display

#### Styling (`static/css/style.css`)
- **TailwindCSS**: Utility-first CSS framework
- **Theme System**: CSS variables and custom classes for theme switching
- **Coffee Theme**: Complete visual overhaul with warm brown palette
- **Responsive Design**: Mobile-first approach with adaptive layouts
## Data Flow
### Pixel Placement Flow
1. **User Input**: Click on canvas → JavaScript captures coordinates
2. **Validation**: Client-side boundary checking
3. **API Request**: POST to `/api/place-pixel` with coordinates and color
4. **Server Processing**:
   - Cooldown validation
   - Pixel placement in canvas data
   - Cache updates (user stats, canvas cache invalidation)
   - File persistence
5. **Real-time Update**: WebSocket broadcast to all connected clients
6. **Client Update**: All clients render the new pixel immediately
### Caching Strategy
```
┌─────────────────┐
│ Request Arrives │
└─────┬───────────┘
      │
      ▼
┌─────────────────┐    Yes   ┌─────────────────┐
│ Check Cache     │─────────►│ Return Cached   │
│ (Redis/Memory)  │          │ Data            │
└─────┬───────────┘          └─────────────────┘
      │ No
      ▼
┌─────────────────┐          ┌─────────────────┐
│ Generate Data   │─────────►│ Cache Result    │
│ (DB/File/Calc)  │          │ & Return        │
└─────────────────┘          └─────────────────┘
```

## Configuration Management
### Environment-Based Configuration (`config.py`)
- **Development**: Shorter cooldowns, debug mode, verbose logging
- **Production**: Longer cooldowns, optimized settings, error tracking
- **Configurable Parameters**:
  - `PIXEL_COOLDOWN`: Seconds between pixel placements
  - `CANVAS_WIDTH/HEIGHT`: Canvas dimensions
  - Cache TTL values
  - CORS settings
### Runtime Configuration (`.env`)
```properties
PIXEL_COOLDOWN=5
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
FLASK_ENV=development
```
## Persistence Strategy

### Canvas Data Persistence
- **Primary**: JSON file (`canvas_data.json`)
- **Format**: `{"x,y": {"color": "#hex", "timestamp": "ISO", "user_id": "uuid"}}`
- **Triggers**: After each pixel placement, periodic backups
- **Recovery**: Automatic loading on application start

### Session Persistence
- **Flask Sessions**: Secure signed cookies
- **User Identification**: UUID-based anonymous users
- **Lifetime**: 24 hours configurable
## Scalability Considerations

### Current Architecture Limitations
- **Single Server**: No horizontal scaling support
- **File-based Storage**: Not suitable for multi-server deployments
- **In-memory Sessions**: Lost on server restart

### Future Scalability Enhancements
- **Database Migration**: SQLAlchemy models ready for PostgreSQL/MySQL
- **Session Store**: Redis-based session storage
- **Load Balancing**: WebSocket session affinity considerations
- **CDN Integration**: Static asset optimization

## Security Features

### Input Validation
- **Coordinate Bounds**: Strict canvas boundary enforcement
- **Color Format**: Hex color validation (#RRGGBB)
- **Rate Limiting**: Cooldown system prevents spam
### Session Security
- **Secure Cookies**: HTTPOnly, Secure flags in production
- **CSRF Protection**: Built-in Flask session protection
- **Anonymous Users**: No personal data collection
## Performance Optimizations

### Client-Side
- **Canvas Rendering**: Efficient pixel-by-pixel drawing
- **Event Debouncing**: Reduced API calls during rapid interactions
- **Theme Caching**: Local storage for user preferences
- **Lazy Loading**: Progressive canvas loading for large datasets
### Server-Side
- **Multi-tier Caching**: Redis → Memory → Database/File
- **Connection Pooling**: Efficient WebSocket management
- **Background Tasks**: Periodic cleanup and maintenance
- **Optimized Queries**: Indexed database queries (when using SQLAlchemy)
## Monitoring and Observability
### Logging
- **Structured Logging**: JSON format for production
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Key Metrics**: Pixel placement rate, cache hit ratios, error rates
### Health Checks
- **Redis Connectivity**: Automatic fallback on Redis failure
- **File System**: Canvas data persistence monitoring
- **Memory Usage**: Cooldown and cache cleanup












































