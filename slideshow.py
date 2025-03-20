# /// script
# requires-python = "==3.12"
# dependencies = [
#     "PySide6",
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

# Check Python version - require exactly 3.12.x
import platform
python_version = platform.python_version_tuple()
if python_version[0] != '3' or python_version[1] != '12':
    print(f"Error: This script requires Python 3.12.x exactly")
    print(f"Current Python version: {platform.python_version()}")
    sys.exit(1)

try:
    from PySide6.QtWidgets import (QApplication, QWidget, QMainWindow)
    from PySide6.QtGui import (QPixmap, QPainter, QColor, QPalette, QKeyEvent,
                              QGuiApplication, QMouseEvent, QShortcut, QKeySequence)
    from PySide6.QtCore import (Qt, QTimer, QRect, QObject)
except ImportError:
    print("PySide6 is required. Install it with: pip install PySide6")
    sys.exit(1)

# Supported image formats
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

class TransitionManager(QObject):
    """Manages different transition effects between images"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pixmap = None
        self.next_pixmap = None
        self.progress = 0.0
        self.current_random_direction = 'right'  # Default direction

        # Available transition types
        self.transitions = {
            'none': self.no_transition,
            'fade': self.fade_transition,
            'slide_left': lambda p, c, n: self.slide_transition(p, c, n, 'left'),
            'slide_right': lambda p, c, n: self.slide_transition(p, c, n, 'right'),
            'slide_up': lambda p, c, n: self.slide_transition(p, c, n, 'up'),
            'slide_down': lambda p, c, n: self.slide_transition(p, c, n, 'down'),
            'blinds': self.blinds_transition,
            'slide_random': self.slide_random_transition,
        }

        self.transition_type = 'fade'

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

    def no_transition(self, painter: QPainter, rect: QRect, progress: float) -> None:
        """No transition effect - just switch images at 50% progress"""
        if progress < 0.5:
            painter.drawPixmap(rect, self.current_pixmap)
        else:
            painter.drawPixmap(rect, self.next_pixmap)

    def fade_transition(self, painter: QPainter, rect: QRect, progress: float) -> None:
        """Fade transition effect"""
        # Draw current image
        painter.setOpacity(1.0 - progress)
        painter.drawPixmap(rect, self.current_pixmap)

        # Draw next image
        painter.setOpacity(progress)
        painter.drawPixmap(rect, self.next_pixmap)

    def blinds_transition(self, painter: QPainter, rect: QRect, progress: float) -> None:
        """Vertical blinds transition effect"""
        w, h = rect.width(), rect.height()
        
        # Number of blinds (vertical slices)
        num_blinds = 20
        blind_width = w // num_blinds
        
        # Draw the current image as base
        painter.drawPixmap(rect, self.current_pixmap)
        
        # Draw the next image in vertical strips
        for i in range(num_blinds):
            # Calculate the opening of each blind based on progress
            # Add slight delay for each successive blind
            blind_progress = progress * 1.5 - (i * 0.05)
            
            # Ensure progress is between 0 and 1
            blind_progress = max(0, min(1, blind_progress))
            
            if blind_progress > 0:
                # Calculate blind position and width
                blind_x = i * blind_width
                
                # Create source rectangle from the next image
                source_rect = QRect(blind_x, 0, blind_width, h)
                
                # Create target rectangle in the current view
                target_rect = QRect(blind_x, 0, blind_width * blind_progress, h)
                
                # Draw this slice of the next image
                painter.drawPixmap(target_rect, self.next_pixmap, source_rect)

    def slide_transition(self, painter: QPainter, rect: QRect, progress: float, direction: str) -> None:
        """Slide transition effect in the specified direction"""
        w, h = rect.width(), rect.height()

        if direction == 'left':
            # Current image moves left
            current_x = -w * progress
            # Next image comes from right
            next_x = w - (w * progress)

            painter.drawPixmap(QRect(current_x, 0, w, h), self.current_pixmap)
            painter.drawPixmap(QRect(next_x, 0, w, h), self.next_pixmap)

        elif direction == 'right':
            # Current image moves right
            current_x = w * progress
            # Next image comes from left
            next_x = -(w - (w * progress))

            painter.drawPixmap(QRect(current_x, 0, w, h), self.current_pixmap)
            painter.drawPixmap(QRect(next_x, 0, w, h), self.next_pixmap)

        elif direction == 'up':
            # Current image moves up
            current_y = -h * progress
            # Next image comes from bottom
            next_y = h - (h * progress)

            painter.drawPixmap(QRect(0, current_y, w, h), self.current_pixmap)
            painter.drawPixmap(QRect(0, next_y, w, h), self.next_pixmap)

        elif direction == 'down':
            # Current image moves down
            current_y = h * progress
            # Next image comes from top
            next_y = -(h - (h * progress))

            painter.drawPixmap(QRect(0, current_y, w, h), self.current_pixmap)
            painter.drawPixmap(QRect(0, next_y, w, h), self.next_pixmap)

    def slide_random_transition(self, painter: QPainter, rect: QRect, progress: float) -> None:
        """Random slide transition that uses a different direction each time"""
        self.slide_transition(painter, rect, progress, self.current_random_direction)


class SlideshowWidget(QWidget):
    """Widget that displays images with transition effects"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Image data
        self.current_image = QPixmap()
        self.next_image = QPixmap()
        self.scaled_current = QPixmap()
        self.scaled_next = QPixmap()

        # Animation state
        self.animation_progress = 0.0
        self.in_transition = False

        # Transition manager
        self.transition_mgr = TransitionManager(self)

        # Animation timer
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_duration = 500  # milliseconds
        self.animation_steps = 20
        self.animation_step = 0

        # Set background to black
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.setPalette(palette)

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
        """Scale a pixmap to fit widget size while maintaining aspect ratio"""
        if pixmap.isNull():
            return QPixmap()

        return pixmap.scaled(
            self.width(), self.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

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

    def paintEvent(self, event) -> None:
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

    def resizeEvent(self, event) -> None:
        """Handle resize events"""
        super().resizeEvent(event)
        self.scale_images()

        # Update transition manager with new scaled images
        if self.in_transition:
            self.transition_mgr.set_images(self.scaled_current, self.scaled_next)


class SlideshowWindow(QMainWindow):
    """Main window for the slideshow application"""

    def __init__(self):
        super().__init__()

        # Default configuration
        self.config = {
            'folder': '.',
            'duration': 5,
            'monitor': 0,
            'transition': 'fade',
            'shuffle': False
        }

        # Image list
        self.images = []
        self.current_index = -1

        # State variables
        self.is_fullscreen = False
        self.is_paused = False

        # Timers
        self.slide_timer = QTimer(self)
        self.slide_timer.timeout.connect(self.next_slide)

        # Initialize UI
        self.init_ui()

        # Set up global shortcut for quitting
        self.setup_quit_shortcuts()

        # Parse command line arguments
        self.parse_args()

        # Load images from folder
        self.load_images()

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
    
    def quit_application(self) -> None:
        """Quit the application"""
        # Stop any active timers
        self.slide_timer.stop()
        
        # Close main window
        self.close()
        
        # Quit application
        QApplication.quit()

    def init_ui(self) -> None:
        """Initialize the user interface"""
        self.setWindowTitle("Slideshow")
        self.resize(800, 600)

        # Create central widget
        self.slideshow_widget = SlideshowWidget(self)
        self.setCentralWidget(self.slideshow_widget)

        # Hide cursor in fullscreen mode
        self.slideshow_widget.setCursor(Qt.BlankCursor)

        # Create status bar for non-fullscreen mode
        self.statusBar().showMessage("Press 'F' for fullscreen, 'ESC' to quit")

        # Set focus policy to accept keyboard events
        self.setFocusPolicy(Qt.StrongFocus)

    def parse_args(self) -> None:
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(description="Full-Screen Image Slideshow")
        parser.add_argument("--folder", help="Path to folder with images", default=None)
        parser.add_argument("--duration", type=int, help="Seconds to display each image", default=None)
        parser.add_argument("--monitor", type=int, help="Monitor index to use", default=None)
        parser.add_argument("--transition", help="Transition effect to use",
                         choices=["fade", "slide_left", "slide_right", "slide_up", "slide_down", 
                                 "slide_random", "blinds", "none"],
                         default=None)
        parser.add_argument("--shuffle", action="store_true", help="Randomize the order of images")

        args = parser.parse_args()

        # Override configuration with command line arguments if provided
        if args.folder is not None:
            self.config['folder'] = args.folder
        if args.duration is not None:
            self.config['duration'] = args.duration
        if args.monitor is not None:
            self.config['monitor'] = args.monitor
        if args.transition is not None:
            self.config['transition'] = args.transition
        if args.shuffle:
            self.config['shuffle'] = True

    def load_images(self) -> None:
        """Load images from the configured folder"""
        folder_path = Path(self.config['folder'])
        self.images = []

        if not folder_path.exists() or not folder_path.is_dir():
            print(f"Error: Folder not found: {folder_path}")
            return

        # Find image files in the folder
        for ext in IMAGE_EXTENSIONS:
            self.images.extend(list(folder_path.glob(f"*{ext}")))
            self.images.extend(list(folder_path.glob(f"*{ext.upper()}")))

        if not self.images:
            print(f"No images found in {folder_path}")
            return

        # Shuffle if configured
        if self.config['shuffle']:
            random.shuffle(self.images)
        else:
            # Sort by filename
            self.images.sort()

        print(f"Found {len(self.images)} images in {folder_path}")

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

        # Move and resize window to fill the screen
        self.setGeometry(screen_geometry)

    def toggle_fullscreen(self, fullscreen: bool = None) -> None:
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

    def next_slide(self) -> None:
        """Show the next slide"""
        if not self.images:
            return

        # Increment index with wraparound
        self.current_index = (self.current_index + 1) % len(self.images)
        self.show_current_slide()

    def prev_slide(self) -> None:
        """Show the previous slide"""
        if not self.images:
            return

        # Decrement index with wraparound
        self.current_index = (self.current_index - 1) % len(self.images)
        self.show_current_slide()

    def show_current_slide(self) -> None:
        """Show the current slide based on index"""
        if 0 <= self.current_index < len(self.images):
            image_path = self.images[self.current_index]

            try:
                # Load the image
                pixmap = QPixmap(str(image_path))

                if pixmap.isNull():
                    print(f"Error loading image: {image_path}")
                    return

                # If this is the very first image shown (slideshow just started)
                if self.slideshow_widget.current_image.isNull():
                    self.slideshow_widget.set_current_image(pixmap)
                else:
                    # For all other cases, including looping back to first slide, use transition
                    self.slideshow_widget.set_next_image(pixmap)

                # Show image number in statusbar
                self.statusBar().showMessage(
                    f"Image {self.current_index + 1} of {len(self.images)}: {image_path.name}"
                )

                # Restart the timer for the next slide
                if not self.is_paused:
                    self.slide_timer.start(self.config['duration'] * 1000)

            except Exception as e:
                print(f"Error showing image: {e}")

    def toggle_pause(self) -> None:
        """Toggle pause state of the slideshow"""
        self.is_paused = not self.is_paused

        if self.is_paused:
            self.slide_timer.stop()
        else:
            self.slide_timer.start(self.config['duration'] * 1000)

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

    def closeEvent(self, event) -> None:
        """Handle window close event"""
        self.slide_timer.stop()
        event.accept()


def main():
    """Main function"""
    app = QApplication(sys.argv)
    window = SlideshowWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
