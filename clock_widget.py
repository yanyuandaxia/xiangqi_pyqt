from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QObject, QTimer, Qt
from chess_logic import Side

class ClockLabel(QLabel):
    """
    Component widget to display a single clock.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(140, 50) # Adjusted size
        
        # Default style
        self.default_style = """
            QLabel {
                background-color: #f0f0f0;
                color: #333;
                border: 2px solid #ccc;
                border-radius: 5px;
                font-family: monospace;
                font-size: 24px;
                font-weight: bold;
                padding: 2px;
            }
        """
        self.setStyleSheet(self.default_style)

class ClockManager(QObject):
    """
    Manages two separate clock widgets (top and bottom) and the timing logic.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create the two display widgets
        self.top_label = ClockLabel()
        self.bottom_label = ClockLabel()
        
        # Hide initially
        self.top_label.hide()
        self.bottom_label.hide()
        
        self.red_time = 0  # Seconds
        self.black_time = 0 # Seconds
        self.active_side = None
        self.is_running = False
        self.flipped = False
        
        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.setInterval(1000) # 1 second
        
        # Styles
        self.red_style = """
            QLabel {
                background-color: #f8dede;
                color: #c00;
                border: 2px solid #e00;
                border-radius: 5px;
                font-family: monospace;
                font-size: 24px;
                font-weight: bold;
                padding: 2px;
            }
        """
        
        self.black_style = """
            QLabel {
                background-color: #dedede;
                color: #000;
                border: 2px solid #333;
                border-radius: 5px;
                font-family: monospace;
                font-size: 24px;
                font-weight: bold;
                padding: 2px;
            }
        """
        
        self.reset()
        
    def show(self):
        self.top_label.show()
        self.bottom_label.show()
        
    def hide(self):
        self.top_label.hide()
        self.bottom_label.hide()
        
    def isVisible(self):
        return self.top_label.isVisible()

    def set_flipped(self, flipped: bool):
        """Set board orientation (flipped=True means Red is at top)"""
        self.flipped = flipped
        self._update_display()

    def reset(self):
        """Reset clocks to 0"""
        self.red_time = 0
        self.black_time = 0
        self.active_side = None
        self.is_running = False
        self.timer.stop()
        self._update_display()
        self._highlight_active()

    def start_timing(self, side: Side):
        """Start timing for the specified side"""
        self.active_side = side
        self.is_running = True
        if not self.timer.isActive():
            self.timer.start()
        self._highlight_active()

    def stop_timing(self):
        """Stop temporary (e.g. game paused or over)"""
        self.is_running = False
        self.timer.stop()
        self._highlight_active()

    def _update_time(self):
        if not self.is_running:
            return
            
        if self.active_side == Side.RED:
            self.red_time += 1
        elif self.active_side == Side.BLACK:
            self.black_time += 1
            
        self._update_display()

    def _update_display(self):
        # Determine which label shows what
        if self.flipped:
            # Red is at Top
            self.top_label.setText(self._format_time(self.red_time))
            self.top_label.setStyleSheet(self.red_style)
            
            # Black is at Bottom
            self.bottom_label.setText(self._format_time(self.black_time))
            self.bottom_label.setStyleSheet(self.black_style)
        else:
            # Black is at Top
            self.top_label.setText(self._format_time(self.black_time))
            self.top_label.setStyleSheet(self.black_style)
            
            # Red is at Bottom
            self.bottom_label.setText(self._format_time(self.red_time))
            self.bottom_label.setStyleSheet(self.red_style)
            
        # Re-apply highlights if needed
        self._highlight_active()

    def _format_time(self, seconds):
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02}:{m:02}:{s:02}"
        else:
            return f"{m:02}:{s:02}"

    def _highlight_active(self):
        """Highlight the active clock"""
        if not self.is_running or self.active_side is None:
             self._update_display_styles(highlight_label=None)
             return

        # Determine which label corresponds to active side
        active_label = None
        if self.flipped:
            # Top=Red, Bottom=Black
            if self.active_side == Side.RED:
                active_label = self.top_label
            else:
                active_label = self.bottom_label
        else:
            # Top=Black, Bottom=Red
            if self.active_side == Side.BLACK:
                active_label = self.top_label
            else:
                active_label = self.bottom_label
        
        self._update_display_styles(highlight_label=active_label)

    def _update_display_styles(self, highlight_label):
        """Helper to apply styles with optional highlight"""
        # Base styles
        top_style = self.top_label.styleSheet()
        btm_style = self.bottom_label.styleSheet()
        
        # Reset borders to 2px first to clean state
        top_style = top_style.replace("border: 4px", "border: 2px")
        btm_style = btm_style.replace("border: 4px", "border: 2px")
        
        if highlight_label == self.top_label:
            top_style = top_style.replace("border: 2px", "border: 4px")
        elif highlight_label == self.bottom_label:
            btm_style = btm_style.replace("border: 2px", "border: 4px")
            
        self.top_label.setStyleSheet(top_style)
        self.bottom_label.setStyleSheet(btm_style)
