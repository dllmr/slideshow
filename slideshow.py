# /// script
# requires-python = "~=3.12"
# dependencies = [
#     "PySide6~=6.8",
# ]
# ///

"""
Full-Screen Image Slideshow

Features:
- Display images from a specified folder in sequence
- Full-screen display on a configurable monitor
- Configurable slide duration
- Various transition effects
- Configuration via command-line arguments

Usage:
    python slideshow.py [OPTIONS]

Options:
    --folder PATH         Path to folder with images (default: current directory)
    --duration SECONDS    Seconds to display each image (default: 5)
    --monitor NUMBER      Monitor index to use (default: primary monitor)
    --transition TYPE     Transition effect to use (default: fade)
                          Options: fade, slide_left, slide_right, slide_up, slide_down, 
                                   slide_random, blinds, none
    --shuffle             Randomize the order of images

Controls:
    ESC/Q        - Quit slideshow
    Space/Right  - Next image
    Left         - Previous image
    P            - Pause/Resume
    F            - Toggle fullscreen
"""

import sys
import random
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set, Callable, Optional, Any, TypedDict

# Check Python version - require exactly 3.12.x
import platform
python_version = platform.python_version_tuple()
if python_version[0] != '3' or python_version[1] != '12':
    print("Error: This script requires Python 3.12.x exactly")
    print(f"Current Python version: {platform.python_version()}")
    sys.exit(1)

try:
    from PySide6.QtWidgets import (QApplication, QWidget, QMainWindow)
    from PySide6.QtGui import (QPixmap, QPainter, QColor, QPalette, QKeyEvent,
                              QGuiApplication, QMouseEvent, QShortcut, QKeySequence)
    from PySide6.QtCore import (Qt, QTimer, QRect, QObject, QFileSystemWatcher)
except ImportError:
    print("PySide6 is required. Install it with: pip install PySide6")
    sys.exit(1)

# Configuration Types
class ConfigDict(TypedDict):
    folders: List[str]
    duration: int
    monitor: int
    transition: str
    shuffle: bool

# Configuration Constants
DEFAULT_CONFIG: ConfigDict = {
    'folders': ['.'],  # Changed from 'folder' to 'folders' list
    'duration': 5,
    'monitor': 0,
    'transition': 'fade',
    'shuffle': False
}

# Window Settings
INITIAL_WINDOW_WIDTH: int = 800
INITIAL_WINDOW_HEIGHT: int = 600
WINDOW_SIZE_PERCENT: float = 0.8  # 80% of screen size for non-fullscreen mode

# Transition Settings
TRANSITION_DURATION: int = 1000  # milliseconds
TRANSITION_STEPS: int = 60
BLINDS_COUNT: int = 40  # Number of vertical blinds

# Cache Settings
MAX_CACHE_SIZE: int = 10  # Maximum number of images to cache
MAX_CACHE_MEMORY: int = 100 * 1024 * 1024  # 100MB max cache size

# Error Handling
MAX_IMAGE_FAILURES: int = 3  # Maximum number of consecutive image load failures before stopping

# File System Settings
FOLDER_CHANGE_DEBOUNCE: int = 500  # milliseconds to wait before processing folder changes

# Supported image formats
IMAGE_EXTENSIONS: List[str] = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

# Type aliases
TransitionFunc = Callable[[QPainter, QRect, float], None]
ImagePathInfo = Tuple[Path, int]  # (path, folder_index)
CacheKey = Tuple[int, int, int]  # (pixmap.cacheKey(), width, height)

