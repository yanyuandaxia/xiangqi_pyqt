#!/usr/bin/env python3
"""
Main Window for Xiangqi GUI
"""

import os
import json
import re
import datetime
import time
from enum import Enum
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QMenuBar, QMenu, QAction, QToolBar, QStatusBar,
    QFileDialog, QMessageBox, QDialog, QLabel, 
    QComboBox, QPushButton, QSpinBox, QGroupBox,
    QFormLayout, QDialogButtonBox, QGridLayout, QButtonGroup,
    QRadioButton, QFrame, QInputDialog, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from chess_logic import ChessBoard, Side, STARTING_FEN, Piece, PieceType
from board_widget import BoardWidget
from move_history import MoveHistoryWidget
from uci_engine import UCIEngine, EngineInfo
from win_rate_bar import WinRateBar
from analysis_chart import AnalysisChart
from clock_widget import ClockManager
from resource_path import get_settings_path, get_resource_path, get_user_data_path, get_engine_path, get_default_engine_path


class PlayerType(Enum):
    HUMAN = "玩家"
    ENGINE = "引擎"


class SettingsDialog(QDialog):
    """Dialog for game settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("游戏设置")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Player settings
        player_group = QGroupBox("对弈设置")
        player_layout = QFormLayout()
        
        self.red_player = QComboBox()
        self.red_player.addItems([t.value for t in PlayerType])
        player_layout.addRow("红方:", self.red_player)
        
        self.black_player = QComboBox()
        self.black_player.addItems([t.value for t in PlayerType])
        self.black_player.setCurrentIndex(1)  # Default to engine
        player_layout.addRow("黑方:", self.black_player)
        
        player_group.setLayout(player_layout)
        layout.addWidget(player_group)
        
        # Engine settings
        engine_group = QGroupBox("引擎设置")
        engine_layout = QFormLayout()
        
        self.engine_path_label = QLabel("未选择")
        self.engine_path_label.setWordWrap(True)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.engine_path_label)
        browse_btn = QPushButton("选择...")
        browse_btn.clicked.connect(self._browse_engine)
        path_layout.addWidget(browse_btn)
        
        engine_layout.addRow("引擎路径:", path_layout)
        
        self.think_time = QSpinBox()
        self.think_time.setRange(0, 600000)  # Up to 600 seconds
        self.think_time.setValue(2000)
        self.think_time.setSuffix(" 毫秒")
        self.think_time.setSpecialValueText("不限")
        engine_layout.addRow("思考时间:", self.think_time)
        
        self.depth = QSpinBox()
        self.depth.setRange(0, 100)
        self.depth.setValue(0)
        self.depth.setSpecialValueText("不限")
        engine_layout.addRow("思考深度:", self.depth)
        
        self.threads = QSpinBox()
        self.threads.setRange(1, 32)
        self.threads.setValue(1)
        engine_layout.addRow("线程数:", self.threads)
        
        engine_group.setLayout(engine_layout)
        layout.addWidget(engine_group)


        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.engine_path = ""
    
    def _browse_engine(self):
        """Browse for engine executable"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择引擎", "", "可执行文件 (*)"
        )
        if path:
            self.engine_path = path
            self.engine_path_label.setText(os.path.basename(path))
    
    def get_settings(self) -> dict:
        """Get the current settings"""
        return {
            'red_player': PlayerType.HUMAN if self.red_player.currentIndex() == 0 else PlayerType.ENGINE,
            'black_player': PlayerType.HUMAN if self.black_player.currentIndex() == 0 else PlayerType.ENGINE,
            'engine_path': self.engine_path,
            'think_time': self.think_time.value(),
            'depth': self.depth.value(),
            'threads': self.threads.value(),
            'threads': self.threads.value(),
        }
    
    def set_settings(self, settings: dict):
        """Set the current settings"""
        if 'red_player' in settings:
            self.red_player.setCurrentIndex(0 if settings['red_player'] == PlayerType.HUMAN else 1)
        if 'black_player' in settings:
            self.black_player.setCurrentIndex(0 if settings['black_player'] == PlayerType.HUMAN else 1)
        if 'engine_path' in settings and settings['engine_path']:
            self.engine_path = settings['engine_path']
            self.engine_path_label.setText(os.path.basename(settings['engine_path']))
        if 'think_time' in settings:
            self.think_time.setValue(settings['think_time'])
        if 'depth' in settings:
            self.depth.setValue(settings['depth'])
        if 'threads' in settings:
            self.threads.setValue(settings['threads'])



