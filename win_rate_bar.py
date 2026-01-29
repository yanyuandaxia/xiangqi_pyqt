#!/usr/bin/env python3
"""
Win Rate Bar Widget for Xiangqi GUI
Displays the win/draw/loss probability for red and black sides based on engine evaluation
"""

import math
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QFont, QPen


class WinRateBar(QWidget):
    """A vertical bar showing win/draw/loss rate for red and black sides"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # WDL rates (in per mille, 0-1000)
        self._win = 0      # Red win rate
        self._draw = 1000  # Draw rate
        self._loss = 0     # Black win rate (red loss)
        
        # Flipped state (matches board orientation)
        self._flipped = False  # False = red at bottom, True = black at bottom
        
        # Colors
        self.red_color = QColor("#c81e1e")  # Red side
        self.draw_color = QColor("#888888")  # Draw (gray)
        self.black_color = QColor("#1a1a1a")  # Black side
        self.border_color = QColor("#666666")
        
        # Setup - narrower without labels
        self.setMinimumWidth(30)
        self.setMaximumWidth(45)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI layout - just the bar"""
        main_layout = QVBoxLayout(self)
        # Margins to match board widget (margin=40 + 20 for background padding)
        main_layout.setContentsMargins(5, 60, 5, 60)
        main_layout.setSpacing(0)
        
        # The bar itself
        self.bar_widget = _WinRateBarCanvas(self)
        self.bar_widget.setMinimumWidth(20)
        self.bar_widget.setMaximumWidth(35)
        main_layout.addWidget(self.bar_widget, stretch=1)
    
    def set_flipped(self, flipped: bool):
        """Set the flipped state to match board orientation"""
        if self._flipped != flipped:
            self._flipped = flipped
            self.bar_widget.set_flipped(flipped)
            self.update()
    
    def set_score(self, score_cp: int):
        """
        Set the win rate based on engine score in centipawns.
        Uses sigmoid function to convert score to win probability.
        
        Args:
            score_cp: Engine score in centipawns (positive = red advantage)
        """
        # Convert centipawns to win rate using sigmoid function
        k = 400.0
        score_cp = max(-10000, min(10000, score_cp))
        
        try:
            red_win_rate = 1.0 / (1.0 + math.pow(10, -score_cp / k))
        except (OverflowError, ValueError):
            red_win_rate = 1.0 if score_cp > 0 else 0.0
        
        # Convert to per mille and assume no draw for score-based
        self._win = int(red_win_rate * 1000)
        self._loss = 1000 - self._win
        self._draw = 0
        
        self._update_display()
    
    def set_wdl(self, win: int, draw: int, loss: int):
        """
        Set the win rate directly from engine WDL (Win/Draw/Loss) data.
        
        Args:
            win: Win probability in per mille (0-1000) - Red wins
            draw: Draw probability in per mille (0-1000)
            loss: Loss probability in per mille (0-1000) - Black wins
        """
        self._win = win
        self._draw = draw
        self._loss = loss
        
        self._update_display()
    
    def _update_display(self):
        """Update the bar"""
        # Update bar only (labels removed)
        self.bar_widget.set_wdl(self._win, self._draw, self._loss)
    
    def reset(self):
        """Reset to equal position (100% draw)"""
        self.set_wdl(0, 1000, 0)


