<p align="center">
  <img src="assets/logo.png" alt="DocuMancer" width="300"/>
</p>

---

# DocuMancer

---
A modern Electron application for document conversion and management, built with a Python backend and Electron frontend.

## 🏗️ Project Structure

```
DocuMancer/
├── assets/                 # Static assets (icons, backgrounds)
├── backend/               # Python backend services
├── docs/                  # Documentation
├── frontend/              # Electron frontend application
├── scripts/               # Build and deployment scripts
├── shared/                # Shared utilities and constants
├── tests/                 # Test files
├── electron-builder.yml   # Electron builder configuration
├── package.json           # Node.js dependencies and scripts
└── README.md             # This file
```

## 🚀 Quick Start

### Prerequisites

- Node.js (v16 or higher)
- Python 3.8+
- npm or yarn

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/DocuMancer.git
   cd DocuMancer
   ```

2. **Install Node.js dependencies**
   ```bash
   npm install
   ```

3. **Install Python dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   cd ..
   ```

### Development

1. **Start the development server**
   ```bash
   npm run dev
   ```

2. **Build the application**
   ```bash
   npm run build
   ```

3. **Package for distribution**
   ```bash
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
- Sets up DMG installer with custom background
- Defines application metadata and categories

### Package Configuration (`package.json`)
- Defines application metadata
- Contains build and development scripts
- Manages Node.js dependencies

## 🎨 Asset Requirements

### Background Images
- **background.jpg**: 1920x1080 pixels (Full HD) for main app background
- **dmg-background.png**: 540x380 pixels for macOS DMG installer

### Icons
- **app_icon.icns**: macOS application icon (512x512 pixels recommended)

## 🧪 Testing

```bash
# Run tests
npm test

# Run backend tests
cd backend && python -m pytest
```

## 📦 Building

### Development Build
```bash
npm run build
```

### Production Distribution
```bash
npm run dist
```

This will create:
- **Windows**: NSIS installer and ZIP
- **macOS**: DMG and ZIP
- **Linux**: AppImage and DEB

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Issues

If you encounter any issues, please [open an issue](https://github.com/yourusername/DocuMancer/issues) on GitHub.

## 📞 Support

For support and questions, please contact [your-email@example.com](mailto:your-email@example.com).
