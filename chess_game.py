"""
CHESS V2 — a pygame chess game with cosmic vibes,
                  particle effects, comic-book text stamps,
                  meme popups, screen shake, and full chess rules.
 
Drop your assets into:
    assets/pieces/   — wP.png, wN.png, wB.png, wR.png, wQ.png, wK.png
                       bP.png, bN.png, bB.png, bR.png, bQ.png, bK.png
                       (any square images, ideally transparent PNG)
    assets/memes/    — any .png/.jpg files; one is shown randomly on captures
    assets/sounds/   — move.wav, capture.wav, check.wav, checkmate.wav (optional)
 
Controls:
    Left-click       — select / move
    R                — reset game
    U                — undo last move
    F                — flip board
    M                — toggle meme popups
    Esc              — quit
"""
 
import os
import sys
import math
import random
from pathlib import Path
import pygame
 
# ════════════════════════════════════════════════════════════════════
#                           CONSTANTS
# ════════════════════════════════════════════════════════════════════
 
WIDTH, HEIGHT       = 1280, 800
BOARD_PX            = 640
SQUARE              = BOARD_PX // 8
BOARD_X             = 60
BOARD_Y             = (HEIGHT - BOARD_PX) // 2
SIDE_X              = BOARD_X + BOARD_PX + 60
SIDE_W              = WIDTH - SIDE_X - 40
FPS                 = 60
 
# Cosmic Royal palette
COL_BG_TOP          = (12, 10, 30)
COL_BG_BOT          = (30, 16, 56)
COL_PANEL           = (22, 18, 44, 220)
COL_PANEL_BORDER    = (110, 80, 200)
COL_LIGHT_SQ        = (234, 221, 200)
COL_DARK_SQ         = (92, 75, 122)
COL_GOLD            = (255, 185, 56)
COL_ACCENT          = (185, 104, 255)
COL_CYAN            = (110, 240, 255)
COL_CREAM           = (244, 236, 220)
COL_DIM             = (160, 150, 190)
COL_DANGER          = (255, 92, 110)
COL_GOOD            = (120, 230, 160)
 
ASSET_DIR    = Path(__file__).parent / "assets"
PIECES_DIR   = ASSET_DIR / "pieces"
MEMES_DIR    = ASSET_DIR / "memes"
SOUNDS_DIR   = ASSET_DIR / "sounds"
 
ANIM_MOVE_FRAMES   = 14   # frames a piece slide takes
STAMP_LIFETIME     = 60   # frames a text-stamp stays
MEME_LIFETIME      = 110  # frames a meme popup stays
 
CAPTURE_STAMPS = ["GOTCHA!", "BOOM!", "POW!", "KAPOW!", "REKT", "BYE!",
                  "OOF.", "TAKEN!", "💥", "SNATCHED", "GG EZ"]
CHECK_STAMPS   = ["CHECK!", "RUN!", "DANGER!", "WATCH OUT!", "INCOMING!"]
MATE_STAMPS    = ["CHECKMATE!", "DOMINATED!", "GG!", "THE END", "FINISHED!", "AU REVOIR"]
BRILLIANT      = ["BRILLIANT!", "GENIUS!", "MAGNIFICENT!", "INSANE!", "!!", "IM LITERALLY TAL"]
BLUNDER        = ["BLUNDER?", "LOL", "U OK?", "?!", "WHAT WAS THAT"]
RANDOM_FLAVOR  = ["NICE.", "INTERESTING.", "BOLD MOVE.", "SURE.", "BASED.",
                  "HELL YEAH", "NO THOUGHTS", "🧠", "I GUESS BRO"]
 
 
# ════════════════════════════════════════════════════════════════════
#                        ASSET MANAGER
# ════════════════════════════════════════════════════════════════════
 
class Assets:
    """Loads images/sounds with graceful fallback if missing."""
 
    PIECE_CODES = ["wP", "wN", "wB", "wR", "wQ", "wK",
                   "bP", "bN", "bB", "bR", "bQ", "bK"]
    UNICODE = {"P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
               "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚"}
 
    def __init__(self):
        self.pieces = {}
        self.memes  = []
        self.sounds = {}
        self._font_cache = {}
        self._load_pieces()
        self._load_memes()
        self._load_sounds()
 
    def font(self, size, bold=False):
        key = (size, bold)
        if key not in self._font_cache:
            try:
                f = pygame.font.SysFont("georgia,times,serif", size, bold=bold)
            except Exception:
                f = pygame.font.Font(None, size)
            self._font_cache[key] = f
        return self._font_cache[key]
 
    def piece_font(self, size):
        key = ("piece", size)
        if key not in self._font_cache:
            f = None
            for name in ("dejavusans", "segoeuisymbol", "arial", "freeserif", None):
                try:
                    f = pygame.font.SysFont(name, size) if name else pygame.font.Font(None, size)
                    test = f.render("♔", True, (0, 0, 0))
                    if test.get_width() > size * 0.3:
                        break
                except Exception:
                    continue
            self._font_cache[key] = f
        return self._font_cache[key]
 
    def _load_pieces(self):
        if not PIECES_DIR.exists():
            PIECES_DIR.mkdir(parents=True, exist_ok=True)
            return
        for code in self.PIECE_CODES:
            for ext in (".png", ".PNG", ".jpg", ".jpeg", ".webp"):
                p = PIECES_DIR / f"{code}{ext}"
                if p.exists():
                    try:
                        img = pygame.image.load(str(p)).convert_alpha()
                        size = int(SQUARE * 0.86)
                        self.pieces[code] = pygame.transform.smoothscale(img, (size, size))
                        break
                    except Exception as e:
                        print(f"[assets] failed to load {p}: {e}")
 
    def _load_memes(self):
        if not MEMES_DIR.exists():
            MEMES_DIR.mkdir(parents=True, exist_ok=True)
            return
        for f in sorted(MEMES_DIR.iterdir()):
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
                try:
                    img = pygame.image.load(str(f)).convert_alpha()
                    # scale to fit max 280px wide preserving aspect
                    w, h = img.get_size()
                    scale = min(280 / w, 280 / h, 1.0)
                    if scale < 1.0:
                        img = pygame.transform.smoothscale(
                            img, (int(w * scale), int(h * scale)))
                    self.memes.append(img)
                except Exception as e:
                    print(f"[assets] meme load failed {f}: {e}")
 
    def _load_sounds(self):
        if not SOUNDS_DIR.exists():
            SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
            return
        for name in ("move", "capture", "check", "checkmate", "select",
                     "castle", "illegal", "notify", "premove", "promote", "start"):
            for ext in (".wav", ".ogg", ".mp3", ".webm"):
                p = SOUNDS_DIR / f"{name}{ext}"
                if p.exists():
                    try:
                        self.sounds[name] = pygame.mixer.Sound(str(p))
                        break
                    except Exception as e:
                        print(f"[assets] sound load failed {p}: {e}")
 
    def play(self, name):
        s = self.sounds.get(name)
        if s:
            s.play()
 
    def random_meme(self):
        return random.choice(self.memes) if self.memes else None
 
    def draw_piece(self, surf, code, x, y, size=None):
        """Draw a piece centred on (x,y) — use real image or fallback."""
        if size is None:
            size = int(SQUARE * 0.86)
        img = self.pieces.get(code)
        if img is not None:
            if img.get_width() != size:
                img = pygame.transform.smoothscale(img, (size, size))
            rect = img.get_rect(center=(x, y))
            # subtle drop shadow
            shadow = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            shadow.blit(img, (0, 0))
            shadow.fill((0, 0, 0, 120), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(shadow, (rect.x + 3, rect.y + 4))
            surf.blit(img, rect)
        else:
            # Fallback: unicode chess glyph with custom styling
            color_white = code[0] == "w"
            letter = code[1] if color_white else code[1].lower()
            glyph = self.UNICODE[letter]
            fnt = self.piece_font(int(size * 1.1))
            # halo
            for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                outline = fnt.render(glyph, True, (15, 12, 30))
                rect = outline.get_rect(center=(x + dx, y + dy))
                surf.blit(outline, rect)
            colour = (250, 240, 215) if color_white else (40, 25, 70)
            face = fnt.render(glyph, True, colour)
            rect = face.get_rect(center=(x, y))
            surf.blit(face, rect)
 
 
# ════════════════════════════════════════════════════════════════════
#                       PARTICLE SYSTEM
# ════════════════════════════════════════════════════════════════════
 
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "size", "color", "gravity", "shape")
 
    def __init__(self, x, y, vx, vy, life, size, color, gravity=0.15, shape="circle"):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.size = size
        self.color = color
        self.gravity = gravity
        self.shape = shape
 
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.vx *= 0.985
        self.life -= 1
 
    def draw(self, surf):
        if self.life <= 0:
            return
        t = self.life / self.max_life
        size = max(1, int(self.size * t))
        alpha = max(0, min(255, int(255 * t)))
        if self.shape == "star":
            self._draw_star(surf, size, alpha)
        else:
            s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            col = (*self.color, alpha)
            pygame.draw.circle(s, col, (size, size), size)
            surf.blit(s, (self.x - size, self.y - size),
                      special_flags=pygame.BLEND_PREMULTIPLIED if False else 0)
 
    def _draw_star(self, surf, size, alpha):
        pts = []
        for i in range(10):
            angle = i * math.pi / 5 - math.pi / 2
            r = size if i % 2 == 0 else size * 0.45
            pts.append((self.x + math.cos(angle) * r, self.y + math.sin(angle) * r))
        s = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
        offset = (self.x - size * 1.5, self.y - size * 1.5)
        pts2 = [(p[0] - offset[0], p[1] - offset[1]) for p in pts]
        pygame.draw.polygon(s, (*self.color, alpha), pts2)
        surf.blit(s, offset)
 
 
