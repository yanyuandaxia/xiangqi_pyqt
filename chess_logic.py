#!/usr/bin/env python3
"""
Xiangqi (Xiangqi) Board Logic Module
Handles board state, move validation, and FEN parsing
"""

from typing import Optional
from dataclasses import dataclass
from enum import Enum
import copy


class PieceType(Enum):
    KING = 'k'      # 将/帅
    ADVISOR = 'a'   # 士/仕
    BISHOP = 'b'    # 象/相
    ROOK = 'r'      # 车
    KNIGHT = 'n'    # 马
    CANNON = 'c'    # 炮
    PAWN = 'p'      # 卒/兵


class Side(Enum):
    RED = 0
    BLACK = 1


@dataclass
class Piece:
    type: PieceType
    side: Side
    
    def to_char(self) -> str:
        """Convert piece to FEN character"""
        char = self.type.value
        return char.upper() if self.side == Side.RED else char.lower()
    
    def to_chinese(self) -> str:
        """Convert piece to Chinese character"""
        chinese_names = {
            PieceType.KING: ('帅', '将'),
            PieceType.ADVISOR: ('仕', '士'),
            PieceType.BISHOP: ('相', '象'),
            PieceType.ROOK: ('车', '車'),
            PieceType.KNIGHT: ('马', '馬'),
            PieceType.CANNON: ('炮', '砲'),
            PieceType.PAWN: ('兵', '卒'),
        }
        return chinese_names[self.type][self.side.value]
    
    @staticmethod
    def from_char(char: str) -> Optional['Piece']:
        """Create piece from FEN character"""
        if not char or char.isdigit():
            return None
        
        side = Side.RED if char.isupper() else Side.BLACK
        char_lower = char.lower()
        
        for pt in PieceType:
            if pt.value == char_lower:
                return Piece(pt, side)
        return None


# Starting position FEN for Xiangqi
STARTING_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"


