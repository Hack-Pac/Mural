# Mural - Collaborative Pixel Art

A recreation of Reddit's r/Place, allowing users to collaboratively create pixel art on a shared canvas in real-time.

## Features

- **Real-time collaboration**: Multiple users can place pixels simultaneously
- **Live updates**: See other users' pixels appear instantly via WebSocket connections
- **Interactive canvas**: Zoom, pan, and navigate the 500x500 pixel canvas
- **Color palette**: 32 predefined colors to choose from
- **Cooldown system**: Configurable pixel placement cooldown (default: 5 minutes in production, 1 minute in development)
- **Activity feed**: Track recent pixel placements and system events
- **Statistics**: Monitor total pixels placed and your contributions
- **Session management**: Unique user identification and cooldown tracking
- **Responsive design**: Works on desktop and mobile devices

## Technology Stack

- **Backend**: Flask (Python)
- **Real-time communication**: Flask-SocketIO
- **Frontend**: HTML5 Canvas, TailwindCSS, Vanilla JavaScript
- **Styling**: TailwindCSS for modern, responsive UI

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Mural
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```
   
   **Or run with custom cooldown**:
   ```bash
   # Windows
   start-with-cooldown.bat 30  # 30 second cooldown
   start-with-cooldown.bat 300 # 5 minute cooldown
   
   # Or set environment variable
   set PIXEL_COOLDOWN=120
   python app.py
   ```

6. **Open your browser** and navigate to `http://localhost:5000`

## Usage

1. **Select a color** from the palette on the right sidebar
2. **Click on the canvas** to place a pixel at that location
3. **Drag on the canvas** to pan around and explore different areas
4. **Use zoom controls** to zoom in/out of the canvas, or use the scroll wheel
5. **Use Ctrl+drag or middle mouse** for alternative panning methods
6. **Watch the activity feed** to see real-time updates from other users

## Project Structure

```
Mural/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # Project documentation
├── templates/
│   └── index.html        # Main HTML template
├── static/
│   ├── css/
│   │   └── style.css     # Custom CSS styles
│   └── js/
│       └── mural.js      # Frontend JavaScript logic
```

## API Endpoints

- `GET /` - Main application page
- `GET /api/canvas` - Get current canvas state
- `GET /api/cooldown` - Get user's current cooldown status
- `POST /api/place-pixel` - Place a pixel on the canvas (with cooldown enforcement)

## WebSocket Events

- `connect` - Client connects to the server
- `disconnect` - Client disconnects from the server
- `pixel_placed` - Broadcast when a pixel is placed
- `canvas_update` - Send current canvas state to new clients

## Configuration

### Environment Variables

- `SECRET_KEY`: Flask secret key (change in production)
- `PIXEL_COOLDOWN`: Cooldown time in seconds (default: 300 for production, 60 for development)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 5000)
- `FLASK_ENV`: Flask environment (development/production)

### Cooldown Settings

You can easily adjust the pixel placement cooldown:

1. **Environment Variable**: Set `PIXEL_COOLDOWN=120` (for 2 minutes)
2. **Batch Script**: Use `start-with-cooldown.bat 120`
3. **Config File**: Copy `.env.example` to `.env` and modify `PIXEL_COOLDOWN`

### Canvas Settings

- Canvas size: 500x500 pixels
- Color palette: 32 predefined colors
- Real-time updates via WebSocket
- Session-based user identification

## Development

### Adding New Colors

To add new colors to the palette, modify the `colors` array in `static/js/mural.js`:

```javascript
this.colors = [
    '#000000', '#FFFFFF', // existing colors...
    '#NEW_COLOR_HEX'      // add new color
];
```

### Database Integration

The current implementation uses in-memory storage. For production, consider integrating with a database:

1. Add database dependencies (e.g., SQLAlchemy)
2. Create pixel storage models
3. Update the pixel placement and retrieval logic

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Deployment

### Production Considerations

1. **Use a production WSGI server** (e.g., Gunicorn)
2. **Set up a reverse proxy** (e.g., Nginx)
3. **Use a proper database** (e.g., PostgreSQL, Redis)
4. **Configure environment variables**
5. **Set up SSL/HTTPS**
6. **Implement rate limiting**
7. **Add user authentication**

### Example Production Setup

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

## Troubleshooting

### Common Issues

1. **WebSocket connection fails**: Check firewall settings and ensure port 5000 is accessible
2. **Pixels not appearing**: Verify the Flask-SocketIO installation and configuration
3. **Canvas not loading**: Check browser console for JavaScript errors

### Support

For issues and questions, please open an issue on the GitHub repository.