class ParticleSystem:
    def __init__(self):
        self.parts = []
 
    def burst(self, x, y, color, n=30, speed=6, life=40, size=4, shape="circle"):
        for _ in range(n):
            a = random.random() * math.tau
            v = random.uniform(speed * 0.3, speed)
            self.parts.append(Particle(
                x, y, math.cos(a) * v, math.sin(a) * v - random.uniform(0, 2),
                int(life * random.uniform(0.6, 1.2)),
                size * random.uniform(0.6, 1.4),
                color, gravity=0.2, shape=shape))
 
    def confetti(self, w, h, n=120):
        colors = [COL_GOLD, COL_ACCENT, COL_CYAN, COL_CREAM, COL_GOOD, COL_DANGER]
        for _ in range(n):
            self.parts.append(Particle(
                random.uniform(0, w), -random.uniform(0, 100),
                random.uniform(-2, 2), random.uniform(2, 6),
                random.randint(120, 240),
                random.randint(3, 6),
                random.choice(colors),
                gravity=0.08))
 
    def trail(self, x, y, color):
        for _ in range(2):
            a = random.random() * math.tau
            self.parts.append(Particle(
                x + random.uniform(-4, 4), y + random.uniform(-4, 4),
                math.cos(a) * 0.5, math.sin(a) * 0.5,
                random.randint(15, 25),
                random.uniform(2, 4),
                color, gravity=-0.02))
 
    def update(self):
        self.parts = [p for p in self.parts if p.life > 0]
        for p in self.parts:
            p.update()
 
    def draw(self, surf):
        for p in self.parts:
            p.draw(surf)
 
 
# ════════════════════════════════════════════════════════════════════
#                  ANIMATED COSMIC BACKGROUND
# ════════════════════════════════════════════════════════════════════
 
class CosmicBackground:
    def __init__(self):
        self.stars = []
        for _ in range(140):
            self.stars.append({
                "x": random.uniform(0, WIDTH),
                "y": random.uniform(0, HEIGHT),
                "r": random.uniform(0.5, 2.2),
                "speed": random.uniform(0.05, 0.4),
                "phase": random.uniform(0, math.tau),
            })
        self.t = 0
        # pre-render gradient
        self.grad = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / HEIGHT
            c = tuple(int(COL_BG_TOP[i] * (1 - t) + COL_BG_BOT[i] * t) for i in range(3))
            pygame.draw.line(self.grad, c, (0, y), (WIDTH, y))
 
    def update(self):
        self.t += 1
        for s in self.stars:
            s["y"] += s["speed"]
            if s["y"] > HEIGHT:
                s["y"] = 0
                s["x"] = random.uniform(0, WIDTH)

    def draw(self, surf):
        surf.blit(self.grad, (0, 0))
        # Stars twinkle
        for s in self.stars:
            tw = 0.6 + 0.4 * math.sin(self.t * 0.05 + s["phase"])
            a = int(180 * tw)
            col = (COL_CREAM[0], COL_CREAM[1], COL_CREAM[2], a)
            ss = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(ss, col, (3, 3), s["r"])
            surf.blit(ss, (s["x"] - 3, s["y"] - 3))
 
 
# ════════════════════════════════════════════════════════════════════
#                         TEXT STAMPS
# ════════════════════════════════════════════════════════════════════
 
class TextStamp:
    """Comic-book style text that bursts in and fades out."""
 
    def __init__(self, text, x, y, assets, color=None, big=False):
        self.text = text
        self.x, self.y = x, y
        self.life = STAMP_LIFETIME
        self.max_life = STAMP_LIFETIME
        self.color = color or random.choice([COL_GOLD, COL_ACCENT, COL_CYAN, COL_DANGER])
        size = 64 if big else 42
        fnt = assets.font(size, bold=True)
        self.surf = fnt.render(text, True, self.color)
        self.outline = fnt.render(text, True, (15, 10, 30))
        self.angle = random.uniform(-18, 18)
        self.vy = -1.0
 
    def update(self):
        self.life -= 1
        self.y += self.vy
        self.vy *= 0.92
 
    def draw(self, surf):
        if self.life <= 0:
            return
        t = self.life / self.max_life
        # burst-in scale: starts big, settles
        progress = 1 - t
        scale = 1.4 - 0.4 * min(1, progress * 4) if progress < 0.25 else 1.0
        # last 30% fade
        alpha = int(255 * min(1.0, t / 0.3))
        w, h = self.surf.get_size()
        sw, sh = int(w * scale), int(h * scale)
        base = pygame.Surface((sw + 8, sh + 8), pygame.SRCALPHA)
        outline_s = pygame.transform.smoothscale(self.outline, (sw, sh))
        face_s    = pygame.transform.smoothscale(self.surf, (sw, sh))
        for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2)]:
            base.blit(outline_s, (4 + dx, 4 + dy))
        base.blit(face_s, (4, 4))
        rotated = pygame.transform.rotate(base, self.angle)
        rotated.set_alpha(alpha)
        rect = rotated.get_rect(center=(self.x, self.y))
        surf.blit(rotated, rect)
 
 
# ════════════════════════════════════════════════════════════════════
#                       MEME POPUP
# ════════════════════════════════════════════════════════════════════
 
class MemePopup:
    def __init__(self, image, side="right"):
        self.image = image
        self.life = MEME_LIFETIME
        self.max_life = MEME_LIFETIME
        self.side = side
        self.target_x = WIDTH - image.get_width() - 20 if side == "right" else 20
        self.x = WIDTH + 20 if side == "right" else -image.get_width() - 20
        self.y = HEIGHT - image.get_height() - 30
 
    def update(self):
        self.life -= 1
        # slide in fast, hover, slide out
        if self.life > self.max_life * 0.7:
            self.x += (self.target_x - self.x) * 0.25
        elif self.life < self.max_life * 0.25:
            if self.side == "right":
                self.x += (WIDTH + 50 - self.x) * 0.15
            else:
                self.x += (-self.image.get_width() - 50 - self.x) * 0.15
 
    def draw(self, surf):
        if self.life <= 0:
            return
        # subtle bob
        bob = math.sin((self.max_life - self.life) * 0.2) * 4
        # frame
        rect = self.image.get_rect(topleft=(int(self.x), int(self.y + bob)))
        frame = rect.inflate(16, 16)
        pygame.draw.rect(surf, (15, 10, 30), frame, border_radius=10)
        pygame.draw.rect(surf, COL_GOLD, frame, 3, border_radius=10)
        surf.blit(self.image, rect)
 
 