class TransitionManager(QObject):
    """Manages different transition effects between images"""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.current_pixmap: Optional[QPixmap] = None
        self.next_pixmap: Optional[QPixmap] = None
        self.progress: float = 0.0
        self.current_random_direction: str = 'right'  # Default direction

        # Available transition types
        self.transitions: Dict[str, TransitionFunc] = {
            'none': self.no_transition,
            'fade': self.fade_transition,
            'slide_left': lambda p, c, n: self.slide_transition(p, c, n, 'left'),
            'slide_right': lambda p, c, n: self.slide_transition(p, c, n, 'right'),
            'slide_up': lambda p, c, n: self.slide_transition(p, c, n, 'up'),
            'slide_down': lambda p, c, n: self.slide_transition(p, c, n, 'down'),
            'blinds': self.blinds_transition,
            'slide_random': self.slide_random_transition,
        }

        self.transition_type: str = 'fade'

    def set_transition(self, transition_name: str) -> None:
        """Set the current transition effect"""
        if transition_name in self.transitions:
            self.transition_type = transition_name

    def set_images(self, current: QPixmap, next_img: QPixmap) -> None:
        """Set the current and next images for the transition"""
        self.current_pixmap = current
        self.next_pixmap = next_img
        self.progress = 0.0
        
        # Choose a new random direction if using slide_random
        if self.transition_type == 'slide_random':
            self.current_random_direction = random.choice(['left', 'right', 'up', 'down'])

    def draw(self, painter: QPainter, rect: QRect, progress: float) -> None:
        """Draw the current transition state"""
        if not self.current_pixmap or not self.next_pixmap:
            return

        self.progress = progress
        transition_func = self.transitions.get(self.transition_type, self.fade_transition)
        transition_func(painter, rect, progress)

    def get_centered_rect(self, pixmap: QPixmap, rect: QRect) -> QRect:
        """Calculate the centered rectangle for the pixmap.
        This is needed to properly position images in the widget when in windowed mode."""
        if pixmap.width() == rect.width() and pixmap.height() == rect.height():
            # If the pixmap is already exactly the same size as the rect, just return the rect
            return rect
            
        # Otherwise calculate the centered position
        x = rect.x() + (rect.width() - pixmap.width()) // 2
        y = rect.y() + (rect.height() - pixmap.height()) // 2
        
        return QRect(x, y, pixmap.width(), pixmap.height())

    def no_transition(self, painter: QPainter, rect: QRect, progress: float) -> None:
        """No transition effect - just switch images at 50% progress"""
        if progress < 0.5:
            painter.drawPixmap(self.get_centered_rect(self.current_pixmap, rect), self.current_pixmap)
        else:
            painter.drawPixmap(self.get_centered_rect(self.next_pixmap, rect), self.next_pixmap)

    def fade_transition(self, painter: QPainter, rect: QRect, progress: float) -> None:
        """Fade transition effect"""
        # Draw current image
        painter.setOpacity(1.0 - progress)
        painter.drawPixmap(self.get_centered_rect(self.current_pixmap, rect), self.current_pixmap)

        # Draw next image
        painter.setOpacity(progress)
        painter.drawPixmap(self.get_centered_rect(self.next_pixmap, rect), self.next_pixmap)

    def blinds_transition(self, painter: QPainter, rect: QRect, progress: float) -> None:
        """Vertical blinds transition effect"""
        # Get positioned rectangles for both images
        current_rect = self.get_centered_rect(self.current_pixmap, rect)
        next_rect = self.get_centered_rect(self.next_pixmap, rect)
        
        # Fill the background with black (in case the widget is larger than images)
        painter.fillRect(rect, QColor(0, 0, 0))
        
        # Don't proceed if progress is 0
        if progress <= 0:
            painter.drawPixmap(current_rect, self.current_pixmap)
            return
            
        # First draw the current image as the base
        painter.drawPixmap(current_rect, self.current_pixmap)
        
        # Number of blinds (vertical strips)
        num_blinds = BLINDS_COUNT
        
        # Use ceiling division to ensure we don't get gaps due to rounding
        blind_width = current_rect.width() / num_blinds
        
        # With PySide6, we need to use QPainterPath to combine clip regions
        from PySide6.QtGui import QPainterPath
        clip_path = QPainterPath()
        
        for i in range(num_blinds):
            # Calculate blind position (ensure integers to avoid pixel gaps)
            blind_x = current_rect.x() + int(i * blind_width)
            
            # Calculate the width of the blind opening, ensure it fills the entire blind width when progress=1
            # Use the next blind position to ensure no gaps
            next_blind_x = current_rect.x() + int((i+1) * blind_width)
            this_blind_width = next_blind_x - blind_x
            open_width = int(this_blind_width * progress)
            
            # Skip if nothing to draw
            if open_width <= 0:
                continue
                
            # For even-indexed blinds, align from left
            # For odd-indexed blinds, align from right
            if i % 2 == 0:
                blind_start_x = blind_x
            else:
                blind_start_x = next_blind_x - open_width
            
            # Add this rect to the clip path
            clip_rect = QRect(
                blind_start_x, current_rect.y(), 
                open_width, current_rect.height()
            )
            clip_path.addRect(clip_rect)
        
        # Apply the combined clip path
        painter.save()
        painter.setClipPath(clip_path)
        
        # Draw next image through all clip regions at once
        painter.drawPixmap(next_rect, self.next_pixmap)
        
        # Restore painter state (removes clipping)
        painter.restore()

    def slide_transition(self, painter: QPainter, rect: QRect, progress: float, direction: str) -> None:
        """Slide transition effect in the specified direction"""
        # Get the centered rectangles for both images
        current_rect = self.get_centered_rect(self.current_pixmap, rect)
        next_rect = self.get_centered_rect(self.next_pixmap, rect)
        
        # Store the original positions for reference
        current_original_x = current_rect.x()
        current_original_y = current_rect.y()
        
        # Fill background with black
        painter.fillRect(rect, QColor(0, 0, 0))

        if direction == 'left':
            # Current image moves left
            current_x = current_original_x - rect.width() * progress
            # Next image comes from right
            next_x = current_original_x + rect.width() * (1.0 - progress)

            painter.drawPixmap(QRect(current_x, current_original_y, current_rect.width(), current_rect.height()), 
                              self.current_pixmap)
            painter.drawPixmap(QRect(next_x, current_original_y, next_rect.width(), next_rect.height()), 
                              self.next_pixmap)

        elif direction == 'right':
            # Current image moves right
            current_x = current_original_x + rect.width() * progress
            # Next image comes from left
            next_x = current_original_x - rect.width() * (1.0 - progress)

            painter.drawPixmap(QRect(current_x, current_original_y, current_rect.width(), current_rect.height()), 
                              self.current_pixmap)
            painter.drawPixmap(QRect(next_x, current_original_y, next_rect.width(), next_rect.height()), 
                              self.next_pixmap)

        elif direction == 'up':
            # Current image moves up
            current_y = current_original_y - rect.height() * progress
            # Next image comes from bottom
            next_y = current_original_y + rect.height() * (1.0 - progress)

            painter.drawPixmap(QRect(current_original_x, current_y, current_rect.width(), current_rect.height()), 
                              self.current_pixmap)
            painter.drawPixmap(QRect(current_original_x, next_y, next_rect.width(), next_rect.height()), 
                              self.next_pixmap)

        elif direction == 'down':
            # Current image moves down
            current_y = current_original_y + rect.height() * progress
            # Next image comes from top
            next_y = current_original_y - rect.height() * (1.0 - progress)

            painter.drawPixmap(QRect(current_original_x, current_y, current_rect.width(), current_rect.height()), 
                              self.current_pixmap)
            painter.drawPixmap(QRect(current_original_x, next_y, next_rect.width(), next_rect.height()), 
                              self.next_pixmap)

    def slide_random_transition(self, painter: QPainter, rect: QRect, progress: float) -> None:
        """Random slide transition that uses a different direction each time"""
        self.slide_transition(painter, rect, progress, self.current_random_direction)


