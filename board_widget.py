#!/usr/bin/env python3
"""
Xiangqi Board Widget for PyQt5
Renders the board and handles piece interaction
"""

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontMetrics

from chess_logic import ChessBoard, Piece, Side, PieceType


class BoardWidget(QWidget):
    """Widget for rendering the Xiangqi board"""
    
    # Signals
    move_made = pyqtSignal(str)  # Emitted when a move is made
    piece_placed = pyqtSignal(int, int, object)  # Emitted when piece is placed in edit mode (file, rank, piece)
    
    # Colors
    BOARD_COLOR = QColor(245, 222, 179)  # Wheat color
    LINE_COLOR = QColor(0, 0, 0)
    RED_PIECE_COLOR = QColor(200, 30, 30)
    BLACK_PIECE_COLOR = QColor(20, 20, 20)
    PIECE_BG_COLOR = QColor(255, 248, 220)  # Cornsilk
    SELECTED_COLOR = QColor(0, 200, 0, 100)
    LEGAL_MOVE_COLOR = QColor(0, 150, 0, 150)
    LAST_MOVE_COLOR = QColor(255, 200, 0, 100)
    EDIT_HIGHLIGHT_COLOR = QColor(100, 100, 255, 100)
    HINT_COLOR = QColor(0, 100, 255, 150)  # Blue for hint
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.board = ChessBoard()
        
        # UI state
        self.selected_pos: tuple[int, int] | None = None
        self.legal_moves: list[tuple[int, int]] = []
        self.last_move: tuple[int, int, int, int] | None = None
        self.flipped = False  # View from black side
        self.hint_move: tuple[int, int, int, int] | None = None  # Hint from engine
        self.interaction_enabled = True  # Control user interaction
        
        # Edit mode
        self.edit_mode = False
        self.edit_piece: Piece | None = None  # Piece to place in edit mode
        
        # Layout
        self.margin = 40
        self.cell_size = 60
        
        self.setMinimumSize(600, 680)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
    
    def set_board(self, board: ChessBoard):
        """Set the chess board"""
        self.board = board
        self.selected_pos = None
        self.legal_moves = []
        self.update()
    
    def flip_board(self):
        """Flip the board view"""
        self.flipped = not self.flipped
        self.update()
    
    def _calculate_layout(self):
        """Calculate board layout based on widget size"""
        available_width = self.width() - 2 * self.margin
        available_height = self.height() - 2 * self.margin
        
        # Board is 9 wide, 10 tall (but 8 and 9 cells)
        cell_w = available_width // 8
        cell_h = available_height // 9
        self.cell_size = min(cell_w, cell_h)
        
        # Center the board
        board_width = self.cell_size * 8
        board_height = self.cell_size * 9
        self.offset_x = (self.width() - board_width) // 2
        self.offset_y = (self.height() - board_height) // 2
    
    def _board_to_screen(self, file: int, rank: int) -> QPoint:
        """Convert board coordinates to screen coordinates"""
        if self.flipped:
            file = 8 - file
            rank = 9 - rank
        x = self.offset_x + file * self.cell_size
        y = self.offset_y + (9 - rank) * self.cell_size
        return QPoint(x, y)
    
    def _screen_to_board(self, x: int, y: int) -> tuple[int, int] | None:
        """Convert screen coordinates to board coordinates"""
        file = round((x - self.offset_x) / self.cell_size)
        rank = round(9 - (y - self.offset_y) / self.cell_size)
        
        if self.flipped:
            file = 8 - file
            rank = 9 - rank
        
        if 0 <= file < 9 and 0 <= rank < 10:
            return (file, rank)
        return None
    
    def paintEvent(self, event):
        """Paint the board"""
        self._calculate_layout()
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        self._draw_board(painter)
        self._draw_highlights(painter)
        self._draw_pieces(painter)
    
    def _draw_board(self, painter: QPainter):
        """Draw the board grid"""
        # Background
        bg_rect = QRect(
            self.offset_x - 20,
            self.offset_y - 20,
            self.cell_size * 8 + 40,
            self.cell_size * 9 + 40
        )
        painter.fillRect(bg_rect, self.BOARD_COLOR)
        
        # Draw grid lines
        pen = QPen(self.LINE_COLOR, 2)
        painter.setPen(pen)
        
        # Horizontal lines
        for rank in range(10):
            y = self.offset_y + (9 - rank) * self.cell_size
            x1 = self.offset_x
            x2 = self.offset_x + 8 * self.cell_size
            painter.drawLine(x1, y, x2, y)
        
        # Vertical lines (split at river)
        for file in range(9):
            x = self.offset_x + file * self.cell_size
            # Top half (black side)
            y1 = self.offset_y
            y2 = self.offset_y + 4 * self.cell_size
            painter.drawLine(x, y1, x, y2)
            # Bottom half (red side)
            y1 = self.offset_y + 5 * self.cell_size
            y2 = self.offset_y + 9 * self.cell_size
            painter.drawLine(x, y1, x, y2)
        
        # Border left and right at river
        x_left = self.offset_x
        x_right = self.offset_x + 8 * self.cell_size
        y_river_top = self.offset_y + 4 * self.cell_size
        y_river_bottom = self.offset_y + 5 * self.cell_size
        painter.drawLine(x_left, y_river_top, x_left, y_river_bottom)
        painter.drawLine(x_right, y_river_top, x_right, y_river_bottom)
        
        # Palace diagonals
        self._draw_palace_diagonals(painter, 3, 0, 5, 2)  # Red palace
        self._draw_palace_diagonals(painter, 3, 7, 5, 9)  # Black palace
        
        # River text
        font = QFont("SimHei", int(self.cell_size * 0.3))
        painter.setFont(font)
        painter.setPen(self.LINE_COLOR)
        
        river_y = self.offset_y + 4.5 * self.cell_size
        
        # 楚河
        text1 = "楚  河"
        if self.flipped:
            text1, text2 = "汉  界", "楚  河"
        else:
            text1, text2 = "楚  河", "汉  界"
        
        fm = QFontMetrics(font)
        
        text1_rect = QRect(
            self.offset_x + int(self.cell_size * 0.5),
            int(river_y - fm.height() // 2),
            int(self.cell_size * 3),
            fm.height()
        )
        painter.drawText(text1_rect, Qt.AlignCenter, text1)
        
        text2_rect = QRect(
            self.offset_x + int(self.cell_size * 4.5),
            int(river_y - fm.height() // 2),
            int(self.cell_size * 3),
            fm.height()
        )
        painter.drawText(text2_rect, Qt.AlignCenter, text2)
    
    def _draw_palace_diagonals(self, painter: QPainter, f1: int, r1: int, f2: int, r2: int):
        """Draw palace diagonal lines"""
        p1 = self._board_to_screen(f1, r1)
        p2 = self._board_to_screen(f2, r2)
        painter.drawLine(p1, p2)
        
        p1 = self._board_to_screen(f2, r1)
        p2 = self._board_to_screen(f1, r2)
        painter.drawLine(p1, p2)
    
    def _draw_highlights(self, painter: QPainter):
        """Draw selection and legal move highlights"""
        radius = int(self.cell_size * 0.45)
        
        # Hint move highlight (blue arrow)
        if self.hint_move:
            ff, fr, tf, tr = self.hint_move
            from_pos = self._board_to_screen(ff, fr)
            to_pos = self._board_to_screen(tf, tr)
            
            # Draw hint circles
            painter.setBrush(QBrush(self.HINT_COLOR))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(from_pos, radius, radius)
            painter.drawEllipse(to_pos, radius, radius)
            
            # Draw arrow line
            painter.setPen(QPen(self.HINT_COLOR, 4))
            painter.drawLine(from_pos, to_pos)
        
        # Last move highlight
        if self.last_move:
            painter.setBrush(QBrush(self.LAST_MOVE_COLOR))
            painter.setPen(Qt.NoPen)
            ff, fr, tf, tr = self.last_move
            for f, r in [(ff, fr), (tf, tr)]:
                pos = self._board_to_screen(f, r)
                painter.drawEllipse(pos, radius, radius)
        
        # Selected piece highlight
        if self.selected_pos:
            painter.setBrush(QBrush(self.SELECTED_COLOR))
            painter.setPen(Qt.NoPen)
            pos = self._board_to_screen(*self.selected_pos)
            painter.drawEllipse(pos, radius, radius)
        
        # Legal moves
        small_radius = int(self.cell_size * 0.15)
        for f, r in self.legal_moves:
            pos = self._board_to_screen(f, r)
            if self.board.get_piece(f, r):
                # Capture indicator
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(self.LEGAL_MOVE_COLOR, 3))
                painter.drawEllipse(pos, radius, radius)
            else:
                # Move indicator
                painter.setBrush(QBrush(self.LEGAL_MOVE_COLOR))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(pos, small_radius, small_radius)
    
    def _draw_pieces(self, painter: QPainter):
        """Draw all pieces on the board"""
        for rank in range(10):
            for file in range(9):
                piece = self.board.get_piece(file, rank)
                if piece:
                    self._draw_piece(painter, file, rank, piece)
    
    def _draw_piece(self, painter: QPainter, file: int, rank: int, piece: Piece):
        """Draw a single piece"""
        pos = self._board_to_screen(file, rank)
        radius = int(self.cell_size * 0.42)
        
        # Piece background
        painter.setBrush(QBrush(self.PIECE_BG_COLOR))
        if piece.side == Side.RED:
            painter.setPen(QPen(self.RED_PIECE_COLOR, 2))
        else:
            painter.setPen(QPen(self.BLACK_PIECE_COLOR, 2))
        painter.drawEllipse(pos, radius, radius)
        
        # Inner circle
        inner_radius = int(radius * 0.85)
        painter.drawEllipse(pos, inner_radius, inner_radius)
        
        # Piece text
        text = piece.to_chinese()
        font = QFont("SimHei", int(self.cell_size * 0.35), QFont.Bold)
        painter.setFont(font)
        
        if piece.side == Side.RED:
            painter.setPen(self.RED_PIECE_COLOR)
        else:
            painter.setPen(self.BLACK_PIECE_COLOR)
        
        text_rect = QRect(
            pos.x() - radius,
            pos.y() - radius,
            radius * 2,
            radius * 2
        )
        painter.drawText(text_rect, Qt.AlignCenter, text)
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        # Block interaction if disabled (unless in edit mode)
        if not self.interaction_enabled and not self.edit_mode:
            return
            
        pos = self._screen_to_board(event.x(), event.y())
        if pos is None:
            if not self.edit_mode:
                self.selected_pos = None
                self.legal_moves = []
                self.update()
            return
        
        file, rank = pos
        
        # Edit mode handling
        if self.edit_mode:
            if event.button() == Qt.LeftButton:
                # Place piece
                self.board.set_piece(file, rank, self.edit_piece)
                self.piece_placed.emit(file, rank, self.edit_piece)
                self.update()
            elif event.button() == Qt.RightButton:
                # Remove piece
                self.board.set_piece(file, rank, None)
                self.piece_placed.emit(file, rank, None)
                self.update()
            return
        
        # Normal game mode
        if event.button() != Qt.LeftButton:
            return
        
        # If we have a selection and click on a legal move, make the move
        if self.selected_pos and pos in self.legal_moves:
            from_file, from_rank = self.selected_pos
            move = ChessBoard.format_move(from_file, from_rank, file, rank)
            
            if self.board.make_move(move):
                self.last_move = (from_file, from_rank, file, rank)
                self.move_made.emit(move)
            
            self.selected_pos = None
            self.legal_moves = []
            self.update()
            return
        
        # Otherwise, try to select a piece
        piece = self.board.get_piece(file, rank)
        if piece and piece.side == self.board.current_side:
            self.selected_pos = pos
            self.legal_moves = self.board.get_legal_moves(file, rank)
        else:
            self.selected_pos = None
            self.legal_moves = []
        
        self.update()
    
    def clear_selection(self):
        """Clear current selection"""
        self.selected_pos = None
        self.legal_moves = []
        self.update()
    
    def set_last_move(self, move: str):
        """Set the last move for highlighting"""
        coords = ChessBoard.parse_move(move)
        if coords:
            self.last_move = coords
            self.update()