class ChessBoard:
    """Xiangqi board state and logic"""
    
    # Board dimensions: 9 files (a-i), 10 ranks (0-9)
    FILES = 9
    RANKS = 10
    
    def __init__(self):
        # board[rank][file], rank 0 is at bottom (Red side)
        self.board: list[list[Optional[Piece]]] = [[None] * self.FILES for _ in range(self.RANKS)]
        self.current_side: Side = Side.RED
        self.move_history: list[str] = []
        self.position_history: list[list[list[Optional[Piece]]]] = []
        self.check_history: list[tuple[str, bool]] = []  # (position_key, is_check) for perpetual check detection
        self.halfmove_clock: int = 0
        self.fullmove_number: int = 1
        
        self.load_fen(STARTING_FEN)
    
    def copy(self) -> 'ChessBoard':
        """Create a deep copy of the board"""
        new_board = ChessBoard.__new__(ChessBoard)
        new_board.board = copy.deepcopy(self.board)
        new_board.current_side = self.current_side
        new_board.move_history = self.move_history.copy()
        new_board.position_history = []
        new_board.check_history = self.check_history.copy()
        new_board.halfmove_clock = self.halfmove_clock
        new_board.fullmove_number = self.fullmove_number
        return new_board
    
    def load_fen(self, fen: str) -> bool:
        """Load position from FEN string"""
        parts = fen.split()
        if len(parts) < 1:
            return False
        
        # Clear board
        self.board = [[None] * self.FILES for _ in range(self.RANKS)]
        self.move_history = []
        self.position_history = []
        self.check_history = []
        
        # Parse piece placement
        ranks = parts[0].split('/')
        if len(ranks) != self.RANKS:
            return False
        
        for rank_idx, rank_str in enumerate(ranks):
            file_idx = 0
            real_rank = self.RANKS - 1 - rank_idx  # FEN starts from top (rank 9)
            
            for char in rank_str:
                if char.isdigit():
                    file_idx += int(char)
                else:
                    piece = Piece.from_char(char)
                    if piece and file_idx < self.FILES:
                        self.board[real_rank][file_idx] = piece
                    file_idx += 1
        
        # Parse active color
        if len(parts) >= 2:
            self.current_side = Side.RED if parts[1] == 'w' else Side.BLACK
        
        # Parse halfmove clock
        if len(parts) >= 5:
            try:
                self.halfmove_clock = int(parts[4])
            except ValueError:
                pass
        
        # Parse fullmove number
        if len(parts) >= 6:
            try:
                self.fullmove_number = int(parts[5])
            except ValueError:
                pass
        
        return True
    
    def to_fen(self) -> str:
        """Convert current position to FEN string"""
        fen_parts = []
        
        # Piece placement
        ranks = []
        for rank in range(self.RANKS - 1, -1, -1):
            rank_str = ""
            empty_count = 0
            
            for file in range(self.FILES):
                piece = self.board[rank][file]
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        rank_str += str(empty_count)
                        empty_count = 0
                    rank_str += piece.to_char()
            
            if empty_count > 0:
                rank_str += str(empty_count)
            ranks.append(rank_str)
        
        fen_parts.append('/'.join(ranks))
        
        # Active color
        fen_parts.append('w' if self.current_side == Side.RED else 'b')
        
        # Placeholder fields (no castling/en passant in Xiangqi)
        fen_parts.append('-')
        fen_parts.append('-')
        
        # Halfmove clock and fullmove number
        fen_parts.append(str(self.halfmove_clock))
        fen_parts.append(str(self.fullmove_number))
        
        return ' '.join(fen_parts)
    
    def get_piece(self, file: int, rank: int) -> Optional[Piece]:
        """Get piece at position"""
        if 0 <= file < self.FILES and 0 <= rank < self.RANKS:
            return self.board[rank][file]
        return None
    
    def set_piece(self, file: int, rank: int, piece: Optional[Piece]):
        """Set piece at position"""
        if 0 <= file < self.FILES and 0 <= rank < self.RANKS:
            self.board[rank][file] = piece
    
    @staticmethod
    def parse_move(move: str) -> Optional[tuple[int, int, int, int]]:
        """Parse UCI move string to coordinates (from_file, from_rank, to_file, to_rank)"""
        if len(move) < 4:
            return None
        
        try:
            from_file = ord(move[0]) - ord('a')
            from_rank = int(move[1])
            to_file = ord(move[2]) - ord('a')
            to_rank = int(move[3])
            
            if not (0 <= from_file < 9 and 0 <= from_rank < 10 and
                    0 <= to_file < 9 and 0 <= to_rank < 10):
                return None
            
            return (from_file, from_rank, to_file, to_rank)
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def format_move(from_file: int, from_rank: int, to_file: int, to_rank: int) -> str:
        """Format coordinates to UCI move string"""
        return f"{chr(ord('a') + from_file)}{from_rank}{chr(ord('a') + to_file)}{to_rank}"
    
    def is_valid_move(self, from_file: int, from_rank: int, to_file: int, to_rank: int) -> bool:
        """Check if a move is valid"""
        piece = self.get_piece(from_file, from_rank)
        if piece is None or piece.side != self.current_side:
            return False
        
        # Can't capture own piece
        target = self.get_piece(to_file, to_rank)
        if target is not None and target.side == piece.side:
            return False
        
        # Check piece-specific movement rules
        valid = self._is_valid_piece_move(piece, from_file, from_rank, to_file, to_rank)
        if not valid:
            return False
        
        # Check if move leaves king in check
        test_board = self.copy()
        test_board.board[to_rank][to_file] = piece
        test_board.board[from_rank][from_file] = None
        if test_board._is_king_in_check(piece.side):
            return False
        
        # Check if kings face each other (flying general)
        if test_board._kings_face_each_other():
            return False
        
        # Check for perpetual check (长将) - can't give check 4 times in same position
        # Only the side giving check is restricted, not the side being checked
        enemy_side = Side.BLACK if piece.side == Side.RED else Side.RED
        if test_board._is_king_in_check(enemy_side):
            # Switch side on test_board to match how positions are recorded in check_history
            test_board.current_side = enemy_side
            if self._is_perpetual_check(test_board, piece.side):
                return False
        
        return True
    
    def _get_position_key(self) -> str:
        """Generate a unique key for the current position"""
        key_parts = []
        for rank in range(self.RANKS):
            for file in range(self.FILES):
                piece = self.board[rank][file]
                if piece:
                    key_parts.append(f"{file}{rank}{piece.to_char()}")
        key_parts.append('w' if self.current_side == Side.RED else 'b')
        return '|'.join(key_parts)
    
    def _is_perpetual_check(self, test_board: 'ChessBoard', checking_side: Side) -> bool:
        """Check if this would be perpetual check (same checking position occurred 2+ times already)
        
        According to Xiangqi rules, perpetual check (长将) is forbidden. 
        If the same position with check occurs 3 times, the checking side loses.
        So we forbid the move that would create the 3rd occurrence.
        
        Args:
            test_board: The board state after the move
            checking_side: The side that is giving check
        """
        new_key = test_board._get_position_key()
        
        # Count how many times this exact position occurred with check
        # where the same side was giving check
        check_count = 0
        for i, (pos_key, was_check) in enumerate(self.check_history):
            if pos_key == new_key and was_check:
                # Check if the same side was giving check in this position
                # The checking side alternates, so we check based on move index parity
                # Even index = Red just moved (Black in check), Odd index = Black just moved (Red in check)
                if checking_side == Side.RED:
                    # Red is checking, so this should be when Red just moved (even index in 0-based)
                    if i % 2 == 0:  # Red just moved
                        check_count += 1
                else:
                    # Black is checking
                    if i % 2 == 1:  # Black just moved
                        check_count += 1
        
        # If already occurred 2 times with check from this side, this would be the 3rd - forbidden
        return check_count >= 2
    
    def _is_valid_piece_move(self, piece: Piece, ff: int, fr: int, tf: int, tr: int) -> bool:
        """Check if piece movement follows the rules"""
        df = tf - ff
        dr = tr - fr
        adf, adr = abs(df), abs(dr)
        
        if piece.type == PieceType.KING:
            # King moves one step orthogonally within palace
            if not self._in_palace(tf, tr, piece.side):
                return False
            return (adf == 1 and adr == 0) or (adf == 0 and adr == 1)
        
        elif piece.type == PieceType.ADVISOR:
            # Advisor moves diagonally within palace
            if not self._in_palace(tf, tr, piece.side):
                return False
            return adf == 1 and adr == 1
        
        elif piece.type == PieceType.BISHOP:
            # Bishop moves diagonally 2 squares, cannot cross river
            if not self._on_own_side(tr, piece.side):
                return False
            if adf != 2 or adr != 2:
                return False
            # Check blocking piece (elephant eye)
            block_file = ff + df // 2
            block_rank = fr + dr // 2
            return self.get_piece(block_file, block_rank) is None
        
        elif piece.type == PieceType.ROOK:
            # Rook moves orthogonally
            if df != 0 and dr != 0:
                return False
            return self._path_clear(ff, fr, tf, tr)
        
        elif piece.type == PieceType.KNIGHT:
            # Knight moves in 日 pattern
            if not ((adf == 1 and adr == 2) or (adf == 2 and adr == 1)):
                return False
            # Check blocking piece (horse leg)
            if adf == 2:
                block_file = ff + df // 2
                block_rank = fr
            else:
                block_file = ff
                block_rank = fr + dr // 2
            return self.get_piece(block_file, block_rank) is None
        
        elif piece.type == PieceType.CANNON:
            # Cannon moves orthogonally, captures by jumping
            if df != 0 and dr != 0:
                return False
            
            pieces_between = self._count_pieces_between(ff, fr, tf, tr)
            target = self.get_piece(tf, tr)
            
            if target is None:
                return pieces_between == 0
            else:
                return pieces_between == 1
        
        elif piece.type == PieceType.PAWN:
            # Pawn moves forward, can move sideways after crossing river
            if piece.side == Side.RED:
                crossed_river = fr >= 5
                forward = dr == 1 and df == 0
                sideways = dr == 0 and adf == 1 and crossed_river
            else:
                crossed_river = fr <= 4
                forward = dr == -1 and df == 0
                sideways = dr == 0 and adf == 1 and crossed_river
            
            return forward or sideways
        
        return False
    
    def _in_palace(self, file: int, rank: int, side: Side) -> bool:
        """Check if position is in the palace"""
        if not (3 <= file <= 5):
            return False
        if side == Side.RED:
            return 0 <= rank <= 2
        else:
            return 7 <= rank <= 9
    
    def _on_own_side(self, rank: int, side: Side) -> bool:
        """Check if position is on own side of the river"""
        if side == Side.RED:
            return rank <= 4
        else:
            return rank >= 5
    
    def _path_clear(self, ff: int, fr: int, tf: int, tr: int) -> bool:
        """Check if path is clear for rook movement"""
        if ff == tf:  # Vertical
            start, end = (fr + 1, tr) if fr < tr else (tr + 1, fr)
            for rank in range(start, end):
                if self.get_piece(ff, rank) is not None:
                    return False
        else:  # Horizontal
            start, end = (ff + 1, tf) if ff < tf else (tf + 1, ff)
            for file in range(start, end):
                if self.get_piece(file, fr) is not None:
                    return False
        return True
    
    def _count_pieces_between(self, ff: int, fr: int, tf: int, tr: int) -> int:
        """Count pieces between two positions (for cannon)"""
        count = 0
        if ff == tf:  # Vertical
            start, end = (fr + 1, tr) if fr < tr else (tr + 1, fr)
            for rank in range(start, end):
                if self.get_piece(ff, rank) is not None:
                    count += 1
        else:  # Horizontal
            start, end = (ff + 1, tf) if ff < tf else (tf + 1, ff)
            for file in range(start, end):
                if self.get_piece(file, fr) is not None:
                    count += 1
        return count
    
    def _find_king(self, side: Side) -> Optional[tuple[int, int]]:
        """Find the king's position"""
        for rank in range(self.RANKS):
            for file in range(self.FILES):
                piece = self.board[rank][file]
                if piece and piece.type == PieceType.KING and piece.side == side:
                    return (file, rank)
        return None
    
    def _is_red_on_top(self) -> bool:
        """Check if red side is on top of the board (rank 5-9)
        
        This is used to determine pawn direction and other side-specific rules.
        Returns True if red king is in upper half, False otherwise.
        """
        red_king = self._find_king(Side.RED)
        if red_king:
            return red_king[1] >= 5
        # Default: red at bottom
        return False
    
    def _kings_face_each_other(self) -> bool:
        """Check if kings face each other (flying general rule)"""
        red_king = self._find_king(Side.RED)
        black_king = self._find_king(Side.BLACK)
        
        if not red_king or not black_king:
            return False
        
        if red_king[0] != black_king[0]:
            return False
        
        # Check if path between kings is clear
        file = red_king[0]
        # Ensure we iterate from lower rank to higher rank
        min_rank = min(red_king[1], black_king[1])
        max_rank = max(red_king[1], black_king[1])
        
        for rank in range(min_rank + 1, max_rank):
            if self.get_piece(file, rank) is not None:
                return False
        
        return True
    
    def _is_king_in_check(self, side: Side) -> bool:
        """Check if the king of the given side is in check"""
        king_pos = self._find_king(side)
        if not king_pos:
            return True  # King captured
        
        enemy_side = Side.BLACK if side == Side.RED else Side.RED
        kf, kr = king_pos
        
        # Check all enemy pieces
        for rank in range(self.RANKS):
            for file in range(self.FILES):
                piece = self.board[rank][file]
                if piece and piece.side == enemy_side:
                    # Temporarily switch sides to check if this piece can attack the king
                    if self._is_valid_piece_move(piece, file, rank, kf, kr):
                        # For cannon, also check capture rules
                        if piece.type == PieceType.CANNON:
                            if self._count_pieces_between(file, rank, kf, kr) == 1:
                                return True
                        else:
                            return True
        
        return False
    
    def get_legal_moves(self, from_file: int, from_rank: int) -> list[tuple[int, int]]:
        """Get all legal moves for a piece"""
        moves = []
        for tf in range(self.FILES):
            for tr in range(self.RANKS):
                if self.is_valid_move(from_file, from_rank, tf, tr):
                    moves.append((tf, tr))
        return moves
    
    def make_move(self, move: str) -> bool:
        """Make a move on the board"""
        coords = self.parse_move(move)
        if coords is None:
            return False
        
        ff, fr, tf, tr = coords
        if not self.is_valid_move(ff, fr, tf, tr):
            return False
        
        # Save position for undo
        self.position_history.append(copy.deepcopy(self.board))
        
        # Make the move
        piece = self.board[fr][ff]
        captured = self.board[tr][tf]
        
        self.board[tr][tf] = piece
        self.board[fr][ff] = None
        
        # Update game state
        self.move_history.append(move)
        
        if captured or piece.type == PieceType.PAWN:
            self.halfmove_clock = 0
            self.check_history = []  # Reset check history on capture or pawn move
        else:
            self.halfmove_clock += 1
        
        if self.current_side == Side.BLACK:
            self.fullmove_number += 1
        
        self.current_side = Side.BLACK if self.current_side == Side.RED else Side.RED
        
        # Record position and check status for perpetual check detection
        pos_key = self._get_position_key()
        is_check = self._is_king_in_check(self.current_side)
        self.check_history.append((pos_key, is_check))
        
        return True
    
    def undo_move(self) -> str | None:
        """Undo the last move"""
        if not self.move_history or not self.position_history:
            return None
        
        self.board = self.position_history.pop()
        move = self.move_history.pop()
        
        # Also remove the check history entry for this move
        if self.check_history:
            self.check_history.pop()
        
        self.current_side = Side.BLACK if self.current_side == Side.RED else Side.RED
        
        if self.current_side == Side.BLACK:
            self.fullmove_number -= 1
        
        return move
    
    def is_checkmate(self) -> bool:
        """Check if current side is in checkmate"""
        if not self._is_king_in_check(self.current_side):
            return False
        
        # Check if any legal move exists
        for rank in range(self.RANKS):
            for file in range(self.FILES):
                piece = self.board[rank][file]
                if piece and piece.side == self.current_side:
                    if self.get_legal_moves(file, rank):
                        return False
        
        return True
    
    def is_stalemate(self) -> bool:
        """Check if current side is in stalemate"""
        if self._is_king_in_check(self.current_side):
            return False
        
        # Check if any legal move exists
        for rank in range(self.RANKS):
            for file in range(self.FILES):
                piece = self.board[rank][file]
                if piece and piece.side == self.current_side:
                    if self.get_legal_moves(file, rank):
                        return False
        
        return True
    
    def is_draw(self) -> bool:
        """Check if the game is a draw by any automatic rule"""
        return self.is_threefold_repetition() or self.is_sixty_move_rule()
    
    def is_threefold_repetition(self) -> bool:
        """Check if the same position has occurred 3 times (三次同形重复)"""
        if len(self.check_history) < 5:  # Need at least 5 positions for 3 repetitions
            return False
        
        current_key = self._get_position_key()
        count = 0
        
        for pos_key, _ in self.check_history:
            if pos_key == current_key:
                count += 1
                if count >= 3:
                    return True
        
        return False
    
    def is_sixty_move_rule(self) -> bool:
        """Check if 60 moves (120 half-moves) have been made without capture or pawn move
        
        This is the Xiangqi equivalent of the 50-move rule in international chess.
        """
        return self.halfmove_clock >= 120
    
    def can_claim_draw(self) -> tuple[bool, str]:
        """Check if a player can claim a draw
        
        Returns:
            Tuple of (can_claim, reason)
        """
        if self.is_threefold_repetition():
            return True, "三次同形重复"
        if self.is_sixty_move_rule():
            return True, "六十回合无吃子"
        return False, ""
    
    def move_to_chinese(self, move: str, board_before: 'ChessBoard' = None) -> str:
        """Convert UCI move to Chinese notation
        
        Args:
            move: UCI move string like "h2e2"
            board_before: Board state before the move (uses self if None)
        
        Returns:
            Chinese notation like "炮二平五"
        """
        board = board_before if board_before else self
        coords = self.parse_move(move)
        if coords is None:
            return move
        
        ff, fr, tf, tr = coords
        piece = board.get_piece(ff, fr)
        if piece is None:
            return move
        
        # Chinese numerals for red, Arabic for black
        RED_NUMS = ['一', '二', '三', '四', '五', '六', '七', '八', '九']
        BLACK_NUMS = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
        
        is_red = piece.side == Side.RED
        nums = RED_NUMS if is_red else BLACK_NUMS
        
        # File numbers: Red counts from right (9-file), Black counts from left (1+file)
        # In Xiangqi, file 0 is 'a' (leftmost), file 8 is 'i' (rightmost)
        # Red: rightmost = 一, leftmost = 九 (so file 8 = 一, file 0 = 九)
        # Black: leftmost = 1, rightmost = 9 (so file 0 = 1, file 8 = 9)
        if is_red:
            from_num = nums[8 - ff]
            to_num = nums[8 - tf]
        else:
            from_num = nums[ff]
            to_num = nums[tf]
        
        piece_name = piece.to_chinese()
        
        # Check for duplicate pieces on the same file (need 前/后 prefix)
        same_type_on_file = []
        for rank in range(self.RANKS):
            p = board.get_piece(ff, rank)
            if p and p.type == piece.type and p.side == piece.side:
                same_type_on_file.append(rank)
        
        prefix = ""
        if len(same_type_on_file) >= 2:
            # Sort by rank (low to high for Red is bottom to top)
            same_type_on_file.sort()
            if is_red:
                # Red: higher rank is "前" (closer to opponent), lower rank is "后" (closer to self)
                if fr == same_type_on_file[-1]:
                    prefix = "前"
                elif fr == same_type_on_file[0]:
                    prefix = "后"
                else:
                    # Middle piece - number from front (high rank) to back (low rank)
                    idx = same_type_on_file.index(fr)
                    prefix = nums[len(same_type_on_file) - 1 - idx]
            else:
                # Black: lower rank is "前" (closer to opponent), higher rank is "后" (closer to self)
                if fr == same_type_on_file[0]:
                    prefix = "前"
                elif fr == same_type_on_file[-1]:
                    prefix = "后"
                else:
                    idx = same_type_on_file.index(fr)
                    prefix = nums[idx]
        
        # Determine action (进/退/平)
        df = tf - ff
        dr = tr - fr
        
        if dr == 0:
            # Horizontal move (平)
            action = "平"
            target = to_num
        else:
            # Vertical or diagonal move
            if is_red:
                action = "进" if dr > 0 else "退"
            else:
                action = "进" if dr < 0 else "退"
            
            # For pieces that move orthogonally (Rook, Cannon, Pawn, King), target is distance
            # For pieces that move diagonally (Knight, Bishop, Advisor), target is destination file
            if piece.type in [PieceType.ROOK, PieceType.CANNON, PieceType.PAWN, PieceType.KING]:
                distance = abs(dr)
                target = nums[distance - 1]
            else:
                # Knight, Bishop, Advisor - use destination file
                target = to_num
        
        if prefix:
            return f"{prefix}{piece_name}{action}{target}"
        else:
            return f"{piece_name}{from_num}{action}{target}"

    def get_all_legal_moves(self) -> list[str]:
        """Get all legal moves for current side (return UCI strings)"""
        moves = []
        from_files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i']
        
        for r1 in range(self.RANKS):
            for f1 in range(self.FILES):
                piece = self.board[r1][f1]
                if not piece or piece.side != self.current_side:
                    continue
                
                targets = []
                pt = piece.type
                
                if pt == PieceType.KING:
                    # Orthogonal 1 step within palace
                    for df, dr in [(0,1), (0,-1), (1,0), (-1,0)]:
                        targets.append((f1+df, r1+dr))
                elif pt == PieceType.ADVISOR:
                    # Diagonal 1 step within palace
                    for df, dr in [(1,1), (1,-1), (-1,1), (-1,-1)]:
                        targets.append((f1+df, r1+dr))
                elif pt == PieceType.BISHOP:
                    # Diagonal 2 steps (check eye later in is_valid_move)
                    for df, dr in [(2,2), (2,-2), (-2,2), (-2,-2)]:
                        targets.append((f1+df, r1+dr))
                elif pt == PieceType.KNIGHT:
                    # 8 targets (check leg later)
                    for df, dr in [(1,2), (1,-2), (-1,2), (-1,-2), (2,1), (2,-1), (-2,1), (-2,-1)]:
                        targets.append((f1+df, r1+dr))
                elif pt == PieceType.ROOK or pt == PieceType.CANNON:
                    # Scan lines
                    for i in range(self.FILES):
                        if i != f1: targets.append((i, r1))
                    for i in range(self.RANKS):
                        if i != r1: targets.append((f1, i))
                elif pt == PieceType.PAWN:
                    # Forward + Side (if crossed river)
                    # Forward direction
                    dr = 1 if self.current_side == Side.RED else -1
                    targets.append((f1, r1+dr))
                    
                    # Check if crossed river
                    is_crossed = (self.current_side == Side.RED and r1 > 4) or \
                                 (self.current_side == Side.BLACK and r1 < 5)
                    if is_crossed:
                        targets.append((f1+1, r1))
                        targets.append((f1-1, r1))
                
                # Check validity and add to moves
                for f2, r2 in targets:
                    if 0 <= f2 < self.FILES and 0 <= r2 < self.RANKS:
                         if self.is_valid_move(f1, r1, f2, r2):
                             moves.append(f"{from_files[f1]}{r1}{from_files[f2]}{r2}")
        return moves

    def chinese_to_move(self, text: str) -> str | None:
        """Convert Chinese notation to UCI move"""
        # Brute force match against all legal moves
        legal_moves = self.get_all_legal_moves()
        
        # Trim text just in case
        text = text.strip()
        
        # We try to match the chinese output of the move
        # Note: move_to_chinese requires board state for context (Same file pieces)
        # self.move_to_chinese already handles this using self.board if no temp board provided
        
        for move in legal_moves:
             if self.move_to_chinese(move) == text:
                 return move
                 
        return None

    def move_to_iccs(self, move: str) -> str:
        """Convert UCI move to ICCS notation (e.g. c3c4 -> C3-C4)"""
        if len(move) == 4:
            return f"{move[0].upper()}{move[1]}-{move[2].upper()}{move[3]}"
        return move

    def iccs_to_move(self, text: str) -> str | None:
        """Convert ICCS notation to UCI move (e.g. C3-C4 -> c3c4)"""
        if not text:
            return None
            
        clean_text = text.replace("-", "").lower()
        if len(clean_text) == 4:
             if 'a' <= clean_text[0] <= 'i' and \
                '0' <= clean_text[1] <= '9' and \
                'a' <= clean_text[2] <= 'i' and \
                '0' <= clean_text[3] <= '9':
                 return clean_text
        return None
