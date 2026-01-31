#!/usr/bin/env python3
"""
UCI Engine Interface for Xiangqi (Xiangqi)
Handles communication with UCI-compatible engines like Pikafish
"""

import subprocess
import threading
import queue
import os
from typing import Optional, Callable
from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSignal
from resource_path import get_base_path


@dataclass
class EngineInfo:
    """Engine search information"""
    depth: int = 0
    score: int = 0
    pv: str = ""
    nodes: int = 0
    nps: int = 0
    time: int = 0
    # WDL (Win/Draw/Loss) in per mille (0-1000 each)
    wdl: tuple = (0, 1000, 0)  # Default to draw (0% win, 100% draw, 0% loss)
    wdl_valid: bool = False  # True if WDL was actually parsed from engine output


class UCIEngine(QObject):
    """UCI Engine communication handler
    
    Uses Qt signals to safely communicate engine events to the main thread.
    """
    
    # Signals for thread-safe communication with Qt main thread
    bestmove_signal = pyqtSignal(str)
    info_signal = pyqtSignal(object)  # EngineInfo
    ready_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process: Optional[subprocess.Popen] = None
        self.engine_path: str = ""
        self.is_ready: bool = False
        self.is_thinking: bool = False
        
        self._output_queue: queue.Queue = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Callbacks (connected via signals for thread-safety)
        self.on_bestmove: Optional[Callable[[str], None]] = None
        self.on_info: Optional[Callable[[EngineInfo], None]] = None
        self.on_ready: Optional[Callable[[], None]] = None
        
        # Store candidate moves from search (first move of each PV line at max depth)
        self._candidate_moves: list[str] = []
        self._current_depth: int = 0
        
        # Connect signals to internal dispatch methods
        self.bestmove_signal.connect(self._dispatch_bestmove)
        self.info_signal.connect(self._dispatch_info)
        self.ready_signal.connect(self._dispatch_ready)
    
    def _dispatch_bestmove(self, move: str):
        """Called in main thread when bestmove is received"""
        if self.on_bestmove:
            self.on_bestmove(move)
    
    def _dispatch_info(self, info: EngineInfo):
        """Called in main thread when info is received"""
        if self.on_info:
            self.on_info(info)
    
    def _dispatch_ready(self):
        """Called in main thread when engine is ready"""
        if self.on_ready:
            self.on_ready()
    
    def start(self, engine_path: str) -> bool:
        """Start the engine process"""
        self.stop()
        self.engine_path = engine_path
        
        try:
            # 设置工作目录为资源基础目录，以便引擎找到 NNUE 文件
            working_dir = get_base_path()
            
            self.process = subprocess.Popen(
                [engine_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=working_dir
            )
        except (FileNotFoundError, PermissionError) as e:
            print(f"Failed to start engine: {e}")
            return False
        
        self._stop_event.clear()
        self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self._reader_thread.start()
        
        # Initialize UCI
        self._send_command("uci")
        return True
    
    def stop(self):
        """Stop the engine process"""
        if self.process:
            self._stop_event.set()
            self._send_command("quit")
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        self.is_ready = False
        self.is_thinking = False
    
    def _send_command(self, command: str):
        """Send a command to the engine"""
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
    
    def _read_output(self):
        """Read engine output in a separate thread"""
        while not self._stop_event.is_set() and self.process:
            try:
                if self.process.stdout:
                    line = self.process.stdout.readline()
                    if line:
                        self._parse_output(line.strip())
                    elif self.process.poll() is not None:
                        break
            except Exception:
                break
    
    def _parse_output(self, line: str):
        """Parse engine output (called from reader thread)"""
        if not line:
            return
        
        tokens = line.split()
        if not tokens:
            return
        
        if tokens[0] == "uciok":
            # Enable WDL output for win rate display
            self._send_command("setoption name UCI_ShowWDL value true")
            self._send_command("isready")
        
        elif tokens[0] == "readyok":
            self.is_ready = True
            # Emit signal to call callback in main thread
            self.ready_signal.emit()
        
        elif tokens[0] == "bestmove":
            self.is_thinking = False
            if len(tokens) >= 2:
                # Emit signal to call callback in main thread
                self.bestmove_signal.emit(tokens[1])
        
        elif tokens[0] == "info":
            info = self._parse_info(tokens[1:])
            
            # Collect candidate moves from PV lines
            if info.pv and info.depth > 0:
                pv_moves = info.pv.split()
                if pv_moves:
                    first_move = pv_moves[0]
                    # If depth increased, start fresh candidate list
                    if info.depth > self._current_depth:
                        self._current_depth = info.depth
                        self._candidate_moves = [first_move]
                    elif info.depth == self._current_depth:
                        # Same depth, add to candidates if not already present
                        if first_move not in self._candidate_moves:
                            self._candidate_moves.append(first_move)
            
            # Emit signal to call callback in main thread
            self.info_signal.emit(info)
    
    def _parse_info(self, tokens: list) -> EngineInfo:
        """Parse info line from engine"""
        info = EngineInfo()
        i = 0
        while i < len(tokens):
            if tokens[i] == "depth" and i + 1 < len(tokens):
                try:
                    info.depth = int(tokens[i + 1])
                except ValueError:
                    pass
                i += 2
            elif tokens[i] == "score" and i + 2 < len(tokens):
                if tokens[i + 1] == "cp":
                    try:
                        info.score = int(tokens[i + 2])
                    except ValueError:
                        pass
                elif tokens[i + 1] == "mate":
                    try:
                        mate_in = int(tokens[i + 2])
                        info.score = 30000 if mate_in > 0 else -30000
                    except ValueError:
                        pass
                i += 3
            elif tokens[i] == "wdl" and i + 3 < len(tokens):
                # Parse WDL (Win/Draw/Loss) in per mille
                try:
                    win = int(tokens[i + 1])
                    draw = int(tokens[i + 2])
                    loss = int(tokens[i + 3])
                    info.wdl = (win, draw, loss)
                    info.wdl_valid = True
                except ValueError:
                    pass
                i += 4
            elif tokens[i] == "nodes" and i + 1 < len(tokens):
                try:
                    info.nodes = int(tokens[i + 1])
                except ValueError:
                    pass
                i += 2
            elif tokens[i] == "nps" and i + 1 < len(tokens):
                try:
                    info.nps = int(tokens[i + 1])
                except ValueError:
                    pass
                i += 2
            elif tokens[i] == "time" and i + 1 < len(tokens):
                try:
                    info.time = int(tokens[i + 1])
                except ValueError:
                    pass
                i += 2
            elif tokens[i] == "pv":
                info.pv = " ".join(tokens[i + 1:])
                break
            else:
                i += 1
        return info
    
    def new_game(self):
        """Start a new game"""
        if self.is_ready:
            self._send_command("ucinewgame")
            self._send_command("isready")
    
    def set_position(self, fen: str = "", moves: list[str] = None):
        """Set position using FEN and/or moves"""
        if not self.is_ready:
            return
        
        if fen:
            cmd = f"position fen {fen}"
        else:
            cmd = "position startpos"
        
        if moves:
            cmd += " moves " + " ".join(moves)
        
        self._send_command(cmd)
    
    def go(self, depth: int = None, movetime: int = None, infinite: bool = False, searchmoves: list = None):
        """Start searching for the best move
        
        Args:
            depth: Search to this depth
            movetime: Search for this many milliseconds
            infinite: Search until stopped
            searchmoves: Optional list of moves to search (UCI format)
        """
        if not self.is_ready or self.is_thinking:
            return
        
        # Clear candidate moves for new search
        self._candidate_moves = []
        self._current_depth = 0
        
        self.is_thinking = True
        cmd = "go"
        
        # Add searchmoves if specified (must come first according to UCI spec)
        if searchmoves:
            cmd += " searchmoves " + " ".join(searchmoves)
        
        if infinite:
            cmd += " infinite"
        else:
            has_condition = False
            if depth:
                cmd += f" depth {depth}"
                has_condition = True
            if movetime:
                cmd += f" movetime {movetime}"
                has_condition = True
            
            if not has_condition:
                cmd += " movetime 2000"  # Default 2 seconds
        
        self._send_command(cmd)
    
    def stop_thinking(self):
        """Stop the current search"""
        if self.is_thinking:
            self._send_command("stop")
    
    def set_option(self, name: str, value: str):
        """Set engine option"""
        self._send_command(f"setoption name {name} value {value}")
    
    def get_candidate_moves(self) -> list[str]:
        """Get the list of candidate moves from the last search
        
        Returns a list of candidate moves collected during the search,
        ordered by when they were first seen at the maximum depth.
        """
        return self._candidate_moves.copy()
