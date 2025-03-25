# Full-Screen Image Slideshow

A Python application that displays images from a folder as a full-screen slideshow with configurable transition effects.

## Features

- Display images from a specified folder in sequence
- Full-screen display on a configurable monitor
- Configurable slide duration
- Various transition effects (fade, slide, blinds)
- Image shuffling option
- Simple keyboard and mouse controls

## Requirements

- Python 3.12
- PySide6 (Qt for Python)

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/slideshow.git
cd slideshow
```

2. Install dependencies:
```
pip install PySide6
```

Alternatively, you can use the script's embedded dependencies header:
```
pip install -e .
```

## Usage

```
python slideshow.py [OPTIONS]
```

### Command-line Options

| Option | Description |
|--------|-------------|
| `--folder PATH` | Path to folder with images (default: current directory) |
| `--duration SECONDS` | Seconds to display each image (default: 5) |
| `--monitor NUMBER` | Monitor index to use (default: primary monitor) |
| `--transition TYPE` | Transition effect to use (default: fade) |
| `--shuffle` | Randomize the order of images |

### Available Transition Effects

- `fade` - Cross-fade between images
- `slide_left` - Slide current image left, next image comes from right
- `slide_right` - Slide current image right, next image comes from left
- `slide_up` - Slide current image up, next image comes from bottom
- `slide_down` - Slide current image down, next image comes from top
- `slide_random` - Random slide direction for each transition
- `blinds` - Vertical blinds effect
- `none` - No transition effect

### Keyboard Controls

| Key | Action |
|-----|--------|
| ESC/Q | Quit slideshow |
| Space/Right Arrow | Next image |
| Left Arrow | Previous image |
| P | Pause/Resume |
| F | Toggle fullscreen |

### Mouse Controls

- Left Click: Next image
- Right Click: Previous image
- Double Click: Toggle fullscreen

## Supported Image Formats

- JPG/JPEG
- PNG
- GIF
- BMP
- WebP

## Examples

Display images from the "photos" folder with a 3-second duration:
```
python slideshow.py --folder photos --duration 3
```

Display images on the second monitor with a slide-left transition:
```
python slideshow.py --monitor 1 --transition slide_left
```

Shuffle images and use random slide transitions:
```
python slideshow.py --shuffle --transition slide_random
```

## License

[GNU GPLv3](https://choosealicense.com/licenses/gpl-3.0/)
