#!/usr/bin/env python3
"""
Analysis Chart Widget for Xiangqi GUI
Displays a vertical line chart showing the evaluation score for each move
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QLinearGradient


class AnalysisChart(QWidget):
    """A vertical chart showing evaluation scores for each move in the game"""
    
    # Signal emitted when a point is clicked, with move index
    point_clicked = pyqtSignal(int)
    
    # Signal emitted when score is updated (move_index, score_cp)
    score_updated = pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Store scores: list of (move_index, score_cp) tuples
        self._scores = []
        
        # Currently highlighted move
        self._highlighted_index = -1
        
        # Chart settings
        self._max_score = 1000  # Maximum score in centipawns for scaling
        self._point_radius = 4
        
        # Colors
        self._red_color = QColor("#c81e1e")
        self._black_color = QColor("#1a1a1a")
        self._draw_color = QColor("#888888")
        self._line_color = QColor("#4a90d9")
        self._highlight_color = QColor("#FFD700")
        self._grid_color = QColor("#e0e0e0")
        self._bg_color = QColor("#fafafa")
        
        # Setup
        # Setup
        self.setMinimumWidth(150)
        # self.setMaximumWidth(250)  # Removed to match move history width
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        # Remove custom spacing to match MoveHistoryWidget
        
        # Title
        self.title_label = QLabel("分析")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14px;
                color: #333;
            }
        """)
        layout.addWidget(self.title_label)
        
        # Chart canvas
        self.chart_canvas = _AnalysisChartCanvas(self)
        layout.addWidget(self.chart_canvas, stretch=1)
    
    def set_scores(self, scores: list):
        """
        Set the analysis scores.
        
        Args:
            scores: List of scores in centipawns (positive = red advantage)
                   Index in list corresponds to move index
        """
        self._scores = scores
        self.chart_canvas.set_scores(scores)
        self.update()
    
    def add_score(self, score_cp: int):
        """Add a single score to the analysis"""
        self._scores.append(score_cp)
        self.chart_canvas.set_scores(self._scores)
        self.update()
    
    def clear(self):
        """Clear all scores"""
        self._scores = []
        self.chart_canvas.set_scores([])
        self.update()
    
    def highlight_move(self, index: int):
        """Highlight a specific move on the chart"""
        self._highlighted_index = index
        self.chart_canvas.set_highlighted_index(index)
        
        # Emit score update signal
        if 0 <= index < len(self._scores):
            score = self._scores[index]
            self.score_updated.emit(index, score)
    
    def _update_score_label(self, score_cp: int, move_index: int):
        """Emit score update signal"""
        self.score_updated.emit(move_index, score_cp)


