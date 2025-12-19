# Packaging & Distribution

DocuMancer uses [Electron Builder](https://www.electron.build/) to produce installers that include the Electron frontend and bundled Python backend.

## Install builder

```bash
npm install
```

## package.json scripts

```json
{
  "name": "documancer",
  "version": "2.1.0",
  "description": "Advanced Document to AI-Optimized JSON Converter",
  "main": "frontend/electron-main.js",
  "scripts": {
    "start": "electron .",
    "dev": "ELECTRON_ENABLE_LOGGING=1 electron .",
    "pack": "electron-builder --config electron-builder.yml --dir",
    "dist": "electron-builder --config electron-builder.yml",
    "lint": "eslint frontend/*.js",
    "test:backend": "pytest"
  },
  "build": {
    "appId": "com.yourcompany.documancer",
    "productName": "DocuMancer",
    "files": [
      "frontend/**/*",
      "backend/**/*",
      "assets/**/*",
      "package.json"
    ],
    "win": {
      "target": ["nsis", "zip"],
      "artifactName": "DocuMancer-Setup-${version}.${ext}"
    },
    "nsis": {
      "oneClick": false,
      "perMachine": false,
      "allowToChangeInstallationDirectory": true
    },
    "mac": {
      "target": ["dmg", "zip"],
      "category": "public.app-category.productivity"
    },
    "dmg": {
      "background": "assets/dmg-background.png",
      "icon": "assets/app_icon.icns",
      "contents": [
        { "x": 410, "y": 150, "type": "link", "path": "/Applications" },
        { "x": 130, "y": 150, "type": "file" }
      ]
    },
    "linux": {
      "target": ["AppImage", "deb"],
      "category": "Utility"
    }
  }
}
```

## Build for all platforms

```bash
# produce unpacked directories:
npm run pack

# produce installers (.exe, .dmg, .AppImage, .deb):
npm run dist
```

After `npm run dist` you’ll find installers under `dist/` for Windows, macOS, and Linux targets.
