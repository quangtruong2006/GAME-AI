# stages/stage4_forest.py
import pygame
import os
import json
import random
import math
from typing import Set, Tuple, Dict, Optional

from algorithms.complex_environments.and_or_search import (
    PortalDef, NondetGridProblem, AndOrSearch,
)
from algorithms.complex_environments.online_search import OnlineReplanningAStar
from algorithms.complex_environments.belief_search import BeliefSearchAgent

DIRS = {
    pygame.K_UP:    (-1, 0),
    pygame.K_DOWN:  ( 1, 0),
    pygame.K_LEFT:  ( 0,-1),
    pygame.K_RIGHT: ( 0, 1),
}

# ── Màu sắc ───────────────────────────────────────────────────────────
C_WATER_BLOCK = (40,  120, 255)
C_WATER_FENCE = (0,   160, 255)
C_STAR        = (255, 220,  40)
C_BELIEF_GOAL = (255, 100, 200)
C_START       = (0,   200, 255)
C_GOAL_MARK   = (255, 215,   0)
C_AGENT       = (255, 255, 255)
C_CONFIRMED   = (80,  255, 120)
C_ELIMINATED  = (120, 120, 120)

C_PORTAL = {
    "C1": (200, 100, 255),
    "C2": (100, 220, 255),
    "C3": (255, 160,  60),
}
C_PORTAL_DEST = {
    "A": (100, 220, 255),
    "B": (100, 220, 255),
    "C": (255, 200,  50),
    "D": (255, 200,  50),
    "E": (255, 200,  50),
}