# ════════════════════════════════════════════════════════════════════
#                       CHESS ENGINE
# ════════════════════════════════════════════════════════════════════
 
class CastleRights:
    __slots__ = ("wks", "bks", "wqs", "bqs")
 
    def __init__(self, wks=True, bks=True, wqs=True, bqs=True):
        self.wks, self.bks, self.wqs, self.bqs = wks, bks, wqs, bqs
 
    def copy(self):
        return CastleRights(self.wks, self.bks, self.wqs, self.bqs)
 
 
class Move:
    """One half-move. Stores enough info to undo."""
 
    FILES = "abcdefgh"
    RANKS = "87654321"
 
    def __init__(self, start, end, board, *,
                 enpassant=False, castle=False, promotion=None):
        self.r1, self.c1 = start
        self.r2, self.c2 = end
        self.piece = board[self.r1][self.c1]
        self.captured = board[self.r2][self.c2]
        self.enpassant = enpassant
        if enpassant:
            self.captured = "bP" if self.piece == "wP" else "wP"
        self.castle = castle
        # promotion is target piece letter (Q/R/B/N) or None
        self.promotion = promotion
        # only set true when this move IS a pawn reaching the back rank;
        # if promotion is None it means awaiting choice
        self.is_promotion = self.piece[1] == "P" and (self.r2 == 0 or self.r2 == 7)
        self.id = (self.r1, self.c1, self.r2, self.c2,
                   promotion or "", enpassant, castle)
 
    def __eq__(self, o):
        return isinstance(o, Move) and self.id == o.id
 
    def __hash__(self):
        return hash(self.id)
 
    def notation(self):
        sq1 = self.FILES[self.c1] + self.RANKS[self.r1]
        sq2 = self.FILES[self.c2] + self.RANKS[self.r2]
        if self.castle:
            return "O-O" if self.c2 == 6 else "O-O-O"
        prefix = "" if self.piece[1] == "P" else self.piece[1]
        cap = "x" if self.captured != "--" else ""
        prom = f"={self.promotion}" if self.promotion else ""
        if self.piece[1] == "P" and cap:
            prefix = self.FILES[self.c1]
        return f"{prefix}{cap}{sq2}{prom}"
 
 