class _WinRateBarCanvas(QWidget):
    """Internal canvas widget for drawing the win rate bar with three colors"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Current display values (for animation)
        self._win = 0
        self._draw = 1000
        self._loss = 0
        
        # Target values
        self._target_win = 0
        self._target_draw = 1000
        self._target_loss = 0
        
        # Flipped state
        self._flipped = False
        
        # Animation
        self._animation_timer = None
        
        self.setMinimumHeight(200)
    
    def set_flipped(self, flipped: bool):
        """Set the flipped state"""
        self._flipped = flipped
        self.update()
        
    def set_wdl(self, win: int, draw: int, loss: int):
        """Set the WDL values and trigger animation"""
        self._target_win = win
        self._target_draw = draw
        self._target_loss = loss
        
        # Smooth animation
        if self._animation_timer is None:
            from PyQt5.QtCore import QTimer
            self._animation_timer = QTimer(self)
            self._animation_timer.timeout.connect(self._animate)
        
        if not self._animation_timer.isActive():
            self._animation_timer.start(16)  # ~60fps
    
    def _animate(self):
        """Animate the bar movement"""
        # Interpolate each value
        alpha = 0.15
        
        diff_win = self._target_win - self._win
        diff_draw = self._target_draw - self._draw
        diff_loss = self._target_loss - self._loss
        
        if abs(diff_win) < 5 and abs(diff_draw) < 5 and abs(diff_loss) < 5:
            self._win = self._target_win
            self._draw = self._target_draw
            self._loss = self._target_loss
            if self._animation_timer:
                self._animation_timer.stop()
        else:
            self._win += diff_win * alpha
            self._draw += diff_draw * alpha
            self._loss += diff_loss * alpha
        
        self.update()
    
    def paintEvent(self, event):
        """Paint the win rate bar with three colors, order depends on flipped state"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Dimensions
        w = self.width()
        h = self.height()
        margin = 2
        bar_x = margin
        bar_y = margin
        bar_w = w - 2 * margin
        bar_h = h - 2 * margin
        
        # Calculate section heights based on WDL
        total = self._win + self._draw + self._loss
        if total <= 0:
            total = 1000
        
        red_ratio = self._win / total
        draw_ratio = self._draw / total
        black_ratio = self._loss / total
        
        red_height = int(bar_h * red_ratio)
        draw_height = int(bar_h * draw_ratio)
        black_height = bar_h - red_height - draw_height  # Remainder to avoid gaps
        
        current_y = bar_y
        
        # Draw order depends on flipped state:
        # Not flipped (red at bottom): black on top, draw in middle, red at bottom
        # Flipped (black at bottom): red on top, draw in middle, black at bottom
        
        if self._flipped:
            # Flipped: red on top, draw in middle, black at bottom
            # Draw red section (top) - Red wins
            if red_height > 0:
                red_gradient = QLinearGradient(0, current_y, 0, current_y + red_height)
                red_gradient.setColorAt(0, QColor("#e63946"))
                red_gradient.setColorAt(1, QColor("#c81e1e"))
                painter.fillRect(bar_x, current_y, bar_w, red_height, red_gradient)
                current_y += red_height
            
            # Draw gray section (middle) - Draw
            if draw_height > 0:
                painter.fillRect(bar_x, current_y, bar_w, draw_height, QColor("#777777"))
                current_y += draw_height
            
            # Draw black section (bottom) - Black wins
            if black_height > 0:
                black_gradient = QLinearGradient(0, current_y, 0, current_y + black_height)
                black_gradient.setColorAt(0, QColor("#3a3a3a"))
                black_gradient.setColorAt(1, QColor("#1a1a1a"))
                painter.fillRect(bar_x, current_y, bar_w, black_height, black_gradient)
        else:
            # Not flipped: black on top, draw in middle, red at bottom
            # Draw black section (top) - Black wins
            if black_height > 0:
                black_gradient = QLinearGradient(0, current_y, 0, current_y + black_height)
                black_gradient.setColorAt(0, QColor("#1a1a1a"))
                black_gradient.setColorAt(1, QColor("#3a3a3a"))
                painter.fillRect(bar_x, current_y, bar_w, black_height, black_gradient)
                current_y += black_height
            
            # Draw gray section (middle) - Draw
            if draw_height > 0:
                painter.fillRect(bar_x, current_y, bar_w, draw_height, QColor("#777777"))
                current_y += draw_height
            
            # Draw red section (bottom) - Red wins
            if red_height > 0:
                red_gradient = QLinearGradient(0, current_y, 0, current_y + red_height)
                red_gradient.setColorAt(0, QColor("#c81e1e"))
                red_gradient.setColorAt(1, QColor("#e63946"))
                painter.fillRect(bar_x, current_y, bar_w, red_height, red_gradient)
        
        # Draw border
        pen = QPen(QColor("#888888"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawRect(bar_x, bar_y, bar_w, bar_h)
        
        painter.end()
