<p align="center">
  <img src="assets/logo.png" alt="DocuMancer" width="300"/>
</p>

---

# DocuMancer

---
A modern Electron application for document conversion and management, built with a hardened Python backend and Electron frontend.

## 🏗️ Project Structure

```
DocuMancer/
├── assets/                 # Static assets (icons, backgrounds)
├── backend/                # Python backend services
├── docs/                   # Documentation
├── frontend/               # Electron frontend application
├── scripts/                # Build and deployment scripts
├── shared/                 # Shared utilities and constants
├── tests/                  # Test files
├── electron-builder.yml    # Electron builder configuration
├── package.json            # Node.js dependencies and scripts
└── README.md               # This file
```

## 🚀 Quick Start

### Prerequisites

- Node.js (v20 or higher)
- Python 3.11+
- npm

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/DocuMancer.git
   cd DocuMancer
   ```

2. **Install Node.js dependencies** (installs Electron, preload tooling, and linting)
   ```bash
   npm install
   ```

3. **Install Python dependencies** (FastAPI service + converter stack)
   ```bash
   pip install -r backend/requirements.txt
   ```
   - Fallback (unlocked): `pip install -r backend/requirements.txt`

### Development

1. **Run the app in development** – starts Electron and will spawn the FastAPI backend when conversions are requested:
   ```bash
   npm run dev
   ```

2. **Lint frontend code**
   ```bash
   npm run lint
   ```

3. **Run backend tests**
   ```bash
   npm run test:backend
   ```

### Packaging

Electron Builder is configured via `electron-builder.yml` to bundle both the frontend and backend:

```bash
# produce unpacked directories
npm run pack

# produce installers (.exe, .dmg, .AppImage, .deb)
npm run dist
```

## 📁 Directory Structure

### Frontend (`frontend/`)
- `electron-main.js` - Main Electron process
- `preload.js` - Preload script for security
- `index.html` - Main application window
- `renderer.js` - Renderer process script
- `styles.css` - Application styles

### Backend (`backend/`)
- `server.py` - FastAPI wrapper with health and conversion endpoints
- `converter.py` - Document conversion logic
- `requirements.txt` - Python dependencies
- `__init__.py` - Python package initialization

### Assets (`assets/`)
- `app_icon.icns` - Application icon (macOS)
- `background.jpg` - Main app background (1920x1080 recommended)
- `dmg-background.png` - DMG installer background (540x380 recommended)

## 🛠️ Configuration

### Electron Builder (`electron-builder.yml`)
- Configures build targets for Windows, macOS, and Linux
- Includes backend, frontend, and assets for packaging
- Defines application metadata and categories

### Package Configuration (`package.json`)
- Defines application metadata
- Contains build, packaging, lint, and test scripts
- Manages Node.js dependencies

## 🧪 Testing

```bash
# Run backend tests via npm wrapper
npm run test:backend

# Or directly
pytest -q
```

## 🧱 Backend configuration

The Electron shell launches `backend/server.py` with environment-driven settings:

- `DOCUMANCER_HOST` / `DOCUMANCER_PORT` – override bind address and port
- `DOCUMANCER_LOG_LEVEL` – `DEBUG`, `INFO`, `WARNING`, etc.
- `DOCUMANCER_LOG_DIR` – folder for rotating JSON logs

Each request returns an `x-request-id` header and uses structured logging for correlation.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Issues

If you encounter any issues, please open an issue on GitHub.