class GameState:
    """Full chess game state with legal-move generation."""
 
    def __init__(self):
        self.board = [
            ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
            ["bP"] * 8,
            ["--"] * 8, ["--"] * 8, ["--"] * 8, ["--"] * 8,
            ["wP"] * 8,
            ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"],
        ]
        self.white_to_move = True
        self.move_log = []
        self.wk = (7, 4); self.bk = (0, 4)
        self.checkmate = False
        self.stalemate = False
        self.enpassant_sq = ()      # square eligible for en passant capture
        self.enpassant_log = [()]
        self.castle = CastleRights()
        self.castle_log = [self.castle.copy()]
 
    # ---- piece movers ----
 
    def make_move(self, m, promotion_choice=None):
        b = self.board
        b[m.r1][m.c1] = "--"
        # actual placed piece (handle promotion)
        placed = m.piece
        if m.is_promotion:
            choice = promotion_choice or m.promotion or "Q"
            placed = m.piece[0] + choice
            m.promotion = choice
        b[m.r2][m.c2] = placed
        # king tracking
        if m.piece == "wK": self.wk = (m.r2, m.c2)
        if m.piece == "bK": self.bk = (m.r2, m.c2)
        # en passant capture removes the pawn
        if m.enpassant:
            b[m.r1][m.c2] = "--"
        # set enpassant square if double pawn push
        if m.piece[1] == "P" and abs(m.r1 - m.r2) == 2:
            self.enpassant_sq = ((m.r1 + m.r2) // 2, m.c1)
        else:
            self.enpassant_sq = ()
        # castle: move rook
        if m.castle:
            if m.c2 == 6:        # kingside
                b[m.r2][5] = b[m.r2][7]; b[m.r2][7] = "--"
            else:                # queenside
                b[m.r2][3] = b[m.r2][0]; b[m.r2][0] = "--"
        # update castle rights
        self._update_castle_rights(m)
        self.castle_log.append(self.castle.copy())
        self.enpassant_log.append(self.enpassant_sq)
        self.move_log.append(m)
        self.white_to_move = not self.white_to_move
 
    def undo_move(self):
        if not self.move_log:
            return None
        m = self.move_log.pop()
        b = self.board
        b[m.r1][m.c1] = m.piece
        b[m.r2][m.c2] = m.captured if not m.enpassant else "--"
        if m.enpassant:
            b[m.r1][m.c2] = m.captured
        if m.piece == "wK": self.wk = (m.r1, m.c1)
        if m.piece == "bK": self.bk = (m.r1, m.c1)
        if m.castle:
            if m.c2 == 6:
                b[m.r2][7] = b[m.r2][5]; b[m.r2][5] = "--"
            else:
                b[m.r2][0] = b[m.r2][3]; b[m.r2][3] = "--"
        self.castle_log.pop()
        self.castle = self.castle_log[-1].copy()
        self.enpassant_log.pop()
        self.enpassant_sq = self.enpassant_log[-1]
        self.white_to_move = not self.white_to_move
        self.checkmate = False
        self.stalemate = False
        return m
 
    def _update_castle_rights(self, m):
        if m.piece == "wK":
            self.castle.wks = self.castle.wqs = False
        elif m.piece == "bK":
            self.castle.bks = self.castle.bqs = False
        elif m.piece == "wR":
            if m.r1 == 7:
                if m.c1 == 0: self.castle.wqs = False
                elif m.c1 == 7: self.castle.wks = False
        elif m.piece == "bR":
            if m.r1 == 0:
                if m.c1 == 0: self.castle.bqs = False
                elif m.c1 == 7: self.castle.bks = False
        # capturing rook on its starting square also kills that right
        if m.captured == "wR":
            if m.r2 == 7 and m.c2 == 0: self.castle.wqs = False
            if m.r2 == 7 and m.c2 == 7: self.castle.wks = False
        elif m.captured == "bR":
            if m.r2 == 0 and m.c2 == 0: self.castle.bqs = False
            if m.r2 == 0 and m.c2 == 7: self.castle.bks = False
 
    # ---- move generation ----
 
    def get_valid_moves(self):
        """Pseudo-legal moves filtered for own-king safety."""
        temp_ep = self.enpassant_sq
        temp_cr = self.castle.copy()
        moves = self._all_pseudo_moves()
        # castle moves are also generated, but they include their own safety check
        legal = []
        for mv in moves:
            self.make_move(mv)
            self.white_to_move = not self.white_to_move
            if not self._in_check():
                legal.append(mv)
            self.white_to_move = not self.white_to_move
            self.undo_move()
        if not legal:
            if self._in_check():
                self.checkmate = True
            else:
                self.stalemate = True
        else:
            self.checkmate = False
            self.stalemate = False
        self.enpassant_sq = temp_ep
        self.castle = temp_cr
        return legal
 
    def in_check(self):
        return self._in_check()
 
    def _in_check(self):
        kr, kc = self.wk if self.white_to_move else self.bk
        return self._square_attacked(kr, kc)
 
    def _square_attacked(self, r, c):
        self.white_to_move = not self.white_to_move
        opp = self._all_pseudo_moves(skip_castle=True)
        self.white_to_move = not self.white_to_move
        for m in opp:
            if (m.r2, m.c2) == (r, c):
                return True
        return False
 
    def _all_pseudo_moves(self, skip_castle=False):
        moves = []
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p == "--":
                    continue
                colour = p[0]
                if (colour == "w") != self.white_to_move:
                    continue
                kind = p[1]
                if   kind == "P": self._pawn_moves(r, c, moves)
                elif kind == "R": self._slide(r, c, moves, [(-1, 0), (1, 0), (0, -1), (0, 1)])
                elif kind == "N": self._knight_moves(r, c, moves)
                elif kind == "B": self._slide(r, c, moves, [(-1, -1), (-1, 1), (1, -1), (1, 1)])
                elif kind == "Q": self._slide(r, c, moves,
                                              [(-1, 0), (1, 0), (0, -1), (0, 1),
                                               (-1, -1), (-1, 1), (1, -1), (1, 1)])
                elif kind == "K": self._king_moves(r, c, moves, include_castle=not skip_castle)
        return moves
 
    def _pawn_moves(self, r, c, moves):
        b = self.board
        if self.white_to_move:
            dirn = -1; start_row = 6; enemy = "b"
        else:
            dirn = 1; start_row = 1; enemy = "w"
        # forward
        if 0 <= r + dirn < 8 and b[r + dirn][c] == "--":
            moves.append(Move((r, c), (r + dirn, c), b))
            if r == start_row and b[r + 2 * dirn][c] == "--":
                moves.append(Move((r, c), (r + 2 * dirn, c), b))
        # captures
        for dc in (-1, 1):
            nr, nc = r + dirn, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                tgt = b[nr][nc]
                if tgt != "--" and tgt[0] == enemy:
                    moves.append(Move((r, c), (nr, nc), b))
                elif (nr, nc) == self.enpassant_sq:
                    moves.append(Move((r, c), (nr, nc), b, enpassant=True))
 
    def _knight_moves(self, r, c, moves):
        b = self.board
        own = "w" if self.white_to_move else "b"
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                       (1, -2), (1, 2), (2, -1), (2, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8 and (b[nr][nc] == "--" or b[nr][nc][0] != own):
                moves.append(Move((r, c), (nr, nc), b))
 
    def _slide(self, r, c, moves, dirs):
        b = self.board
        own = "w" if self.white_to_move else "b"
        for dr, dc in dirs:
            for k in range(1, 8):
                nr, nc = r + dr * k, c + dc * k
                if not (0 <= nr < 8 and 0 <= nc < 8):
                    break
                t = b[nr][nc]
                if t == "--":
                    moves.append(Move((r, c), (nr, nc), b))
                elif t[0] != own:
                    moves.append(Move((r, c), (nr, nc), b))
                    break
                else:
                    break
 
    def _king_moves(self, r, c, moves, include_castle=True):
        b = self.board
        own = "w" if self.white_to_move else "b"
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8 and (b[nr][nc] == "--" or b[nr][nc][0] != own):
                    moves.append(Move((r, c), (nr, nc), b))
        if include_castle:
            self._castle_moves(r, c, moves)
 
    def _castle_moves(self, r, c, moves):
        if self._in_check():
            return
        own = "w" if self.white_to_move else "b"
        cr = self.castle
        # kingside
        kside = (own == "w" and cr.wks) or (own == "b" and cr.bks)
        qside = (own == "w" and cr.wqs) or (own == "b" and cr.bqs)
        if kside:
            if self.board[r][c + 1] == "--" and self.board[r][c + 2] == "--":
                if not self._square_attacked(r, c + 1) and not self._square_attacked(r, c + 2):
                    moves.append(Move((r, c), (r, c + 2), self.board, castle=True))
        if qside:
            if self.board[r][c - 1] == "--" and self.board[r][c - 2] == "--" and self.board[r][c - 3] == "--":
                if not self._square_attacked(r, c - 1) and not self._square_attacked(r, c - 2):
                    moves.append(Move((r, c), (r, c - 2), self.board, castle=True))
 
 
# ════════════════════════════════════════════════════════════════════
#                       UI HELPERS
# ════════════════════════════════════════════════════════════════════
 
class Button:
    def __init__(self, rect, label, color=COL_ACCENT):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.hover = False
        self.click_t = 0
 
    def update(self, mouse_pos, click):
        self.hover = self.rect.collidepoint(mouse_pos)
        self.click_t = max(0, self.click_t - 1)
        if self.hover and click:
            self.click_t = 8
            return True
        return False
 
    def draw(self, surf, assets):
        col = tuple(min(255, c + (40 if self.hover else 0)) for c in self.color)
        scale = 1 - 0.05 * (self.click_t / 8)
        w = int(self.rect.w * scale)
        h = int(self.rect.h * scale)
        x = self.rect.x + (self.rect.w - w) // 2
        y = self.rect.y + (self.rect.h - h) // 2
        # shadow
        shadow = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 100), shadow.get_rect(), border_radius=10)
        surf.blit(shadow, (x + 2, y + 4))
        # body
        pygame.draw.rect(surf, col, (x, y, w, h), border_radius=10)
        pygame.draw.rect(surf, COL_GOLD, (x, y, w, h), 2, border_radius=10)
        # label
        fnt = assets.font(20, bold=True)
        s = fnt.render(self.label, True, COL_CREAM)
        surf.blit(s, s.get_rect(center=self.rect.center))
 
 
# ════════════════════════════════════════════════════════════════════
#                       MAIN GAME
# ════════════════════════════════════════════════════════════════════
 
class ChessGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Chess V2")
        try:
            pygame.mixer.init()
        except pygame.error:
            pass
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
 
        self.assets = Assets()
        self.bg = CosmicBackground()
        self.particles = ParticleSystem()
        self.stamps = []
        self.memes = []
        self.show_memes = True
 
        self.gs = GameState()
        self.valid_moves = self.gs.get_valid_moves()
 
        self.selected = None        # (r, c)
        self.move_from_to = None    # ((r1,c1),(r2,c2)) being animated
        self.anim_progress = 0
        self.anim_move = None
        self.anim_callback = None
        self.last_move = None
        self.flipped = False
        self.shake = 0
        self.promotion_pending = None    # Move awaiting promotion choice
        self.promotion_buttons = []
        self.captured = {"w": [], "b": []}
        self.game_over_t = 0
        self.setup_active = True
        self.time_options = [1, 3, 5, 10, 15, 30]
        self.time_index = 3
        self.base_time = self.time_options[self.time_index] * 60
        self.time_left = {"w": self.base_time, "b": self.base_time}
        self.last_clock_tick = pygame.time.get_ticks()
        self.timeout_winner = None
        self.low_time_alerted = {"w": False, "b": False}
        self.premove_selected = None
        self.premove = None
 
        # Buttons
        bx = SIDE_X + 20
        by = HEIGHT - 130
        bw = (SIDE_W - 80) // 3
        self.buttons = {
            "new":  Button((bx,             by, bw, 50), "NEW GAME", COL_ACCENT),
            "undo": Button((bx + bw + 20,   by, bw, 50), "UNDO",     COL_CYAN),
            "flip": Button((bx + 2*(bw+20), by, bw, 50), "FLIP",     COL_GOLD),
        }
        cx = WIDTH // 2
        cy = HEIGHT // 2
        self.setup_buttons = {
            "minus": Button((cx - 170, cy + 12, 58, 52), "-", COL_CYAN),
            "plus":  Button((cx + 112, cy + 12, 58, 52), "+", COL_CYAN),
            "start": Button((cx - 105, cy + 88, 210, 56), "START", COL_GOLD),
        }
        self.move_scroll = 0
 
    # ────────────────────────────────────────────────
    #                   GAME LOOP
    # ────────────────────────────────────────────────
 
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif self.setup_active and event.key in (pygame.K_LEFT, pygame.K_a):
                        self._change_time(-1)
                    elif self.setup_active and event.key in (pygame.K_RIGHT, pygame.K_d):
                        self._change_time(1)
                    elif self.setup_active and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self._start_game()
                    elif event.key == pygame.K_r:
                        self._reset()
                    elif event.key == pygame.K_u:
                        self._undo()
                    elif event.key == pygame.K_f:
                        self.flipped = not self.flipped
                    elif event.key == pygame.K_m:
                        self.show_memes = not self.show_memes
                    elif event.key == pygame.K_MINUSEQUALS if False else False:
                        pass
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._on_click(event.pos)
                elif event.type == pygame.MOUSEWHEEL:
                    self.move_scroll = max(0, self.move_scroll - event.y * 30)
 
            self._update()
            self._draw()
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()
 
    # ────────────────────────────────────────────────
    #                   INPUT
    # ────────────────────────────────────────────────
 
    def _on_click(self, pos):
        if self.setup_active:
            if self.setup_buttons["minus"].update(pos, True):
                self._change_time(-1)
            elif self.setup_buttons["plus"].update(pos, True):
                self._change_time(1)
            elif self.setup_buttons["start"].update(pos, True):
                self._start_game()
            return

        # promotion overlay takes priority
        if self.promotion_pending:
            for btn, choice in self.promotion_buttons:
                if btn.collidepoint(pos):
                    mv = self.promotion_pending
                    mv.promotion = choice
                    self.promotion_pending = None
                    self.promotion_buttons = []
                    self._commit_move(mv, animate=False)
                    return
            return
 
        # UI buttons
        click_in_button = False
        if self.buttons["new"].update(pos, True):
            self._reset(); click_in_button = True
        elif self.buttons["undo"].update(pos, True):
            self._undo(); click_in_button = True
        elif self.buttons["flip"].update(pos, True):
            self.flipped = not self.flipped; click_in_button = True
        if click_in_button:
            return
 
        # During a move animation, allow the next side to queue a premove.
        if self.anim_move is not None:
            self._on_premove_click(pos)
            return
        if self.gs.checkmate or self.gs.stalemate or self.timeout_winner:
            return
 
        rc = self._pixel_to_square(pos)
        if rc is None:
            return
        r, c = rc
        piece = self.gs.board[r][c]
        if self.selected is None:
            if piece != "--" and (piece[0] == "w") == self.gs.white_to_move:
                self.selected = (r, c)
                self.assets.play("select")
        else:
            if (r, c) == self.selected:
                self.selected = None
                return
            # try to find a legal move
            target = None
            for mv in self.valid_moves:
                if (mv.r1, mv.c1) == self.selected and (mv.r2, mv.c2) == (r, c):
                    target = mv
                    break
            if target is None:
                # maybe selecting another own piece
                if piece != "--" and (piece[0] == "w") == self.gs.white_to_move:
                    self.selected = (r, c)
                else:
                    self.assets.play("illegal")
                    self.selected = None
                return
            # Promotion?
            if target.is_promotion and not target.promotion:
                self.promotion_pending = target
                self._build_promotion_buttons()
                self.selected = None
                return
            # Start animated move
            self._begin_animation(target)
            self.selected = None

    def _change_time(self, direction):
        self.time_index = max(0, min(len(self.time_options) - 1,
                                     self.time_index + direction))
        self.base_time = self.time_options[self.time_index] * 60
        self.time_left = {"w": self.base_time, "b": self.base_time}
        self.assets.play("select")

    def _start_game(self):
        self.setup_active = False
        self.timeout_winner = None
        self.last_clock_tick = pygame.time.get_ticks()
        self.low_time_alerted = {"w": False, "b": False}
        self.assets.play("start")
        self._add_stamp("START!", WIDTH // 2, HEIGHT // 2,
                        color=COL_GOLD, big=True)

    def _format_time(self, seconds):
        seconds = max(0, int(math.ceil(seconds)))
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"

    def _tick_clock(self):
        now = pygame.time.get_ticks()
        elapsed = (now - self.last_clock_tick) / 1000
        self.last_clock_tick = now
        if (self.setup_active or self.gs.checkmate or self.gs.stalemate or
                self.timeout_winner):
            return
        side = "w" if self.gs.white_to_move else "b"
        self.time_left[side] = max(0, self.time_left[side] - elapsed)
        if self.time_left[side] <= 10 and not self.low_time_alerted[side]:
            self.low_time_alerted[side] = True
            self.assets.play("notify")
        if self.time_left[side] <= 0:
            self.timeout_winner = "b" if side == "w" else "w"
            self._add_stamp("TIME!", WIDTH // 2, HEIGHT // 2 - 40,
                            color=COL_DANGER, big=True)
            self.particles.confetti(WIDTH, HEIGHT, n=140)
            self.shake = 18
            self.game_over_t = 0

    def _try_play_premove(self):
        if not self.premove or self.anim_move is not None:
            return
        start, end = self.premove
        self.premove = None
        self.premove_selected = None
        for mv in self.valid_moves:
            if (mv.r1, mv.c1) == start and (mv.r2, mv.c2) == end:
                if mv.is_promotion and not mv.promotion:
                    mv.promotion = "Q"
                self._begin_animation(mv)
                return
        self.assets.play("illegal")

    def _on_premove_click(self, pos):
        rc = self._pixel_to_square(pos)
        if rc is None:
            self.premove_selected = None
            return
        r, c = rc
        future_color = "b" if self.gs.white_to_move else "w"
        piece = self.gs.board[r][c]
        if self.premove_selected is None:
            if piece != "--" and piece[0] == future_color:
                self.premove_selected = (r, c)
                self.premove = None
                self.assets.play("select")
            else:
                self.assets.play("illegal")
        else:
            if (r, c) == self.premove_selected:
                self.premove_selected = None
                self.premove = None
                return
            self.premove = (self.premove_selected, (r, c))
            self.premove_selected = None
            self.assets.play("premove")
 
    def _build_promotion_buttons(self):
        # Centered overlay with 4 choices
        cx = BOARD_X + BOARD_PX // 2
        cy = BOARD_Y + BOARD_PX // 2
        choices = ["Q", "R", "B", "N"]
        w = 80
        total = w * 4 + 30
        start_x = cx - total // 2
        self.promotion_buttons = []
        for i, ch in enumerate(choices):
            rect = pygame.Rect(start_x + i * (w + 10), cy - w // 2, w, w)
            self.promotion_buttons.append((rect, ch))
 
    # ────────────────────────────────────────────────
    #                   MOVE COMMIT
    # ────────────────────────────────────────────────
 
    def _begin_animation(self, mv):
        self.anim_move = mv
        self.anim_progress = 0
 
    def _commit_move(self, mv, animate=True):
        # actually perform on gs
        captured_piece = self.gs.board[mv.r2][mv.c2]
        was_capture = captured_piece != "--" or mv.enpassant
        if mv.enpassant:
            captured_piece = "bP" if mv.piece == "wP" else "wP"
 
        self.gs.make_move(mv, promotion_choice=mv.promotion)
        if was_capture:
            owner = captured_piece[0]
            self.captured[owner].append(captured_piece)
 
        self.last_move = mv
        self.valid_moves = self.gs.get_valid_moves()
 
        # ── effects ──
        cx, cy = self._square_to_pixel_center(mv.r2, mv.c2)
        if was_capture:
            self.assets.play("capture")
            self.particles.burst(cx, cy, COL_GOLD, n=40, speed=7, life=45, size=5, shape="star")
            self.particles.burst(cx, cy, COL_DANGER, n=20, speed=5, life=30, size=4)
            self._add_stamp(random.choice(CAPTURE_STAMPS), cx, cy - 20)
            if self.show_memes and random.random() < 0.55:
                mm = self.assets.random_meme()
                if mm:
                    self.memes.append(MemePopup(mm, side=random.choice(["left", "right"])))
            self.shake = max(self.shake, 10)
        elif mv.castle:
            self.assets.play("castle")
            self.particles.burst(cx, cy, COL_CYAN, n=12, speed=3, life=25, size=3)
        else:
            self.assets.play("move")
            self.particles.burst(cx, cy, COL_CYAN, n=12, speed=3, life=25, size=3)
 
        if mv.castle:
            self._add_stamp("CASTLE!", cx, cy - 40, color=COL_CYAN)
            self.particles.burst(cx, cy, COL_CYAN, n=30, speed=5, life=40, size=4)
 
        if mv.promotion:
            self.assets.play("promote")
            self._add_stamp(f"PROMOTED → {mv.promotion}!", cx, cy - 40,
                            color=COL_GOLD, big=True)
            self.particles.burst(cx, cy, COL_GOLD, n=60, speed=8, life=60, size=6, shape="star")
 
        # check/checkmate
        if self.gs.checkmate:
            self.assets.play("checkmate")
            kr, kc = (self.gs.wk if self.gs.white_to_move else self.gs.bk)
            kx, ky = self._square_to_pixel_center(kr, kc)
            self._add_stamp(random.choice(MATE_STAMPS),
                            WIDTH // 2, HEIGHT // 2 - 40, color=COL_DANGER, big=True)
            self.particles.confetti(WIDTH, HEIGHT, n=180)
            self.shake = 25
            self.game_over_t = 0
        elif self.gs.in_check():
            self.assets.play("check")
            kr, kc = (self.gs.wk if self.gs.white_to_move else self.gs.bk)
            kx, ky = self._square_to_pixel_center(kr, kc)
            self._add_stamp(random.choice(CHECK_STAMPS), kx, ky - 30, color=COL_DANGER)
            self.particles.burst(kx, ky, COL_DANGER, n=30, speed=5, life=35, size=4)
            self.shake = max(self.shake, 6)
        elif self.gs.stalemate:
            self._add_stamp("STALEMATE!", WIDTH // 2, HEIGHT // 2 - 40,
                            color=COL_DIM, big=True)
        else:
            # Random flavor stamps occasionally
            roll = random.random()
            if roll < 0.10:
                self._add_stamp(random.choice(BRILLIANT), cx, cy - 30, color=COL_GOOD)
            elif roll < 0.13:
                self._add_stamp(random.choice(BLUNDER), cx, cy - 30, color=COL_DANGER)
            elif roll < 0.20:
                self._add_stamp(random.choice(RANDOM_FLAVOR), cx, cy - 30, color=COL_CYAN)
        if (not self.gs.checkmate and not self.gs.stalemate and
                not self.timeout_winner):
            self._try_play_premove()
 
    def _undo(self):
        if self.anim_move is not None or self.promotion_pending:
            return
        self.premove = None
        self.premove_selected = None
        m = self.gs.undo_move()
        if m is None:
            return
        # restore captured pile
        if m.captured != "--":
            owner = m.captured[0]
            if self.captured[owner]:
                self.captured[owner].pop()
        self.valid_moves = self.gs.get_valid_moves()
        self.last_move = self.gs.move_log[-1] if self.gs.move_log else None
        self._add_stamp("UNDONE", WIDTH // 2 - 150, BOARD_Y + 30, color=COL_DIM)
 
    def _reset(self):
        self.gs = GameState()
        self.valid_moves = self.gs.get_valid_moves()
        self.selected = None
        self.anim_move = None
        self.anim_progress = 0
        self.last_move = None
        self.captured = {"w": [], "b": []}
        self.stamps.clear()
        self.memes.clear()
        self.particles.parts.clear()
        self.shake = 0
        self.promotion_pending = None
        self.premove = None
        self.premove_selected = None
        self.timeout_winner = None
        self.base_time = self.time_options[self.time_index] * 60
        self.time_left = {"w": self.base_time, "b": self.base_time}
        self.low_time_alerted = {"w": False, "b": False}
        self.last_clock_tick = pygame.time.get_ticks()
        self.setup_active = True
        self._add_stamp("NEW GAME", WIDTH // 2, HEIGHT // 2,
                        color=COL_GOLD, big=True)
        self.particles.confetti(WIDTH, HEIGHT, n=80)
 
    # ────────────────────────────────────────────────
    #                   UPDATE
    # ────────────────────────────────────────────────
 
    def _update(self):
        self._tick_clock()
        self.bg.update()
        self.particles.update()
        self.stamps = [s for s in self.stamps if s.life > 0]
        for s in self.stamps:
            s.update()
        self.memes = [m for m in self.memes if m.life > 0]
        for m in self.memes:
            m.update()
        if self.shake > 0:
            self.shake -= 1
        # animation tick
        if self.anim_move is not None:
            self.anim_progress += 1
            # add a trail
            t = self.anim_progress / ANIM_MOVE_FRAMES
            t = min(1.0, t)
            x0, y0 = self._square_to_pixel_center(self.anim_move.r1, self.anim_move.c1)
            x1, y1 = self._square_to_pixel_center(self.anim_move.r2, self.anim_move.c2)
            # ease out cubic
            te = 1 - (1 - t) ** 3
            x = x0 + (x1 - x0) * te
            y = y0 + (y1 - y0) * te
            self.particles.trail(x, y, COL_CYAN)
            if self.anim_progress >= ANIM_MOVE_FRAMES:
                mv = self.anim_move
                self.anim_move = None
                self._commit_move(mv)
        # update buttons hover (without click) so they animate even on hover
        mp = pygame.mouse.get_pos()
        for b in self.buttons.values():
            b.hover = b.rect.collidepoint(mp)
            b.click_t = max(0, b.click_t - 1)
        for b in self.setup_buttons.values():
            b.hover = b.rect.collidepoint(mp)
            b.click_t = max(0, b.click_t - 1)
        if self.gs.checkmate or self.gs.stalemate or self.timeout_winner:
            self.game_over_t += 1
 
    def _add_stamp(self, text, x, y, color=None, big=False):
        # cap stamps to avoid clutter
        if len(self.stamps) > 7:
            self.stamps.pop(0)
        self.stamps.append(TextStamp(text, x, y, self.assets, color=color, big=big))
 
    # ────────────────────────────────────────────────
    #                   COORDS
    # ────────────────────────────────────────────────
 
    def _square_to_pixel_center(self, r, c):
        if self.flipped:
            r = 7 - r; c = 7 - c
        return (BOARD_X + c * SQUARE + SQUARE // 2,
                BOARD_Y + r * SQUARE + SQUARE // 2)
 
    def _square_to_pixel_topleft(self, r, c):
        if self.flipped:
            r = 7 - r; c = 7 - c
        return (BOARD_X + c * SQUARE, BOARD_Y + r * SQUARE)
 
    def _pixel_to_square(self, pos):
        x, y = pos
        if not (BOARD_X <= x < BOARD_X + BOARD_PX and BOARD_Y <= y < BOARD_Y + BOARD_PX):
            return None
        c = (x - BOARD_X) // SQUARE
        r = (y - BOARD_Y) // SQUARE
        if self.flipped:
            r = 7 - r; c = 7 - c
        return int(r), int(c)
 
    # ────────────────────────────────────────────────
    #                   DRAW
    # ────────────────────────────────────────────────
 
    def _draw(self):
        # apply shake offset by drawing to off-screen if shaking
        target = self.screen
        offx, offy = 0, 0
        if self.shake > 0:
            offx = random.randint(-self.shake, self.shake)
            offy = random.randint(-self.shake, self.shake)
            target = pygame.Surface((WIDTH, HEIGHT))
 
        self.bg.draw(target)
        self._draw_board(target)
        self._draw_highlights(target)
        self._draw_pieces(target)
        self._draw_animating_piece(target)
        self.particles.draw(target)
        self._draw_side_panel(target)
        self._draw_title(target)
        for s in self.stamps:
            s.draw(target)
        if self.show_memes:
            for m in self.memes:
                m.draw(target)
        if self.promotion_pending:
            self._draw_promotion_overlay(target)
        if self.setup_active:
            self._draw_setup_overlay(target)
        if self.gs.checkmate or self.gs.stalemate or self.timeout_winner:
            self._draw_game_over(target)
 
        if self.shake > 0:
            self.screen.fill((0, 0, 0))
            self.screen.blit(target, (offx, offy))
 
    def _draw_board(self, surf):
        # Board glow
        glow = pygame.Surface((BOARD_PX + 60, BOARD_PX + 60), pygame.SRCALPHA)
        for i in range(20, 0, -1):
            a = 3 + i // 2
            pygame.draw.rect(glow, (*COL_ACCENT, a),
                             (30 - i, 30 - i, BOARD_PX + i * 2, BOARD_PX + i * 2),
                             border_radius=12 + i)
        surf.blit(glow, (BOARD_X - 30, BOARD_Y - 30), special_flags=pygame.BLEND_ADD)
 
        # frame
        frame = pygame.Rect(BOARD_X - 6, BOARD_Y - 6, BOARD_PX + 12, BOARD_PX + 12)
        pygame.draw.rect(surf, (24, 16, 50), frame, border_radius=8)
        pygame.draw.rect(surf, COL_GOLD, frame, 2, border_radius=8)
 
        for r in range(8):
            for c in range(8):
                light = (r + c) % 2 == 0
                col = COL_LIGHT_SQ if light else COL_DARK_SQ
                draw_r, draw_c = (7 - r, 7 - c) if self.flipped else (r, c)
                x = BOARD_X + draw_c * SQUARE
                y = BOARD_Y + draw_r * SQUARE
                pygame.draw.rect(surf, col, (x, y, SQUARE, SQUARE))
 
        # Coordinate labels
        fnt = self.assets.font(14, bold=True)
        for i in range(8):
            file_ch = Move.FILES[i]
            rank_ch = Move.RANKS[i]
            if self.flipped:
                file_ch = Move.FILES[7 - i]
                rank_ch = Move.RANKS[7 - i]
            col = COL_DARK_SQ if (7 + i) % 2 == 0 else COL_LIGHT_SQ
            s = fnt.render(file_ch, True, col)
            surf.blit(s, (BOARD_X + i * SQUARE + SQUARE - 14, BOARD_Y + BOARD_PX - 16))
            col2 = COL_DARK_SQ if (i) % 2 == 0 else COL_LIGHT_SQ
            s2 = fnt.render(rank_ch, True, col2)
            surf.blit(s2, (BOARD_X + 4, BOARD_Y + i * SQUARE + 4))
 
    def _draw_highlights(self, surf):
        # last move
        if self.last_move and self.anim_move is None:
            for (r, c) in [(self.last_move.r1, self.last_move.c1),
                           (self.last_move.r2, self.last_move.c2)]:
                x, y = self._square_to_pixel_topleft(r, c)
                s = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
                s.fill((255, 185, 56, 75))
                surf.blit(s, (x, y))

        if self.premove:
            for (r, c) in self.premove:
                x, y = self._square_to_pixel_topleft(r, c)
                s = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
                s.fill((255, 50, 70, 95))
                surf.blit(s, (x, y))
                pygame.draw.rect(surf, COL_DANGER, (x, y, SQUARE, SQUARE), 3)
        elif self.premove_selected:
            x, y = self._square_to_pixel_topleft(*self.premove_selected)
            s = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
            s.fill((255, 50, 70, 80))
            surf.blit(s, (x, y))
            pygame.draw.rect(surf, COL_DANGER, (x, y, SQUARE, SQUARE), 3)
 
        # check on king
        if self.gs.in_check() and not self.gs.checkmate and self.anim_move is None:
            kr, kc = (self.gs.wk if self.gs.white_to_move else self.gs.bk)
            x, y = self._square_to_pixel_topleft(kr, kc)
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.012)
            for i in range(6, 0, -1):
                a = int(40 * pulse + i * 10)
                pygame.draw.rect(surf, (255, 70, 90, a),
                                 (x - i, y - i, SQUARE + i * 2, SQUARE + i * 2),
                                 2, border_radius=4)
 
        # selected
        if self.selected and self.anim_move is None:
            r, c = self.selected
            x, y = self._square_to_pixel_topleft(r, c)
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.01)
            s = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
            s.fill((110, 240, 255, int(70 + 50 * pulse)))
            surf.blit(s, (x, y))
            pygame.draw.rect(surf, COL_CYAN, (x, y, SQUARE, SQUARE), 3)
 
            # legal moves
            for mv in self.valid_moves:
                if (mv.r1, mv.c1) == self.selected:
                    mx, my = self._square_to_pixel_center(mv.r2, mv.c2)
                    is_cap = self.gs.board[mv.r2][mv.c2] != "--" or mv.enpassant
                    pulse2 = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.008
                                                  + (mv.r2 + mv.c2))
                    if is_cap:
                        # ring
                        for w in range(3, 0, -1):
                            pygame.draw.circle(surf, COL_GOLD, (mx, my),
                                               int(SQUARE * 0.42), w)
                    else:
                        dotsurf = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
                        pygame.draw.circle(dotsurf, (110, 240, 255, int(150 * pulse2)),
                                           (SQUARE // 2, SQUARE // 2),
                                           int(SQUARE * 0.16))
                        surf.blit(dotsurf, (mx - SQUARE // 2, my - SQUARE // 2))
 
    def _draw_pieces(self, surf):
        # Skip the piece that is currently being animated
        skip = None
        if self.anim_move is not None:
            skip = (self.anim_move.r1, self.anim_move.c1)
        for r in range(8):
            for c in range(8):
                if (r, c) == skip:
                    continue
                p = self.gs.board[r][c]
                if p == "--":
                    continue
                x, y = self._square_to_pixel_center(r, c)
                self.assets.draw_piece(surf, p, x, y)
 
    def _draw_animating_piece(self, surf):
        if self.anim_move is None:
            return
        m = self.anim_move
        t = min(1.0, self.anim_progress / ANIM_MOVE_FRAMES)
        te = 1 - (1 - t) ** 3
        x0, y0 = self._square_to_pixel_center(m.r1, m.c1)
        x1, y1 = self._square_to_pixel_center(m.r2, m.c2)
        x = x0 + (x1 - x0) * te
        y = y0 + (y1 - y0) * te
        # tiny lift for knights & captures
        if m.piece[1] == "N" or self.gs.board[m.r2][m.c2] != "--":
            arc = math.sin(t * math.pi) * 14
            y -= arc
        self.assets.draw_piece(surf, m.piece, int(x), int(y))
 
    def _draw_side_panel(self, surf):
        # Panel background
        panel_rect = pygame.Rect(SIDE_X, 30, SIDE_W, HEIGHT - 60)
        panel = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
        panel.fill(COL_PANEL)
        pygame.draw.rect(panel, COL_PANEL_BORDER, panel.get_rect(),
                         2, border_radius=14)
        surf.blit(panel, panel_rect.topleft)
 
        x0 = panel_rect.x + 24
        y = panel_rect.y + 20
 
        # Title
        title_fnt = self.assets.font(32, bold=True)
        title = title_fnt.render("CHESS V2", True, COL_GOLD)
        surf.blit(title, (x0, y))
        y += 50
 
        # Turn indicator
        turn_fnt = self.assets.font(20, bold=True)
        if self.timeout_winner:
            mover = ("WHITE" if self.timeout_winner == "w" else "BLACK") + " WINS ON TIME"
            col = COL_GOOD
        elif self.gs.checkmate:
            mover = "WHITE WINS" if not self.gs.white_to_move else "BLACK WINS"
            col = COL_GOOD
        elif self.gs.stalemate:
            mover = "STALEMATE"
            col = COL_DIM
        else:
            mover = ("WHITE" if self.gs.white_to_move else "BLACK") + " TO MOVE"
            col = COL_CREAM
        pulse = 0.7 + 0.3 * math.sin(pygame.time.get_ticks() * 0.005)
        glow_col = tuple(int(c * pulse) for c in (col[:3]))
        s = turn_fnt.render(mover, True, glow_col)
        surf.blit(s, (x0, y))
        y += 40

        clock_fnt = self.assets.font(30, bold=True)
        small_fnt = self.assets.font(14, bold=True)
        for side, label in [("b", "BLACK"), ("w", "WHITE")]:
            active = (side == ("w" if self.gs.white_to_move else "b") and
                      not self.setup_active and not self.timeout_winner and
                      not self.gs.checkmate and not self.gs.stalemate)
            box = pygame.Rect(x0, y, panel_rect.right - x0 - 24, 42)
            fill = (255, 255, 255, 22) if active else (255, 255, 255, 10)
            pygame.draw.rect(surf, fill, box, border_radius=8)
            if active:
                pygame.draw.rect(surf, COL_GOLD, box, 2, border_radius=8)
            label_s = small_fnt.render(label, True, COL_DIM)
            time_col = COL_DANGER if self.time_left[side] <= 10 else COL_CREAM
            time_s = clock_fnt.render(self._format_time(self.time_left[side]), True, time_col)
            surf.blit(label_s, (box.x + 12, box.y + 14))
            surf.blit(time_s, time_s.get_rect(midright=(box.right - 12, box.centery)))
            y += 50
 
        if self.gs.in_check() and not self.gs.checkmate:
            warn = self.assets.font(18, bold=True).render("✦ CHECK", True, COL_DANGER)
            surf.blit(warn, (x0, y))
            y += 28
 
        # Captured pieces
        cap_fnt = self.assets.font(16, bold=True)
        for owner, label in [("b", "WHITE CAPTURED"), ("w", "BLACK CAPTURED")]:
            lab = cap_fnt.render(label, True, COL_DIM)
            surf.blit(lab, (x0, y))
            y += 24
            row_x = x0
            for piece in self.captured[owner]:
                self.assets.draw_piece(surf, piece, row_x + 16, y + 16,
                                       size=int(SQUARE * 0.45))
                row_x += 34
                if row_x > panel_rect.right - 60:
                    row_x = x0; y += 36
            y += 40
 
        # Move log header
        log_fnt = self.assets.font(16, bold=True)
        surf.blit(log_fnt.render("MOVE LOG", True, COL_DIM), (x0, y))
        y += 24
 
        # Move log (paged)
        log_rect = pygame.Rect(x0, y, panel_rect.right - x0 - 24, HEIGHT - y - 180)
        # subtle background for log
        log_bg = pygame.Surface((log_rect.w, log_rect.h), pygame.SRCALPHA)
        log_bg.fill((255, 255, 255, 8))
        pygame.draw.rect(log_bg, (110, 80, 200, 80), log_bg.get_rect(),
                         1, border_radius=8)
        surf.blit(log_bg, log_rect.topleft)
 
        # render pairs
        mv_fnt = self.assets.font(15)
        lines = []
        for i in range(0, len(self.gs.move_log), 2):
            wm = self.gs.move_log[i].notation()
            bm = self.gs.move_log[i + 1].notation() if i + 1 < len(self.gs.move_log) else ""
            lines.append(f"{i // 2 + 1}. {wm:<8} {bm}")
        line_h = 20
        max_visible = log_rect.h // line_h
        start_idx = max(0, len(lines) - max_visible)
        # auto-scroll to bottom
        for i, ln in enumerate(lines[start_idx:]):
            ts = mv_fnt.render(ln, True, COL_CREAM)
            surf.blit(ts, (log_rect.x + 12, log_rect.y + 6 + i * line_h))
 
        # Buttons
        for b in self.buttons.values():
            b.draw(surf, self.assets)
 
        # Hint line at bottom
        hint = self.assets.font(13).render(
            "R: reset · U: undo · F: flip · M: memes · Esc: quit",
            True, COL_DIM)
        surf.blit(hint, (panel_rect.x + 20, panel_rect.bottom - 26))
 
    def _draw_title(self, surf):
        # subtle floating title-bar above board
        fnt = self.assets.font(16, bold=True)
        sub = "♛ " + ("WHITE" if self.gs.white_to_move else "BLACK") + "'s turn ♛"
        if self.gs.checkmate or self.timeout_winner:
            sub = "♛ GAME OVER ♛"
        s = fnt.render(sub, True, COL_DIM)
        surf.blit(s, (BOARD_X, BOARD_Y - 28))

    def _draw_setup_overlay(self, surf):
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 165))
        surf.blit(dim, (0, 0))

        cx = WIDTH // 2
        cy = HEIGHT // 2
        panel = pygame.Rect(cx - 260, cy - 185, 520, 370)
        pygame.draw.rect(surf, (22, 18, 44), panel, border_radius=14)
        pygame.draw.rect(surf, COL_GOLD, panel, 3, border_radius=14)

        title = self.assets.font(46, bold=True).render("CHESS V2", True, COL_GOLD)
        surf.blit(title, title.get_rect(center=(cx, cy - 118)))
        label = self.assets.font(18, bold=True).render("CHOOSE TIME", True, COL_DIM)
        surf.blit(label, label.get_rect(center=(cx, cy - 58)))

        value = self.assets.font(54, bold=True).render(
            f"{self.time_options[self.time_index]} MIN", True, COL_CREAM)
        surf.blit(value, value.get_rect(center=(cx, cy + 38)))

        for b in self.setup_buttons.values():
            b.draw(surf, self.assets)

        hint = self.assets.font(14).render(
            "Left/Right: change time    Enter: start",
            True, COL_DIM)
        surf.blit(hint, hint.get_rect(center=(cx, cy + 158)))
 
    def _draw_promotion_overlay(self, surf):
        # Dim background
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        surf.blit(dim, (0, 0))
 
        cx = BOARD_X + BOARD_PX // 2
        cy = BOARD_Y + BOARD_PX // 2
        title = self.assets.font(36, bold=True).render(
            "CHOOSE PROMOTION", True, COL_GOLD)
        surf.blit(title, title.get_rect(center=(cx, cy - 100)))
 
        mp = pygame.mouse.get_pos()
        owner = self.promotion_pending.piece[0]
        for rect, ch in self.promotion_buttons:
            hover = rect.collidepoint(mp)
            col = COL_ACCENT if hover else (60, 40, 100)
            pygame.draw.rect(surf, col, rect, border_radius=12)
            pygame.draw.rect(surf, COL_GOLD, rect, 3, border_radius=12)
            self.assets.draw_piece(surf, owner + ch, rect.centerx, rect.centery,
                                   size=int(rect.w * 0.85))
 
    def _draw_game_over(self, surf):
        if self.game_over_t < 30:
            return  # let initial confetti show
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        surf.blit(dim, (0, 0))
        # huge text
        big = self.assets.font(80, bold=True)
        if self.timeout_winner:
            winner = "WHITE WINS" if self.timeout_winner == "w" else "BLACK WINS"
            col = COL_GOLD
        elif self.gs.checkmate:
            winner = "BLACK WINS" if self.gs.white_to_move else "WHITE WINS"
            col = COL_GOLD
        else:
            winner = "STALEMATE"
            col = COL_DIM
        text = big.render(winner, True, col)
        outline = big.render(winner, True, (15, 10, 30))
        cx = WIDTH // 2; cy = HEIGHT // 2
        for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
            surf.blit(outline, outline.get_rect(center=(cx + dx, cy + dy)))
        surf.blit(text, text.get_rect(center=(cx, cy)))
        sub = self.assets.font(20).render("press R to play again",
                                          True, COL_CREAM)
        surf.blit(sub, sub.get_rect(center=(cx, cy + 70)))
 
 
# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    ChessGame().run()
