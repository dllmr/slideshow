# Full-Screen Image Slideshow

A Python-based slideshow application that displays images in full-screen mode with smooth transitions and real-time folder monitoring.

## Features

- Display images from multiple folders in sequence
- Full-screen display on any configured monitor
- Configurable slide duration
- Various transition effects:
  - Fade
  - Slide (left, right, up, down)
  - Random slide
  - Blinds
  - None (instant switch)
- Real-time folder monitoring (images are updated automatically when added/removed)
- Configurable via command-line arguments
- Keyboard and mouse controls
- Automatic image scaling with aspect ratio preservation
- Image caching for smooth performance
- Support for multiple image formats (JPG, PNG, GIF, BMP, WEBP)

## Requirements

- Python ~=3.12 (compatible with Python 3.12.x)
- PySide6 ~=6.8 (compatible with PySide6 6.8.x)

## Installation

1. Clone this repository or download the source code
2. Install the required dependencies:
   ```bash
   pip install "PySide6~=6.8"
   ```

## Usage

Basic usage:
```bash
python slideshow.py [OPTIONS]
```

### Command Line Options

- `-f, --folder PATH`: Path to folder with images (can be specified multiple times)
- `-d, --duration SECONDS`: Seconds to display each image (default: 5)
- `-m, --monitor NUMBER`: Monitor index to use (default: primary monitor)
- `-t, --transition TYPE`: Transition effect to use (default: fade)
  - Options: fade, slide_left, slide_right, slide_up, slide_down, slide_random, blinds, none
- `-s, --shuffle`: Randomize the order of images

### Examples

Display images from a single folder:
```bash
python slideshow.py -f /path/to/images
```

Display images from multiple folders in sequence:
```bash
python slideshow.py -f /path/to/folder1 -f /path/to/folder2 -f /path/to/folder3
```

Customize duration and transition:
```bash
python slideshow.py -f /path/to/images -d 10 -t slide_left
```

Use on a specific monitor with shuffled images:
```bash
python slideshow.py -f /path/to/images -m 1 -s
```

### Controls

- `ESC` or `Q`: Quit slideshow
- `Space` or `Right Arrow`: Next image
- `Left Arrow`: Previous image
- `P`: Pause/Resume slideshow
- `F`: Toggle fullscreen mode
- `Left Click`: Next image
- `Right Click`: Previous image
- `Double Left Click`: Toggle fullscreen mode

## Behavior

- Images are displayed in alphabetical order within each folder
- When multiple folders are specified, images are shown in folder order (unless shuffled)
- The slideshow automatically updates when images are added or removed from monitored folders
- If all images are deleted, the last displayed image remains until new images are added
- The application maintains aspect ratio of images, adding black bars as needed

## Error Handling

- The application gracefully handles missing folders
- Failed image loads are logged and skipped
- After 3 consecutive image load failures, the slideshow stops
- Invalid monitor indices default to the primary monitor
- Missing or invalid transition types default to 'fade'

## Performance Considerations

- Images are cached to improve performance
- Maximum cache size is limited to 10 images or 100MB
- Cache is cleared when the window is resized or the application is paused
- Folder changes are debounced to prevent excessive updates

## License

This project is open source and available under the MIT License.
