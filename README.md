# Pixelizer

Desktop app for pixelating PNG and JPEG images.

<img width="1051" height="713" alt="screen" src="https://github.com/user-attachments/assets/1fe8b41f-8038-4b36-9665-0ab2934fab3a" />

## Features

- Load images via **Upload** or drag-and-drop onto the preview
- Live preview while moving the pixelation slider
- **Smoothing** toggle — sharp blocks vs soft blocks
- **Compare** mode — processed image on the left, original on the right
- Pan (drag) and zoom (mouse wheel) in preview
- Export result as PNG or JPEG

## Requirements

- Windows (drag-and-drop uses `tkinterdnd2`)
- Python 3.12+

## Setup

```powershell
py -m pip install -r requirements.txt
```

## Run

```powershell
py main.py
```

## Build `.exe`

```powershell
.\build.bat
```

Output: `dist\Pixelizer.exe`

## Project layout

| File                | Description                          |
| ------------------- | ------------------------------------ |
| `main.py`           | Entry point and UI                   |
| `pixelizer_core.py` | Pixelation algorithms                |
| `preview_view.py`   | Preview canvas (pan / zoom)          |
| `toggle_switch.py`  | Smoothing toggle widget              |
| `worker.py`         | Image processing worker (subprocess) |
| `pixelizer.spec`    | PyInstaller configuration            |
| `build.bat`         | One-step Windows build script        |

## License

MIT — free to use and modify. Just for fun!