class _AnalysisChartCanvas(QWidget):
    """Internal canvas widget for drawing the analysis chart"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scores = []
        self._highlighted_index = -1
        self._hovered_index = -1
        
        # Chart settings
        self._max_score = 1000  # Score for full height
        self._margin_top = 0
        self._margin_bottom = 0
        self._margin_left = 0
        self._margin_right = 0
        
        self.setMinimumHeight(100)
        self.setMouseTracking(True)
    
    def set_scores(self, scores: list):
        """Set the scores to display"""
        self._scores = scores
        self.update()
    
    def set_highlighted_index(self, index: int):
        """Set the highlighted move index"""
        self._highlighted_index = index
        self.update()
    
    def _get_point_position(self, index: int, score: int) -> tuple:
        """Calculate the pixel position for a score point"""
        w = self.width() - self._margin_left - self._margin_right
        h = self.height() - self._margin_top - self._margin_bottom
        
        if len(self._scores) <= 1:
            y = self._margin_top + h / 2
        else:
            # Y position based on move index (top to bottom)
            y = self._margin_top + (index / (len(self._scores) - 1)) * h
        
        # X position based on score (center is 0, left is negative, right is positive)
        # Clamp score to max range
        clamped_score = max(-self._max_score, min(self._max_score, score))
        x_ratio = (clamped_score + self._max_score) / (2 * self._max_score)
        x = self._margin_left + x_ratio * w
        
        return (x, y)
    
    def _get_index_at_position(self, y: int) -> int:
        """Get the move index at a given Y position"""
        if len(self._scores) <= 1:
            return 0 if self._scores else -1
        
        h = self.height() - self._margin_top - self._margin_bottom
        ratio = (y - self._margin_top) / h
        index = int(ratio * (len(self._scores) - 1) + 0.5)
        return max(0, min(len(self._scores) - 1, index))
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for hover effects"""
        if self._scores:
            index = self._get_index_at_position(event.y())
            if index != self._hovered_index:
                self._hovered_index = index
                self.update()
                # Update parent's score label
                if hasattr(self.parent(), '_update_score_label'):
                    self.parent()._update_score_label(self._scores[index], index)
    
    def mousePressEvent(self, event):
        """Handle mouse click to select a move"""
        if self._scores and event.button() == Qt.LeftButton:
            index = self._get_index_at_position(event.y())
            if hasattr(self.parent(), 'point_clicked'):
                self.parent().point_clicked.emit(index)
    
    def leaveEvent(self, event):
        """Handle mouse leave"""
        self._hovered_index = -1
        self.update()
    
    def paintEvent(self, event):
        """Paint the analysis chart"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        chart_w = w - self._margin_left - self._margin_right
        chart_h = h - self._margin_top - self._margin_bottom
        
        # Draw background
        painter.fillRect(0, 0, w, h, QColor("#fafafa"))
        
        # Draw center line (0 score)
        center_x = self._margin_left + chart_w / 2
        pen = QPen(QColor("#cccccc"))
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(int(center_x), self._margin_top, 
                        int(center_x), h - self._margin_bottom)
        
        # Draw advantage indicators
        # Left side: black advantage area
        black_gradient = QLinearGradient(self._margin_left, 0, center_x, 0)
        black_gradient.setColorAt(0, QColor(0, 0, 0, 50))       # Dark Black
        black_gradient.setColorAt(1, QColor(180, 180, 180, 50)) # Grey
        painter.fillRect(self._margin_left, self._margin_top, 
                        int(center_x - self._margin_left), chart_h, black_gradient)
        
        # Right side: red advantage area
        red_gradient = QLinearGradient(center_x, 0, w - self._margin_right, 0)
        red_gradient.setColorAt(0, QColor(180, 180, 180, 50))   # Grey
        red_gradient.setColorAt(1, QColor(200, 30, 30, 50))     # Red
        painter.fillRect(int(center_x), self._margin_top, 
                        int(w - self._margin_right - center_x), chart_h, red_gradient)
        
        if not self._scores:
            # Draw "No data" text
            painter.setPen(QColor("#999999"))
            painter.drawText(self.rect(), Qt.AlignCenter, "无数据")
            painter.end()
            return
        
        # Draw the line connecting all points
        if len(self._scores) > 1:
            path = QPainterPath()
            first_pos = self._get_point_position(0, self._scores[0])
            path.moveTo(first_pos[0], first_pos[1])
            
            for i in range(1, len(self._scores)):
                pos = self._get_point_position(i, self._scores[i])
                path.lineTo(pos[0], pos[1])
            
            # Draw line
            line_pen = QPen(QColor("#4a90d9"))
            line_pen.setWidth(2)
            painter.setPen(line_pen)
            painter.drawPath(path)
        
        # Draw points
        for i, score in enumerate(self._scores):
            pos = self._get_point_position(i, score)
            
            # Determine point color based on score
            if score > 100:
                point_color = QColor("#c81e1e")  # Red advantage
            elif score < -100:
                point_color = QColor("#1a1a1a")  # Black advantage
            else:
                point_color = QColor("#888888")  # Even
            
            # Highlight if this is the highlighted or hovered move
            radius = 4
            if i == self._highlighted_index:
                # Draw highlight circle
                painter.setPen(QPen(QColor("#FFD700"), 2))
                painter.setBrush(QBrush(point_color))
                radius = 6
            elif i == self._hovered_index:
                painter.setPen(QPen(QColor("#4a90d9"), 2))
                painter.setBrush(QBrush(point_color))
                radius = 5
            else:
                painter.setPen(QPen(point_color.darker(120), 1))
                painter.setBrush(QBrush(point_color))
            
            painter.drawEllipse(int(pos[0] - radius), int(pos[1] - radius), 
                               radius * 2, radius * 2)
        
        # Draw border
        painter.setPen(QPen(QColor("#cccccc")))
        painter.setBrush(Qt.NoBrush)
        # Draw rect with -1 adjustment to ensure border is visible within widget bounds
        rect_w = chart_w - 1 if chart_w > 0 else 0
        rect_h = chart_h - 1 if chart_h > 0 else 0
        painter.drawRect(self._margin_left, self._margin_top, 
                        rect_w, rect_h)
        
        painter.end()