class SlideshowWidget(QWidget):
    """Widget that displays images with transition effects"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Image data
        self.current_image: QPixmap = QPixmap()
        self.next_image: QPixmap = QPixmap()
        self.scaled_current: QPixmap = QPixmap()
        self.scaled_next: QPixmap = QPixmap()
        
        # Cache for scaled images
        self.image_cache: Dict[CacheKey, QPixmap] = {}
        self.cache_size: int = MAX_CACHE_SIZE
        self.max_cache_size: int = MAX_CACHE_MEMORY

        # Animation state
        self.animation_progress: float = 0.0
        self.in_transition: bool = False

        # Transition manager
        self.transition_mgr: TransitionManager = TransitionManager(self)

        # Animation timer
        self.animation_timer: QTimer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_duration: int = TRANSITION_DURATION
        self.animation_steps: int = TRANSITION_STEPS
        self.animation_step: int = 0

        # Set background to black
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.setPalette(palette)

    def clear_cache(self) -> None:
        """Clear the image cache"""
        self.image_cache.clear()

    def get_cache_size(self) -> int:
        """Calculate total size of cached images in bytes"""
        total_size = 0
        for pixmap in self.image_cache.values():
            # Approximate size: width * height * 4 bytes per pixel
            total_size += pixmap.width() * pixmap.height() * 4
        return total_size

    def set_current_image(self, pixmap: QPixmap) -> None:
        """Set the current image"""
        self.current_image = pixmap
        self.scale_images()
        self.update()

    def set_next_image(self, pixmap: QPixmap) -> None:
        """Set the next image and start transition"""
        self.next_image = pixmap
        self.scale_images()

        # Set images in transition manager
        self.transition_mgr.set_images(self.scaled_current, self.scaled_next)

        # Start transition animation
        self.start_transition()

    def scale_images(self) -> None:
        """Scale images to fit widget size while maintaining aspect ratio"""
        if self.current_image and not self.current_image.isNull():
            self.scaled_current = self.scale_pixmap(self.current_image)

        if self.next_image and not self.next_image.isNull():
            self.scaled_next = self.scale_pixmap(self.next_image)

    def scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """Scale a pixmap to fit widget size while maintaining aspect ratio.
        This maintains the original proportions of the already pre-formatted image."""
        if pixmap.isNull():
            return QPixmap()

        # Create a cache key based on the image and current size
        cache_key: CacheKey = (pixmap.cacheKey(), self.width(), self.height())
        
        # Check if we have a cached version
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        # For pre-formatted images (which already have letterboxing/pillarboxing),
        # we want to scale the entire image uniformly to fit the widget
        scaled = pixmap.scaled(
            self.width(), self.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        # Check cache size before adding new image
        while len(self.image_cache) >= self.cache_size or self.get_cache_size() >= self.max_cache_size:
            # Remove oldest entry
            self.image_cache.pop(next(iter(self.image_cache)))

        # Cache the result
        self.image_cache[cache_key] = scaled

        return scaled

    def start_transition(self) -> None:
        """Start the transition animation"""
        if self.in_transition:
            return

        self.in_transition = True
        self.animation_step = 0
        self.animation_progress = 0.0
        self.animation_timer.start(self.animation_duration // self.animation_steps)

    def update_animation(self) -> None:
        """Update the animation progress"""
        self.animation_step += 1
        self.animation_progress = self.animation_step / self.animation_steps

        if self.animation_progress >= 1.0:
            self.animation_timer.stop()
            self.in_transition = False
            self.animation_progress = 1.0

            # Transition complete, make next image the current image
            self.current_image = self.next_image
            self.scaled_current = self.scaled_next
            self.next_image = QPixmap()
            self.scaled_next = QPixmap()

        self.update()

    def set_transition(self, transition_type: str) -> None:
        """Set the transition effect type"""
        self.transition_mgr.set_transition(transition_type)

    def paintEvent(self, event: Any) -> None:
        """Paint the widget"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = self.rect()

        if self.in_transition and not self.scaled_next.isNull():
            # Draw transition between images
            self.transition_mgr.draw(painter, rect, self.animation_progress)
        elif not self.scaled_current.isNull():
            # Center the current image in the widget
            x = (rect.width() - self.scaled_current.width()) // 2
            y = (rect.height() - self.scaled_current.height()) // 2
            painter.drawPixmap(x, y, self.scaled_current)

    def resizeEvent(self, event: Any) -> None:
        """Handle resize events"""
        super().resizeEvent(event)
        # Clear cache when window is resized
        self.image_cache.clear()
        self.scale_images()

        # Update transition manager with new scaled images
        if self.in_transition:
            self.transition_mgr.set_images(self.scaled_current, self.scaled_next)

    def closeEvent(self, event: Any) -> None:
        """Handle widget close event"""
        self.animation_timer.stop()
        self.clear_cache()
        super().closeEvent(event)