class Stage4Forest:
    ROWS = 40
    COLS = 39

    ALG_ONLINE = "online"
    ALG_ANDOR  = "andor"
    ALG_BELIEF = "belief"

    WATER_TILE_PATH  = "assets/images/water_tile.png"
    STAR_IMG_PATH    = "assets/images/star.png"
    QMARK_IMG_PATH   = "assets/images/question_mark.png"
    PORTAL_IMG_PATH  = "assets/images/portal.png"
    MAP_PATH         = "assets/maps/stage4_map.json"

    # ==================================================================
    def __init__(self, screen, stage_manager):
        self.screen        = screen
        self.stage_manager = stage_manager
        self.left_w        = 320

        # ── Fonts ─────────────────────────────────────────────────────
        try:
            self.font       = pygame.font.Font("assets/fonts/minecraft.ttf", 20)
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 24)
            self.small_font = pygame.font.Font("assets/fonts/minecraft.ttf", 17)
            self.tiny_font  = pygame.font.Font("assets/fonts/minecraft.ttf", 14)
        except Exception:
            self.font       = pygame.font.SysFont("Arial", 18, bold=True)
            self.title_font = pygame.font.SysFont("Arial", 22, bold=True)
            self.small_font = pygame.font.SysFont("Arial", 16)
            self.tiny_font  = pygame.font.SysFont("Arial", 14, bold=True)

        # ── Background map ────────────────────────────────────────────
        self.map_bg_raw         = None
        self.map_bg_scaled      = None
        self.map_bg_scaled_size = None
        bg_path = "assets/images/stage4_grid.png"
        if os.path.exists(bg_path):
            self.map_bg_raw = pygame.image.load(bg_path).convert()
        else:
            print("[WARN] Missing:", bg_path)

        # ── Water tile ────────────────────────────────────────────────
        self.water_raw         = None
        self.water_scaled      = None
        self.water_scaled_size = None
        if os.path.exists(self.WATER_TILE_PATH):
            self.water_raw = pygame.image.load(self.WATER_TILE_PATH).convert_alpha()
        else:
            print("[WARN] Missing:", self.WATER_TILE_PATH)

        # ── Star image ────────────────────────────────────────────────
        self.star_raw         = None
        self.star_scaled      = None
        self.star_scaled_size = None
        if os.path.exists(self.STAR_IMG_PATH):
            self.star_raw = pygame.image.load(self.STAR_IMG_PATH).convert_alpha()
        else:
            print("[WARN] Missing:", self.STAR_IMG_PATH)

        # ── Question mark image ───────────────────────────────────────
        self.qmark_raw         = None
        self.qmark_scaled      = None
        self.qmark_scaled_size = None
        if os.path.exists(self.QMARK_IMG_PATH):
            self.qmark_raw = pygame.image.load(self.QMARK_IMG_PATH).convert_alpha()
        else:
            print("[WARN] Missing:", self.QMARK_IMG_PATH)

        # ── Portal image ──────────────────────────────────────────────
        self.portal_raw         = None
        self.portal_scaled      = None
        self.portal_scaled_size = None
        if os.path.exists(self.PORTAL_IMG_PATH):
            self.portal_raw = pygame.image.load(self.PORTAL_IMG_PATH).convert_alpha()
        else:
            print("[WARN] Missing:", self.PORTAL_IMG_PATH)

        self._portal_tinted_cache: Dict[str, pygame.Surface] = {}
        self._portal_tinted_size  = None

        os.makedirs("assets/maps", exist_ok=True)

        # ── Algorithm state ───────────────────────────────────────────
        self.selected_algo = self.ALG_ONLINE
        self.auto          = False
        self.andor_policy  = None

        # ── Map data ──────────────────────────────────────────────────
        self.START:        Tuple[int, int]      = (14, 2)
        self.GOAL:         Tuple[int, int]      = (30, 34)
        self.blocked:      Set[Tuple[int, int]] = set()
        self.fences:       Set[Tuple[int, int]] = set()
        self.stars:        Set[Tuple[int, int]] = set()
        self.belief_goals: Set[Tuple[int, int]] = set()

        # ── AND-OR portals / points ───────────────────────────────────
        self.POINTS: Dict[str, Tuple[int,int]] = {
            "A":  (5,  5),
            "B":  (4,  29),
            "C":  (35, 34),
            "D":  (38, 27),
            "E":  (32, 17),
            "C1": (20, 10),
            "C2": (10,  8),
            "C3": (10, 28),
        }

        self.moving_portal: Optional[str] = None

        self._rebuild_portals()

        # ── Load map ──────────────────────────────────────────────────
        self._load_map()

        # ── Agent ─────────────────────────────────────────────────────
        self.agent_r, self.agent_c = self.START
        self.collected_stars: Set[Tuple[int, int]] = set()

        # ── Fog ───────────────────────────────────────────────────────
        self.fog_enabled = False
        self.fog_alpha   = 220
        self.explored:   Set[Tuple[int, int]] = set()
        self._init_explored()

        # ── Edit mode ─────────────────────────────────────────────────
        self.edit_mode     = False
        self.pending_place = None
        self.edit_tool     = "block"

        # ── Tốc độ tự động ───────────────────────────────────────────
        self.nobita_speed    = 280
        self.auto_delay_ms   = 280
        self._last_auto_tick = 0

        # ── Planners ──────────────────────────────────────────────────
        self.planner = OnlineReplanningAStar(
            rows=self.ROWS, cols=self.COLS,
            start=self.START, goal=self.GOAL,
        )
        self.belief_agent = BeliefSearchAgent()

        self.belief_path_surface = None
        self._belief_board_size  = None

        self.detector_popup_text  = None
        self.detector_popup_until = 0

        self._portal_anim_tick = 0

        # ── UI ────────────────────────────────────────────────────────
        self.ui_buttons      = {}
        self.slider_rect     = None
        self.dragging_slider = False
        self.show_coords     = True

        # ── Toast ─────────────────────────────────────────────────────
        self.toast_text  = None
        self.toast_until = 0

    # ==================================================================
    #  Portal helpers
    # ==================================================================

    def _rebuild_portals(self):
        self.portals = [
            PortalDef(
                "C1", self.POINTS["C1"],
                actions_to={"C1->A": self.POINTS["A"],
                            "C1->B": self.POINTS["B"]},
            ),
            PortalDef(
                "C2", self.POINTS["C2"],
                outcomes=[self.POINTS["C"], self.POINTS["D"]],
                action_name="C2",
            ),
            PortalDef(
                "C3", self.POINTS["C3"],
                outcomes=[self.POINTS["C"], self.POINTS["E"]],
                action_name="C3",
            ),
        ]

    def _portal_tinted(self, key: str, ts: int) -> pygame.Surface:
        size = (ts, ts)
        if self._portal_tinted_size != size:
            self._portal_tinted_cache.clear()
            self._portal_tinted_size = size

        if key in self._portal_tinted_cache:
            return self._portal_tinted_cache[key]

        col = C_PORTAL.get(key, C_PORTAL_DEST.get(key, (200, 200, 255)))

        if self.portal_raw:
            img  = pygame.transform.smoothscale(self.portal_raw, size)
            tint = pygame.Surface(size, pygame.SRCALPHA)
            tint.fill((*col, 100))
            img.blit(tint, (0, 0))
        else:
            img = pygame.Surface(size, pygame.SRCALPHA)
            r_half = ts // 2
            for radius in range(r_half, 0, -1):
                alpha = int(180 * (1 - radius / r_half))
                pygame.draw.circle(img, (*col, alpha),
                                   (ts//2, ts//2), radius)
            pygame.draw.circle(img, (*col, 220), (ts//2, ts//2), max(2, ts//6))

        self._portal_tinted_cache[key] = img
        return img

    def _is_portal_key(self, key: str) -> bool:
        return key in ("C1", "C2", "C3")

    def _is_dest_key(self, key: str) -> bool:
        return key in ("A", "B", "C", "D", "E")

    # ==================================================================
    #  Helpers
    # ==================================================================

    def _all_blocked(self):
        return self.blocked | self.fences

    def _is_protected(self, cell):
        if cell is None:
            return True
        if cell in (self.START, self.GOAL):
            return True
        if not self.edit_mode:
            if cell in self.POINTS.values():
                return True
        return False

    def _sanitize(self):
        protected = {self.START, self.GOAL} | set(self.POINTS.values())
        for layer in (self.blocked, self.fences, self.stars, self.belief_goals):
            layer -= protected

    def _toast(self, text, ms=1800):
        self.toast_text  = text
        self.toast_until = pygame.time.get_ticks() + ms

    def _show_detector_popup(self, text, ms=2500):
        self.detector_popup_text  = text
        self.detector_popup_until = pygame.time.get_ticks() + ms

    # ==================================================================
    #  JSON
    # ==================================================================

    def _load_json(self, path):
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _extract_water_from_bg(self):
        if not self.map_bg_raw:
            return set()
        surf    = self.map_bg_raw
        iw, ih  = surf.get_size()
        tw, th  = iw / self.COLS, ih / self.ROWS
        blocked = set()
        offsets = [(0, 0), (-2, 0), (2, 0), (0, -2), (0, 2)]
        for r in range(self.ROWS):
            for c in range(self.COLS):
                cx    = int((c + 0.5) * tw)
                cy    = int((r + 0.5) * th)
                votes = 0
                for ox, oy in offsets:
                    x        = max(0, min(iw - 1, cx + ox))
                    y        = max(0, min(ih - 1, cy + oy))
                    rr,gg,bb = surf.get_at((x, y))[:3]
                    if bb > 150 and bb > rr + 40 and bb > gg + 40:
                        votes += 1
                if votes >= 3:
                    blocked.add((r, c))
        return blocked

    # ==================================================================
    #  Load / Save
    # ==================================================================

    def _load_map(self):
        data = self._load_json(self.MAP_PATH)
        if data and data.get("rows") == self.ROWS and data.get("cols") == self.COLS:
            s = data.get("start", [14, 2])
            g = data.get("goal",  [30, 34])
            self.START        = (int(s[0]), int(s[1]))
            self.GOAL         = (int(g[0]), int(g[1]))
            self.blocked      = {(int(r), int(c)) for r, c in data.get("blocked",      [])}
            self.fences       = {(int(r), int(c)) for r, c in data.get("fences",       [])}
            self.stars        = {(int(r), int(c)) for r, c in data.get("stars",        [])}
            self.belief_goals = {(int(r), int(c)) for r, c in data.get("belief_goals", [])}

            if "points" in data:
                for k, v in data["points"].items():
                    if k in self.POINTS and len(v) == 2:
                        self.POINTS[k] = (int(v[0]), int(v[1]))
            self._rebuild_portals()
        else:
            self.START        = (14, 2)
            self.GOAL         = (30, 34)
            self.blocked      = self._extract_water_from_bg()
            self.fences, self.stars, self.belief_goals = set(), set(), set()
            self._rebuild_portals()
        self._sanitize()

    def _save_map(self):
        self._sanitize()
        self._save_json(self.MAP_PATH, {
            "rows":         self.ROWS,
            "cols":         self.COLS,
            "start":        list(self.START),
            "goal":         list(self.GOAL),
            "blocked":      sorted([[r, c] for r, c in self.blocked]),
            "fences":       sorted([[r, c] for r, c in self.fences]),
            "stars":        sorted([[r, c] for r, c in self.stars]),
            "belief_goals": sorted([[r, c] for r, c in self.belief_goals]),
            "points":       {k: list(v) for k, v in self.POINTS.items()},
        })
        self._toast(f"Saved → {self.MAP_PATH}")

    # ==================================================================
    #  Switch algorithm
    # ==================================================================

    def _switch_algo(self, algo):
        self.selected_algo       = algo
        self.auto                = False
        self.andor_policy        = None
        self.belief_path_surface = None
        self.belief_agent.reset()
        self.moving_portal         = None
        self.agent_r, self.agent_c = self.START
        self.collected_stars       = set()
        self.planner.reset(start=self.START, goal=self.GOAL)
        self.fog_enabled = False
        self._init_explored()

    # ==================================================================
    #  Layout helpers
    # ==================================================================

    def _map_rect(self):
        sw, sh = self.screen.get_size()
        return pygame.Rect(self.left_w, 0, sw - self.left_w, sh)

    def _tile_size(self):
        mr = self._map_rect()
        return max(8, min(mr.w // self.COLS, mr.h // self.ROWS))

    def _board_rect(self):
        mr   = self._map_rect()
        ts   = self._tile_size()
        w, h = ts * self.COLS, ts * self.ROWS
        x    = mr.x + (mr.w - w) // 2
        y    = mr.y + (mr.h - h) // 2
        return pygame.Rect(x, y, w, h), ts

    def _px_to_cell(self, px, py):
        board, ts = self._board_rect()
        if not board.collidepoint(px, py):
            return None
        c = (px - board.x) // ts
        r = (py - board.y) // ts
        if 0 <= r < self.ROWS and 0 <= c < self.COLS:
            return int(r), int(c)
        return None

    def _cell_to_px(self, r, c):
        board, ts = self._board_rect()
        return board.x + c * ts, board.y + r * ts, ts

    # ==================================================================
    #  Fog
    # ==================================================================

    def _visible_cells(self):
        vis = set()
        for rr in range(self.agent_r - 1, self.agent_r + 2):
            for cc in range(self.agent_c - 1, self.agent_c + 2):
                if 0 <= rr < self.ROWS and 0 <= cc < self.COLS:
                    vis.add((rr, cc))
        return vis

    def _sense(self):
        blk = self._all_blocked()
        return {cell: (cell in blk) for cell in self._visible_cells()}

    def _init_explored(self):
        self.explored = {(self.agent_r, self.agent_c)} | self._visible_cells()

    def _reveal(self):
        self.explored |= self._visible_cells()

    # ==================================================================
    #  Movement
    # ==================================================================

    def _can_move_to(self, r, c):
        return (0 <= r < self.ROWS and 0 <= c < self.COLS
                and (r, c) not in self._all_blocked())

    def _move(self, dr, dc):
        nr, nc = self.agent_r + dr, self.agent_c + dc
        if self._can_move_to(nr, nc):
            self.agent_r, self.agent_c = nr, nc
            self._on_enter_cell(nr, nc)

    def _on_enter_cell(self, r, c):
        cell = (r, c)
        if cell in self.stars and cell not in self.collected_stars:
            self.collected_stars.add(cell)
            if self.selected_algo == self.ALG_BELIEF and self.auto:
                self._trigger_belief_detector(cell)
            else:
                self._toast(
                    f"⭐ Star collected! ({len(self.collected_stars)}/{len(self.stars)})"
                )
        if self.selected_algo == self.ALG_BELIEF:
            self.belief_agent.notify_position(cell)

    def _trigger_belief_detector(self, star_pos):
        result = self.belief_agent.trigger_detector(
            current_pos=(self.agent_r, self.agent_c)
        )
        if result is None:
            self._toast("⭐ Star collected! (no remaining beliefs)")
            return
        msg = result["msg"]
        self._show_detector_popup(msg, ms=3000)
        self._toast(f"⭐ Detector: {msg}", ms=3000)
        self.belief_path_surface = None
        print(f"[Detector] {msg}")

    # ==================================================================
    #  AND-OR
    # ==================================================================

    def _exec_andor_action(self, a: str):
        if   a == "U":     self._move(-1,  0)
        elif a == "D":     self._move( 1,  0)
        elif a == "L":     self._move( 0, -1)
        elif a == "R":     self._move( 0,  1)
        elif a == "C1->A": self.agent_r, self.agent_c = self.POINTS["A"]
        elif a == "C1->B": self.agent_r, self.agent_c = self.POINTS["B"]
        elif a == "C2":
            self.agent_r, self.agent_c = random.choice(
                [self.POINTS["C"], self.POINTS["D"]]
            )
        elif a == "C3":
            self.agent_r, self.agent_c = random.choice(
                [self.POINTS["C"], self.POINTS["E"]]
            )

    # ==================================================================
    #  Belief path surface
    # ==================================================================

    def _rebuild_belief_path_surface(self, board, ts):
        size = (board.w, board.h)
        if self._belief_board_size == size and self.belief_path_surface:
            return
        self._belief_board_size = size
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        seq = self.belief_agent.pos_sequence
        if len(seq) >= 2:
            pts = [(c * ts + ts // 2, r * ts + ts // 2) for (r, c) in seq]
            pygame.draw.lines(surf, (255, 180, 0, 200), False, pts, 3)
            for idx, (r, c) in enumerate(seq):
                cx, cy = c * ts + ts // 2, r * ts + ts // 2
                col    = (255, 100, 0, 180) if idx == 0 else (255, 220, 80, 160)
                pygame.draw.circle(surf, col, (cx, cy), max(3, ts // 5))
        self.belief_path_surface = surf

    # ==================================================================
    #  Draw helpers
    # ==================================================================

    def _draw_water_cells(self, board, ts, cells, alpha=255):
        if not cells:
            return
        size = (ts, ts)
        if self.water_raw:
            if self.water_scaled is None or self.water_scaled_size != size:
                self.water_scaled      = pygame.transform.smoothscale(self.water_raw, size)
                self.water_scaled_size = size
            tile = self.water_scaled
            if alpha != 255:
                tile = tile.copy(); tile.set_alpha(alpha)
            for (r, c) in cells:
                self.screen.blit(tile, (board.x + c * ts, board.y + r * ts))
        else:
            s = pygame.Surface((board.w, board.h), pygame.SRCALPHA)
            for (r, c) in cells:
                pygame.draw.rect(s, (*C_WATER_BLOCK, min(255, alpha)),
                                 (c * ts, r * ts, ts, ts))
            self.screen.blit(s, board.topleft)

    def _draw_star_cells(self, board, ts, cells):
        """Vẽ ngôi sao lớn hơn ô (150% kích thước ô)."""
        if not cells:
            return

        # Tăng kích thước sao lên 150% tile size
        star_size = int(ts * 1.5)
        offset    = (ts - star_size) // 2  # offset âm → sao tràn ra ngoài ô
        size      = (star_size, star_size)

        if self.star_raw:
            if self.star_scaled is None or self.star_scaled_size != size:
                self.star_scaled      = pygame.transform.smoothscale(self.star_raw, size)
                self.star_scaled_size = size
            for (r, c) in cells:
                x = board.x + c * ts + offset
                y = board.y + r * ts + offset
                if (r, c) in self.collected_stars:
                    dim = self.star_scaled.copy()
                    dim.set_alpha(55)
                    self.screen.blit(dim, (x, y))
                else:
                    self.screen.blit(self.star_scaled, (x, y))
        else:
            for (r, c) in cells:
                x, y   = board.x + c * ts, board.y + r * ts
                cx, cy = x + ts // 2, y + ts // 2
                col    = (100, 100, 60) if (r, c) in self.collected_stars else C_STAR
                self._fallback_draw_star(self.screen, cx, cy,
                                         max(4, int(ts * 0.70)), col)

    def _fallback_draw_star(self, surface, cx, cy, r, color):
        pts = []
        for i in range(5):
            a_out = math.radians(-90 + i * 72)
            a_in  = math.radians(-90 + i * 72 + 36)
            pts.append((cx + r       * math.cos(a_out), cy + r       * math.sin(a_out)))
            pts.append((cx + r * 0.4 * math.cos(a_in),  cy + r * 0.4 * math.sin(a_in)))
        if len(pts) >= 3:
            pygame.draw.polygon(surface, color, pts)
            pygame.draw.polygon(surface, (255, 255, 255), pts, 1)

    def _draw_qmark_cells(self, board, ts, cells):
        """Vẽ ô ? lớn hơn ô (150% kích thước ô)."""
        if not cells:
            return

        # Tăng kích thước ô ? lên 150% tile size
        qmark_size = int(ts * 1.5)
        offset     = (ts - qmark_size) // 2  # offset âm → tràn ra ngoài ô
        size       = (qmark_size, qmark_size)

        if self.qmark_raw:
            if self.qmark_scaled is None or self.qmark_scaled_size != size:
                self.qmark_scaled      = pygame.transform.smoothscale(self.qmark_raw, size)
                self.qmark_scaled_size = size
            for (r, c) in cells:
                x   = board.x + c * ts + offset
                y   = board.y + r * ts + offset
                img = self.qmark_scaled.copy()
                if (r, c) in self.belief_agent.eliminated:
                    tint = pygame.Surface(size, pygame.SRCALPHA)
                    tint.fill((80, 80, 80, 160))
                    img.blit(tint, (0, 0))
                    img.set_alpha(100)
                elif (r, c) == self.belief_agent.confirmed_goal:
                    tint = pygame.Surface(size, pygame.SRCALPHA)
                    tint.fill((80, 255, 120, 140))
                    img.blit(tint, (0, 0))
                self.screen.blit(img, (x, y))
        else:
            for (r, c) in cells:
                x, y   = board.x + c * ts, board.y + r * ts
                cx, cy = x + ts // 2, y + ts // 2
                if   (r, c) in self.belief_agent.eliminated:
                    col = C_ELIMINATED
                elif (r, c) == self.belief_agent.confirmed_goal:
                    col = C_CONFIRMED
                else:
                    col = C_BELIEF_GOAL
                pygame.draw.circle(self.screen, col, (cx, cy),
                                   max(4, int(ts * 0.70)))
                lbl = self.title_font.render("?", True, (255, 255, 255))
                self.screen.blit(lbl, (cx - lbl.get_width()  // 2,
                                       cy - lbl.get_height() // 2))

    # ==================================================================
    #  Draw portals
    # ==================================================================

    def _draw_all_portals(self, board, ts):
        """
        Luôn hiển thị cổng không gian với mọi thuật toán.
        Nếu fog bật (Online Search đang chạy) thì chỉ hiện khi đã explored.
        """
        now      = pygame.time.get_ticks()
        pulse    = 0.5 + 0.5 * math.sin(now / 300)
        show_all = self.edit_mode or not self.fog_enabled

        # ── Cổng C1, C2, C3 ──────────────────────────────────────────
        for key in ("C1", "C2", "C3"):
            pos       = self.POINTS[key]
            px, py, _ = self._cell_to_px(*pos)
            col       = C_PORTAL[key]

            # Kiểm tra fog
            if not show_all and pos not in self.explored:
                continue

            is_moving = (self.moving_portal == key)

            img = self._portal_tinted(key, ts)
            if is_moving:
                bright = img.copy()
                tint2  = pygame.Surface((ts, ts), pygame.SRCALPHA)
                tint2.fill((255, 255, 255, int(60 * pulse)))
                bright.blit(tint2, (0, 0))
                self.screen.blit(bright, (px, py))
            else:
                self.screen.blit(img, (px, py))

            halo_r = max(ts // 2 + 2, ts // 2 + int(4 * pulse))
            pygame.draw.circle(
                self.screen, (*col, int(120 * pulse + 60)),
                (px + ts // 2, py + ts // 2), halo_r, 2
            )
            self._draw_portal_label(key, px, py, ts, col, is_moving)

        # ── Điểm đích A, B, C, D, E ──────────────────────────────────
        for key in ("A", "B", "C", "D", "E"):
            pos       = self.POINTS[key]
            px, py, _ = self._cell_to_px(*pos)

            # Kiểm tra fog
            if not show_all and pos not in self.explored:
                continue

            if key in ("A", "B"):
                col = C_PORTAL["C1"]
            elif key == "D":
                col = C_PORTAL["C2"]
            elif key == "E":
                col = C_PORTAL["C3"]
            else:
                col = (200, 200, 100)

            dest_ts = max(ts * 3 // 4, 8)
            offset  = (ts - dest_ts) // 2
            img     = self._portal_tinted(key, dest_ts)
            self.screen.blit(img, (px + offset, py + offset))
            self._draw_portal_label(key, px, py, ts, col, False, is_dest=True)

        # ── Đường kết nối (chỉ khi edit) ─────────────────────────────
        if self.edit_mode:
            self._draw_portal_connections(board, ts, pulse)

    def _draw_portal_label(self, key: str, px: int, py: int, ts: int,
                            col: tuple, is_moving: bool, is_dest: bool = False):
        lbl    = self.tiny_font.render(key, True, (255, 255, 255))
        lw, lh = lbl.get_size()
        pad    = 3
        bg_w   = lw + pad * 2
        bg_h   = lh + pad * 2

        if is_dest:
            bx = px + (ts - bg_w) // 2
            by = py + ts - bg_h - 1
        else:
            bx = px + (ts - bg_w) // 2
            by = py - bg_h - 1

        bg_col  = (220, 220, 0, 210) if is_moving else (*col[:3], 200)
        bg_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        bg_surf.fill(bg_col)
        self.screen.blit(bg_surf, (bx, by))
        pygame.draw.rect(self.screen, (255, 255, 255),
                         (bx, by, bg_w, bg_h), 1, border_radius=2)
        self.screen.blit(lbl, (bx + pad, by + pad))

    def _draw_portal_connections(self, board, ts, pulse):
        connections = [
            ("C1", "A", C_PORTAL["C1"]),
            ("C1", "B", C_PORTAL["C1"]),
            ("C2", "C", C_PORTAL["C2"]),
            ("C2", "D", C_PORTAL["C2"]),
            ("C3", "C", C_PORTAL["C3"]),
            ("C3", "E", C_PORTAL["C3"]),
        ]
        for src, dst, col in connections:
            sr, sc = self.POINTS[src]
            dr, dc = self.POINTS[dst]
            sx     = board.x + sc * ts + ts // 2
            sy     = board.y + sr * ts + ts // 2
            dx     = board.x + dc * ts + ts // 2
            dy     = board.y + dr * ts + ts // 2

            total  = max(1, int(math.hypot(dx - sx, dy - sy)))
            segs   = max(4, total // (ts // 2))
            for i in range(segs):
                t0 = i / segs
                t1 = (i + 0.5) / segs
                if i % 2 == 0:
                    x0 = int(sx + (dx - sx) * t0)
                    y0 = int(sy + (dy - sy) * t0)
                    x1 = int(sx + (dx - sx) * t1)
                    y1 = int(sy + (dy - sy) * t1)
                    alpha = int(150 * pulse + 60)
                    pygame.draw.line(self.screen, (*col, alpha),
                                     (x0, y0), (x1, y1), 2)

    def _draw_detector_popup(self):
        now = pygame.time.get_ticks()
        if not self.detector_popup_text or now > self.detector_popup_until:
            self.detector_popup_text = None
            return
        sw, sh   = self.screen.get_size()
        lines    = self.detector_popup_text.split("|")
        line_h   = 36; pad = 20
        max_w    = max(self.font.size(l.strip())[0] for l in lines) + pad * 2
        box_h    = line_h * len(lines) + pad * 2
        box_x    = (sw - max_w) // 2
        box_y    = sh // 2 - box_h // 2
        bg       = pygame.Surface((max_w, box_h), pygame.SRCALPHA)
        bg.fill((20, 20, 30, 210))
        self.screen.blit(bg, (box_x, box_y))
        pygame.draw.rect(self.screen, (200, 200, 80),
                         (box_x, box_y, max_w, box_h), 2, border_radius=8)
        for i, line in enumerate(lines):
            col = (80, 255, 120) \
                  if "confirmed" in line.lower() or "goal" in line.lower() \
                  else (255, 120, 80)
            t = self.font.render(line.strip(), True, col)
            self.screen.blit(t, (box_x + pad, box_y + pad + i * line_h))

    # ==================================================================
    #  Edit mode
    # ==================================================================

    def _enter_edit(self):
        self.edit_mode     = True
        self.pending_place = None
        self.edit_tool     = "block"
        self.moving_portal = None
        self.auto          = False
        self.fog_enabled   = False

    def _save_and_exit_edit(self):
        self._sanitize()
        self._rebuild_portals()
        self._save_map()
        self.edit_mode           = False
        self.pending_place       = None
        self.moving_portal       = None
        self.fog_enabled         = False
        self.auto                = False
        self.andor_policy        = None
        self.belief_path_surface = None
        self.belief_agent.reset()
        self.agent_r, self.agent_c = self.START
        self.collected_stars       = set()
        self._portal_tinted_cache.clear()
        self.planner.reset(start=self.START, goal=self.GOAL)
        self._init_explored()

    def _set_start(self, cell):
        if cell is None: return
        self.blocked.discard(cell); self.fences.discard(cell)
        self.START = cell; self.agent_r, self.agent_c = cell

    def _set_goal(self, cell):
        if cell is None: return
        self.blocked.discard(cell); self.fences.discard(cell)
        self.GOAL = cell

    def _move_portal_to(self, key: str, cell: Tuple[int, int]):
        if cell is None: return
        if cell in (self.START, self.GOAL): return
        for k, v in self.POINTS.items():
            if k != key and v == cell:
                self._toast(f"Ô {cell} đã có điểm {k}!")
                return
        self.blocked.discard(cell)
        self.fences.discard(cell)
        old_pos = self.POINTS[key]
        self.POINTS[key] = cell
        self._rebuild_portals()
        self._portal_tinted_cache.clear()
        self._toast(f"Moved {key}: {old_pos} → {cell}")

    def _apply_tool(self, cell, button):
        if cell is None:
            return

        if self.moving_portal is not None:
            self._move_portal_to(self.moving_portal, cell)
            self.moving_portal = None
            return

        if self._is_protected(cell):
            return

        if button == 3:
            for layer in (self.blocked, self.fences, self.stars, self.belief_goals):
                layer.discard(cell)
            return

        tool = self.edit_tool
        if tool == "erase":
            for layer in (self.blocked, self.fences, self.stars, self.belief_goals):
                layer.discard(cell)
        elif tool == "block":
            self.fences.discard(cell); self.stars.discard(cell)
            self.belief_goals.discard(cell)
            if cell in self.blocked: self.blocked.remove(cell)
            else:                    self.blocked.add(cell)
        elif tool == "fence":
            self.blocked.discard(cell); self.stars.discard(cell)
            self.belief_goals.discard(cell)
            if cell in self.fences: self.fences.remove(cell)
            else:                   self.fences.add(cell)
        elif tool == "star":
            self.blocked.discard(cell); self.fences.discard(cell)
            self.belief_goals.discard(cell)
            if cell in self.stars: self.stars.remove(cell)
            else:                  self.stars.add(cell)
        elif tool == "belief_goal":
            self.blocked.discard(cell); self.fences.discard(cell)
            self.stars.discard(cell)
            if cell in self.belief_goals: self.belief_goals.remove(cell)
            else:                         self.belief_goals.add(cell)

    # ==================================================================
    #  UI helpers
    # ==================================================================

    def _button(self, name, x, y, w, h):
        r = pygame.Rect(x, y, w, h); self.ui_buttons[name] = r; return r

    def _draw_button(self, rect, label, active=False, disabled=False,
                     color=None, text_color=None):
        if disabled:
            bg, fg, border = (70,70,70),(150,150,150),(90,90,90)
        else:
            bg, fg, border = (45,55,65),(240,240,240),(120,130,140)
        if color and not disabled: bg = color; border = (255,255,255)
        if active and not disabled and color is None:
            bg = (45,110,190); border = (150,200,255)
        if text_color: fg = text_color
        pygame.draw.rect(self.screen, bg,     rect, border_radius=7)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=7)
        txt = self.font.render(label, True, fg)
        self.screen.blit(txt, (rect.x + 10,
                               rect.y + (rect.h - txt.get_height()) // 2))

    def _draw_slider(self, x, y, w, label, value, vmin, vmax):
        t = self.font.render(f"{label}: {int(value)}", True, (220,220,220))
        self.screen.blit(t, (x, y)); y += 26
        bar = pygame.Rect(x, y+10, w, 6)
        pygame.draw.rect(self.screen, (90,100,110), bar, border_radius=4)
        ratio = (value-vmin)/max(1,vmax-vmin)
        kx, ky = int(bar.x + ratio*bar.w), bar.y + bar.h//2
        pygame.draw.circle(self.screen, (220,220,220), (kx,ky), 10)
        pygame.draw.circle(self.screen, (40,40,40),    (kx,ky), 10, 2)
        self.slider_rect = pygame.Rect(bar.x, bar.y-10, bar.w, 26)
        return y + 32

    def _sep(self, y, label=""):
        pygame.draw.line(self.screen, (70,80,90),
                         (10, y+6), (self.left_w-10, y+6), 1)
        if label:
            t = self.small_font.render(label, True, (140,150,160))
            self.screen.blit(t, (14, y-1))
        return y + 18

    # ==================================================================
    #  Left panel
    # ==================================================================

    def _layout_left_panel(self):
        sw, sh = self.screen.get_size()
        panel  = pygame.Surface((self.left_w, sh), pygame.SRCALPHA)
        panel.fill((22, 28, 32, 235))
        self.screen.blit(panel, (0, 0))
        pygame.draw.line(self.screen, (75,82,90),
                         (self.left_w, 0), (self.left_w, sh), 2)

        self.ui_buttons.clear()
        self.slider_rect = None

        x, y = 12, 12
        w    = self.left_w - 24
        bh   = 38
        g    = 8

        # Title
        self.screen.blit(
            self.title_font.render("STAGE 4 – FOREST", True, (240,240,240)), (x, y))
        y += 34
        self.screen.blit(
            self.small_font.render("Shared map · all algorithms", True, (120,180,120)),
            (x, y))
        y += 26

        # ── Algorithm ──────────────────────────────────────────────────
        y = self._sep(y, "ALGORITHM")
        for key, label, col in [
            (self.ALG_ONLINE, "ONLINE SEARCH",  (30,  90, 160)),
            (self.ALG_ANDOR,  "AND-OR SEARCH",  (140, 60, 160)),
            (self.ALG_BELIEF, "BELIEF SEARCH",  (160, 80,  30)),
        ]:
            r = self._button(f"alg_{key}", x, y, w, bh)
            self._draw_button(r, label,
                              active=(self.selected_algo == key),
                              disabled=self.edit_mode,
                              color=col if self.selected_algo == key else None)
            y += bh + g

        # ── Control ────────────────────────────────────────────────────
        y = self._sep(y, "CONTROL")
        r = self._button("run_ai", x, y, w, bh)
        self._draw_button(r, "▶  RUN AI", disabled=self.edit_mode,
                          color=(35,155,85) if not self.edit_mode else None)
        y += bh + g
        r = self._button("cancel_ai", x, y, w, bh)
        self._draw_button(r, "■  CANCEL", disabled=self.edit_mode,
                          color=(190,60,60) if not self.edit_mode else None)
        y += bh + g
        r = self._button("reset", x, y, w, bh)
        self._draw_button(r, "↺  RESET", disabled=self.edit_mode,
                          color=(110,60,160) if not self.edit_mode else None)
        y += bh + g

        # ── Speed ──────────────────────────────────────────────────────
        y = self._sep(y, "SPEED")
        y = self._draw_slider(x, y, w, "ms/step", self.nobita_speed, 60, 800)

        # ── Map editor ────────────────────────────────────────────────
        y = self._sep(y, "MAP EDITOR")
        r = self._button("edit_toggle", x, y, w, bh)
        if not self.edit_mode:
            self._draw_button(r, "✏  EDIT MAP")
        else:
            self._draw_button(r, "💾  SAVE & EXIT", active=True, color=(40,120,60))
        y += bh + g

        if self.edit_mode:
            y = self._sep(y, "TOOLS")

            tw1 = (w - 2 * g) // 3
            tx  = x
            for key, lbl, col in [
                ("block", "BLOCK", (100, 70,  40)),
                ("fence", "FENCE", ( 30, 90, 180)),
                ("erase", "ERASE", (160, 50,  50)),
            ]:
                tr = self._button(f"tool_{key}", tx, y, tw1, bh)
                self._draw_button(tr, lbl,
                                  active=(self.edit_tool == key), color=col)
                tx += tw1 + g
            y += bh + g

            tw2 = (w - g) // 2
            tx  = x
            for key, lbl, col in [
                ("star",        "⭐ STAR",     (170,130, 15)),
                ("belief_goal", "?  BELIEF ?", (160, 50,160)),
            ]:
                tr = self._button(f"tool_{key}", tx, y, tw2, bh)
                self._draw_button(tr, lbl,
                                  active=(self.edit_tool == key), color=col)
                tx += tw2 + g
            y += bh + g

            hw = (w - g) // 2
            r  = self._button("place_start", x, y, hw, bh)
            self._draw_button(r, "Set START",
                              active=(self.pending_place == "START"),
                              color=(0,160,210))
            r2 = self._button("place_goal", x+hw+g, y, hw, bh)
            self._draw_button(r2, "Set GOAL",
                              active=(self.pending_place == "GOAL"),
                              color=(200,160,0))
            y += bh + g + 2

            y = self._sep(y, "MOVE PORTALS")

            tw3 = (w - 2 * g) // 3
            tx  = x
            for key in ("C1", "C2", "C3"):
                col = C_PORTAL[key]
                tr  = self._button(f"move_{key}", tx, y, tw3, bh)
                is_moving = (self.moving_portal == key)
                self._draw_button(tr, key, active=is_moving, color=col)
                tx += tw3 + g
            y += bh + g

            tw4 = (w - 4 * g) // 5
            tx  = x
            for key in ("A", "B", "C", "D", "E"):
                tr        = self._button(f"move_{key}", tx, y, tw4, bh)
                is_moving = (self.moving_portal == key)
                self._draw_button(tr, key, active=is_moving,
                                  color=(180,180,60) if is_moving else (60,60,80))
                tx += tw4 + g
            y += bh + g + 2

            if self.moving_portal:
                msg = f"Click map → place {self.moving_portal}"
                self.screen.blit(
                    self.small_font.render(msg, True, (255,255,100)), (x, y))
                y += 22
                r = self._button("cancel_move_portal", x, y, w, bh)
                self._draw_button(r, "✗  Cancel move", color=(160,50,50))
                y += bh + g
            else:
                for line, col in [
                    ("Click C1/C2/C3 to move portal",  (160,160,160)),
                    ("Click A-E to move dest point",    (160,160,160)),
                    ("Then click map to place",         (160,160,160)),
                ]:
                    self.screen.blit(
                        self.small_font.render(line, True, col), (x, y))
                    y += 20

            tool_col_map = {
                "block":       (200,200,200),
                "fence":       C_WATER_FENCE,
                "star":        C_STAR,
                "belief_goal": C_BELIEF_GOAL,
                "erase":       (255,80,80),
            }
            for line, col in [
                (f"Tool: {self.edit_tool.upper()}",
                 tool_col_map.get(self.edit_tool, (200,200,200))),
                (f"Belief goals: {len(self.belief_goals)}", C_BELIEF_GOAL),
                (f"Stars: {len(self.stars)}",               C_STAR),
                ("GOAL also in belief set",                 (200,180,100)),
            ]:
                self.screen.blit(
                    self.small_font.render(line, True, col), (x, y))
                y += 20

        else:
            for line, col in [
                ("Move: Arrow Keys", (170,170,170)),
                ("Back:  ESC",       (170,170,170)),
            ]:
                self.screen.blit(
                    self.small_font.render(line, True, col), (x, y))
                y += 22

            if self.selected_algo == self.ALG_BELIEF:
                act_b   = len(self.belief_agent.active_belief)
                elim_b  = len(self.belief_agent.eliminated)
                total_b = len(self.belief_agent.belief_goals)
                for line, col in [
                    (f"Belief pool: {total_b} (? + GOAL)", C_BELIEF_GOAL),
                    (f"Active: {act_b}  Eliminated: {elim_b}", (200,200,200)),
                    (self.belief_agent.progress,               (200,200,200)),
                    (f"Stars (detector): "
                     f"{len(self.collected_stars)}/{len(self.stars)}", C_STAR),
                ]:
                    self.screen.blit(
                        self.small_font.render(line, True, col), (x, y))
                    y += 22
                if self.belief_agent.goal_confirmed:
                    self.screen.blit(
                        self.small_font.render(
                            f"✓ Goal: {self.belief_agent.confirmed_goal}",
                            True, C_CONFIRMED), (x, y))
                    y += 22

            elif self.selected_algo == self.ALG_ANDOR:
                y = self._sep(y, "PORTAL POSITIONS")
                for key in ("C1", "C2", "C3"):
                    pos = self.POINTS[key]
                    col = C_PORTAL[key]
                    self.screen.blit(
                        self.tiny_font.render(
                            f"{key}: r={pos[0]+1} c={pos[1]+1}", True, col),
                        (x, y))
                    y += 20
            else:
                total_s  = len(self.stars)
                coll_s   = len(self.collected_stars)
                star_col = (80,220,80) \
                           if (total_s > 0 and coll_s == total_s) else C_STAR
                self.screen.blit(
                    self.small_font.render(
                        f"Stars: {coll_s}/{total_s}", True, star_col),
                    (x, y))
                y += 22

        # Toast
        now = pygame.time.get_ticks()
        if self.toast_text:
            if now <= self.toast_until:
                self.screen.blit(
                    self.font.render(self.toast_text, True, (255,255,160)),
                    (x, sh - 36))
            else:
                self.toast_text = None

    # ==================================================================
    #  Slider
    # ==================================================================

    def _set_speed_from_mouse(self, mx):
        if not self.slider_rect: return
        vmin, vmax = 60, 800
        x0 = self.slider_rect.x
        x1 = self.slider_rect.x + self.slider_rect.w
        mx = max(x0, min(x1, mx))
        self.nobita_speed  = int(vmin + (mx-x0)/(x1-x0) * (vmax-vmin))
        self.auto_delay_ms = self.nobita_speed

    # ==================================================================
    #  Panel click
    # ==================================================================

    def _handle_left_panel_click(self, pos):
        if not self.ui_buttons:
            self._layout_left_panel()
        mx, my = pos
        if mx > self.left_w:
            return False

        if self.slider_rect and self.slider_rect.collidepoint(mx, my):
            self.dragging_slider = True
            self._set_speed_from_mouse(mx)
            return True

        for name, rect in self.ui_buttons.items():
            if not rect.collidepoint(mx, my):
                continue

            if name.startswith("alg_") and not self.edit_mode:
                self._switch_algo(name[4:])
                self._toast(f"Algorithm: {name[4:].upper()}")
                return True

            if name == "run_ai" and not self.edit_mode:
                self._run_ai(); return True

            if name == "cancel_ai" and not self.edit_mode:
                self.auto            = False
                self.belief_path_surface = None
                self.belief_agent.reset()
                self.fog_enabled     = False
                self._toast("Canceled.")
                return True

            if name == "reset" and not self.edit_mode:
                self._reset_agent(); self._toast("Reset.")
                return True

            if name == "edit_toggle":
                if not self.edit_mode: self._enter_edit()
                else:                  self._save_and_exit_edit()
                return True

            if name.startswith("tool_") and self.edit_mode:
                self.edit_tool     = name[5:]
                self.pending_place = None
                self.moving_portal = None
                self._toast(f"Tool: {self.edit_tool.upper()}")
                return True

            if name == "place_start" and self.edit_mode:
                self.moving_portal = None
                self.pending_place = (None if self.pending_place == "START"
                                      else "START")
                self._toast("Click map → set START"
                            if self.pending_place else "Cancelled.")
                return True

            if name == "place_goal" and self.edit_mode:
                self.moving_portal = None
                self.pending_place = (None if self.pending_place == "GOAL"
                                      else "GOAL")
                self._toast("Click map → set GOAL"
                            if self.pending_place else "Cancelled.")
                return True

            if name.startswith("move_") and self.edit_mode:
                key = name[5:]
                if self.moving_portal == key:
                    self.moving_portal = None
                    self._toast("Cancelled move.")
                else:
                    self.moving_portal = key
                    self.pending_place = None
                    self._toast(f"Click map to place {key} "
                                f"(current: {self.POINTS[key]})")
                return True

            if name == "cancel_move_portal" and self.edit_mode:
                self.moving_portal = None
                self._toast("Move cancelled.")
                return True

        return False

    # ------------------------------------------------------------------
    def _run_ai(self):
        if self.selected_algo == self.ALG_ONLINE:
            # Bật fog chỉ khi chạy Online Search
            self.fog_enabled = True
            self._init_explored()
            self.auto = True
            self._toast("ONLINE: running… (fog ON)")

        elif self.selected_algo == self.ALG_ANDOR:
            self.fog_enabled = False
            self._rebuild_portals()
            problem = NondetGridProblem(
                rows=self.ROWS, cols=self.COLS,
                start=(self.agent_r, self.agent_c),
                goal=self.GOAL,
                blocked=self._all_blocked(),
                portals=self.portals,
            )
            solver = AndOrSearch(problem, max_expansions=50000)
            policy = solver.plan()
            if policy is None:
                self._toast("AND-OR: No policy found!")
            else:
                self.andor_policy = policy
                self.auto         = True
                self._toast(f"AND-OR: OK ({solver.expansions} nodes)")

        elif self.selected_algo == self.ALG_BELIEF:
            self.fog_enabled = False
            if not self.belief_goals:
                self._toast("Add ? cells first!"); return
            full_belief = self.belief_goals | {self.GOAL}
            ok = self.belief_agent.plan(
                rows=self.ROWS, cols=self.COLS,
                start=(self.agent_r, self.agent_c),
                belief_goals=full_belief,
                blocked=self._all_blocked(),
                true_goal=self.GOAL,
            )
            self.belief_path_surface = None
            if ok:
                self.auto = True
                self._toast(
                    f"BELIEF: {len(self.belief_agent.path)} steps | "
                    f"pool: {len(full_belief)}"
                )
            else:
                self._toast(
                    f"BELIEF: No plan! ({self.belief_agent.expansions} states)")

    def _reset_agent(self):
        self.auto                = False
        self.andor_policy        = None
        self.belief_path_surface = None
        self.detector_popup_text = None
        self.moving_portal       = None
        self.belief_agent.reset()
        self.agent_r, self.agent_c = self.START
        self.collected_stars       = set()
        self.fog_enabled           = False
        self.planner.reset(start=self.START, goal=self.GOAL)
        self._init_explored()

    # ==================================================================
    #  Stage API
    # ==================================================================

    def handle_events(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.moving_portal:
                        self.moving_portal = None
                    else:
                        self.stage_manager.change_stage("stage_select")
                if e.key in DIRS and not self.edit_mode and not self.auto:
                    self._move(*DIRS[e.key])

            elif e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:
                    if self._handle_left_panel_click(e.pos):
                        continue
                    if self.edit_mode:
                        cell = self._px_to_cell(*e.pos)
                        if cell is None: continue
                        r, c = cell

                        if self.moving_portal is not None:
                            self._move_portal_to(self.moving_portal, cell)
                            self.moving_portal = None
                            continue

                        if self.pending_place == "START":
                            self._set_start(cell)
                            self.pending_place = None
                            self._toast(f"START → r={r+1}, c={c+1}")
                        elif self.pending_place == "GOAL":
                            self._set_goal(cell)
                            self.pending_place = None
                            self._toast(f"GOAL → r={r+1}, c={c+1}")
                        else:
                            portal_clicked = None
                            for k, v in self.POINTS.items():
                                if v == cell:
                                    portal_clicked = k
                                    break
                            if portal_clicked:
                                self.moving_portal = portal_clicked
                                self._toast(
                                    f"Click map to move {portal_clicked}")
                            else:
                                self._apply_tool(cell, 1)

                elif e.button == 3 and self.edit_mode:
                    cell = self._px_to_cell(*e.pos)
                    self._apply_tool(cell, 3)

            elif e.type == pygame.MOUSEBUTTONUP:
                if e.button == 1:
                    self.dragging_slider = False

            elif e.type == pygame.MOUSEMOTION:
                if self.dragging_slider:
                    self._set_speed_from_mouse(e.pos[0])
                elif (self.edit_mode
                      and pygame.mouse.get_pressed()[0]
                      and self.pending_place is None
                      and self.moving_portal is None):
                    cell = self._px_to_cell(*e.pos)
                    if cell and not self._is_protected(cell):
                        self._apply_tool(cell, 1)

    # ------------------------------------------------------------------
    def update(self):
        if not self.edit_mode and self.fog_enabled:
            self._reveal()

        self.planner.observe(self._sense())
        self._portal_anim_tick = pygame.time.get_ticks()

        now = pygame.time.get_ticks()
        if self.edit_mode or not self.auto:
            return
        if now - self._last_auto_tick < self.auto_delay_ms:
            return
        self._last_auto_tick = now

        # ONLINE
        if self.selected_algo == self.ALG_ONLINE:
            self.planner.set_goal(self.GOAL)
            dr, dc = self.planner.next_action((self.agent_r, self.agent_c))
            if (dr, dc) != (0, 0):
                self._move(dr, dc)
                if self.fog_enabled: self._reveal()
            self.planner.set_position((self.agent_r, self.agent_c))
            if (self.agent_r, self.agent_c) == self.GOAL:
                self.auto        = False
                self.fog_enabled = False
                self._toast("🎉 Reached GOAL!")

        # AND-OR
        elif self.selected_algo == self.ALG_ANDOR:
            if not self.andor_policy: self.auto = False; return
            s = (self.agent_r, self.agent_c)
            a = self.andor_policy.get(s)
            if a is None:
                self.auto = False
                self._toast("AND-OR: no action."); return
            self._exec_andor_action(a)
            if (self.agent_r, self.agent_c) == self.GOAL:
                self.auto = False; self._toast("🎉 Reached GOAL!")

        # BELIEF
        elif self.selected_algo == self.ALG_BELIEF:
            if self.belief_agent.solved:
                self.auto = False; self._toast("🎉 Reached TRUE GOAL!"); return
            if self.belief_agent.failed or not self.belief_agent.has_next():
                self.auto = False; self._toast("BELIEF: no more steps."); return
            a = self.belief_agent.next_action()
            if a:
                dr, dc = {"U":(-1,0),"D":(1,0),"L":(0,-1),"R":(0,1)}[a]
                self._move(dr, dc)
            if self.belief_agent.solved:
                self.auto = False; self._toast("🎉 Reached TRUE GOAL!")

    # ------------------------------------------------------------------
    def draw(self):
        board, ts = self._board_rect()
        self.screen.fill((10, 12, 14))

        # ── Background ────────────────────────────────────────────────
        if self.map_bg_raw:
            size = (board.w, board.h)
            if self.map_bg_scaled is None or self.map_bg_scaled_size != size:
                self.map_bg_scaled      = pygame.transform.smoothscale(
                    self.map_bg_raw, size)
                self.map_bg_scaled_size = size
            self.screen.blit(self.map_bg_scaled, board.topleft)
        else:
            pygame.draw.rect(self.screen, (70,160,80), board)

        show_all = self.edit_mode or not self.fog_enabled

        # ── Blocked ───────────────────────────────────────────────────
        vis_blocked = self.blocked if show_all else self.blocked & self.explored
        self._draw_water_cells(board, ts, vis_blocked, alpha=110)

        # ── Fences ────────────────────────────────────────────────────
        vis_fences = self.fences if show_all else self.fences & self.explored
        self._draw_water_cells(board, ts, vis_fences, alpha=210)

        # ── Portals ───────────────────────────────────────────────────
        self._draw_all_portals(board, ts)

        # ── Belief path ───────────────────────────────────────────────
        if self.selected_algo == self.ALG_BELIEF and \
                self.belief_agent.pos_sequence:
            self._rebuild_belief_path_surface(board, ts)
            if self.belief_path_surface:
                self.screen.blit(self.belief_path_surface, board.topleft)

        # ── Belief goals & GOAL marker logic ──────────────────────────
        if self.selected_algo == self.ALG_BELIEF and not self.edit_mode:
            # Vẽ các ô belief_goals bằng ký hiệu "?"
            self._draw_qmark_cells(board, ts, self.belief_goals)
            # GOAL hiện là "?" khi đang chạy và chưa confirmed
            goal_confirmed = (self.belief_agent.goal_confirmed and
                              self.belief_agent.confirmed_goal == self.GOAL)
            if not goal_confirmed and self.auto:
                self._draw_qmark_cells(board, ts, {self.GOAL})
        else:
            vis_bgoals = (self.belief_goals if show_all
                          else self.belief_goals & self.explored)
            self._draw_qmark_cells(board, ts, vis_bgoals)

        # ── Stars ─────────────────────────────────────────────────────
        vis_stars = self.stars if show_all else self.stars & self.explored
        self._draw_star_cells(board, ts, vis_stars)

        # ── START ─────────────────────────────────────────────────────
        sx, sy, _ = self._cell_to_px(*self.START)
        pygame.draw.rect(self.screen, C_START,
                         (sx+3, sy+3, ts-6, ts-6), 3, border_radius=3)
        lbl = self.small_font.render("S", True, C_START)
        self.screen.blit(lbl, (sx + ts//2 - lbl.get_width()//2,
                               sy + ts//2 - lbl.get_height()//2))

        # ── GOAL marker ───────────────────────────────────────────────
        if self.selected_algo == self.ALG_BELIEF and not self.edit_mode:
            goal_confirmed = (self.belief_agent.goal_confirmed and
                              self.belief_agent.confirmed_goal == self.GOAL)
            show_goal_marker = (not self.auto) or goal_confirmed
        else:
            show_goal_marker = True

        if show_goal_marker:
            gx, gy, _ = self._cell_to_px(*self.GOAL)
            pygame.draw.rect(self.screen, C_GOAL_MARK,
                             (gx+2, gy+2, ts-4, ts-4), 3, border_radius=3)
            lbl = self.small_font.render("G", True, C_GOAL_MARK)
            self.screen.blit(lbl, (gx + ts//2 - lbl.get_width()//2,
                                   gy + ts//2 - lbl.get_height()//2))

        # ── Confirmed goal highlight ───────────────────────────────────
        if (self.selected_algo == self.ALG_BELIEF
                and self.belief_agent.goal_confirmed
                and not self.edit_mode):
            gr, gc    = self.belief_agent.confirmed_goal
            gx, gy, _ = self._cell_to_px(gr, gc)
            pygame.draw.rect(self.screen, C_CONFIRMED,
                             (gx+1, gy+1, ts-2, ts-2), 4, border_radius=3)
            lbl = self.small_font.render("G!", True, C_CONFIRMED)
            self.screen.blit(lbl, (gx + ts//2 - lbl.get_width()//2,
                                   gy + ts//2 - lbl.get_height()//2))

        # ── Agent ─────────────────────────────────────────────────────
        ax, ay, _ = self._cell_to_px(self.agent_r, self.agent_c)
        pygame.draw.circle(self.screen, (30,30,30),
                           (ax+ts//2, ay+ts//2), max(4, ts//3)+1)
        pygame.draw.circle(self.screen, C_AGENT,
                           (ax+ts//2, ay+ts//2), max(4, ts//3))

        # ── Fog (chỉ Online Search khi đang chạy) ─────────────────────
        if self.fog_enabled and not self.edit_mode:
            fog = pygame.Surface((board.w, board.h), pygame.SRCALPHA)
            fog.fill((0, 0, 0, self.fog_alpha))
            # Chỉ mở 3x3 xung quanh agent
            for (r, c) in self._visible_cells():
                pygame.draw.rect(fog, (0,0,0,0), (c*ts, r*ts, ts, ts))
            self.screen.blit(fog, board.topleft)

        # ── Moving portal cursor highlight ────────────────────────────
        if self.edit_mode and self.moving_portal:
            mx, my = pygame.mouse.get_pos()
            cell   = self._px_to_cell(mx, my)
            if cell:
                hr, hc    = cell
                hx, hy, _ = self._cell_to_px(hr, hc)
                col       = C_PORTAL.get(self.moving_portal, (255,255,0))
                pulse     = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 200)
                pygame.draw.rect(self.screen, col,
                                 (hx+1, hy+1, ts-2, ts-2), 3, border_radius=3)
                pygame.draw.rect(self.screen, (255,255,255),
                                 (hx+3, hy+3, ts-6, ts-6),
                                 max(1, int(2*pulse)), border_radius=2)
        elif self.edit_mode:
            mx, my = pygame.mouse.get_pos()
            cell   = self._px_to_cell(mx, my)
            if cell:
                hr, hc    = cell
                hx, hy, _ = self._cell_to_px(hr, hc)
                tool_col  = {
                    "block":       (255,140,  0),
                    "fence":       (  0,150,255),
                    "star":        (255,220,  0),
                    "belief_goal": (220,  0,220),
                    "erase":       (255, 60, 60),
                }.get(self.edit_tool, (255,255,255))
                if self.pending_place: tool_col = (0,255,0)
                pygame.draw.rect(self.screen, tool_col,
                                 (hx+1, hy+1, ts-2, ts-2), 2, border_radius=2)

        # ── Detector popup ────────────────────────────────────────────
        self._draw_detector_popup()

        # ── Coordinates ───────────────────────────────────────────────
        if self.show_coords:
            for c in range(self.COLS):
                t = self.small_font.render(str(c+1), True, (220,220,220))
                self.screen.blit(t, (board.x + c*ts + 2, board.y - 20))
            for r in range(self.ROWS):
                t = self.small_font.render(str(r+1), True, (220,220,220))
                self.screen.blit(t, (board.x - 28, board.y + r*ts + 2))

        # ── Left panel (vẽ sau cùng) ──────────────────────────────────
        self._layout_left_panel()