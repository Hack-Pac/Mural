# Mural - Collaborative Pixel Art Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
A modern, feature-rich recreation of Reddit's r/Place, enabling real-time collaborative pixel art creation on a shared canvas. Built with Flask, SocketIO, and modern web technologies.
## Key Features

### **Real-Time Collaboration**
- Multiple users can place pixels simultaneously
- Instant updates via WebSocket connections
- Live activity feed showing recent placements

### **Advanced Canvas System**
- Interactive 500×500 pixel canvas with smooth zoom and pan
- 32-color palette with carefully selected colors
- Responsive touch and mouse controls
- Smart viewport optimization

### **Performance & Reliability**
- Intelligent caching system (Redis/in-memory)
- Configurable rate limiting and cooldowns
- Session-based user management
- Optimized real-time synchronization

### **Modern UI/UX**
- Multi-theme support (Light/Dark/Auto)
- Mobile-responsive design
- Intuitive controls and visual feedback
- Real-time statistics and user insights

### **Developer-Friendly**
- Modular architecture with service layers
- Comprehensive API endpoints
- Extensive configuration options
- Built-in development tools

## 🛠 Technology Stack
- **Backend**: Flask 2.0+, Flask-SocketIO, Redis (optional)
- **Frontend**: HTML5 Canvas, TailwindCSS 3.0, Vanilla JavaScript
- **Real-time**: WebSocket via Socket.IO
- **Caching**: Redis or in-memory fallback
- **Architecture**: Service-oriented with factory pattern

## Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git
### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/Mural.git
cd Mural

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Access the Application
Open your browser and navigate to **http://localhost:5000**

## Documentation

| Document | Description |
|----------|-------------|
| [**Architecture Guide**](docs/ARCHITECTURE.md) | Detailed system architecture and design patterns |
| [**Setup Guide**](docs/SETUP.md) | Comprehensive installation and configuration |
| [**API Reference**](docs/API.md) | Complete API documentation and examples |
| [**Development Guide**](docs/DEVELOPMENT.md) | Contributing guidelines and development workflow |
| [**Configuration**](docs/CONFIGURATION.md) | Environment variables and customization options |
| [**Troubleshooting**](docs/TROUBLESHOOTING.md) | Common issues and solutions |

## How to Use

1. **Select a Color**: Choose from the 32-color palette
2. **Place Pixels**: Click anywhere on the canvas to place a pixel
3. **Navigate**: 
   - **Pan**: Drag with mouse or touch
   - **Zoom**: Mouse wheel, pinch gesture, or zoom controls
   - **Alternative**: Ctrl+drag or middle mouse for panning
4. **Monitor Activity**: Watch the live activity feed for real-time updates
5. **⏱Cooldown**: Wait for your cooldown timer before placing the next pixel

## Configuration Quick Reference
```bash
# Set custom cooldown (in seconds)
export PIXEL_COOLDOWN=120  # 2 minutes
# Enable Redis caching
export REDIS_URL=redis://localhost:6379

# Set production environment
export FLASK_ENV=production

# Custom host and port
export HOST=0.0.0.0
export PORT=8080
```

## Project Structure

```
Mural/
├── app.py                      # Application entry point
├── app_factory.py              # Flask app factory
├── config.py                   # Configuration management
├── cache_service.py            # Caching abstraction layer
├── models.py                   # Data models
├── services/                   # Business logic services
│   ├── canvas_service.py       # Canvas operations
│   └── user_service.py         # User management
├── routes/                     # API route handlers
│   └── api.py                  # API endpoints
├── templates/                  # HTML templates
│   └── index.html              # Main application template
├── static/                     # Static assets
│   ├── css/style.css           # Custom styles
│   └── js/mural.js             # Frontend application logic
├── docs/                       # Documentation
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Contributing

We welcome contributions! Please see our [Development Guide](docs/DEVELOPMENT.md) for detailed information.

### Quick Contribution Steps
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and test thoroughly
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Deployment

For production deployment instructions, see our [Setup Guide](docs/SETUP.md#production-deployment).
### Quick Production Setup
```bash
# Install production dependencies
pip install gunicorn redis

# Run with Gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```
## Performance

- **Concurrent Users**: Supports 100+ simultaneous users
- **Canvas Updates**: Sub-100ms real-time synchronization
- **Memory Usage**: ~50MB base, scales with canvas activity
- **Caching**: Redis or in-memory with intelligent invalidation

## Issues & Support

- **Bug Reports**: [GitHub Issues](https://github.com/your-username/Mural/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/your-username/Mural/discussions)
- **Documentation**: [docs/](docs/) directory

## Acknowledgments

- Inspired by Reddit's r/Place
- Built with the Flask and Socket.IO communities
- TailwindCSS for beautiful, responsive UI

---