class SlideshowWindow(QMainWindow):
    """Main window for the slideshow application"""

    def __init__(self) -> None:
        super().__init__()

        # Default configuration
        self.config: ConfigDict = DEFAULT_CONFIG.copy()

        # Image list - now stores tuples of (path, folder_index)
        self.images: List[ImagePathInfo] = []
        self.current_index: int = -1
        self.current_image_path: Optional[Path] = None  # Track current image path

        # State variables
        self.is_fullscreen: bool = False
        self.is_paused: bool = False
        self.failed_image_count: int = 0  # Track consecutive image load failures
        self.max_failures: int = MAX_IMAGE_FAILURES

        # Monitor dimensions
        self.monitor_width: int = 0
        self.monitor_height: int = 0
        
        # Cache for monitor-scaled images
        self.monitor_scaled_cache: Dict[CacheKey, QPixmap] = {}
        self.monitor_cache_size: int = MAX_CACHE_SIZE
        
        # UI components
        self.slideshow_widget: SlideshowWidget = None  # Will be set in init_ui
        self.escape_action: QShortcut = None  # Will be set in setup_quit_shortcuts
        self.q_action: QShortcut = None  # Will be set in setup_quit_shortcuts

        # Initialize UI
        self.init_ui()

        # Set up global shortcut for quitting
        self.setup_quit_shortcuts()

        # Parse command line arguments
        self.parse_args()

        # Load images from folders
        self.load_images()

        # Set up file system watchers for all folders
        self.fs_watchers: List[QFileSystemWatcher] = []
        self.setup_folder_watchers()

        # Set up debounce timer for folder changes
        self.folder_change_timer: QTimer = QTimer(self)
        self.folder_change_timer.setSingleShot(True)
        self.folder_change_timer.timeout.connect(self.process_folder_changes)
        self.pending_folder_changes: Optional[str] = None

        # Set up slide timer
        self.slide_timer: QTimer = QTimer(self)
        self.slide_timer.timeout.connect(self.next_slide)

        # Start slideshow
        if self.images:
            self.start_slideshow()

    def setup_quit_shortcuts(self) -> None:
        """Set up application-level shortcuts for quitting"""
        # Create actions for Escape and Q keys that will work regardless of focus
        self.escape_action = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.escape_action.activated.connect(self.quit_application)
        
        self.q_action = QShortcut(QKeySequence(Qt.Key_Q), self)
        self.q_action.activated.connect(self.quit_application)
    
    def cleanup(self) -> None:
        """Clean up resources before quitting"""
        # Stop timers
        self.slide_timer.stop()
        self.folder_change_timer.stop()
        
        # Remove file system watchers
        for watcher in self.fs_watchers:
            for path in watcher.directories():
                watcher.removePath(path)
        self.fs_watchers.clear()
        
        # Clean up pixmaps and cache
        if hasattr(self, 'slideshow_widget'):
            self.slideshow_widget.current_image = None
            self.slideshow_widget.next_image = None
            self.slideshow_widget.scaled_current = None
            self.slideshow_widget.scaled_next = None
            self.slideshow_widget.clear_cache()
        
        # Clear monitor cache
        self.clear_monitor_cache()
        
        # Clear image list
        self.images.clear()
    
    def quit_application(self) -> None:
        """Quit the application"""
        # Clean up resources
        self.cleanup()
        
        # Close main window
        self.close()
        
        # Quit application
        QApplication.quit()

    def init_ui(self) -> None:
        """Initialize the user interface"""
        self.setWindowTitle("Slideshow")
        
        # Set a reasonable initial size that's not too large
        self.resize(INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT)

        # Create central widget
        self.slideshow_widget = SlideshowWidget(self)
        self.setCentralWidget(self.slideshow_widget)

        # Hide cursor in fullscreen mode
        self.slideshow_widget.setCursor(Qt.BlankCursor)

        # Create status bar for non-fullscreen mode
        self.statusBar().showMessage("Press 'F' for fullscreen, 'ESC' to quit")

        # Set focus policy to accept keyboard events
        self.setFocusPolicy(Qt.StrongFocus)

    def set_window_size_for_image(self, pixmap: QPixmap) -> None:
        """Set window size based on image aspect ratio while maintaining a reasonable size"""
        if pixmap.isNull():
            return

        # Get the screen size
        screen = QGuiApplication.primaryScreen().geometry()
        max_width = int(screen.width() * WINDOW_SIZE_PERCENT)  # 80% of screen width
        max_height = int(screen.height() * WINDOW_SIZE_PERCENT)  # 80% of screen height

        # Calculate aspect ratio
        image_ratio = pixmap.width() / pixmap.height()
        window_ratio = max_width / max_height

        if image_ratio > window_ratio:
            # Image is wider than window ratio
            width = max_width
            height = int(width / image_ratio)
        else:
            # Image is taller than window ratio
            height = max_height
            width = int(height * image_ratio)

        # Set the window size
        self.resize(width, height)

    def setup_folder_watchers(self) -> None:
        """Set up file system watchers for all folders"""
        # Clean up existing watchers
        for watcher in self.fs_watchers:
            for path in watcher.directories():
                watcher.removePath(path)
        self.fs_watchers.clear()

        # Set up new watchers
        for folder_path in self.config['folders']:
            path = Path(folder_path)
            if path.exists() and path.is_dir():
                try:
                    watcher = QFileSystemWatcher(self)
                    watcher.directoryChanged.connect(self.handle_folder_changes)
                    if watcher.addPath(str(path)):
                        self.fs_watchers.append(watcher)
                    else:
                        print(f"Warning: Failed to add watcher for folder: {path}")
                except Exception as e:
                    print(f"Error setting up watcher for folder {path}: {e}")

    def parse_args(self) -> None:
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(description="Full-Screen Image Slideshow")
        parser.add_argument("-f", "--folder", action="append", help="Path to folder with images (can be specified multiple times)")
        parser.add_argument("-d", "--duration", type=int, help="Seconds to display each image", default=None)
        parser.add_argument("-m", "--monitor", type=int, help="Monitor index to use", default=None)
        parser.add_argument("-t", "--transition", help="Transition effect to use",
                         choices=["fade", "slide_left", "slide_right", "slide_up", "slide_down", 
                                 "slide_random", "blinds", "none"],
                         default=None)
        parser.add_argument("-s", "--shuffle", action="store_true", help="Randomize the order of images")

        args = parser.parse_args()

        # Override configuration with command line arguments if provided
        if args.folder is not None:
            self.config['folders'] = args.folder
        if args.duration is not None:
            self.config['duration'] = args.duration
        if args.monitor is not None:
            self.config['monitor'] = args.monitor
        if args.transition is not None:
            self.config['transition'] = args.transition
        if args.shuffle:
            self.config['shuffle'] = True

    def load_images(self) -> None:
        """Load images from all configured folders"""
        self.images = []

        for folder_index, folder_path in enumerate(self.config['folders']):
            folder_path = Path(folder_path)
            if not folder_path.exists() or not folder_path.is_dir():
                print(f"Error: Folder not found: {folder_path}")
                continue

            # Find image files in the folder
            # On Windows, we only need to search once since it's case-insensitive
            if sys.platform == 'win32':
                for ext in IMAGE_EXTENSIONS:
                    for img_path in folder_path.glob(f"*{ext}"):
                        self.images.append((img_path, folder_index))
            else:
                # On case-sensitive systems (Linux, macOS), search for both cases
                for ext in IMAGE_EXTENSIONS:
                    for img_path in folder_path.glob(f"*{ext}"):
                        self.images.append((img_path, folder_index))
                    for img_path in folder_path.glob(f"*{ext.upper()}"):
                        self.images.append((img_path, folder_index))

        # Only exit if no images found during initial load (when current_index is -1)
        if not self.images and self.current_index == -1:
            print("No images found in any of the specified folders")
            sys.exit(1)

        # Shuffle if configured
        if self.config['shuffle']:
            random.shuffle(self.images)
        else:
            # Sort by folder index first, then by filename
            self.images.sort(key=lambda x: (x[1], x[0].name))

        if self.images:
            total_folders = len(set(folder_index for _, folder_index in self.images))
            print(f"Found {len(self.images)} images across {total_folders} folders")

    def handle_folder_changes(self, path: str) -> None:
        """Handle changes to any of the image folders with debouncing"""
        # Stop any existing timer to prevent race conditions
        if self.folder_change_timer.isActive():
            self.folder_change_timer.stop()
        self.pending_folder_changes = path
        self.folder_change_timer.start(FOLDER_CHANGE_DEBOUNCE)

    def process_folder_changes(self) -> None:
        """Process the folder changes after debounce delay"""
        if self.pending_folder_changes is None:
            return

        path = self.pending_folder_changes
        self.pending_folder_changes = None

        # Get current image path before updating list
        current_path: Optional[Path] = None
        if self.images and 0 <= self.current_index < len(self.images):
            current_path = self.images[self.current_index][0]
        
        # Reload images
        old_images: Set[ImagePathInfo] = set(self.images)
        self.load_images()
        new_images: Set[ImagePathInfo] = set(self.images)
        
        # If no images remain, stop the timer and keep current image displayed
        if not self.images:
            self.slide_timer.stop()
            print(f"All images have been deleted from {path}. Last image will remain displayed.")
            self.statusBar().showMessage("No images in any folder - last image remains displayed")
            return
            
        # If current image was deleted, keep it displayed until timer expires
        if current_path and not any(img[0] == current_path for img in new_images):
            # Don't update current_index or show next slide
            # Just update the status bar to show we're on the last image
            self.statusBar().showMessage(
                f"Last image (deleted): {current_path.name} - {len(self.images)} images remain"
            )
            return
            
        # If we were in an empty state and now have images, resume the slideshow
        if not old_images and new_images:
            self.current_index = -1
            self.next_slide()
            return
            
        # Update current index to point to same image if it still exists
        if current_path and any(img[0] == current_path for img in new_images):
            self.current_index = next(i for i, img in enumerate(self.images) if img[0] == current_path)
            # Update status bar
            self.statusBar().showMessage(
                f"Image {self.current_index + 1} of {len(self.images)}: {self.images[self.current_index][0].name}"
            )
        else:
            # If no current image or it was deleted, start from beginning
            self.current_index = -1
            self.next_slide()

    def start_slideshow(self) -> None:
        """Start the slideshow"""
        # Reset index
        self.current_index = -1

        # Set transition effect
        self.slideshow_widget.set_transition(self.config['transition'])

        # Show first slide
        self.next_slide()

        # Move window to the selected monitor if multiple screens available
        self.move_to_monitor()

        # Set fullscreen
        self.toggle_fullscreen(True)

    def move_to_monitor(self) -> None:
        """Move the window to the selected monitor"""
        screens = QGuiApplication.screens()

        # Validate monitor index
        monitor_index = self.config['monitor']
        if monitor_index >= len(screens):
            print(f"Warning: Monitor {monitor_index} not available. Using primary monitor.")
            monitor_index = 0

        # Get screen geometry
        screen = screens[monitor_index]
        screen_geometry = screen.geometry()
        
        # Store monitor dimensions and clear cache if dimensions change
        if self.monitor_width != screen_geometry.width() or self.monitor_height != screen_geometry.height():
            self.monitor_width = screen_geometry.width()
            self.monitor_height = screen_geometry.height()
            self.clear_monitor_cache()

        # Move and resize window to fill the screen
        self.setGeometry(screen_geometry)

    def toggle_fullscreen(self, fullscreen: Optional[bool] = None) -> None:
        """Toggle fullscreen mode"""
        if fullscreen is None:
            fullscreen = not self.is_fullscreen

        if fullscreen:
            self.showFullScreen()
            self.statusBar().hide()
        else:
            self.showNormal()
            self.statusBar().show()

        self.is_fullscreen = fullscreen

    def _handle_empty_slideshow(self) -> None:
        """Handle the case when there are no images to display"""
        self.slide_timer.stop()
        self.statusBar().showMessage("No images in any folder - last image remains displayed")

    def next_slide(self) -> None:
        """Show the next slide"""
        if not self.images:
            self._handle_empty_slideshow()
            return

        # Increment index with wraparound
        self.current_index = (self.current_index + 1) % len(self.images)
        self.show_current_slide()

    def prev_slide(self) -> None:
        """Show the previous slide"""
        if not self.images:
            self._handle_empty_slideshow()
            return

        # Decrement index with wraparound
        self.current_index = (self.current_index - 1) % len(self.images)
        self.show_current_slide()

    def handle_image_error(self, image_path: Path, error: Exception) -> None:
        """Handle errors when loading images"""
        print(f"Error loading image: {image_path}")
        print(f"Error details: {error}")
        
        self.failed_image_count += 1
        if self.failed_image_count >= self.max_failures:
            print("Too many consecutive image load failures. Stopping slideshow.")
            self.slide_timer.stop()
            self.statusBar().showMessage("Slideshow stopped due to image load failures")
            return
            
        # Skip to next image if current one fails to load
        self.next_slide()

    def show_current_slide(self) -> None:
        """Show the current slide based on index"""
        if 0 <= self.current_index < len(self.images):
            image_path, folder_index = self.images[self.current_index]
            self.current_image_path = image_path  # Track current image path

            try:
                # Load the image
                pixmap = QPixmap(str(image_path))

                if pixmap.isNull():
                    self.handle_image_error(image_path, Exception("Failed to load image"))
                    return

                # Reset failure count on successful load
                self.failed_image_count = 0
                
                # Resize image to monitor dimensions while preserving aspect ratio
                pixmap = self.resize_image_to_monitor(pixmap)

                # If this is the very first image shown (slideshow just started)
                # or if there's only one image, don't use transition
                if (self.slideshow_widget.current_image.isNull() or 
                    len(self.images) == 1):
                    self.slideshow_widget.set_current_image(pixmap)
                    # Set window size based on first image if not fullscreen
                    if not self.is_fullscreen:
                        self.set_window_size_for_image(pixmap)
                else:
                    # For all other cases, including looping back to first slide, use transition
                    self.slideshow_widget.set_next_image(pixmap)

                # Show image number in statusbar with truncated filename and folder name
                filename = image_path.name
                folder_name = image_path.parent.name
                if len(filename) > 30:
                    filename = filename[:27] + "..."
                self.statusBar().showMessage(
                    f"Image {self.current_index + 1} of {len(self.images)}: {folder_name}/{filename}"
                )

                # Restart the timer for the next slide
                if not self.is_paused:
                    self.slide_timer.start(self.config['duration'] * 1000)

            except Exception as e:
                self.handle_image_error(image_path, e)

    def toggle_pause(self) -> None:
        """Toggle pause state of the slideshow"""
        self.is_paused = not self.is_paused

        if self.is_paused:
            self.slide_timer.stop()
            self.statusBar().showMessage("Slideshow paused")
            # Clear caches when paused to save memory
            self.slideshow_widget.clear_cache()
            self.clear_monitor_cache()
        else:
            self.slide_timer.start(self.config['duration'] * 1000)
            self.statusBar().showMessage("Slideshow resumed")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events"""
        key = event.key()

        # ESC and Q are handled by global shortcuts
        if key == Qt.Key_F:
            self.toggle_fullscreen()
        elif key == Qt.Key_Space or key == Qt.Key_Right:
            self.slide_timer.stop()
            self.next_slide()
        elif key == Qt.Key_Left:
            self.slide_timer.stop()
            self.prev_slide()
        elif key == Qt.Key_P:
            self.toggle_pause()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle mouse double-click events"""
        if event.button() == Qt.LeftButton:
            self.toggle_fullscreen()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press events"""
        if event.button() == Qt.LeftButton:
            # Left click for next slide
            self.slide_timer.stop()
            self.next_slide()
        elif event.button() == Qt.RightButton:
            # Right click for previous slide
            self.slide_timer.stop()
            self.prev_slide()

    def closeEvent(self, event: Any) -> None:
        """Handle window close event"""
        self.slide_timer.stop()
        self.folder_change_timer.stop()
        # Remove file system watchers
        for watcher in self.fs_watchers:
            for path in watcher.directories():
                watcher.removePath(path)
        # Clean up pixmaps and cache
        if hasattr(self, 'slideshow_widget'):
            # Explicitly delete QPixmap objects
            self.slideshow_widget.current_image = None
            self.slideshow_widget.next_image = None
            self.slideshow_widget.scaled_current = None
            self.slideshow_widget.scaled_next = None
            self.slideshow_widget.clear_cache()
        # Clear monitor cache
        self.clear_monitor_cache()
        event.accept()

    def resize_image_to_monitor(self, pixmap: QPixmap) -> QPixmap:
        """Resize an image to exactly match the target dimensions
        This ensures all images have the same exact size, with black bars as needed"""
        if pixmap.isNull() or self.monitor_width <= 0 or self.monitor_height <= 0:
            return pixmap
            
        # Create a cache key based on the image and monitor dimensions
        cache_key: CacheKey = (pixmap.cacheKey(), self.monitor_width, self.monitor_height)
        
        # Check if we have a cached version
        if cache_key in self.monitor_scaled_cache:
            return self.monitor_scaled_cache[cache_key]
            
        # Calculate target dimensions - we'll use these dimensions consistently
        # regardless of whether we're in fullscreen or windowed mode
        target_width = self.monitor_width
        target_height = self.monitor_height
        
        # Create a new pixmap with the target dimensions (filled with black)
        result = QPixmap(target_width, target_height)
        result.fill(QColor(0, 0, 0))
        
        # Calculate aspect ratios
        image_ratio = pixmap.width() / pixmap.height()
        target_ratio = target_width / target_height
        
        # Scale the image while preserving aspect ratio
        if image_ratio > target_ratio:
            # Image is wider than target ratio (letterboxing - black bars on top/bottom)
            scaled_width = target_width
            scaled_height = int(scaled_width / image_ratio)
        else:
            # Image is taller than target ratio (pillarboxing - black bars on sides)
            scaled_height = target_height
            scaled_width = int(scaled_height * image_ratio)
            
        # Scale the original image
        scaled_img = pixmap.scaled(
            scaled_width, scaled_height,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        # Calculate centered position
        x = (target_width - scaled_img.width()) // 2
        y = (target_height - scaled_img.height()) // 2
        
        # Paint the scaled image onto the black background using a context manager
        with QPainter(result) as painter:
            painter.drawPixmap(x, y, scaled_img)
        
        # Manage cache size
        if len(self.monitor_scaled_cache) >= self.monitor_cache_size:
            # Remove oldest entry
            self.monitor_scaled_cache.pop(next(iter(self.monitor_scaled_cache)))
            
        # Add to cache
        self.monitor_scaled_cache[cache_key] = result
        
        return result
        
    def clear_monitor_cache(self) -> None:
        """Clear the monitor-scaled image cache"""
        self.monitor_scaled_cache.clear()


def main() -> None:
    """Main function"""
    app = QApplication(sys.argv)
    window = SlideshowWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