class AnalysisOptionsDialog(QDialog):
    """Dialog for choosing analysis mode and managing analysis results"""

    load_clicked = pyqtSignal()
    save_clicked = pyqtSignal()

    def __init__(self, realtime_enabled: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("分析选项")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        mode_group = QGroupBox("分析模式")
        mode_layout = QVBoxLayout()
        self.realtime_radio = QRadioButton("实时分析")
        self.record_radio = QRadioButton("分析对局记录")
        mode_layout.addWidget(self.realtime_radio)
        mode_layout.addWidget(self.record_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        if realtime_enabled:
            self.realtime_radio.setChecked(True)
        else:
            self.record_radio.setChecked(True)

        action_group = QGroupBox("分析结果")
        action_layout = QHBoxLayout()
        self.load_btn = QPushButton("读取结果")
        self.save_btn = QPushButton("存储结果")
        action_layout.addWidget(self.load_btn)
        action_layout.addWidget(self.save_btn)
        action_group.setLayout(action_layout)
        layout.addWidget(action_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("开始")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.load_btn.clicked.connect(self.load_clicked.emit)
        self.save_btn.clicked.connect(self.save_clicked.emit)

    def is_realtime_selected(self) -> bool:
        return self.realtime_radio.isChecked()


class PgnDialog(QDialog):
    """Dialog for PGN actions"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("棋谱")
        self.setMinimumWidth(240)

        layout = QVBoxLayout(self)

        action_group = QGroupBox("棋谱操作")
        action_layout = QHBoxLayout()
        self.open_btn = QPushButton("打开")
        self.save_btn = QPushButton("保存")
        action_layout.addWidget(self.open_btn)
        action_layout.addWidget(self.save_btn)
        action_group.setLayout(action_layout)
        action_group.setLayout(action_layout)
        layout.addWidget(action_group)
        
        # Format settings
        format_group = QGroupBox("格式设置")
        format_layout = QFormLayout()
        
        self.pgn_format = QComboBox()
        self.pgn_format.addItems(["中文纵线格式 (炮二平五)", "ICCS 坐标格式 (C2-E2)"])
        format_layout.addRow("棋谱格式:", self.pgn_format)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def set_format(self, format_str: str):
        """Set current PGN format"""
        self.pgn_format.setCurrentIndex(1 if format_str == 'ICCS' else 0)

    def get_format(self) -> str:
        """Get selected PGN format"""
        return 'ICCS' if self.pgn_format.currentIndex() == 1 else 'Chinese'


class BoardEditorDialog(QDialog):
    """Dialog for editing board position"""
    
    def __init__(self, board_widget, parent=None):
        super().__init__(parent)
        self.board_widget = board_widget
        self.setWindowTitle("编辑棋盘")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("左键放置棋子，右键删除棋子")
        instructions.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(instructions)
        
        # Red pieces
        red_group = QGroupBox("红方棋子")
        red_layout = QGridLayout()
        self.red_buttons = []
        red_pieces = [
            (PieceType.KING, "帅"), (PieceType.ADVISOR, "仕"), (PieceType.BISHOP, "相"),
            (PieceType.ROOK, "车"), (PieceType.KNIGHT, "马"), (PieceType.CANNON, "炮"),
            (PieceType.PAWN, "兵")
        ]
        for i, (ptype, name) in enumerate(red_pieces):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet("color: #c81e1e; font-weight: bold; font-size: 14px;")
            btn.setMinimumSize(40, 40)
            btn.clicked.connect(lambda checked, pt=ptype, s=Side.RED: self._select_piece(pt, s))
            red_layout.addWidget(btn, 0, i)
            self.red_buttons.append(btn)
        red_group.setLayout(red_layout)
        layout.addWidget(red_group)
        
        # Black pieces
        black_group = QGroupBox("黑方棋子")
        black_layout = QGridLayout()
        self.black_buttons = []
        black_pieces = [
            (PieceType.KING, "将"), (PieceType.ADVISOR, "士"), (PieceType.BISHOP, "象"),
            (PieceType.ROOK, "車"), (PieceType.KNIGHT, "馬"), (PieceType.CANNON, "砲"),
            (PieceType.PAWN, "卒")
        ]
        for i, (ptype, name) in enumerate(black_pieces):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet("color: #141414; font-weight: bold; font-size: 14px;")
            btn.setMinimumSize(40, 40)
            btn.clicked.connect(lambda checked, pt=ptype, s=Side.BLACK: self._select_piece(pt, s))
            black_layout.addWidget(btn, 0, i)
            self.black_buttons.append(btn)
        black_group.setLayout(black_layout)
        layout.addWidget(black_group)
        
        # Side to move
        side_group = QGroupBox("先行方")
        side_layout = QHBoxLayout()
        self.red_first = QRadioButton("红先")
        self.black_first = QRadioButton("黑先")
        self.red_first.setChecked(True)
        side_layout.addWidget(self.red_first)
        side_layout.addWidget(self.black_first)
        side_group.setLayout(side_layout)
        layout.addWidget(side_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        import_btn = QPushButton("导入局面")
        import_btn.clicked.connect(self._import_fen)
        action_layout.addWidget(import_btn)
        
        export_btn = QPushButton("导出局面")
        export_btn.clicked.connect(self._export_fen)
        action_layout.addWidget(export_btn)
        
        clear_btn = QPushButton("清空棋盘")
        clear_btn.clicked.connect(self._clear_board)
        action_layout.addWidget(clear_btn)
        
        reset_btn = QPushButton("初始局面")
        reset_btn.clicked.connect(self._reset_board)
        action_layout.addWidget(reset_btn)
        
        layout.addLayout(action_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._confirm)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.selected_piece = None
        self.all_buttons = self.red_buttons + self.black_buttons
    
    def _select_piece(self, piece_type: PieceType, side: Side):
        """Select a piece type to place"""
        # Uncheck all other buttons
        for btn in self.all_buttons:
            if btn.isChecked() and btn != self.sender():
                btn.setChecked(False)
        
        if self.sender().isChecked():
            self.selected_piece = Piece(piece_type, side)
            self.board_widget.edit_piece = self.selected_piece
        else:
            self.selected_piece = None
            self.board_widget.edit_piece = None
    
    def _clear_board(self):
        """Clear all pieces from the board"""
        for rank in range(10):
            for file in range(9):
                self.board_widget.board.set_piece(file, rank, None)
        self.board_widget.update()
    
    def _reset_board(self):
        """Reset to starting position"""
        self.board_widget.board.load_fen(STARTING_FEN)
        self.red_first.setChecked(True)
        self.board_widget.update()
    
    def _import_fen(self):
        """Import position from FEN string via dialog"""
        text, ok = QInputDialog.getText(
            self, "导入局面", "请输入FEN字符串:",
            text="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        )
        
        if ok and text.strip():
            fen = text.strip()
            # Load FEN
            if self.board_widget.board.load_fen(fen):
                # Update side to move radio buttons
                if self.board_widget.board.current_side == Side.RED:
                    self.red_first.setChecked(True)
                else:
                    self.black_first.setChecked(True)
                self.board_widget.update()
            else:
                QMessageBox.warning(self, "错误", "无效的FEN字符串")

    def _export_fen(self):
        """Export current position to FEN string via dialog"""
        # Set current side based on radio buttons first
        orig_side = self.board_widget.board.current_side
        if self.red_first.isChecked():
            self.board_widget.board.current_side = Side.RED
        else:
            self.board_widget.board.current_side = Side.BLACK
            
        fen = self.board_widget.board.to_fen()
        
        # Restore side
        self.board_widget.board.current_side = orig_side
        
        # Show dialog with FEN string that can be copied
        dialog = QDialog(self)
        dialog.setWindowTitle("导出局面")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        label = QLabel("当前局面的FEN字符串（可复制）:")
        layout.addWidget(label)
        
        from PyQt5.QtWidgets import QLineEdit
        fen_edit = QLineEdit()
        fen_edit.setText(fen)
        fen_edit.setReadOnly(True)
        fen_edit.selectAll()
        layout.addWidget(fen_edit)
        
        # Copy button
        copy_btn = QPushButton("复制到剪贴板")
        def copy_fen():
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(fen)
            QMessageBox.information(dialog, "成功", "FEN已复制到剪贴板")
        copy_btn.clicked.connect(copy_fen)
        layout.addWidget(copy_btn)
        
        # Close button
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec_()
    
    def _confirm(self):
        """Confirm the edited position"""
        # Set side to move
        if self.red_first.isChecked():
            self.board_widget.board.current_side = Side.RED
        else:
            self.board_widget.board.current_side = Side.BLACK
        
        # Check if red is on top (non-standard position)
        # If so, flip the board to normalize it
        red_king = self.board_widget.board._find_king(Side.RED)
        if red_king and red_king[1] >= 5:
            # Red king is in upper half - flip the board to normalize
            self._flip_board_position()
        
        # Clear history since this is a new position
        self.board_widget.board.move_history = []
        self.board_widget.board.position_history = []
        self.board_widget.board.check_history = []
        self.board_widget.board.halfmove_clock = 0
        self.board_widget.board.fullmove_number = 1
        
        self.accept()
    
    def _flip_board_position(self):
        """Flip the board position vertically to normalize red to bottom"""
        board = self.board_widget.board
        new_board = [[None] * 9 for _ in range(10)]
        
        for rank in range(10):
            for file in range(9):
                piece = board.board[rank][file]
                if piece:
                    # Flip rank: 0->9, 1->8, ..., 9->0
                    new_rank = 9 - rank
                    new_board[new_rank][file] = piece
        
        board.board = new_board


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("中国象棋")
        self.setMinimumSize(1100, 900)
        
        # Game state
        self.board = ChessBoard()
        self.settings = {
            'red_player': PlayerType.HUMAN,
            'black_player': PlayerType.ENGINE,
            'engine_path': '',
            'think_time': 2000,
            'depth': 0,
            'threads': 1,
            'pgn_format': 'Chinese'
        }
        
        # Engine
        self.engine = UCIEngine()
        self.engine.on_bestmove = self._on_engine_move
        self.engine.on_info = self._on_engine_info
        self.engine.on_ready = self._on_engine_ready
        
        # Hint mode flag
        self.hint_mode = False
        self.showing_hint_result = False
        self.hint_info_text = ""  # 保存提示结果的文本
        
        # Edited position flag (allows engine analysis even if game appears over)
        self.edited_position = False

        # Redo stack (list of UCI move strings)
        self.redo_stack = []

        # Analysis state
        self._analysis_mode = False
        self._analysis_scores = []
        self._analysis_positions = []
        self._analysis_current_index = 0

        # Realtime analysis state
        self._realtime_analysis_enabled = False
        self._realtime_analysis_active = False
        self._realtime_pending = []
        self._realtime_last_score = 0

        # Pending move navigation while engine is thinking
        self._pending_goto_move = None

        # Suppress engine auto-move after history navigation
        self._suppress_engine_turn = False

        # Last PV text (Chinese)
        self._last_pv_text = ""

        self._setup_ui()
        # self._setup_menu()  # Menu bar disabled
        self._setup_toolbar()
        self._setup_statusbar()
        
        # Load settings (this will also start the engine if path is set)
        self.load_settings()
        
        self._update_status()
    
    def _get_engine_go_params(self):
        """Get parameters for engine.go based on settings"""
        think_time = self.settings['think_time']
        depth = self.settings.get('depth', 0)
        
        if think_time == 0 and depth == 0:
            return None  # Invalid configuration
            
        kwargs = {}
        if think_time > 0:
            kwargs['movetime'] = think_time
        
        if depth > 0:
            kwargs['depth'] = depth
            
        return kwargs

    def _setup_ui(self):
        """Setup the main UI layout"""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QHBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Clock Manager (Create logic and widgets)
        self.clock_widget = ClockManager()
        
        # Container for game area (WinRate, Board, Clocks)
        game_area_layout = QGridLayout()
        game_area_layout.setSpacing(5)
        # Vertical spacing for clocks
        game_area_layout.setVerticalSpacing(10)
        
        # Win rate bar (row 0-2, col 0) - Spans all 3 rows
        self.win_rate_bar = WinRateBar()
        game_area_layout.addWidget(self.win_rate_bar, 0, 0, 3, 1)
        
        # Top Clock (row 0, col 1)
        game_area_layout.addWidget(self.clock_widget.top_label, 0, 1, Qt.AlignCenter)
        
        # Board (row 1, col 1)
        self.board_widget = BoardWidget()
        self.board_widget.set_board(self.board)
        self.board_widget.move_made.connect(self._on_player_move)
        game_area_layout.addWidget(self.board_widget, 1, 1)
        
        # Bottom Clock (row 2, col 1)
        game_area_layout.addWidget(self.clock_widget.bottom_label, 2, 1, Qt.AlignCenter)
        
        # Set column stretch
        game_area_layout.setColumnStretch(1, 1) # Board takes extra space
        
        layout.addLayout(game_area_layout, stretch=1)
        
        # Side panel
        side_panel = QVBoxLayout()
        
        # Move history and analysis chart in horizontal splitter for equal sizing
        from PyQt5.QtWidgets import QSplitter
        history_chart_splitter = QSplitter(Qt.Horizontal)
        
        # Move history + PV (wrapped in a container widget)
        move_history_container = QWidget()
        move_history_layout = QVBoxLayout(move_history_container)
        move_history_layout.setContentsMargins(0, 0, 0, 0)

        self.move_history = MoveHistoryWidget()
        self.move_history.move_selected.connect(self._goto_move)
        move_history_layout.addWidget(self.move_history, stretch=1)

        self.pv_label = QLabel("")
        self.pv_label.setWordWrap(True)
        self.pv_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #f8f8f8;
                border-radius: 5px;
                font-size: 12px;
                color: #333;
            }
        """)
        move_history_layout.addWidget(self.pv_label)

        history_chart_splitter.addWidget(move_history_container)
        
        # Analysis chart + score (wrapped in a container widget)
        analysis_container = QWidget()
        analysis_layout = QVBoxLayout(analysis_container)
        analysis_layout.setContentsMargins(0, 0, 0, 0)

        self.analysis_chart = AnalysisChart()
        self.analysis_chart.point_clicked.connect(self._goto_move)
        self.analysis_chart.score_updated.connect(self._on_analysis_score_update)
        self.analysis_chart.show()
        analysis_layout.addWidget(self.analysis_chart, stretch=1)
        
        # Engine info (not shown in UI, kept for internal updates)
        self.engine_info_label = QLabel("引擎: 未连接")
        self.engine_info_label.setWordWrap(True)
        self.engine_info_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f0f0f0;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        self.engine_info_label.hide()

        # Analysis score label (under chart)
        self.analysis_score_label = QLabel("")
        self.analysis_score_label.setWordWrap(True)
        self.analysis_score_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f5f5f5;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        self.analysis_score_label.show()
        analysis_layout.addWidget(self.analysis_score_label)

        history_chart_splitter.addWidget(analysis_container)
        
        # Set equal sizes for both panels
        history_chart_splitter.setSizes([1, 1])
        history_chart_splitter.setStretchFactor(0, 1)
        history_chart_splitter.setStretchFactor(1, 1)
        
        side_panel.addWidget(history_chart_splitter, stretch=1)
        
        # Game controls
        controls_layout = QGridLayout()
        controls_layout.setSpacing(10)
        
        # Common style for all buttons
        btn_style = """
            QPushButton {
                padding: 10px;
                font-size: 14px;
                background-color: #f8f9fa;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                color: #333;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #e2e6ea;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dae0e5;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #aaa;
                border-color: #ddd;
            }
        """
        
        self.prev_btn = QPushButton("上一步")
        self.prev_btn.setStyleSheet(btn_style)
        self.prev_btn.clicked.connect(lambda: self._step_back(allow_redo=True))
        controls_layout.addWidget(self.prev_btn, 0, 0)
        
        self.next_btn = QPushButton("下一步")
        self.next_btn.setStyleSheet(btn_style)
        self.next_btn.clicked.connect(self._step_forward)
        controls_layout.addWidget(self.next_btn, 0, 1)
        
        self.undo_btn = QPushButton("悔棋")
        self.undo_btn.setStyleSheet(btn_style)
        self.undo_btn.clicked.connect(self._undo_move)
        controls_layout.addWidget(self.undo_btn, 1, 0)
        
        self.hint_btn = QPushButton("提示")
        self.hint_btn.setStyleSheet(btn_style)
        self.hint_btn.clicked.connect(self._request_hint)
        controls_layout.addWidget(self.hint_btn, 1, 1)
        
        # Start button - resumes engine thinking
        self.start_btn = QPushButton("开始")
        self.start_btn.setStyleSheet(btn_style)
        self.start_btn.clicked.connect(self._resume_engine)
        controls_layout.addWidget(self.start_btn, 2, 0)
        
        
        # Stop button - stops engine thinking
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setStyleSheet(btn_style)
        self.stop_btn.clicked.connect(self._stop_engine)
        controls_layout.addWidget(self.stop_btn, 2, 1)
        
        side_panel.addLayout(controls_layout)
        
        layout.addLayout(side_panel)
    
    def _setup_menu(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        
        # Game menu
        game_menu = menubar.addMenu("游戏")
        
        new_action = QAction("新游戏", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_game)
        game_menu.addAction(new_action)
        
        game_menu.addSeparator()
        
        settings_action = QAction("设置...", self)
        settings_action.triggered.connect(self._show_settings)
        game_menu.addAction(settings_action)
        
        game_menu.addSeparator()
        
        quit_action = QAction("退出", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        game_menu.addAction(quit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("编辑")
        
        undo_action = QAction("悔棋", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self._undo_move)
        edit_menu.addAction(undo_action)
        
        # View menu
        view_menu = menubar.addMenu("视图")
        
        flip_action = QAction("翻转棋盘", self)
        flip_action.setShortcut("F")
        flip_action.triggered.connect(self._flip_board)
        view_menu.addAction(flip_action)
    
    def _setup_toolbar(self):
        """Setup the toolbar"""
        toolbar = QToolBar("工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        new_btn = QAction("新游戏", self)
        new_btn.triggered.connect(self._new_game)
        toolbar.addAction(new_btn)
        
        toolbar.addSeparator()
        
        flip_btn = QAction("翻转", self)
        flip_btn.triggered.connect(self._flip_board)
        toolbar.addAction(flip_btn)
        
        toolbar.addSeparator()
        
        edit_btn = QAction("编辑", self)
        edit_btn.triggered.connect(self._edit_board)
        toolbar.addAction(edit_btn)
        
        toolbar.addSeparator()

        pgn_btn = QAction("棋谱", self)
        pgn_btn.triggered.connect(self._show_pgn_dialog)
        toolbar.addAction(pgn_btn)
        
        toolbar.addSeparator()
        
        analyze_btn = QAction("分析", self)
        analyze_btn.triggered.connect(self._show_analysis_dialog)
        toolbar.addAction(analyze_btn)
        
        toolbar.addSeparator()

        timer_btn = QAction("计时", self)
        timer_btn.triggered.connect(self._toggle_clock)
        toolbar.addAction(timer_btn)
        
        toolbar.addSeparator()
        
        settings_btn = QAction("设置", self)
        settings_btn.triggered.connect(self._show_settings)
        toolbar.addAction(settings_btn)
        
        toolbar.addSeparator()
        
        about_btn = QAction("关于", self)
        about_btn.triggered.connect(self._show_about)
        toolbar.addAction(about_btn)
    
    def _setup_statusbar(self):
        """Setup the status bar"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        self.turn_label = QLabel()
        self.statusbar.addWidget(self.turn_label)

        self.engine_status_label = QLabel("引擎：未连接")
        self.engine_status_label.setStyleSheet("color: #444;")
        self.engine_status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.engine_status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.statusbar.addWidget(self.engine_status_label, stretch=1)
        
        self.status_label = QLabel()
        self.statusbar.addPermanentWidget(self.status_label)
    
    def _update_status(self):
        """Update the status bar"""
        side = "红方" if self.board.current_side == Side.RED else "黑方"
        player_type = self.settings['red_player'] if self.board.current_side == Side.RED else self.settings['black_player']
        player = player_type.value
        
        self.turn_label.setText(f"当前: {side} ({player})")
        
        if self.board.is_checkmate():
            winner = "黑方" if self.board.current_side == Side.RED else "红方"
            self.status_label.setText(f"将死! {winner}获胜!")
        elif self.board.is_stalemate():
            self.status_label.setText("困毙!")
        elif self.board.is_draw():
            can_draw, reason = self.board.can_claim_draw()
            self.status_label.setText(f"和棋 ({reason})")
        # elif self.engine.is_thinking and not self.hint_mode:
        #     self.status_label.setText("引擎思考中...")
        elif self.hint_mode:
            self.status_label.setText("正在获取提示...")
        else:
            self.status_label.setText("")

    def _set_engine_status(self, text: str):
        """Set engine status text on status bar"""
        if hasattr(self, 'engine_status_label'):
            self.engine_status_label.setText(text)
    
    def _new_game(self):
        """Start a new game"""
        self.board = ChessBoard()
        self.board_widget.set_board(self.board)
        self.board_widget.last_move = None
        self.move_history.clear()
        self.redo_stack.clear() # Clear redo stack
        self.board_widget.hint_move = None
        self.edited_position = False  # Reset edited position flag
        
        # Reset win rate bar to 50/50 for new game
        self.win_rate_bar.reset()
        
        # Clear and hide analysis chart
        self.analysis_chart.clear()
        self.analysis_chart.show()
        self.analysis_score_label.show()

        # Reset analysis data
        self._analysis_scores = []
        self._analysis_positions = []
        self._analysis_current_index = 0
        self._analysis_mode = False
        self._realtime_pending = []
        self._realtime_analysis_active = False
        
        # Check if both sides are engines - require manual start
        both_engines = (self.settings['red_player'] == PlayerType.ENGINE and 
                       self.settings['black_player'] == PlayerType.ENGINE)
        self._suppress_engine_turn = both_engines
        
        if self.engine.is_ready:
            self.engine.new_game()
        
        self._update_status()
        self._update_clock()
        self._check_engine_turn()
    
    def _toggle_clock(self):
        """Toggle clock visibility"""
        if self.clock_widget.isVisible():
            self.clock_widget.hide()
            self.clock_widget.reset()
        else:
            self.clock_widget.show()
            self._update_clock()
            
    def _update_clock(self):
        """Update clock state based on game state"""
        if not self.clock_widget.isVisible():
            return
            
        # Don't run clock during analysis
        if hasattr(self, '_analysis_mode') and self._analysis_mode:
            self.clock_widget.stop_timing()
            return
            
        # Check if game is over
        if self.board.is_checkmate() or self.board.is_draw() or self.board.is_stalemate():
            self.clock_widget.stop_timing()
            return
            
        move_count = len(self.board.move_history)
        
        if move_count == 0:
            self.clock_widget.reset()
        else:
            # Game is in progress, start timing for current side
            self.clock_widget.start_timing(self.board.current_side)
    
    def _rebuild_move_history_list(self):
        """Rebuild move history widget content"""
        self.move_history.clear()
        
        # 1. Past moves
        temp_board = ChessBoard()
        
        for i, move in enumerate(self.board.move_history):
            if i < len(self.board.position_history):
                # Use historical position to generate notation
                temp_board.board = self.board.position_history[i]
                chinese_move = self.board.move_to_chinese(move, temp_board)
                
                move_num = i // 2 + 1
                is_red = i % 2 == 0
                self.move_history.add_move(move_num, chinese_move, is_red)
            else:
                self.move_history.add_move(i // 2 + 1, move, i % 2 == 0)
        
        # 2. Future moves (Redo stack)
        import copy
        future_board = ChessBoard()
        future_board.board = copy.deepcopy(self.board.board)
        future_board.current_side = self.board.current_side
        
        start_index = len(self.board.move_history)
        
        # Redo stack is LIFO (last undone is at end), so reverse to get chronological order
        for i, move in enumerate(reversed(self.redo_stack)):
            chinese_move = future_board.move_to_chinese(move)
            
            # Make move on future board to prepare for next move in stack
            # We use make_move logic but need to be careful about state
            # Simple apply logic
            future_board.make_move(move)
            
            global_index = start_index + i
            move_num = global_index // 2 + 1
            is_red = global_index % 2 == 0
            self.move_history.add_move(move_num, chinese_move, is_red)
        
        # 3. Highlight current position
        if self.board.move_history:
             index = len(self.board.move_history) - 1
             self.move_history.highlight_move(index)
             self.board_widget.set_last_move(self.board.move_history[-1])
        else:
             self.move_history.highlight_move(-1) # Clear selection
             self.board_widget.last_move = None
        
        
             
    def _goto_move(self, move_index: int):
        """Jump to a specific move"""
        target_len = move_index + 1
        current_len = len(self.board.move_history)
        
        if target_len == current_len:
            return

        # Block navigation while engine is thinking
        if self.engine.is_thinking:
            return

        # Suppress engine auto-move after navigating history
        self._suppress_engine_turn = True
            
        if target_len < current_len:
            # Backward jump
            while len(self.board.move_history) > target_len:
                move = self.board.undo_move()
                if move:
                    self.redo_stack.append(move)
        else:
            # Forward jump
            needed = target_len - current_len
            if len(self.redo_stack) < needed:
                return
                
            for _ in range(needed):
                if not self.redo_stack:
                    break
                move = self.redo_stack.pop()
                self.board.make_move(move)
            
        self.board_widget.set_board(self.board)
        self.board_widget.hint_move = None
        self._rebuild_move_history_list()
        self._rebuild_move_history_list()
        self._update_status()
        self.clock_widget.stop_timing() # Stop clock when navigating history
        
        # Update analysis chart highlight
        if self.analysis_chart.isVisible():
            current_index = len(self.board.move_history) - 1
            self.analysis_chart.highlight_move(current_index)
        
        self._check_engine_turn()
    
    def _on_analysis_score_update(self, move_index: int, score_cp: int):
        """Handle score update from analysis chart"""
        if score_cp >= 30000:
            text = "红方必胜"
        elif score_cp <= -30000:
            text = "黑方必胜"
        else:
            # Show raw score (cumulative score) similar to hint
            if score_cp > 0:
                text = f"+{score_cp}"
            else:
                text = f"{score_cp}"
        
        # Color logic is handled below (always black for score)
        
        move_num = move_index // 2 + 1
        is_red_move = move_index % 2 == 0
        side = "红" if is_red_move else "黑"
        
        # Color for the prefix based on whose move it is
        prefix_color = "#c81e1e" if is_red_move else "#1a1a1a"
        
        # Color for the score is always black as requested
        score_color = "#1a1a1a"
        
        self.analysis_score_label.setText(
            f"<html><span style='color:{prefix_color}; font-weight:bold;'>第{move_num}回合({side})</span>: "
            f"<span style='color:{score_color};'>{text}</span></html>"
        )
        self.analysis_score_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f5f5f5;
                border-radius: 5px;
                font-size: 12px;
            }
        """)

    def _step_back(self, allow_redo=True):
        """Go to previous move"""
        # Block while engine is thinking
        if self.engine.is_thinking:
            return
            
        move = self.board.undo_move()
        if move:
            if allow_redo:
                self.redo_stack.append(move)
            else:
                self.redo_stack.clear()

            self._prune_analysis_after_current()
                
            self.board_widget.set_board(self.board)
            self.board_widget.hint_move = None
            self._rebuild_move_history_list()
            self._rebuild_move_history_list()
            self._update_status()
            self.clock_widget.stop_timing() # Stop clock when navigating history

    def _step_forward(self):
        """Go to next move"""
        # Block while engine is thinking
        if self.engine.is_thinking:
            return
            
        if not self.redo_stack:
            return
            
        # Get move from stack (LIFO)
        move = self.redo_stack.pop()
        
        # Make the move
        if self.board.make_move(move):
            self.board_widget.set_board(self.board)
            self.board_widget.hint_move = None
            self._rebuild_move_history_list()
            self._update_status()
            self._check_game_result()
            self.clock_widget.stop_timing() # Stop clock when navigating history using redo

    def _undo_move(self):
        """Undo the last move (smart undo)"""
        # Block while engine is thinking
        if self.engine.is_thinking:
            return
            
        # Undo one move
        self._step_back(allow_redo=False)
        
        # If playing against engine, undo engine's move too
        # Check if it was engine's turn BEFORE the undo (which is now current_player)
        # Actually, simpler: check settings for current side to move.
        current_player = self.settings['red_player'] if self.board.current_side == Side.RED else self.settings['black_player']
        if current_player == PlayerType.ENGINE:
            self._step_back(allow_redo=False)
    
    def _flip_board(self):
        """Flip the board view"""
        self.board_widget.flip_board()
        # Sync win rate bar with board orientation
        self.win_rate_bar.set_flipped(self.board_widget.flipped)
        # Sync clock positions
        self.clock_widget.set_flipped(self.board_widget.flipped)
    
    def _edit_board(self):
        """Open board editor"""
        # Stop engine if thinking and prevent auto-play
        self._suppress_engine_turn = True
        if self.engine.is_thinking:
            self.engine.stop_thinking()

        # Clear analysis display when entering editor
        self.analysis_chart.clear()
        self.analysis_chart.show()
        self.analysis_score_label.show()
        self._analysis_scores = []
        self._analysis_positions = []
        self._analysis_current_index = 0
        self._analysis_mode = False
        self._cancel_realtime_analysis()
        
        # Save current board state in case of cancel
        import copy
        self._saved_board = copy.deepcopy(self.board.board)
        self._saved_side = self.board.current_side
        
        # Enable edit mode
        self.board_widget.edit_mode = True
        self.board_widget.edit_piece = None
        self.board_widget.clear_selection()
        
        # Show editor dialog (non-modal)
        self._edit_dialog = BoardEditorDialog(self.board_widget, self)
        
        # Set current side in dialog
        if self.board.current_side == Side.RED:
            self._edit_dialog.red_first.setChecked(True)
        else:
            self._edit_dialog.black_first.setChecked(True)
        
        # Connect finished signal
        self._edit_dialog.finished.connect(self._on_edit_finished)
        
        # Show as non-modal
        self._edit_dialog.show()
    
    def _on_edit_finished(self, result):
        """Handle edit dialog close"""
        # Disable edit mode
        self.board_widget.edit_mode = False
        self.board_widget.edit_piece = None
        
        if result == QDialog.Accepted:
            # Update game state
            self.board_widget.last_move = None
            self.move_history.clear()
            self.redo_stack.clear() # Clear redo stack
            
            # Mark as edited position to allow engine analysis
            self.edited_position = True
            
            # Board position has been normalized (red at bottom) in _confirm
            # Reset view to normal orientation
            self.board_widget.flipped = False
            self.win_rate_bar.set_flipped(False)
            self.clock_widget.set_flipped(False)
            self.board_widget.update()
            
            if self.engine.is_ready:
                self.engine.new_game()
            
            self._update_status()
            
            # Check if it's engine's turn after editing
            QTimer.singleShot(100, self._check_engine_turn)
        else:
            # Restore saved board state
            self.board.board = self._saved_board
            self.board.current_side = self._saved_side
            self.board_widget.update()
    
    def _export_pgn(self):
        """Export game to PGN file"""
        file_path, _ = QFileDialog.getSaveFileName(self, "保存对局", "", "PGN Files (*.pgn);;All Files (*)")
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self._build_pgn_text())
                    
            QMessageBox.information(self, "成功", "对局保存成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def _build_pgn_text(self, pgn_format: str = None) -> str:
        """Build PGN text for current game"""
        if pgn_format is None:
            pgn_format = self.settings.get('pgn_format')

        lines = []
        lines.append('[Game "Xiangqi"]')
        lines.append(f'[Date "{datetime.date.today().strftime("%Y.%m.%d")}"]')
        lines.append(f'[Red "{self.settings["red_player"].value}"]')
        lines.append(f'[Black "{self.settings["black_player"].value}"]')
        if pgn_format == 'ICCS':
            lines.append('[Format "ICCS"]')

        result = "*"
        if self.board.is_checkmate():
            result = "0-1" if self.board.current_side == Side.RED else "1-0"
        elif self.board.is_draw() or self.board.is_stalemate():
            result = "1/2-1/2"
        lines.append(f'[Result "{result}"]')
        lines.append("")

        temp_board = ChessBoard()
        line = ""
        use_iccs = pgn_format == 'ICCS'

        for i, move in enumerate(self.board.move_history):
            move_num = i // 2 + 1

            if use_iccs:
                move_str = self.board.move_to_iccs(move)
            else:
                if i < len(self.board.position_history):
                    temp_board.board = self.board.position_history[i]
                    move_str = self.board.move_to_chinese(move, temp_board)
                else:
                    move_str = move

            if i % 2 == 0:
                line += f"{move_num}. {move_str} "
            else:
                line += f"{move_str} "

            if len(line) > 80:
                lines.append(line.rstrip())
                line = ""

        if line:
            lines.append(line.rstrip())

        return "\n".join(lines) + "\n"

    def _import_pgn(self):
        """Import game from PGN file"""
        file_path, _ = QFileDialog.getOpenFileName(self, "打开对局", "", "PGN Files (*.pgn);;All Files (*)")
        if not file_path:
            return
            
        if self.engine.is_thinking:
            self.engine.stop_thinking()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Basic parsing
            content = re.sub(r'\[.*?\]', '', content)
            content = re.sub(r'\{.*?\}', '', content)
            content = re.sub(r'\d+\.', '', content)
            
            moves = content.split()
            
            self._new_game()
            
            for move_str in moves:
                move_str = move_str.strip()
                if not move_str or move_str in ["*", "1-0", "0-1", "1/2-1/2"]:
                    continue
                
                # Try Chinese
                uci_move = self.board.chinese_to_move(move_str)
                
                if not uci_move:
                    # Try ICCS
                    uci_move = self.board.iccs_to_move(move_str)
                
                if not uci_move:
                    # Try UCI
                    if re.match(r'^[a-i]\d[a-i]\d$', move_str):
                        uci_move = move_str
                
                if uci_move:
                    if not self.board.make_move(uci_move):
                         QMessageBox.warning(self, "警告", f"非法走法: {move_str} ({uci_move})")
                         break
                else:
                    QMessageBox.warning(self, "警告", f"无法解析走法: {move_str}\n导入将在此时停止。")
                    break
            
            self.board_widget.set_board(self.board)
            self._rebuild_move_history_list()
            self._update_status()
            
            QMessageBox.information(self, "成功", "对局导入完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")

    def _show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        dialog.set_settings(self.settings)
        
        if dialog.exec_() == QDialog.Accepted:
            new_settings = dialog.get_settings()
            
            # Check if engine path changed
            if new_settings['engine_path'] != self.settings['engine_path'] and new_settings['engine_path']:
                self._start_engine(new_settings['engine_path'])
            
            # Check if threads changed
            if 'threads' in new_settings and new_settings['threads'] != self.settings.get('threads'):
                if self.engine.is_ready:
                    self.engine.set_option('Threads', new_settings['threads'])
            
            self.settings.update(new_settings)
            self.save_settings()
            self._update_status()
            self._check_engine_turn()
            
    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "关于", 
            "软件名称：xiangqi_pyqt\n"
            "软件版本：v1.0.1\n"
            "软件仓库：https://github.com/yanyuandaxia/xiangqi_pyqt\n"
            "作者：yanyuandaxia"
        )

    def _show_analysis_dialog(self):
        """Show analysis options dialog"""
        dialog = AnalysisOptionsDialog(self._realtime_analysis_enabled, self)
        dialog.load_clicked.connect(self._load_analysis_results)
        dialog.save_clicked.connect(self._save_analysis_results)

        if dialog.exec_() == QDialog.Accepted:
            if dialog.is_realtime_selected():
                self._enable_realtime_analysis()
            else:
                self._disable_realtime_analysis()
                self._start_analysis()

    def _show_pgn_dialog(self):
        """Show PGN dialog"""
        dialog = PgnDialog(self)
        
        # Set current format
        current_format = self.settings.get('pgn_format', 'Chinese')
        dialog.set_format(current_format)
        
        # Connect signals
        def update_format():
            self.settings['pgn_format'] = dialog.get_format()
            
        dialog.pgn_format.currentIndexChanged.connect(update_format)
        dialog.open_btn.clicked.connect(self._import_pgn)
        dialog.save_btn.clicked.connect(self._export_pgn)
        
        dialog.exec_()

    def _enable_realtime_analysis(self):
        """Enable realtime analysis mode"""
        if not self.engine.is_ready:
            QMessageBox.information(self, "提示", "引擎未连接，无法进行实时分析")
            return

        self._realtime_analysis_enabled = True
        self.analysis_chart.show()
        self.analysis_score_label.show()
        self.engine_info_label.setText("实时分析已开启")

        # Try to analyze the current position immediately if possible
        self._queue_realtime_analysis()

    def _disable_realtime_analysis(self):
        """Disable realtime analysis mode"""
        self._realtime_analysis_enabled = False
        self._cancel_realtime_analysis()

    def _queue_realtime_analysis(self):
        """Queue realtime analysis for the current position"""
        if self._suppress_engine_turn:
            return
        if not self._realtime_analysis_enabled:
            return
        if self._analysis_mode:
            return
        if not self.engine.is_ready:
            return
        if not self.board.move_history:
            return

        move_index = len(self.board.move_history) - 1
        fen = self.board.to_fen()

        # If engine is busy or we're in hint mode, just store as pending
        # Avoid duplicate queue for the same move
        if self._realtime_pending and self._realtime_pending[-1][1] == move_index:
            return

        self._realtime_pending.append((fen, move_index))

        if self.engine.is_thinking or self.hint_mode or self._realtime_analysis_active:
            return

        self._try_start_realtime_analysis()

    def _try_start_realtime_analysis(self):
        """Start realtime analysis if there is a pending request"""
        if self._suppress_engine_turn:
            return
        if not self._realtime_analysis_enabled:
            return
        if self._analysis_mode:
            return
        if self.engine.is_thinking or self.hint_mode or self._realtime_analysis_active:
            return
        if not self._realtime_pending:
            return

        fen, move_index = self._realtime_pending.pop(0)

        params = self._get_engine_go_params()
        if params is None:
            QMessageBox.warning(self, "错误", "思考时间和深度不能同时为0")
            return

        self._realtime_analysis_active = True
        self._realtime_move_index = move_index

        # Save original callbacks
        self._realtime_original_on_bestmove = self.engine.on_bestmove
        self._realtime_original_on_info = self.engine.on_info

        self.engine.on_bestmove = self._on_realtime_bestmove
        self.engine.on_info = self._on_realtime_info

        self.engine.set_position(fen=fen)
        self.engine.go(**params)

    def _on_realtime_info(self, info: EngineInfo):
        """Handle engine info during realtime analysis"""
        if self._realtime_analysis_active:
            self._realtime_last_score = info.score

    def _on_realtime_bestmove(self, move: str):
        """Handle bestmove during realtime analysis"""
        if not self._realtime_analysis_active:
            return

        score = getattr(self, '_realtime_last_score', 0)
        move_index = getattr(self, '_realtime_move_index', 0)
        score = self._normalize_analysis_score(score, move_index)
        self._set_analysis_score(move_index, score)

        self._finish_realtime_analysis()

    def _finish_realtime_analysis(self):
        """Finish realtime analysis and restore callbacks"""
        self._realtime_analysis_active = False

        if hasattr(self, '_realtime_original_on_bestmove'):
            self.engine.on_bestmove = self._realtime_original_on_bestmove
        if hasattr(self, '_realtime_original_on_info'):
            self.engine.on_info = self._realtime_original_on_info

        # If another analysis is pending, start it
        if self._realtime_pending:
            QTimer.singleShot(50, self._try_start_realtime_analysis)

    def _cancel_realtime_analysis(self):
        """Cancel realtime analysis if running"""
        if self._realtime_analysis_active and self.engine.is_thinking:
            self.engine.stop_thinking()

        if hasattr(self, '_realtime_original_on_bestmove'):
            self.engine.on_bestmove = self._realtime_original_on_bestmove
        if hasattr(self, '_realtime_original_on_info'):
            self.engine.on_info = self._realtime_original_on_info

        self._realtime_analysis_active = False
        self._realtime_pending = []

    def _normalize_analysis_score(self, score: int, move_index: int) -> int:
        """Normalize score so positive means red advantage"""
        if move_index % 2 == 0:
            return -score
        return score

    def _set_analysis_score(self, move_index: int, score: int):
        """Set analysis score for a specific move index"""
        if move_index < 0:
            return

        if move_index >= len(self._analysis_scores):
            missing = move_index - len(self._analysis_scores) + 1
            self._analysis_scores.extend([0] * missing)

        self._analysis_scores[move_index] = score
        self.analysis_chart.set_scores(self._analysis_scores)
        self.analysis_chart.show()
        self.analysis_score_label.show()

        current_index = len(self.board.move_history) - 1
        if current_index >= 0:
            self.analysis_chart.highlight_move(current_index)

    def _save_analysis_results(self):
        """Save analysis results to a JSON file"""
        if not self._analysis_scores:
            QMessageBox.information(self, "提示", "没有可存储的分析结果")
            return

        default_name = f"analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.analysis.json"
        default_path = os.path.join(get_user_data_path(), default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存分析结果",
            default_path,
            "分析结果 (*.analysis.json);;JSON (*.json);;所有文件 (*)"
        )
        if not file_path:
            return

        data = {
            "version": 1,
            "created_at": datetime.datetime.now().isoformat(),
            "moves": list(self.board.move_history),
            "scores": list(self._analysis_scores),
            "pgn_format": self.settings.get('pgn_format'),
            "pgn": self._build_pgn_text()
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"存储分析结果失败: {str(e)}")

    def _load_analysis_results(self):
        """Load analysis results from a JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "读取分析结果",
            get_user_data_path(),
            "分析结果 (*.analysis.json);;JSON (*.json);;所有文件 (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"读取分析结果失败: {str(e)}")
            return

        scores = data.get("scores", [])
        moves = data.get("moves", [])
        if not isinstance(scores, list):
            QMessageBox.warning(self, "错误", "分析结果格式不正确")
            return

        if moves and list(self.board.move_history) != list(moves):
            result = QMessageBox.question(
                self,
                "提示",
                "分析记录包含对局记录，是否加载该对局记录？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if result == QMessageBox.Yes:
                self._new_game()
                for move in moves:
                    if not self.board.make_move(move):
                        QMessageBox.warning(self, "警告", f"对局记录中存在非法走法: {move}\n加载将提前结束。")
                        break

                self.board_widget.set_board(self.board)
                self._rebuild_move_history_list()
                self._update_status()

        self._analysis_scores = scores
        self.analysis_chart.set_scores(self._analysis_scores)
        self.analysis_chart.show()
        self.analysis_score_label.show()

        current_index = len(self.board.move_history) - 1
        if current_index >= 0:
            self.analysis_chart.highlight_move(current_index)
            
    def load_settings(self):
        """Load settings from JSON file"""
        try:
            settings_path = get_settings_path()
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convert string back to Enum (value is the Chinese string)
                if 'red_player' in data:
                    data['red_player'] = PlayerType(data['red_player'])
                if 'black_player' in data:
                    data['black_player'] = PlayerType(data['black_player'])
                
                self.settings.update(data)
            
            # 如果没有设置引擎路径，使用默认引擎
            if not self.settings['engine_path']:
                default_engine = get_default_engine_path()
                if default_engine:
                    self.settings['engine_path'] = default_engine
            
            # Auto start engine if path is set
            if self.settings['engine_path']:
                self._start_engine(self.settings['engine_path'])
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        """Save settings to JSON file"""
        try:
            # Convert Enum to string (value) for JSON serialization
            data = self.settings.copy()
            data['red_player'] = data['red_player'].value
            data['black_player'] = data['black_player'].value
            
            settings_path = get_settings_path()
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存设置失败: {str(e)}")
    
    def _start_engine(self, path: str):
        """Start the chess engine"""
        self.engine.stop()
        
        # 转换引擎路径（处理打包后的相对路径）
        actual_path = get_engine_path(path)
        
        if self.engine.start(actual_path):
            self.engine_info_label.setText("引擎: 正在初始化...")
            self._set_engine_status("引擎：正在初始化")
        else:
            QMessageBox.warning(self, "错误", f"无法启动引擎:\n{actual_path}")
            self.engine_info_label.setText("引擎: 启动失败")
            self._set_engine_status("引擎：启动失败")
    
    def _on_engine_ready(self):
        """Called when engine is ready"""
        # Prevent handling if in analysis mode
        if hasattr(self, '_analysis_mode') and self._analysis_mode:
            return
        
        # If engine was stopped, don't restart
        if self._suppress_engine_turn:
            self._set_engine_status("引擎：已停止")
            return

        # Apply settings
        if 'threads' in self.settings:
            self.engine.set_option('Threads', self.settings['threads'])
            
        # 如果正在显示提示结果，不覆盖
        if self.showing_hint_result and self.hint_info_text:
            return
        self.engine_info_label.setText("引擎: 就绪")
        self._set_engine_status("引擎：就绪")
        self.engine.new_game()
        
        # Check if both sides are engines - require manual start
        both_engines = (self.settings['red_player'] == PlayerType.ENGINE and 
                       self.settings['black_player'] == PlayerType.ENGINE)
        if both_engines:
            self._suppress_engine_turn = True
        
        self._check_engine_turn()
    
    def _on_player_move(self, move: str):
        """Called when player makes a move"""
        # Disable interaction immediately to prevent double moves while checking turn
        self.board_widget.interaction_enabled = False

        # Clear suppression after player makes a move
        self._suppress_engine_turn = False
        
        self.redo_stack.clear() # Clear redo stack
        self._prune_analysis_after_current()
        self.edited_position = False  # Reset edited position flag after a move
        
        # Clear hint when player makes a move
        self.board_widget.hint_move = None
        self.showing_hint_result = False
        self.hint_info_text = ""
        
        self._rebuild_move_history_list()
        
        self._update_status()
        self._update_clock()
        self._check_game_result()
        self._check_engine_turn()

        # Realtime analysis after a move
        self._queue_realtime_analysis()
    
    def _get_chinese_move(self, move: str) -> str:
        """Convert UCI move to Chinese notation using position history"""
        if not self.board.position_history:
            return move
        
        # Create a temporary board with the position before the move
        temp_board = ChessBoard()
        temp_board.board = self.board.position_history[-1]  # Last saved position
        return self.board.move_to_chinese(move, temp_board)

    def _prune_analysis_after_current(self):
        """Trim analysis scores when future moves are deleted"""
        max_len = len(self.board.move_history)
        if len(self._analysis_scores) > max_len:
            self._analysis_scores = self._analysis_scores[:max_len]
            self.analysis_chart.set_scores(self._analysis_scores)

        # Remove queued realtime analysis beyond current move count
        if self._realtime_pending:
            self._realtime_pending = [
                (fen, idx) for (fen, idx) in self._realtime_pending if idx < max_len
            ]

        # Cancel current realtime analysis if it targets a removed move
        if self._realtime_analysis_active:
            current_idx = getattr(self, '_realtime_move_index', -1)
            if current_idx >= max_len:
                self._cancel_realtime_analysis()
    
    def _check_engine_turn(self):
        """Check if it's engine's turn and start thinking"""
        # Don't start engine if in edit mode
        if self.board_widget.edit_mode:
            return
            
        # Check if game is over (checkmate, stalemate, or draw)
        if self._is_game_over():
            self.board_widget.interaction_enabled = False
            return
        
        current_player = self.settings['red_player'] if self.board.current_side == Side.RED else self.settings['black_player']
        
        if current_player == PlayerType.ENGINE:
            if self._suppress_engine_turn:
                self.board_widget.interaction_enabled = True
                return
            self.board_widget.interaction_enabled = False
            if self.engine.is_ready and not self.engine.is_thinking:
                # 清除提示状态，因为轮到引擎走棋了
                self.showing_hint_result = False
                self.hint_info_text = ""
                # Set position using FEN (works for both normal games and edited positions)
                fen = self.board.to_fen()
                self.engine.set_position(fen=fen)
                
                params = self._get_engine_go_params()
                if params is None:
                    # Invalid settings, warn user once if possible, or print to status
                    self.engine_info_label.setText("错误: 思考时间和深度不能同时为0")
                    return
                
                self.engine.go(**params)
                self._update_status()
        else:
            self.board_widget.interaction_enabled = True
    
    def _request_hint(self):
        """Request a move hint from the engine"""
        if not self.engine.is_ready:
            QMessageBox.information(self, "提示", "引擎未连接")
            return
        
        if self._suppress_engine_turn:
            QMessageBox.information(self, "提示", "引擎已停止，请点击开始后再请求提示")
            return
        
        if self.engine.is_thinking:
            QMessageBox.information(self, "提示", "引擎正在思考中...")
            return
        
        if self._is_game_over() and not self.edited_position:
            QMessageBox.information(self, "提示", "游戏已结束")
            return
        
        # Clear previous hint
        self.board_widget.hint_move = None
        self.showing_hint_result = False
        self.hint_info_text = ""
        
        # Set hint mode and request move
        self.hint_mode = True
        self.hint_btn.setEnabled(False)
        self.hint_btn.setText("思考中...")
        self.board_widget.interaction_enabled = False # Disable board while thinking
        
        fen = self.board.to_fen()
        self.engine.set_position(fen=fen)
        
        params = self._get_engine_go_params()
        if params is None:
            QMessageBox.warning(self, "错误", "思考时间和深度不能同时为0")
            self.hint_mode = False
            self.hint_btn.setEnabled(True)
            self.hint_btn.setText("提示")
            self.board_widget.interaction_enabled = True
            return
        
        self.engine.go(**params)
    
    def _on_engine_move(self, move: str):
        """Called when engine returns a move"""
        # If engine was stopped, ignore this move
        if self._suppress_engine_turn:
            self._set_engine_status("引擎：已停止")
            self.board_widget.interaction_enabled = True
            return
            
        if self.hint_mode:
            # Hint mode: display the move on board, don't execute
            self.hint_mode = False
            self.board_widget.interaction_enabled = True # Re-enable board
            self.showing_hint_result = True
            self.hint_btn.setEnabled(True)
            self.hint_btn.setText("提示")

            # Hint finished, update engine status
            self._set_engine_status("引擎：就绪")
            
            coords = ChessBoard.parse_move(move)
            if coords:
                self.board_widget.hint_move = coords
                self.board_widget.update()
                
                # Show hint in Chinese notation
                chinese_move = self.board.move_to_chinese(move)
                
                score_info = ""
                if hasattr(self, 'last_engine_score_str'):
                    score_info = f" (分数: {self.last_engine_score_str})"
                
                self.hint_info_text = f"建议走法: {chinese_move}{score_info}"
                self.engine_info_label.setText(self.hint_info_text)

            # Show PV under move history
            if hasattr(self, 'pv_label'):
                if self._last_pv_text:
                    self.pv_label.setText(f"主变: {self._last_pv_text}")
                else:
                    self.pv_label.setText("")
            return
        
        # Normal mode: execute the move
        if self.board.make_move(move):
            self.redo_stack.clear() # Clear redo stack
            self._prune_analysis_after_current()
            self.edited_position = False  # Reset edited position flag after engine move
            self.board_widget.set_board(self.board)
            self.board_widget.set_last_move(move)
            
            # Clear hint when a move is made
            self.board_widget.hint_move = None
            self.showing_hint_result = False
            self.hint_info_text = ""
            
            # Clear excluded moves on successful move
            if hasattr(self, '_excluded_moves'):
                self._excluded_moves = []
            
            self._rebuild_move_history_list()
            
            self._update_status()
            self._update_clock()
            self._check_game_result()
            
            # Reset engine info label
            self.engine_info_label.setText("引擎: 就绪")
            self._set_engine_status("引擎：就绪")

            # Realtime analysis after engine move
            self._queue_realtime_analysis()
            
            # Check if next turn is also engine
            QTimer.singleShot(100, self._check_engine_turn)

            # Apply any pending navigation after engine finishes
            if self._pending_goto_move is not None:
                pending = self._pending_goto_move
                self._pending_goto_move = None
                QTimer.singleShot(0, lambda: self._goto_move(pending))
        else:
            # Move was rejected (likely due to perpetual check rule)
            # Try to find an alternative move from the candidate list
            candidates = self.engine.get_candidate_moves()
            
            # Find the first valid alternative move
            found_alternative = False
            for alt_move in candidates:
                if alt_move != move:  # Skip the rejected move
                    if self.board.make_move(alt_move):
                        # Found a valid alternative
                        found_alternative = True
                        self.engine_info_label.setText(f"走法 {move} 违反规则，改走 {alt_move}")
                        
                        self.redo_stack.clear()
                        self._prune_analysis_after_current()
                        self.edited_position = False
                        self.board_widget.set_board(self.board)
                        self.board_widget.set_last_move(alt_move)
                        
                        self.board_widget.hint_move = None
                        self.showing_hint_result = False
                        self.hint_info_text = ""
                        
                        self._rebuild_move_history_list()
                        self._update_status()
                        self._update_clock()
                        self._check_game_result()

                        self._queue_realtime_analysis()
                        
                        QTimer.singleShot(100, self._check_engine_turn)

                        if self._pending_goto_move is not None:
                            pending = self._pending_goto_move
                            self._pending_goto_move = None
                            QTimer.singleShot(0, lambda: self._goto_move(pending))
                        break
            
            if not found_alternative:
                # No valid alternative found - try all legal moves as last resort
                all_moves = self.board.get_all_legal_moves()
                for alt_move in all_moves:
                    if alt_move != move:
                        if self.board.make_move(alt_move):
                            found_alternative = True
                            self.engine_info_label.setText(f"走法 {move} 违反规则，强制变招 {alt_move}")
                            
                            self.redo_stack.clear()
                            self.edited_position = False
                            self.board_widget.set_board(self.board)
                            self.board_widget.set_last_move(alt_move)
                            
                            self._rebuild_move_history_list()
                            self._update_status()
                            self._update_clock()
                            self._check_game_result()
                            
                            QTimer.singleShot(100, self._check_engine_turn)
                            break
            
            if not found_alternative:
                # No valid moves at all - this side loses
                self.engine_info_label.setText("无有效走法，长将方判负")
                self._update_status()
    
    def _is_game_over(self) -> bool:
        """Check if the game has ended"""
        return (self.board.is_checkmate() or 
                self.board.is_stalemate() or 
                self.board.is_draw())
    
    def _check_game_result(self):
        """Check if game has ended and display result in move history"""
        if self.board.is_checkmate():
            # The current side is the one who lost (they are checkmated)
            if self.board.current_side == Side.RED:
                self.move_history.set_result("黑方胜", "black")
            else:
                self.move_history.set_result("红方胜", "red")
        elif self.board.is_stalemate():
            # Current side has no legal moves but is not in check
            if self.board.current_side == Side.RED:
                self.move_history.set_result("黑方胜 (困毙)", "black")
            else:
                self.move_history.set_result("红方胜 (困毙)", "red")
        elif self.board.is_draw():
            can_draw, reason = self.board.can_claim_draw()
            self.move_history.set_result(f"和棋 ({reason})", "")
            # Stop engine if both sides are engines
            if self.engine.is_thinking:
                self.engine.stop_thinking()
    
    def _resume_engine(self):
        """Resume engine thinking after being stopped"""
        # Clear the suppress flag to allow engine to think again
        self._suppress_engine_turn = False
        
        # Check if game is over
        if self._is_game_over():
            return
        
        # Trigger engine turn check
        self._check_engine_turn()
    
    def _stop_engine(self):
        """Stop engine thinking and prevent auto-play in engine vs engine mode"""
        # Set flag to suppress engine auto-turn (prevents engine vs engine from continuing)
        self._suppress_engine_turn = True
        
        # Always try to stop engine thinking (unconditionally)
        self.engine.stop_thinking()
        self._set_engine_status("引擎：已停止")
        
        # Cancel hint mode
        if self.hint_mode:
            self.hint_mode = False
            self.showing_hint_result = False
            self.hint_info_text = ""
            self.board_widget.hint_move = None
        
        # Also cancel any ongoing analysis
        if hasattr(self, '_analysis_mode') and self._analysis_mode:
            self._cancel_analysis()
        
        # Cancel realtime analysis if active
        self._cancel_realtime_analysis()
        
        # Enable board interaction so user can make moves
        self.board_widget.interaction_enabled = True
        
        # Update status to reflect stopped state
        self._update_status()
    
    def _propose_draw(self):
        """Propose a draw"""
        # Check if game has already ended
        if self.board.is_checkmate() or self.board.is_stalemate():
            QMessageBox.information(self, "提示", "游戏已结束")
            return
        
        # Check if there's a valid reason for draw
        can_draw, reason = self.board.can_claim_draw()
        
        if can_draw:
            # Automatic draw claim
            reply = QMessageBox.question(
                self, "提和",
                f"满足和棋条件: {reason}\n是否确认和棋?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.move_history.set_result(f"和棋 ({reason})", "")
                self._update_status()
                # Stop engine if thinking
                if self.engine.is_thinking:
                    self.engine.stop_thinking()
        else:
            # Check if opponent is engine or human
            current_player = self.settings['red_player'] if self.board.current_side == Side.RED else self.settings['black_player']
            opponent_player = self.settings['black_player'] if self.board.current_side == Side.RED else self.settings['red_player']
            
            if opponent_player == PlayerType.ENGINE:
                # Engine usually doesn't accept draws without valid reason
                QMessageBox.information(self, "提和", "引擎拒绝和棋请求")
            else:
                # Ask the other human player
                opponent = "黑方" if self.board.current_side == Side.RED else "红方"
                reply = QMessageBox.question(
                    self, "提和",
                    f"{opponent}是否接受和棋?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.move_history.set_result("和棋 (协议)", "")
                    self._update_status()
                    if self.engine.is_thinking:
                        self.engine.stop_thinking()
    
    def _resign_game(self):
        """Resign the game"""
        if self._is_game_over():
            QMessageBox.information(self, "认输", "游戏已结束")
            return
            
        reply = QMessageBox.question(
            self, "认输",
            "确定要认输吗?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Current side loses
            if self.board.current_side == Side.RED:
                self.move_history.set_result("黑方胜 (认输)", "black")
            else:
                self.move_history.set_result("红方胜 (认输)", "red")
                
            self._update_status()
            
            # Stop engine if thinking
            if self.engine.is_thinking:
                self.engine.stop_thinking()
    
    def _on_engine_info(self, info: EngineInfo):
        """Called when engine sends info"""
        # If engine was stopped, ignore info messages
        if self._suppress_engine_turn:
            return
            
        # If engine is not thinking, ignore info messages
        # This prevents delayed info packets from overwriting "Engine Ready" status
        if not self.engine.is_thinking:
            return

        # Save score for potential use (hint etc.) - update this regardless of throttling
        self.last_engine_score_cp = info.score
        score_str = f"{info.score / 100:.2f}"
        self.last_engine_score_str = score_str
        
        # Limit UI update frequency to reduce flickering (every 200ms)
        current_time = time.time()
        if hasattr(self, '_last_info_update_time'):
            if current_time - self._last_info_update_time < 0.2:
                return
        self._last_info_update_time = current_time

        # Update win rate bar based on engine WDL (Win/Draw/Loss) data
        # Note: WDL is from the perspective of the side to move
        # We need to convert it to red's perspective
        # Only update if WDL data was actually parsed (not default values)
        if info.wdl_valid:
            win, draw, loss = info.wdl
            if self.board.current_side == Side.RED:
                # Red's view: win=red wins, loss=black wins
                self.win_rate_bar.set_wdl(win, draw, loss)
            else:
                # Black's view: win=black wins, loss=red wins
                # Swap win and loss for red's perspective
                self.win_rate_bar.set_wdl(loss, draw, win)
        
        lines = []
        status_parts = ["引擎：思考中"]

        if info.nps > 0:
            lines.extend([
                f"深度: {info.depth}",
                f"分数: {score_str}",
                f"速度: {info.nps // 1000}k 节点/秒"
            ])
            status_parts.extend([
                f"深度 {info.depth}",
                f"分数 {score_str}",
                f"速度 {info.nps // 1000}k"
            ])
        else:
            lines.append(f"分数: {score_str}")
            status_parts.append(f"分数 {score_str}")
            
        if info.pv:
            try:
                # Convert PV to Chinese notation
                temp_board = self.board.copy()
                pv_moves = info.pv.split()
                # Limit to 3 moves to keep it readable
                pv_moves_short = pv_moves[:3]
                chinese_pv = []
                
                for move in pv_moves_short:
                    cn_move = temp_board.move_to_chinese(move)
                    chinese_pv.append(cn_move)
                    # Make move on temp board to update state for next move notation
                    temp_board.make_move(move)
                
                pv_text = " ".join(chinese_pv)
                lines.append(f"主变: {pv_text}")
                status_parts.append(f"主变 {pv_text}")
                self._last_pv_text = pv_text
            except Exception:
                # Fallback to simple string if conversion fails（e.g. invalid PV）
                pv_short = " ".join(info.pv.split()[:3])
                lines.append(f"主变: {pv_short}")
                status_parts.append(f"主变 {pv_short}")
                self._last_pv_text = pv_short

        self._set_engine_status(" ".join(status_parts))

        # 如果正在显示提示结果，保持提示信息不变
        if self.showing_hint_result:
            if self.hint_info_text:
                self.engine_info_label.setText(self.hint_info_text)
            return

        self.engine_info_label.setText("引擎:\n" + "\n".join(lines))
    
    def _start_analysis(self):
        """Start analyzing all moves in the game history"""
        if not self.engine.is_ready:
            QMessageBox.information(self, "提示", "引擎未连接，无法进行分析")
            return
        
        if self.engine.is_thinking:
            QMessageBox.information(self, "提示", "引擎正在思考中，请稍后再试")
            return
        
        if not self.board.move_history and not self.redo_stack:
            QMessageBox.information(self, "提示", "没有可分析的走法")
            return

        # Disable realtime analysis when running full game analysis
        self._disable_realtime_analysis()
        
        # Stop any ongoing operations
        if self.engine.is_thinking:
            self.engine.stop_thinking()
            
        # Stop clock during analysis
        self.clock_widget.stop_timing()
        
        # Setup analysis state
        self._analysis_mode = True
        self._analysis_scores = []
        self._analysis_positions = []
        self._analysis_current_index = 0
        
        # Build list of all positions to analyze
        temp_board = ChessBoard()
        
        # Add starting position
        self._analysis_positions.append(temp_board.to_fen())
        
        # Collect all moves (current history + redo stack in order)
        all_moves = list(self.board.move_history)
        for move in reversed(self.redo_stack):
            all_moves.append(move)
        
        # Apply moves and collect positions
        for move in all_moves:
            temp_board.make_move(move)
            self._analysis_positions.append(temp_board.to_fen())
        
        # We analyze positions after each move (so skip starting position)
        # Actually, analyze positions 0 to len(all_moves)-1 which correspond to
        # the positions BEFORE each move was made, to evaluate that move
        # Let's analyze positions after each move instead
        self._analysis_positions = self._analysis_positions[1:]  # Skip starting position
        
        if not self._analysis_positions:
            QMessageBox.information(self, "提示", "没有可分析的走法")
            return
        
        # Save original callbacks
        self._original_on_bestmove = self.engine.on_bestmove
        self._original_on_info = self.engine.on_info
        
        # Set analysis callbacks
        self.engine.on_bestmove = self._on_analysis_bestmove
        self.engine.on_info = self._on_analysis_info
        
        # Clear and show analysis chart
        self.analysis_chart.clear()
        self.analysis_chart.show()
        self.analysis_score_label.show()
        
        # Update status
        self._set_engine_status(f"分析中 (0/{len(self._analysis_positions)})")
        
        # Start analyzing first position
        self._analyze_next_position()
    
    def _analyze_next_position(self):
        """Analyze the next position in the queue"""
        if not hasattr(self, '_analysis_mode') or not self._analysis_mode:
            return
        
        if self._analysis_current_index >= len(self._analysis_positions):
            # Analysis complete
            self._finish_analysis()
            return
        
        fen = self._analysis_positions[self._analysis_current_index]
        
        # Set position and start analysis
        self.engine.set_position(fen=fen)
        
        # Use settings for analysis
        params = self._get_engine_go_params()
        if params is None:
            QMessageBox.warning(self, "错误", "思考时间和深度不能同时为0")
            self._finish_analysis()
            return

        self.engine.go(**params)
        
        # Update progress
        progress = self._analysis_current_index + 1
        total = len(self._analysis_positions)
        self._set_engine_status(f"分析中 ({progress}/{total})")
    
    def _on_analysis_info(self, info: EngineInfo):
        """Handle engine info during analysis"""
        # Store the latest score for this position (raw score from engine)
        if hasattr(self, '_analysis_mode') and self._analysis_mode:
            self._analysis_last_score = info.score
    
    def _on_analysis_bestmove(self, move: str):
        """Handle bestmove during analysis - move to next position"""
        if not hasattr(self, '_analysis_mode') or not self._analysis_mode:
            return
        
        # Record the score for this position
        score = getattr(self, '_analysis_last_score', 0)
        
        # Adjust score: we want positive = red advantage, negative = black advantage
        # The engine reports score from the perspective of the side to move
        # 
        # We analyze positions AFTER each move:
        # - Index 0 = after red's 1st move → it's black's turn → engine gives black's perspective → NEGATE
        # - Index 1 = after black's 1st move → it's red's turn → engine gives red's perspective → OK
        # - Index 2 = after red's 2nd move → it's black's turn → engine gives black's perspective → NEGATE
        # 
        # Rule: even indices need negation, odd indices don't
        if self._analysis_current_index % 2 == 0:
            # After red's move, engine reports from black's perspective, negate it
            score = -score
        
        self._analysis_scores.append(score)
        
        # Update chart
        self.analysis_chart.set_scores(self._analysis_scores)
        
        # Move to next position
        self._analysis_current_index += 1
        
        # Use QTimer to avoid blocking
        QTimer.singleShot(50, self._analyze_next_position)
    
    def _finish_analysis(self):
        """Finish the analysis and restore normal operation"""
        self._analysis_mode = False
        
        # Restore original callbacks
        if hasattr(self, '_original_on_bestmove'):
            self.engine.on_bestmove = self._original_on_bestmove
        if hasattr(self, '_original_on_info'):
            self.engine.on_info = self._original_on_info
        
        # Update status
        total_moves = len(self._analysis_scores)
        self._set_engine_status(f"分析完成: {total_moves} 步")
        
        # Highlight current move in chart
        current_index = len(self.board.move_history) - 1
        if current_index >= 0:
            self.analysis_chart.highlight_move(current_index)
        
        self._update_status()
    
    def _cancel_analysis(self):
        """Cancel ongoing analysis"""
        if hasattr(self, '_analysis_mode') and self._analysis_mode:
            self._analysis_mode = False
            
            if self.engine.is_thinking:
                self.engine.stop_thinking()
            
            # Restore original callbacks
            if hasattr(self, '_original_on_bestmove'):
                self.engine.on_bestmove = self._original_on_bestmove
            if hasattr(self, '_original_on_info'):
                self.engine.on_info = self._original_on_info
            
            self.engine_info_label.setText("分析已取消")
    
    def closeEvent(self, event):
        """Handle window close"""
        # Cancel any ongoing analysis
        if hasattr(self, '_analysis_mode') and self._analysis_mode:
            self._cancel_analysis()

        self._cancel_realtime_analysis()
        
        self.engine.stop()
        event.accept()

