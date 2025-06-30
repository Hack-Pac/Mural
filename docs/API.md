# 📡 API Reference

Complete documentation for Mural's REST API and WebSocket events.

## 📋 Table of Contents

- [API Overview](#api-overview)
- [Authentication](#authentication)
- [REST Endpoints](#rest-endpoints)
- [WebSocket Events](#websocket-events)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)
## 🌐 API Overview

Mural provides both REST API endpoints for data operations and WebSocket connections for real-time collaboration.

### Base URL
- **Development**: `http://localhost:5000`
- **Production**: `https://your-domain.com`
### Content Types
- **Request**: `application/json`
- **Response**: `application/json`
### API Versioning
Current API version: **v1** (implicit, no versioning prefix required)

## 🔐 Authentication

Currently, Mural uses **session-based authentication** with automatic user identification. No explicit authentication is required for basic operations.
### Session Management
- Sessions are automatically created on first visit
- Session ID is used for cooldown tracking
- Sessions persist across browser sessions
```javascript
// Session is automatically handled by the browser
// No additional authentication headers required
```
## 🛠 REST Endpoints

### Canvas Operations

#### Get Canvas Data
Retrieve the current state of the canvas.
```http
GET /api/canvas
```
**Response:**
```json
{
  "canvas": [
    [0, 1, 2, ...],
    [3, 4, 5, ...],
    ...
  ],
  "width": 500,
  "height": 500,
  "total_pixels": 12345,
  "last_updated": "2024-01-15T10:30:00Z"
}
```

**Response Codes:**
- `200 OK` - Canvas data retrieved successfully
- `500 Internal Server Error` - Server error

---
#### Place Pixel
Place a pixel on the canvas at specified coordinates.

```http
POST /api/place-pixel
```

**Request Body:**
```json
{
  "x": 250,
  "y": 250,
  "color": 15
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Pixel placed successfully",
  "cooldown_remaining": 300,
  "pixel": {
    "x": 250,
    "y": 250,
    "color": 15,
    "timestamp": "2024-01-15T10:30:00Z",
    "user_id": "session_123"
  }
}
```

**Response (Cooldown Active):**
```json
{
  "success": false,
  "error": "Cooldown active",
  "cooldown_remaining": 245,
  "message": "Please wait 245 seconds before placing another pixel"
}
```

**Response Codes:**
- `200 OK` - Pixel placed successfully
- `400 Bad Request` - Invalid request data
- `429 Too Many Requests` - Cooldown active
- `500 Internal Server Error` - Server error
**Validation Rules:**
- `x`: Integer, 0 ≤ x < 500
- `y`: Integer, 0 ≤ y < 500
- `color`: Integer, 0 ≤ color < 32

---

### User Operations

#### Get Cooldown Status
Check the remaining cooldown time for the current user.

```http
GET /api/cooldown
```

**Response:**
```json
{
  "cooldown_remaining": 180,
  "can_place_pixel": false,
  "last_pixel_time": "2024-01-15T10:27:00Z"
}
```

**Response Codes:**
- `200 OK` - Cooldown status retrieved
- `500 Internal Server Error` - Server error
---

#### Get User Statistics
Retrieve statistics for the current user session.

```http
GET /api/user/stats
```

**Response:**
```json
{
  "pixels_placed": 42,
  "session_start": "2024-01-15T09:00:00Z",
  "last_activity": "2024-01-15T10:30:00Z",
  "user_id": "session_123"
}
```

---

### System Operations
#### Health Check
Check the API health status.

```http
GET /api/health
```
**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime": 3600,
  "cache_status": "connected"
}
```
---

#### Get System Statistics
Retrieve overall system statistics.
```http
GET /api/stats
```
**Response:**
```json
{
  "total_pixels": 50000,
  "active_users": 15,
  "canvas_completion": 20.0,
  "server_uptime": 86400,
  "cache_hit_ratio": 0.85
}
```

## ⚡ WebSocket Events
WebSocket connection endpoint: `/socket.io/`
### Client-to-Server Events
#### Connection
Automatically triggered when client connects.
```javascript
socket.on('connect', () => {
    console.log('Connected to server');
});
```
#### Disconnection
Automatically triggered when client disconnects.
```javascript
socket.on('disconnect', () => {
    console.log('Disconnected from server');
});
```
### Server-to-Client Events

#### Pixel Placed
Broadcasted when any user places a pixel.

```javascript
socket.on('pixel_placed', (data) => {
    // data structure:
    {
        "x": 250,
        "y": 250,
        "color": 15,
        "user_id": "session_123",
        "timestamp": "2024-01-15T10:30:00Z"
    }
});
```

#### Canvas Update
Sent to newly connected clients with the current canvas state.

```javascript
socket.on('canvas_update', (data) => {
    // data structure:
    {
        "canvas": [[0, 1, 2, ...], ...],
        "stats": {
            "total_pixels": 12345,
            "active_users": 8
        }
    }
});
```
#### User Count Update
Broadcasted when the number of active users changes.
```javascript
socket.on('user_count_update', (data) => {
    // data structure:
    {
        "active_users": 12,
        "total_sessions": 150
    }
});
```

#### Server Message
System messages and announcements.

```javascript
socket.on('server_message', (data) => {
    // data structure:
    {
        "type": "info", // "info", "warning", "error"
        "message": "Server maintenance in 5 minutes",
        "timestamp": "2024-01-15T10:30:00Z"
    }
});
```

## 📊 Data Models

### Pixel Object
```javascript
{
    "x": 250,           // X coordinate (0-499)
    "y": 250,           // Y coordinate (0-499)
    "color": 15,        // Color index (0-31)
    "user_id": "session_123",  // User session ID
    "timestamp": "2024-01-15T10:30:00Z"  // ISO timestamp
}
```
### Canvas Object
```javascript
{
    "canvas": [         // 2D array of color indices
        [0, 1, 2, ...], // Row 0
        [3, 4, 5, ...], // Row 1
        ...
    ],
    "width": 500,       // Canvas width in pixels
    "height": 500,      // Canvas height in pixels
    "total_pixels": 12345,  // Total pixels placed
    "last_updated": "2024-01-15T10:30:00Z"  // Last modification time
}
```
### User Session Object
```javascript
{
    "user_id": "session_123",
    "pixels_placed": 42,
    "cooldown_remaining": 180,
    "can_place_pixel": false,
    "session_start": "2024-01-15T09:00:00Z",
    "last_activity": "2024-01-15T10:30:00Z"
}
```
### Color Palette
The application uses a 32-color palette with the following indices:
```javascript
const COLORS = [
    '#000000', // 0  - Black
    '#FFFFFF', // 1  - White
    '#FF0000', // 2  - Red
    '#00FF00', // 3  - Green
    '#0000FF', // 4  - Blue
    '#FFFF00', // 5  - Yellow
    '#FF00FF', // 6  - Magenta
    '#00FFFF', // 7  - Cyan
    '#800000', // 8  - Maroon
    '#008000', // 9  - Dark Green
    '#000080', // 10 - Navy
    '#808000', // 11 - Olive
    '#800080', // 12 - Purple
    '#008080', // 13 - Teal
    '#C0C0C0', // 14 - Silver
    '#808080', // 15 - Gray
    '#FF8080', // 16 - Light Red
    '#80FF80', // 17 - Light Green
    '#8080FF', // 18 - Light Blue
    '#FFFF80', // 19 - Light Yellow
    '#FF80FF', // 20 - Light Magenta
    '#80FFFF', // 21 - Light Cyan
    '#FFA500', // 22 - Orange
    '#FFC0CB', // 23 - Pink
    '#A52A2A', // 24 - Brown
    '#DDA0DD', // 25 - Plum
    '#90EE90', // 26 - Light Green
    '#F0E68C', // 27 - Khaki
    '#FA8072', // 28 - Salmon
    '#20B2AA', // 29 - Light Sea Green
    '#87CEEB', // 30 - Sky Blue
    '#D2691E'  // 31 - Chocolate
];
```
## ❌ Error Handling
### Error Response Format
All API errors follow a consistent format:

```json
{
    "success": false,
    "error": "error_code",
    "message": "Human-readable error message",
    "timestamp": "2024-01-15T10:30:00Z",
    "details": {
        "field": "validation_error"
    }
}
```

### Common Error Codes

#### 400 Bad Request
```json
{
    "success": false,
    "error": "invalid_coordinates",
    "message": "Coordinates must be within canvas bounds (0-499)",
    "details": {
        "x": 500,
        "y": 250,
        "max_x": 499,
        "max_y": 499
    }
}
```

#### 429 Too Many Requests
```json
{
    "success": false,
    "error": "cooldown_active",
    "message": "Please wait before placing another pixel",
    "cooldown_remaining": 245
}
```
#### 500 Internal Server Error
```json
{
    "success": false,
    "error": "internal_error",
    "message": "An unexpected error occurred",
    "timestamp": "2024-01-15T10:30:00Z"
}
```
## ⏱️ Rate Limiting
### Pixel Placement Cooldown
- **Development**: 60 seconds (configurable)
- **Production**: 300 seconds (5 minutes, configurable)
- Per-session enforcement
- Configurable via `PIXEL_COOLDOWN` environment variable

### API Rate Limits
- **General API calls**: 100 requests per minute per session
- **Canvas data**: 10 requests per minute per session
- **WebSocket connections**: 1 connection per session

## 📝 Examples
### JavaScript/Fetch API
#### Place a Pixel
```javascript
async function placePixel(x, y, color) {
    try {
        const response = await fetch('/api/place-pixel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ x, y, color })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('Pixel placed successfully!');
        } else {
            console.log('Error:', data.message);
        }
    } catch (error) {
        console.error('Network error:', error);
    }
}
// Usage
placePixel(250, 250, 15);
```
#### Get Canvas Data
```javascript
async function getCanvas() {
    try {
        const response = await fetch('/api/canvas');
        const canvas = await response.json();
        
        console.log('Canvas size:', canvas.width, 'x', canvas.height);
        console.log('Total pixels:', canvas.total_pixels);
        return canvas;
    } catch (error) {
        console.error('Failed to load canvas:', error);
    }
}
```

#### WebSocket Integration
```javascript
// Initialize WebSocket connection
const socket = io();
// Handle connection events
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

// Handle pixel updates
socket.on('pixel_placed', (pixel) => {
    console.log('New pixel placed:', pixel);
    updateCanvasDisplay(pixel.x, pixel.y, pixel.color);
});
// Handle canvas updates for new connections
socket.on('canvas_update', (data) => {
    console.log('Canvas state received');
    renderFullCanvas(data.canvas);
});
```
### Python/Requests

#### Place a Pixel
```python
import requests
def place_pixel(x, y, color, base_url='http://localhost:5000'):
    url = f'{base_url}/api/place-pixel'
    data = {'x': x, 'y': y, 'color': color}
    
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        if result['success']:
            print('Pixel placed successfully!')
        else:
            print(f'Error: {result["message"]}')
    else:
        print(f'HTTP Error: {response.status_code}')

# Usage
place_pixel(250, 250, 15)
```
#### Get Canvas Data
```python
import requests
def get_canvas(base_url='http://localhost:5000'):
    url = f'{base_url}/api/canvas'
    
    response = requests.get(url)
    
    if response.status_code == 200:
        canvas = response.json()
        print(f'Canvas size: {canvas["width"]}x{canvas["height"]}')
        print(f'Total pixels: {canvas["total_pixels"]}')
        return canvas
    else:
        print(f'HTTP Error: {response.status_code}')
        return None
```
### cURL Examples

#### Place a Pixel
```bash
curl -X POST http://localhost:5000/api/place-pixel \
  -H "Content-Type: application/json" \
  -d '{"x": 250, "y": 250, "color": 15}'
```
#### Get Canvas Data
```bash
curl http://localhost:5000/api/canvas
```
#### Check Cooldown Status
```bash
curl http://localhost:5000/api/cooldown
```

---

This API documentation provides complete coverage of Mural's REST endpoints and WebSocket events. For implementation examples and integration guides, see the [Development Guide](DEVELOPMENT.md).



























































