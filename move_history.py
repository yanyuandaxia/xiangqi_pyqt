#!/usr/bin/env python3
"""
Move History Widget for Xiangqi
Displays and allows navigation through move history
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor, QBrush


class MoveHistoryWidget(QWidget):
    """Widget for displaying move history"""
    
    move_selected = pyqtSignal(int)  # Emitted when a move is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_index = -1
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("对局记录")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14px;
                color: #333;
            }
        """)
        layout.addWidget(title)
        
        # Move list
        self.move_list = QListWidget()
        self.move_list.setStyleSheet("""
            QListWidget {
                font-family: monospace;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 3px;
            }
            QListWidget::item:selected {
                background-color: #4a90d9;
            }
        """)
        self.move_list.itemDoubleClicked.connect(self._on_item_clicked)
        layout.addWidget(self.move_list)
        
        self.setMinimumWidth(150)
    
    def clear(self):
        """Clear the move history"""
        self.move_list.clear()
        self.current_index = -1
    
    def add_move(self, move_number: int, move: str, is_red: bool):
        """Add a move to the history"""
        if is_red:
            text = f"{move_number}. {move}"
        else:
            text = f"{move_number}. {move}"
        
        item = QListWidgetItem(text)
        item.setData(256, self.move_list.count())  # Store move index
        self.move_list.addItem(item)
        
        # Scroll to the latest move
        self.move_list.scrollToBottom()
    
    def set_moves(self, moves: list[str]):
        """Set all moves at once"""
        self.clear()
        for i, move in enumerate(moves):
            move_number = i // 2 + 1
            is_red = i % 2 == 0
            self.add_move(move_number, move, is_red)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle item click"""
        move_index = item.data(256)
        if move_index is not None:
            self.move_selected.emit(move_index)
    
    def highlight_move(self, index: int):
        """Highlight a specific move"""
        # Clear previous highlight
        if self.current_index >= 0 and self.current_index < self.move_list.count():
            item = self.move_list.item(self.current_index)
            # Reset to transparent/default
            item.setBackground(QBrush(QColor(0, 0, 0, 0))) 
            
            # Reset font weight
            font = item.font()
            font.setBold(False)
            item.setFont(font)
            
        self.current_index = index
        
        # Set new highlight
        if 0 <= index < self.move_list.count():
            item = self.move_list.item(index)
            # Light Green for current move position
            item.setBackground(QBrush(QColor("#C8E6C9"))) 
            
            # Make bold for emphasis
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            
            # Ensure visible
            self.move_list.scrollToItem(item)
            
            # Clear selection so it doesn't conflict visually with our highlight
            self.move_list.clearSelection()
    
    def set_result(self, result: str, winner: str = ""):
        """Display the game result
        
        Args:
            result: Result text like "红方胜", "黑方胜", "和棋"
            winner: "red", "black", or "" for draw
        """
        item = QListWidgetItem()
        item.setText(f"━━━━━━━━━━\n  {result}\n━━━━━━━━━━")
        
        # Style based on winner
        if winner == "red":
            item.setForeground(QColor(200, 30, 30))
        elif winner == "black":
            item.setForeground(QColor(20, 20, 20))
        
        item.setData(256, None)  # Not a clickable move
        self.move_list.addItem(item)
        self.move_list.scrollToBottom()
