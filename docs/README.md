# Packaging & Distribution

We use [Electron Builder](https://www.electron.build/) to create native installers:

## Install builder

```bash
npm install --save-dev electron-builder
```

## package.json scripts

```json
{
  "name": "h2aicv",
  "version": "2.1.0",
  "description": "Advanced Document to AI-Optimized JSON Converter",
  "main": "electron-main.js",
  "scripts": {
    "start": "electron .",
    "pack": "electron-builder --dir",
    "dist": "electron-builder"
  },
  "build": {
    "appId": "com.yourcompany.h2aicv",
    "productName": "H2AICV",
    "files": [
      "electron-main.js",
      "preload.js",
      "index.html",
      "styles.css",
      "renderer.js",
      "assets/**/*"
    ],
    "win": {
      "target": [
        "nsis",
        "zip"
      ],
      "artifactName": "${productName}-Setup-${version}.${ext}"
    },
    "nsis": {
      "oneClick": false,
      "perMachine": false,
      "allowToChangeInstallationDirectory": true
    },
    "mac": {
      "target": [
        "dmg",
        "zip"
      ],
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
      "target": [
        "AppImage",
        "deb"
      ],
      "category": "Utility"
    }
  },
  "devDependencies": {
    "electron": "^12.0.0",
    "electron-builder": "^22.0.0"
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

After `npm run dist` you’ll find:

- `dist/H2AICV-Setup-2.1.0.exe` & `dist/H2AICV-2.1.0.zip` (Windows)
- `dist/H2AICV-2.1.0.dmg` & `dist/H2AICV-2.1.0.zip` (macOS)
- `dist/H2AICV-2.1.0.AppImage`, `dist/H2AICV-2.1.0.deb` (Linux)

Distribute these directly to users for a one-click install on each OS.