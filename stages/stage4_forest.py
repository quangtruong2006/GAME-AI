# stages/stage4_forest.py
import pygame
import os
import json
import random
import math
from typing import Set, Tuple, Dict, Optional
from ui.victory_panel import VictoryPanel

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

MAP_INFO = {
    "online": {
        "path":        "assets/maps/stage4_online.json",
        "title":       "RỪNG SƯƠNG MÙ",
        "subtitle":    "Online Search · Fog of War",
        "bg":          "assets/images/stage4_grid.png",
        "theme_color": (30,  90, 160),
        "desc": [
            "Rừng dày đặc, tầm nhìn giới hạn 3x3",
            "Agent tự khám phá và replanning",
            "Chỉ có vật cản, không có vật phẩm",
        ],
    },
    "andor": {
        "path":        "assets/maps/stage4_andor_extra.json",
        "title":       "RỪNG CỔNG MA THUẬT",
        "subtitle":    "AND-OR Search · Non-deterministic",
        "bg":          "assets/images/stage4_grid.png",
        "theme_color": (140, 60, 160),
        "desc": [
            "Cổng dịch chuyển ra đích ngẫu nhiên",
            "Tìm policy đảm bảo luôn về GOAL",
            "Dù cổng đưa đến đâu cũng thắng",
        ],
    },
    "belief": {
        "path":        "assets/maps/stage4_belief.json",
        "title":       "RỪNG BÍ ẨN",
        "subtitle":    "Belief Search · Unknown Goal",
        "bg":          "assets/images/stage4_grid.png",
        "theme_color": (160, 80,  30),
        "desc": [
            "GOAL ẩn trong các căn lều ?",
            "Thu thập ⭐ để detector hé lộ GOAL",
            "Loại trừ dần → xác nhận đích",
        ],
    },
}

FALLBACK_BG = "assets/images/stage4_grid.png"


# ─────────────────────────────────────────────
# Slider (giống stage1/2/3)
# ─────────────────────────────────────────────
class Slider:
    def __init__(self, rect, vmin, vmax, value, label=""):
        self.rect     = pygame.Rect(rect)
        self.vmin     = float(vmin)
        self.vmax     = float(vmax)
        self.value    = float(value)
        self.label    = label
        self.dragging = False

    def _knob_x(self):
        t = (self.value - self.vmin) / (self.vmax - self.vmin) if self.vmax != self.vmin else 0.0
        return int(self.rect.x + max(0.0, min(1.0, t)) * self.rect.w)

    def handle_event(self, event):
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            knob = pygame.Rect(0, 0, 14, self.rect.h + 8)
            knob.center = (self._knob_x(), self.rect.centery)
            if self.rect.collidepoint(event.pos) or knob.collidepoint(event.pos):
                self.dragging = True
                t = max(0.0, min(1.0, (event.pos[0] - self.rect.x) / self.rect.w if self.rect.w else 0.0))
                self.value = self.vmin + t * (self.vmax - self.vmin)
                changed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            t = max(0.0, min(1.0, (event.pos[0] - self.rect.x) / self.rect.w if self.rect.w else 0.0))
            self.value = self.vmin + t * (self.vmax - self.vmin)
            changed = True
        return changed

    def draw(self, screen, font,
             color_track=(90, 95, 100), color_fill=(40, 110, 190),
             color_knob=(235, 235, 235), text_color=(230, 230, 230)):
        if self.label:
            screen.blit(font.render(f"{self.label}: {int(self.value)}", True, text_color),
                        (self.rect.x, self.rect.y - 18))
        pygame.draw.rect(screen, color_track, self.rect, border_radius=6)
        t = max(0.0, min(1.0, (self.value - self.vmin) / (self.vmax - self.vmin)
                         if self.vmax != self.vmin else 0.0))
        pygame.draw.rect(screen, color_fill,
                         pygame.Rect(self.rect.x, self.rect.y, int(self.rect.w * t), self.rect.h),
                         border_radius=6)
        pygame.draw.circle(screen, color_knob,
                           (self._knob_x(), self.rect.centery), self.rect.h // 2 + 4)


class Stage4Forest:
    ROWS = 40
    COLS = 39

    ALG_ONLINE = "online"
    ALG_ANDOR  = "andor"
    ALG_BELIEF = "belief"

    WATER_TILE_PATH = "assets/images/water_tile.png"
    STAR_IMG_PATH   = "assets/images/star.png"
    QMARK_IMG_PATH  = "assets/images/question_mark.png"
    PORTAL_IMG_PATH = "assets/images/portal.png"

    START_IMG_PATH = "assets/images/stage4_start.png"
    GOAL_IMG_PATH  = "assets/images/stage4_goal.png"

    def __init__(self, screen, stage_manager):
        self.screen        = screen
        self.stage_manager = stage_manager
        self.left_w        = 220

        try:
            self.font       = pygame.font.Font("assets/fonts/minecraft.ttf", 14)
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 18)
            self.small_font = pygame.font.Font("assets/fonts/minecraft.ttf", 12)
            self.tiny_font  = pygame.font.Font("assets/fonts/minecraft.ttf", 11)
        except Exception:
            self.font       = pygame.font.SysFont("Arial", 14, bold=True)
            self.title_font = pygame.font.SysFont("Arial", 18, bold=True)
            self.small_font = pygame.font.SysFont("Arial", 12)
            self.tiny_font  = pygame.font.SysFont("Arial", 11, bold=True)

        self.water_raw  = self._load_img(self.WATER_TILE_PATH)
        self.star_raw   = self._load_img(self.STAR_IMG_PATH)
        self.qmark_raw  = self._load_img(self.QMARK_IMG_PATH)
        self.portal_raw = self._load_img(self.PORTAL_IMG_PATH)

        self.start_img_raw = self._load_img(self.START_IMG_PATH)
        self.goal_img_raw  = self._load_img(self.GOAL_IMG_PATH)

        self._agent_facing_right = True
        self._agent_prev_c       = -1

        self._img_cache: Dict[str, Tuple[pygame.Surface, tuple]] = {}

        self._bg_raw:         Dict[str, Optional[pygame.Surface]] = {}
        self._bg_scaled:      Dict[str, Optional[pygame.Surface]] = {}
        self._bg_scaled_size: Dict[str, Optional[tuple]]          = {}
        for algo in (self.ALG_ONLINE, self.ALG_ANDOR, self.ALG_BELIEF):
            bg_path = MAP_INFO[algo]["bg"]
            raw     = self._load_img(bg_path, alpha=False)
            if raw is None:
                raw = self._load_img(FALLBACK_BG, alpha=False)
            self._bg_raw[algo]         = raw
            self._bg_scaled[algo]      = None
            self._bg_scaled_size[algo] = None

        self._portal_tinted_cache: Dict[str, pygame.Surface] = {}
        self._portal_tinted_size  = None

        os.makedirs("assets/maps", exist_ok=True)

        self.selected_algo = self.ALG_ONLINE
        self.auto          = False
        self.andor_policy  = None

        self.START:        Tuple[int, int]      = (35, 2)
        self.GOAL:         Tuple[int, int]      = (5, 36)
        self.blocked:      Set[Tuple[int, int]] = set()
        self.fences:       Set[Tuple[int, int]] = set()
        self.stars:        Set[Tuple[int, int]] = set()
        self.belief_goals: Set[Tuple[int, int]] = set()

        self.POINTS: Dict[str, Tuple[int, int]] = {
            "A":  (5,  5),  "B":  (4,  29),
            "C":  (35, 34), "D":  (38, 27),
            "E":  (32, 17), "C1": (20, 10),
            "C2": (10,  8), "C3": (10, 28),
        }

        self.moving_portal: Optional[str] = None
        self._rebuild_portals()
        self._load_map_for_algo(self.selected_algo)

        self.agent_r, self.agent_c = self.START
        self.collected_stars: Set[Tuple[int, int]] = set()

        self.fog_enabled = False
        self.fog_alpha   = 220
        self.explored:   Set[Tuple[int, int]] = set()
        self._init_explored()

        self.edit_mode     = False
        self.pending_place = None
        self.edit_tool     = "block"

        self.step_delay_ms = 280.0
        self.slider_speed  = Slider(
            pygame.Rect(0, 0, 1, 14),
            vmin=50, vmax=800, value=self.step_delay_ms,
            label="AI speed (ms)"
        )

        self._last_auto_tick = 0

        self.planner = OnlineReplanningAStar(
            rows=self.ROWS, cols=self.COLS,
            start=self.START, goal=self.GOAL,
        )
        self.belief_agent = BeliefSearchAgent()

        self.belief_path_surface = None
        self._belief_board_size  = None

        self.detector_popup_text  = None
        self.detector_popup_until = 0
        self._portal_anim_tick    = 0

        self.ui_buttons      = {}
        self.show_coords     = True

        self.toast_text  = None
        self.toast_until = 0

        self._bob_tick   = 0
        self._bob_offset = 0

        self._rand_star_count   = 5
        self._rand_belief_count = 5

        self.victory_panel  = VictoryPanel(screen, stage_manager)
        self.steps_count    = 0
        self.nodes_expanded = 0

    # ==================================================================
    #  Asset helpers
    # ==================================================================

    def _load_img(self, path, alpha=True) -> Optional[pygame.Surface]:
        if not os.path.exists(path):
            print(f"[WARN] Missing: {path}")
            return None
        try:
            return (pygame.image.load(path).convert_alpha()
                    if alpha else
                    pygame.image.load(path).convert())
        except Exception as e:
            print(f"[WARN] Load failed {path}: {e}")
            return None

    def _scaled(self, raw: Optional[pygame.Surface],
                size: tuple) -> Optional[pygame.Surface]:
        if raw is None:
            return None
        key = (id(raw), size)
        if key not in self._img_cache or self._img_cache[key][1] != size:
            self._img_cache[key] = (
                pygame.transform.smoothscale(raw, size), size)
        return self._img_cache[key][0]

    # ==================================================================
    #  Draw cell image helper
    # ==================================================================

    def _draw_cell_img(self, raw, x, y, ts,
                       fallback_color, fallback_label,
                       scale=1.5, offset_x=0, offset_y=0,
                       flip_h=False):
        size = max(4, int(ts * scale))
        cx   = x + ts // 2 + offset_x
        cy   = y + ts // 2 + offset_y

        if raw is not None:
            img = self._scaled(raw, (size, size))
            if flip_h:
                img = pygame.transform.flip(img, True, False)
            rect = img.get_rect(center=(cx, cy))
            self.screen.blit(img, rect)
        else:
            pygame.draw.circle(self.screen, (20, 20, 20),
                               (cx, cy), max(4, ts // 2 - 1))
            pygame.draw.circle(self.screen, fallback_color,
                               (cx, cy), max(4, ts // 2 - 2), 3)
            lbl = self.small_font.render(fallback_label, True, fallback_color)
            self.screen.blit(lbl, (cx - lbl.get_width()  // 2,
                                   cy - lbl.get_height() // 2))

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
            img    = pygame.Surface(size, pygame.SRCALPHA)
            r_half = ts // 2
            for radius in range(r_half, 0, -1):
                alpha = int(180 * (1 - radius / r_half))
                pygame.draw.circle(img, (*col, alpha), (ts//2, ts//2), radius)
            pygame.draw.circle(img, (*col, 220), (ts//2, ts//2), max(2, ts//6))

        self._portal_tinted_cache[key] = img
        return img

    # ==================================================================
    #  General helpers
    # ==================================================================

    def _all_blocked(self):
        return self.blocked | self.fences

    def _is_protected(self, cell):
        if cell is None: return True
        if cell in (self.START, self.GOAL): return True
        if not self.edit_mode and cell in self.POINTS.values(): return True
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
        if not os.path.exists(path): return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================================================================
    #  Load / Save map
    # ==================================================================

    def _load_map_for_algo(self, algo: str):
        path = MAP_INFO[algo]["path"]
        data = self._load_json(path)

        default_points = {
            "online": {
                "A":  (5,  5),  "B":  (4,  29),
                "C":  (35, 34), "D":  (38, 27),
                "E":  (32, 17), "C1": (20, 10),
                "C2": (10,  8), "C3": (10, 28),
            },
            "andor": {
                "A":  (8,  10), "B":  (8,  28),
                "C":  (20, 36), "D":  (28, 36),
                "E":  (35, 36), "C1": (20,  5),
                "C2": (15, 20), "C3": (28, 20),
            },
            "belief": {
                "A":  (5,  5),  "B":  (4,  29),
                "C":  (35, 34), "D":  (38, 27),
                "E":  (32, 17), "C1": (20, 10),
                "C2": (10,  8), "C3": (10, 28),
            },
        }

        if data and data.get("rows") == self.ROWS and data.get("cols") == self.COLS:
            s = data.get("start", [35, 2])
            g = data.get("goal",  [5, 36])
            self.START   = (int(s[0]), int(s[1]))
            self.GOAL    = (int(g[0]), int(g[1]))
            self.blocked = {(int(r), int(c)) for r, c in data.get("blocked", [])}

            self.fences = (
                {(int(r), int(c)) for r, c in data.get("fences", [])}
                if algo == self.ALG_ANDOR else set()
            )
            self.stars = (
                {(int(r), int(c)) for r, c in data.get("stars", [])}
                if algo == self.ALG_BELIEF else set()
            )
            self.belief_goals = (
                {(int(r), int(c)) for r, c in data.get("belief_goals", [])}
                if algo == self.ALG_BELIEF else set()
            )

            self.POINTS = default_points[algo].copy()
            if "points" in data:
                for k, v in data["points"].items():
                    if k in self.POINTS and len(v) == 2:
                        self.POINTS[k] = (int(v[0]), int(v[1]))
            # ← THÊM: load số lượng random
            if "rand_star_count" in data:
                self._rand_star_count = int(data["rand_star_count"])
            if "rand_belief_count" in data:
                self._rand_belief_count = int(data["rand_belief_count"])
        else:
            self.START        = (35, 2)
            self.GOAL         = (5, 36)
            self.blocked      = set()
            self.fences       = set()
            self.stars        = set()
            self.belief_goals = set()
            self.POINTS       = default_points[algo].copy()

            if algo == self.ALG_BELIEF:
                self.belief_goals = {(5, 36), (8, 10), (8, 28),
                                     (20, 20), (30, 30)}
                self.stars        = {(15, 10), (25, 20), (10, 30)}

            self._save_map_for_algo(algo)

        self._sanitize()
        self._rebuild_portals()
        self._portal_tinted_cache.clear()

    def _save_map_for_algo(self, algo: str):
        self._sanitize()
        path = MAP_INFO[algo]["path"]
        data_to_save = {
            "rows":    self.ROWS,
            "cols":    self.COLS,
            "start":   list(self.START),
            "goal":    list(self.GOAL),
            "blocked": sorted([[r, c] for r, c in self.blocked]),
            "points":  {k: list(v) for k, v in self.POINTS.items()},
            "fences": (sorted([[r, c] for r, c in self.fences])
                       if algo == self.ALG_ANDOR else []),
            "stars": (sorted([[r, c] for r, c in self.stars])
                      if algo == self.ALG_BELIEF else []),
            "belief_goals": (sorted([[r, c] for r, c in self.belief_goals])
                             if algo == self.ALG_BELIEF else []),
            # ← THÊM: lưu số lượng random để lần sau load lại
            "rand_star_count":   self._rand_star_count,
            "rand_belief_count": self._rand_belief_count,
        }
        self._save_json(path, data_to_save)
        self._toast(f"Saved → {path}")

    # ==================================================================
    #  Switch algorithm
    # ==================================================================

    def _switch_algo(self, algo: str):
        self.selected_algo       = algo
        self.auto                = False
        self.andor_policy        = None
        self.belief_path_surface = None
        self.belief_agent.reset()
        self.moving_portal       = None
        self.fog_enabled         = False
        self.pending_place       = None
        self.edit_tool           = "block"

        self._load_map_for_algo(algo)

        self.agent_r, self.agent_c   = self.START
        self._agent_facing_right     = True
        self._agent_prev_c           = self.START[1]
        self.collected_stars         = set()
        self.planner.reset(start=self.START, goal=self.GOAL)
        self._init_explored()
        self.steps_count    = 0
        self.nodes_expanded = 0

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
        if not board.collidepoint(px, py): return None
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
            if nc > self.agent_c:
                self._agent_facing_right = True
            elif nc < self.agent_c:
                self._agent_facing_right = False
            self.agent_r, self.agent_c = nr, nc
            self._on_enter_cell(nr, nc)

    def _on_enter_cell(self, r, c):
        cell = (r, c)

        if cell in self.stars and cell not in self.collected_stars:
            self.collected_stars.add(cell)
            if self.selected_algo == self.ALG_BELIEF and self.auto:
                self._trigger_belief_detector(cell)
                self.belief_path_surface = None  # ← XÓA ĐƯỜNG VẼ CŨ NGAY LẬP TỨC
            else:
                self._toast(
                    f"⭐ Star collected! "
                    f"({len(self.collected_stars)}/{len(self.stars)})"
                )

        if self.selected_algo == self.ALG_BELIEF:
            self.belief_agent.notify_position(cell)

            if (self.auto
                    and cell in self.belief_goals
                    and cell != self.GOAL
                    and not self.belief_agent.goal_confirmed):
                self._auto_eliminate_belief(cell)

    # ==================================================================
    #  Belief eliminate helpers
    # ==================================================================

    def _auto_eliminate_belief(self, cell: Tuple[int, int]):
        if cell in self.belief_agent.eliminated:
            return

        self.belief_agent.eliminated.add(cell)
        self.belief_agent.active_belief.discard(cell)
        self.belief_path_surface = None

        remaining = (
            self.belief_agent.active_belief
            - self.belief_agent.eliminated
        )

        if len(remaining) == 1:
            confirmed = next(iter(remaining))
            self._confirm_belief_goal(
                confirmed,
                reason=f"đã loại hết trừ {confirmed}"
            )
        elif len(remaining) == 0:
            self._toast(f"❌ Eliminated: {cell} | Không còn belief!")
        else:
            self._toast(
                f"❌ Visited ≠ GOAL: {cell} | "
                f"Còn {len(remaining)} beliefs"
            )

    def _confirm_belief_goal(self, confirmed: Tuple[int, int],
                              reason: str = ""):
        self.belief_agent.confirmed_goal = confirmed
        self.belief_agent.goal_confirmed = True

        for bg in list(self.belief_goals):
            if bg != confirmed:
                self.belief_agent.eliminated.add(bg)
                self.belief_agent.active_belief.discard(bg)

        self.belief_path_surface = None

        popup_msg = f"✓ GOAL xác nhận: {confirmed}!"
        if reason:
            popup_msg += f"| ({reason})"
        self._show_detector_popup(popup_msg, ms=3500)
        self._toast(f"✓ Goal confirmed: {confirmed}!", ms=3500)

    def _trigger_belief_detector(self, star_pos: Tuple[int, int]):
        result = self.belief_agent.trigger_detector(
            current_pos=(self.agent_r, self.agent_c)
        )
        if result is None:
            self._toast("⭐ Star collected! (no remaining beliefs)")
            return

        msg             = result.get("msg", "Detector kích hoạt!")
        eliminated_cell = result.get("eliminated")
        confirmed_cell  = result.get("confirmed")

        if confirmed_cell is not None:
            self._confirm_belief_goal(
                confirmed_cell,
                reason="detector xác nhận"
            )
            return

        if eliminated_cell is not None:
            if eliminated_cell not in self.belief_agent.eliminated:
                self.belief_agent.eliminated.add(eliminated_cell)
                self.belief_agent.active_belief.discard(eliminated_cell)
                self.belief_path_surface = None

                remaining = (
                    self.belief_agent.active_belief
                    - self.belief_agent.eliminated
                )
                if len(remaining) == 1:
                    confirmed = next(iter(remaining))
                    self._confirm_belief_goal(
                        confirmed,
                        reason="còn lại duy nhất sau detector"
                    )
                    return

        if not self.belief_agent.goal_confirmed:
            self._show_detector_popup(msg, ms=3000)
            self._toast(f"⭐ Detector: {msg}", ms=3000)

    # ==================================================================
    #  AND-OR actions
    # ==================================================================

    def _exec_andor_action(self, a: str):
        if   a == "U": self._move(-1,  0)
        elif a == "D": self._move( 1,  0)
        elif a == "L": self._move( 0, -1)
        elif a == "R": self._move( 0,  1)
        elif a == "C1->A":
            dest = self.POINTS["A"]
            self._agent_facing_right = dest[1] >= self.agent_c
            self.agent_r, self.agent_c = dest
        elif a == "C1->B":
            dest = self.POINTS["B"]
            self._agent_facing_right = dest[1] >= self.agent_c
            self.agent_r, self.agent_c = dest
        elif a == "C2":
            dest = random.choice([self.POINTS["C"], self.POINTS["D"]])
            self._agent_facing_right = dest[1] >= self.agent_c
            self.agent_r, self.agent_c = dest
        elif a == "C3":
            dest = random.choice([self.POINTS["C"], self.POINTS["E"]])
            self._agent_facing_right = dest[1] >= self.agent_c
            self.agent_r, self.agent_c = dest

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
            pts = [(c * ts + ts//2, r * ts + ts//2) for (r, c) in seq]
            pygame.draw.lines(surf, (255, 180, 0, 200), False, pts, 3)
            for idx, (r, c) in enumerate(seq):
                cx, cy = c*ts + ts//2, r*ts + ts//2
                col    = (255, 100, 0, 180) if idx == 0 else (255, 220, 80, 160)
                pygame.draw.circle(surf, col, (cx, cy), max(3, ts//5))
        self.belief_path_surface = surf

    # ==================================================================
    #  Draw helpers
    # ==================================================================

    def _draw_water_cells(self, board, ts, cells, alpha=255):
        if not cells: return
        size = (ts, ts)
        if self.water_raw:
            tile = self._scaled(self.water_raw, size)
            if alpha != 255:
                tile = tile.copy(); tile.set_alpha(alpha)
            for (r, c) in cells:
                self.screen.blit(tile, (board.x + c*ts, board.y + r*ts))
        else:
            s = pygame.Surface((board.w, board.h), pygame.SRCALPHA)
            for (r, c) in cells:
                pygame.draw.rect(s, (*C_WATER_BLOCK, min(255, alpha)),
                                 (c*ts, r*ts, ts, ts))
            self.screen.blit(s, board.topleft)

    def _draw_star_cells(self, board, ts, cells):
        if not cells: return
        star_size = int(ts * 2.3)
        offset    = (ts - star_size) // 2
        size      = (star_size, star_size)
        if self.star_raw:
            img = self._scaled(self.star_raw, size)
            for (r, c) in cells:
                x = board.x + c*ts + offset
                y = board.y + r*ts + offset
                if (r, c) in self.collected_stars:
                    dim = img.copy(); dim.set_alpha(55)
                    self.screen.blit(dim, (x, y))
                else:
                    self.screen.blit(img, (x, y))
        else:
            for (r, c) in cells:
                x, y   = board.x + c*ts, board.y + r*ts
                cx, cy = x + ts//2, y + ts//2
                col    = (100, 100, 60) if (r, c) in self.collected_stars else C_STAR
                self._fallback_draw_star(self.screen, cx, cy,
                                         max(4, int(ts*0.70)), col)

    def _fallback_draw_star(self, surface, cx, cy, r, color):
        pts = []
        for i in range(5):
            a_out = math.radians(-90 + i*72)
            a_in  = math.radians(-90 + i*72 + 36)
            pts.append((cx + r*math.cos(a_out), cy + r*math.sin(a_out)))
            pts.append((cx + r*0.4*math.cos(a_in), cy + r*0.4*math.sin(a_in)))
        if len(pts) >= 3:
            pygame.draw.polygon(surface, color, pts)
            pygame.draw.polygon(surface, (255, 255, 255), pts, 1)

    def _draw_qmark_cells(self, board, ts, cells):
        if not cells: return
        qmark_size = int(ts * 1.7)
        offset     = (ts - qmark_size) // 2
        size       = (qmark_size, qmark_size)

        if self.qmark_raw:
            img = self._scaled(self.qmark_raw, size)
            for (r, c) in cells:
                x   = board.x + c*ts + offset
                y   = board.y + r*ts + offset
                srf = img.copy()

                if (r, c) in self.belief_agent.eliminated:
                    dark = pygame.Surface(size, pygame.SRCALPHA)
                    dark.fill((0, 0, 0, 180))
                    srf.blit(dark, (0, 0))
                    srf.set_alpha(80)

                elif (r, c) == self.belief_agent.confirmed_goal:
                    tint = pygame.Surface(size, pygame.SRCALPHA)
                    tint.fill((80, 255, 120, 140))
                    srf.blit(tint, (0, 0))

                self.screen.blit(srf, (x, y))

                if (r, c) == self.belief_agent.confirmed_goal:
                    pygame.draw.rect(
                        self.screen, C_CONFIRMED,
                        (board.x + c*ts + 1,
                         board.y + r*ts + 1,
                         ts - 2, ts - 2),
                        3, border_radius=3
                    )

        else:
            for (r, c) in cells:
                x, y   = board.x + c*ts, board.y + r*ts
                cx, cy = x + ts//2, y + ts//2
                if   (r, c) in self.belief_agent.eliminated:
                    col = C_ELIMINATED
                elif (r, c) == self.belief_agent.confirmed_goal:
                    col = C_CONFIRMED
                else:
                    col = C_BELIEF_GOAL
                pygame.draw.circle(self.screen, col, (cx, cy),
                                   max(4, int(ts*0.70)))
                lbl = self.title_font.render("?", True, (255, 255, 255))
                self.screen.blit(lbl, (cx - lbl.get_width()//2,
                                       cy - lbl.get_height()//2))

    # ==================================================================
    #  Draw portals (AND-OR only)
    # ==================================================================

    def _draw_all_portals(self, board, ts):
        if self.selected_algo != self.ALG_ANDOR:
            return
        now      = pygame.time.get_ticks()
        pulse    = 0.5 + 0.5 * math.sin(now / 300)
        show_all = self.edit_mode or not self.fog_enabled

        for key in ("C1", "C2", "C3"):
            pos       = self.POINTS[key]
            px, py, _ = self._cell_to_px(*pos)
            col       = C_PORTAL[key]
            if not show_all and pos not in self.explored: continue
            is_moving = (self.moving_portal == key)
            img = self._portal_tinted(key, ts)
            if is_moving:
                bright = img.copy()
                tint2  = pygame.Surface((ts, ts), pygame.SRCALPHA)
                tint2.fill((255, 255, 255, int(60*pulse)))
                bright.blit(tint2, (0, 0))
                self.screen.blit(bright, (px, py))
            else:
                self.screen.blit(img, (px, py))
            halo_r = max(ts//2+2, ts//2 + int(4*pulse))
            pygame.draw.circle(self.screen, (*col, int(120*pulse+60)),
                               (px+ts//2, py+ts//2), halo_r, 2)
            self._draw_portal_label(key, px, py, ts, col, is_moving)

        for key in ("A", "B", "C", "D", "E"):
            pos       = self.POINTS[key]
            px, py, _ = self._cell_to_px(*pos)
            if not show_all and pos not in self.explored: continue
            col = (C_PORTAL["C1"] if key in ("A", "B") else
                   C_PORTAL["C2"] if key == "D" else
                   C_PORTAL["C3"] if key == "E" else (200, 200, 100))
            dest_ts = max(ts*3//4, 8)
            off     = (ts - dest_ts) // 2
            img     = self._portal_tinted(key, dest_ts)
            self.screen.blit(img, (px+off, py+off))
            self._draw_portal_label(key, px, py, ts, col, False, is_dest=True)

        if self.edit_mode:
            self._draw_portal_connections(board, ts, pulse)

    def _draw_portal_label(self, key, px, py, ts, col, is_moving,
                            is_dest=False):
        lbl    = self.tiny_font.render(key, True, (255, 255, 255))
        lw, lh = lbl.get_size()
        pad    = 3
        bg_w, bg_h = lw + pad*2, lh + pad*2
        bx = px + (ts - bg_w) // 2
        by = (py + ts - bg_h - 1) if is_dest else (py - bg_h - 1)
        bg_col  = (220, 220, 0, 210) if is_moving else (*col[:3], 200)
        bg_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        bg_surf.fill(bg_col)
        self.screen.blit(bg_surf, (bx, by))
        pygame.draw.rect(self.screen, (255, 255, 255),
                         (bx, by, bg_w, bg_h), 1, border_radius=2)
        self.screen.blit(lbl, (bx+pad, by+pad))

    def _draw_portal_connections(self, board, ts, pulse):
        connections = [
            ("C1", "A", C_PORTAL["C1"]), ("C1", "B", C_PORTAL["C1"]),
            ("C2", "C", C_PORTAL["C2"]), ("C2", "D", C_PORTAL["C2"]),
            ("C3", "C", C_PORTAL["C3"]), ("C3", "E", C_PORTAL["C3"]),
        ]
        for src, dst, col in connections:
            sr, sc = self.POINTS[src]; dr, dc = self.POINTS[dst]
            sx = board.x + sc*ts + ts//2; sy = board.y + sr*ts + ts//2
            dx = board.x + dc*ts + ts//2; dy = board.y + dr*ts + ts//2
            total = max(1, int(math.hypot(dx-sx, dy-sy)))
            segs  = max(4, total//(ts//2))
            for i in range(segs):
                if i % 2 == 0:
                    t0 = i/segs; t1 = (i+0.5)/segs
                    x0 = int(sx+(dx-sx)*t0); y0 = int(sy+(dy-sy)*t0)
                    x1 = int(sx+(dx-sx)*t1); y1 = int(sy+(dy-sy)*t1)
                    pygame.draw.line(self.screen,
                                     (*col, int(150*pulse+60)),
                                     (x0, y0), (x1, y1), 2)

    def _draw_detector_popup(self):
        now = pygame.time.get_ticks()
        if not self.detector_popup_text or now > self.detector_popup_until:
            self.detector_popup_text = None
            return
        sw, sh = self.screen.get_size()
        lines  = self.detector_popup_text.split("|")
        line_h = 36
        pad    = 20
        max_w  = max(self.font.size(l.strip())[0] for l in lines) + pad*2
        box_h  = line_h*len(lines) + pad*2
        box_x  = (sw - max_w)//2
        box_y  = sh//2 - box_h//2
        bg     = pygame.Surface((max_w, box_h), pygame.SRCALPHA)
        bg.fill((20, 20, 30, 210))
        self.screen.blit(bg, (box_x, box_y))
        pygame.draw.rect(self.screen, (200, 200, 80),
                         (box_x, box_y, max_w, box_h), 2, border_radius=8)
        for i, line in enumerate(lines):
            col = (80, 255, 120) if ("confirmed" in line.lower() or
                                     "goal" in line.lower()) else (255, 120, 80)
            t = self.font.render(line.strip(), True, col)
            self.screen.blit(t, (box_x+pad, box_y+pad+i*line_h))

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
        self._save_map_for_algo(self.selected_algo)
        self.edit_mode           = False
        self.pending_place       = None
        self.moving_portal       = None
        self.fog_enabled         = False
        self.auto                = False
        self.andor_policy        = None
        self.belief_path_surface = None
        self.belief_agent.reset()
        self.agent_r, self.agent_c = self.START
        self._agent_facing_right   = True
        self.collected_stars       = set()
        self._portal_tinted_cache.clear()
        self.planner.reset(start=self.START, goal=self.GOAL)
        self._init_explored()
        self.steps_count    = 0
        self.nodes_expanded = 0

    def _set_start(self, cell):
        if cell is None: return
        self.blocked.discard(cell); self.fences.discard(cell)
        self.START = cell; self.agent_r, self.agent_c = cell

    def _set_goal(self, cell):
        if cell is None: return
        self.blocked.discard(cell); self.fences.discard(cell)
        self.GOAL = cell

    def _move_portal_to(self, key, cell):
        if cell is None or cell in (self.START, self.GOAL): return
        for k, v in self.POINTS.items():
            if k != key and v == cell:
                self._toast(f"Ô {cell} đã có điểm {k}!"); return
        self.blocked.discard(cell); self.fences.discard(cell)
        old = self.POINTS[key]
        self.POINTS[key] = cell
        self._rebuild_portals(); self._portal_tinted_cache.clear()
        self._toast(f"Moved {key}: {old} → {cell}")

    def _apply_tool(self, cell, button):
        if cell is None: return
        if self.moving_portal is not None:
            self._move_portal_to(self.moving_portal, cell)
            self.moving_portal = None; return
        if self._is_protected(cell): return
        if button == 3:
            for layer in (self.blocked, self.fences,
                          self.stars, self.belief_goals):
                layer.discard(cell)
            return
        tool = self.edit_tool
        if tool == "erase":
            for layer in (self.blocked, self.fences,
                          self.stars, self.belief_goals):
                layer.discard(cell)
        elif tool == "block":
            self.fences.discard(cell); self.stars.discard(cell)
            self.belief_goals.discard(cell)
            if cell in self.blocked: self.blocked.remove(cell)
            else:                    self.blocked.add(cell)
        elif tool == "fence" and self.selected_algo == self.ALG_ANDOR:
            self.blocked.discard(cell); self.stars.discard(cell)
            self.belief_goals.discard(cell)
            if cell in self.fences: self.fences.remove(cell)
            else:                   self.fences.add(cell)
        elif tool == "star" and self.selected_algo == self.ALG_BELIEF:
            self.blocked.discard(cell); self.fences.discard(cell)
            self.belief_goals.discard(cell)
            if cell in self.stars: self.stars.remove(cell)
            else:                  self.stars.add(cell)
        elif tool == "belief_goal" and self.selected_algo == self.ALG_BELIEF:
            self.blocked.discard(cell); self.fences.discard(cell)
            self.stars.discard(cell)
            if cell in self.belief_goals: self.belief_goals.remove(cell)
            else:                         self.belief_goals.add(cell)

    # ==================================================================
    #  Random generation (BELIEF only)
    # ==================================================================

    def _get_valid_random_cells(self, count: int,
                                 exclude: set = None) -> list:
        protected = (
            {self.START, self.GOAL}
            | set(self.POINTS.values())
            | self._all_blocked()
            | (exclude or set())
        )
        candidates = [
            (r, c)
            for r in range(self.ROWS)
            for c in range(self.COLS)
            if (r, c) not in protected
        ]
        if len(candidates) < count:
            self._toast(
                f"Chỉ còn {len(candidates)} ô trống! "
                f"Giảm số lượng xuống.", ms=2500)
            count = len(candidates)
        return random.sample(candidates, count) if candidates else []

    def _random_gen_stars(self):
        self.stars.clear()
        cells      = self._get_valid_random_cells(
            self._rand_star_count, exclude=self.belief_goals)
        self.stars = set(cells)
        self._sanitize()
        self._toast(f"⭐ Đặt ngẫu nhiên {len(self.stars)} ngôi sao!")

    def _random_gen_beliefs(self):
        self.belief_goals.clear()
        cells = self._get_valid_random_cells(
            self._rand_belief_count,
            exclude=self.stars | {self.GOAL})
        self.belief_goals = set(cells) | {self.GOAL}
        self._sanitize()
        self._toast(
            f"❓ Đặt ngẫu nhiên {len(self.belief_goals)} "
            f"belief goals (gồm GOAL thật)!")

    def _random_gen_all(self):
        self.stars.clear()
        self.belief_goals.clear()
        protected = (
            {self.START, self.GOAL}
            | set(self.POINTS.values())
            | self._all_blocked()
        )
        candidates = [
            (r, c)
            for r in range(self.ROWS)
            for c in range(self.COLS)
            if (r, c) not in protected
        ]
        total_need = self._rand_star_count + self._rand_belief_count
        if len(candidates) < total_need:
            self._toast(
                f"Không đủ ô! Cần {total_need}, "
                f"có {len(candidates)}. Tự điều chỉnh.", ms=2500)
            ratio      = len(candidates) / total_need
            star_cnt   = max(1, int(self._rand_star_count   * ratio))
            belief_cnt = max(1, int(self._rand_belief_count * ratio))
        else:
            star_cnt   = self._rand_star_count
            belief_cnt = self._rand_belief_count

        shuffled = candidates.copy()
        random.shuffle(shuffled)
        self.stars        = set(shuffled[:star_cnt])
        self.belief_goals = (set(shuffled[star_cnt:star_cnt+belief_cnt])
                             | {self.GOAL})
        self._sanitize()
        self._toast(
            f"🎲 Random: {len(self.stars)} ⭐ + "
            f"{len(self.belief_goals)} ❓ (gồm GOAL)")

    def _clear_belief_and_stars(self):
        self.stars.clear()
        self.belief_goals.clear()
        self._toast("🗑 Đã xóa tất cả Stars và Beliefs!")

    # ==================================================================
    #  UI helpers
    # ==================================================================

    def _button(self, name, x, y, w, h):
        r = pygame.Rect(x, y, w, h)
        self.ui_buttons[name] = r
        return r

    def _draw_button(self, rect, label, active=False, disabled=False,
                     color=None, text_color=None):
        if disabled:
            bg, fg, border = (70, 70, 70), (150, 150, 150), (90, 90, 90)
        else:
            bg, fg, border = (45, 55, 65), (240, 240, 240), (120, 130, 140)
        if color and not disabled:
            bg = color; border = (255, 255, 255)
        if active and not disabled and color is None:
            bg = (45, 110, 190); border = (150, 200, 255)
        if text_color:
            fg = text_color
        pygame.draw.rect(self.screen, bg,     rect, border_radius=7)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=7)
        txt = self.font.render(label, True, fg)
        self.screen.blit(txt, (rect.x+10,
                               rect.y + (rect.h - txt.get_height())//2))

    def _sep(self, y, label=""):
        pygame.draw.line(self.screen, (70, 80, 90),
                         (10, y+6), (self.left_w-10, y+6), 1)
        if label:
            t = self.small_font.render(label, True, (140, 150, 160))
            self.screen.blit(t, (14, y-1))
        return y + 18

    # ==================================================================
    #  Status text helper
    # ==================================================================

    def _status_text(self):
        if self.edit_mode:
            return "Editing"
        if self.auto:
            return "🔍 Running..."
        return "Idle"

    # ==================================================================
    #  Stats block (góc trái dưới, trên BACK)
    # ==================================================================

    def _draw_stats_block(self, x, back_y):
        lines = [
            ("Status", self._status_text()),
            ("Steps",  str(self.steps_count)),
        ]
        if self.nodes_expanded > 0:
            lines.append(("Nodes", str(self.nodes_expanded)))

        line_h  = 18
        total_h = len(lines) * line_h + 4
        y0      = back_y - total_h - 10

        for i, (k, v) in enumerate(lines):
            y  = y0 + i * line_h
            ks = self.small_font.render(f"{k}:", True, (160, 160, 160))
            vs = self.small_font.render(v,       True, (255, 220, 80))
            self.screen.blit(ks, (x, y))
            self.screen.blit(vs, (x + ks.get_width() + 4, y))

    # ==================================================================
    #  Run / Reset
    # ==================================================================

    def _run_ai(self):
        self.steps_count    = 0
        self.nodes_expanded = 0

        if self.selected_algo == self.ALG_ONLINE:
            self.fog_enabled = True
            self._init_explored()
            self.auto = True
            self._toast("ONLINE: Bắt đầu khám phá rừng sương mù…")

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
                self._toast("AND-OR: Không tìm được policy!")
            else:
                self.andor_policy   = policy
                self.auto           = True
                self.nodes_expanded = solver.expansions
                self._toast(
                    f"AND-OR: Policy OK ({solver.expansions} nodes)")

        elif self.selected_algo == self.ALG_BELIEF:
            self.fog_enabled = False
            if not self.belief_goals:
                self._toast("Cần đặt ô ? trước!"); return
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
                self.auto           = True
                self.nodes_expanded = self.belief_agent.expansions
                self._toast(
                    f"BELIEF: {len(self.belief_agent.path)} bước | "
                    f"pool: {len(full_belief)}")
            else:
                self._toast(
                    f"BELIEF: Không tìm được kế hoạch! "
                    f"({self.belief_agent.expansions} states)")

    def _reset_agent(self):
        self.auto                = False
        self.andor_policy        = None
        self.belief_path_surface = None
        self.detector_popup_text = None
        self.moving_portal       = None
        self.belief_agent.reset()
        self.agent_r, self.agent_c = self.START
        self._agent_facing_right   = True
        self._bob_offset           = 0
        self.collected_stars       = set()
        self.fog_enabled           = False
        self.planner.reset(start=self.START, goal=self.GOAL)
        self._init_explored()
        self.steps_count    = 0
        self.nodes_expanded = 0

    # ==================================================================
    #  Panel click
    # ==================================================================

    def _handle_left_panel_click(self, pos):
        if not self.ui_buttons: self._layout_left_panel()
        mx, my = pos
        if mx > self.left_w: return False

        for name, rect in self.ui_buttons.items():
            if not rect.collidepoint(mx, my): continue

            if name.startswith("alg_") and not self.edit_mode:
                self._switch_algo(name[4:])
                self._toast(f"Map: {MAP_INFO[name[4:]]['title']}")
                return True
            if name == "run_ai" and not self.edit_mode:
                self._run_ai(); return True
            if name == "cancel_ai" and not self.edit_mode:
                self.auto = False
                self.belief_path_surface = None
                self.belief_agent.reset()
                self.fog_enabled = False
                self._toast("Canceled.")
                return True
            if name == "reset" and not self.edit_mode:
                self._reset_agent(); self._toast("Reset."); return True
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
                    self._toast("Cancelled.")
                else:
                    self.moving_portal = key
                    self.pending_place = None
                    self._toast(f"Click map to place {key}")
                return True
            if name == "cancel_move_portal" and self.edit_mode:
                self.moving_portal = None
                self._toast("Move cancelled.")
                return True

            if name == "rand_star_dec" and self.edit_mode:
                self._rand_star_count = max(1, self._rand_star_count - 1)
                return True
            if name == "rand_star_inc" and self.edit_mode:
                self._rand_star_count = min(50, self._rand_star_count + 1)
                return True
            if name == "rand_belief_dec" and self.edit_mode:
                self._rand_belief_count = max(1, self._rand_belief_count - 1)
                return True
            if name == "rand_belief_inc" and self.edit_mode:
                self._rand_belief_count = min(50, self._rand_belief_count + 1)
                return True
            if name == "rand_gen_stars" and self.edit_mode:
                if self.selected_algo == self.ALG_BELIEF:
                    self._random_gen_stars()
                return True
            if name == "rand_gen_beliefs" and self.edit_mode:
                if self.selected_algo == self.ALG_BELIEF:
                    self._random_gen_beliefs()
                return True
            if name == "rand_clear" and self.edit_mode:
                self._clear_belief_and_stars()
                return True
            if name == "back":
                self.stage_manager.change_stage("stage_select")
                return True

        return False

    # ==================================================================
    #  Stage API
    # ==================================================================

    def handle_events(self, events):
        panel_action = self.victory_panel.handle_events(events)
        if panel_action == "replay":
            return
        if self.victory_panel.visible:
            return

        for e in events:
            if self.slider_speed.handle_event(e):
                self.step_delay_ms = self.slider_speed.value
                continue

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
                    if self._handle_left_panel_click(e.pos): continue
                    if self.edit_mode:
                        cell = self._px_to_cell(*e.pos)
                        if cell is None: continue
                        r, c = cell
                        if self.moving_portal is not None:
                            self._move_portal_to(self.moving_portal, cell)
                            self.moving_portal = None; continue
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
                                    portal_clicked = k; break
                            if portal_clicked:
                                self.moving_portal = portal_clicked
                                self._toast(
                                    f"Click map to move {portal_clicked}")
                            else:
                                self._apply_tool(cell, 1)

                elif e.button == 3 and self.edit_mode:
                    cell = self._px_to_cell(*e.pos)
                    self._apply_tool(cell, 3)

            elif e.type == pygame.MOUSEMOTION:
                if (self.edit_mode
                      and pygame.mouse.get_pressed()[0]
                      and self.pending_place is None
                      and self.moving_portal is None):
                    cell = self._px_to_cell(*e.pos)
                    if cell and not self._is_protected(cell):
                        self._apply_tool(cell, 1)

    def update(self):
        if not self.edit_mode and self.fog_enabled:
            self._reveal()

        self.planner.observe(self._sense())
        self._portal_anim_tick = pygame.time.get_ticks()

        if self.auto and not self.edit_mode:
            now = pygame.time.get_ticks()
            self._bob_offset = int(math.sin(now / 130) * 3)
        else:
            self._bob_offset = 0

        now = pygame.time.get_ticks()
        if self.edit_mode or not self.auto: return
        if now - self._last_auto_tick < int(self.step_delay_ms): return
        self._last_auto_tick = now

        if self.selected_algo == self.ALG_ONLINE:
            self.planner.set_goal(self.GOAL)
            dr, dc = self.planner.next_action((self.agent_r, self.agent_c))
            if (dr, dc) != (0, 0):
                self._move(dr, dc)
                self.steps_count += 1
                if self.fog_enabled: self._reveal()
            self.planner.set_position((self.agent_r, self.agent_c))
            if (self.agent_r, self.agent_c) == self.GOAL:
                self.auto        = False
                self.fog_enabled = False
                self._bob_offset = 0
                self.victory_panel.show(
                    next_stage_id     = "stage5",
                    next_stage_unlock = "stage5",
                    title    = "CHẶNG 4 HOÀN THÀNH!",
                    subtitle = f"Vượt qua rừng sương mù sau {self.steps_count} bước!",
                    nodes_visited = self.steps_count,
                    path_cost     = self.steps_count,
                )

        elif self.selected_algo == self.ALG_ANDOR:
            if not self.andor_policy:
                self.auto = False; return
            s = (self.agent_r, self.agent_c)
            a = self.andor_policy.get(s)
            if a is None:
                self.auto        = False
                self._bob_offset = 0
                self._toast("AND-OR: hết action."); return
            self._exec_andor_action(a)
            self.steps_count += 1
            if (self.agent_r, self.agent_c) == self.GOAL:
                self.auto        = False
                self._bob_offset = 0
                self.victory_panel.show(
                    next_stage_id     = "stage5",
                    next_stage_unlock = "stage5",
                    title    = "CHẶNG 4 HOÀN THÀNH!",
                    subtitle = f"Vượt qua rừng cổng ma thuật sau {self.steps_count} bước!",
                    nodes_visited = self.nodes_expanded,
                    path_cost     = self.steps_count,
                )

        elif self.selected_algo == self.ALG_BELIEF:
            if self.belief_agent.solved:
                self.auto        = False
                self._bob_offset = 0
                self.victory_panel.show(
                    next_stage_id     = "stage5",
                    next_stage_unlock = "stage5",
                    title    = "CHẶNG 4 HOÀN THÀNH!",
                    subtitle = "Tìm ra căn lều đúng!",
                    nodes_visited = self.nodes_expanded,
                    path_cost     = len(self.belief_agent.path),
                )
                return
            if (self.belief_agent.failed
                    or not self.belief_agent.has_next()):
                # ← THÊM: trước khi báo "hết bước", kiểm tra đã solved chưa
                if self.belief_agent.solved:
                    self.auto        = False
                    self._bob_offset = 0
                    self.victory_panel.show(
                        next_stage_id     = "stage5",
                        next_stage_unlock = "stage5",
                        title    = "CHẶNG 4 HOÀN THÀNH!",
                        subtitle = f"Tìm ra căn lều đúng sau "
                                   f"{self.steps_count} bước!",
                        nodes_visited = self.nodes_expanded,
                        path_cost     = self.steps_count,
                    )
                    return
                self.auto        = False
                self._bob_offset = 0
                self._toast("BELIEF: hết bước."); return

            # Nếu vừa replan → xóa cache surface để draw() vẽ đường mới
            if self.belief_agent.path_changed:
                self.belief_path_surface = None
                self.belief_agent.path_changed = False

            a = self.belief_agent.next_action()
            if a:
                dr, dc = {"U": (-1, 0), "D": (1,  0),
                          "L": (0, -1), "R": (0,  1)}[a]
                self._move(dr, dc)
                self.steps_count += 1

            # ← SỬA: sau khi đi bước cuối → check solved → hiện victory NGAY
            if self.belief_agent.solved:
                self.auto        = False
                self._bob_offset = 0
                self.victory_panel.show(
                    next_stage_id     = "stage5",
                    next_stage_unlock = "stage5",
                    title    = "CHẶNG 4 HOÀN THÀNH!",
                    subtitle = f"Tìm ra căn lều đúng sau "
                               f"{self.steps_count} bước!",
                    nodes_visited = self.nodes_expanded,
                    path_cost     = self.steps_count,
                )
                return

    # ==================================================================
    #  Left panel layout
    # ==================================================================

    def _layout_left_panel(self):
        sw, sh = self.screen.get_size()
        info   = MAP_INFO[self.selected_algo]

        panel = pygame.Surface((self.left_w, sh), pygame.SRCALPHA)
        panel.fill((22, 28, 32, 235))
        self.screen.blit(panel, (0, 0))

        theme_bar = pygame.Surface((self.left_w, 6))
        theme_bar.fill(info["theme_color"])
        self.screen.blit(theme_bar, (0, 0))

        pygame.draw.line(self.screen, (75, 82, 90),
                         (self.left_w, 0), (self.left_w, sh), 2)

        self.ui_buttons.clear()
        x, y = 12, 14
        w    = self.left_w - 24
        bh   = 32
        g    = 7

        self.screen.blit(
            self.title_font.render(info["title"], True, (240, 240, 240)),
            (x, y))
        y += 28
        self.screen.blit(
            self.small_font.render(info["subtitle"], True,
                                   info["theme_color"]), (x, y))
        y += 20
        for line in info["desc"]:
            self.screen.blit(
                self.tiny_font.render(line, True, (160, 170, 160)), (x, y))
            y += 16
        y += 6

        y = self._sep(y, "ALGORITHM")
        tab_w = (w - 2*g) // 3
        tx    = x
        for key, label, col in [
            (self.ALG_ONLINE, "ONLINE",  (30,  90, 160)),
            (self.ALG_ANDOR,  "AND-OR",  (140, 60, 160)),
            (self.ALG_BELIEF, "BELIEF",  (160, 80,  30)),
        ]:
            r = self._button(f"alg_{key}", tx, y, tab_w, bh)
            self._draw_button(r, label,
                              active=(self.selected_algo == key),
                              disabled=self.edit_mode,
                              color=col if self.selected_algo == key
                                    else None)
            tx += tab_w + g
        y += bh + g

        y = self._sep(y, "CONTROL")
        r = self._button("run_ai", x, y, w, bh)
        self._draw_button(r, "▶  RUN AI", disabled=self.edit_mode,
                          color=(35, 155, 85) if not self.edit_mode
                                else None)
        y += bh + g
        hw = (w - g) // 2
        r  = self._button("cancel_ai", x, y, hw, bh)

        # giống chặng 5: idle -> disabled (đen/xám), running -> đỏ và bấm được
        cancel_disabled = (self.edit_mode or (not self.auto))
        self._draw_button(
            r, "■  CANCEL",
            disabled=cancel_disabled,
            color=(190, 60, 60) if (self.auto and not self.edit_mode) else None
        )
        r2 = self._button("reset", x+hw+g, y, hw, bh)
        self._draw_button(r2, "↺  RESET", disabled=self.edit_mode,
                          color=(110, 60, 160) if not self.edit_mode
                                else None)
        y += bh + g

        y = self._sep(y, "SPEED")
        self.slider_speed.rect = pygame.Rect(x, y + 20, w, 14)
        self.slider_speed.draw(self.screen, self.font)
        y += 52

        y = self._sep(y, "MAP EDITOR")
        r = self._button("edit_toggle", x, y, w, bh)
        if not self.edit_mode:
            self._draw_button(r, "✏  EDIT MAP")
        else:
            self._draw_button(r, "💾  SAVE & EXIT",
                              active=True, color=(40, 120, 60))
        y += bh + g

        if self.edit_mode:
            y = self._sep(y, "TOOLS")

            if self.selected_algo == self.ALG_ONLINE:
                tw1 = (w - g) // 2
                tx  = x
                for key, lbl, col in [
                    ("block", "BLOCK", (100, 70, 40)),
                    ("erase", "ERASE", (160, 50, 50)),
                ]:
                    tr = self._button(f"tool_{key}", tx, y, tw1, bh)
                    self._draw_button(tr, lbl,
                                      active=(self.edit_tool == key),
                                      color=col)
                    tx += tw1 + g
                y += bh + g

            elif self.selected_algo == self.ALG_ANDOR:
                tw1 = (w - 2*g) // 3
                tx  = x
                for key, lbl, col in [
                    ("block", "BLOCK", (100, 70,  40)),
                    ("fence", "FENCE", ( 30, 90, 180)),
                    ("erase", "ERASE", (160, 50,  50)),
                ]:
                    tr = self._button(f"tool_{key}", tx, y, tw1, bh)
                    self._draw_button(tr, lbl,
                                      active=(self.edit_tool == key),
                                      color=col)
                    tx += tw1 + g
                y += bh + g

            elif self.selected_algo == self.ALG_BELIEF:
                tw1 = (w - g) // 2
                tx  = x
                for key, lbl, col in [
                    ("block", "BLOCK", (100, 70, 40)),
                    ("erase", "ERASE", (160, 50, 50)),
                ]:
                    tr = self._button(f"tool_{key}", tx, y, tw1, bh)
                    self._draw_button(tr, lbl,
                                      active=(self.edit_tool == key),
                                      color=col)
                    tx += tw1 + g
                y += bh + g

                tw2 = (w - g) // 2
                tx  = x
                for key, lbl, col in [
                    ("star",        "⭐ STAR",     (170, 130,  15)),
                    ("belief_goal", "?  BELIEF ?", (160,  50, 160)),
                ]:
                    tr = self._button(f"tool_{key}", tx, y, tw2, bh)
                    self._draw_button(tr, lbl,
                                      active=(self.edit_tool == key),
                                      color=col)
                    tx += tw2 + g
                y += bh + g

                y = self._sep(y, "RANDOM GENERATE")

                # ── Hàng 1: Stars counter (2 cột: - | số | +) ──
                self.screen.blit(
                    self.small_font.render(
                        f"Stars: {self._rand_star_count}",
                        True, C_STAR), (x, y))
                y += 20
                hw3  = (w - 2*g) // 3
                rm_s = self._button("rand_star_dec", x, y, hw3, 30)
                self._draw_button(rm_s, "  -", color=(120, 80, 20))
                num_s = self.font.render(
                    str(self._rand_star_count), True, (255, 220, 100))
                self.screen.blit(num_s, (
                    x + hw3 + g + (hw3 - num_s.get_width()) // 2,
                    y + (30 - num_s.get_height()) // 2))
                rp_s = self._button("rand_star_inc",
                                    x + 2*(hw3+g), y, hw3, 30)
                self._draw_button(rp_s, "  +", color=(120, 80, 20))
                y += 38

                # ── Hàng 2: Beliefs counter (2 cột: - | số | +) ──
                self.screen.blit(
                    self.small_font.render(
                        f"Beliefs: {self._rand_belief_count}",
                        True, C_BELIEF_GOAL), (x, y))
                y += 20
                rm_b = self._button("rand_belief_dec", x, y, hw3, 30)
                self._draw_button(rm_b, "  -", color=(100, 30, 100))
                num_b = self.font.render(
                    str(self._rand_belief_count), True, (220, 100, 220))
                self.screen.blit(num_b, (
                    x + hw3 + g + (hw3 - num_b.get_width()) // 2,
                    y + (30 - num_b.get_height()) // 2))
                rp_b = self._button("rand_belief_inc",
                                    x + 2*(hw3+g), y, hw3, 30)
                self._draw_button(rp_b, "  +", color=(100, 30, 100))
                y += 38

                # ── Hàng 3: 2 nút Random cạnh nhau (2 cột) ──
                hw2 = (w - g) // 2
                r_gen_s = self._button("rand_gen_stars", x, y, hw2, bh)
                self._draw_button(r_gen_s, "🎲 Stars",
                                  color=(150, 110, 20))
                r_gen_b = self._button("rand_gen_beliefs",
                                       x + hw2 + g, y, hw2, bh)
                self._draw_button(r_gen_b, " Beliefs",
                                  color=(120, 40, 140))
                y += bh + g

                # ── Hàng 4: Clear All (full width) ──
                r_clear = self._button("rand_clear", x, y, w, bh)
                self._draw_button(r_clear, "🗑  Clear All",
                                  color=(80, 80, 80))
                y += bh + g

            hw2 = (w - g) // 2
            r   = self._button("place_start", x, y, hw2, bh)
            self._draw_button(r, "Set START",
                              active=(self.pending_place == "START"),
                              color=(0, 160, 210))
            r2  = self._button("place_goal", x+hw2+g, y, hw2, bh)
            self._draw_button(r2, "Set GOAL",
                              active=(self.pending_place == "GOAL"),
                              color=(200, 160, 0))
            y += bh + g + 2

            if self.selected_algo == self.ALG_ANDOR:
                y = self._sep(y, "MOVE PORTALS")
                tw3 = (w - 2*g) // 3
                tx  = x
                for key in ("C1", "C2", "C3"):
                    col = C_PORTAL[key]
                    tr  = self._button(f"move_{key}", tx, y, tw3, bh)
                    self._draw_button(tr, key,
                                      active=(self.moving_portal == key),
                                      color=col)
                    tx += tw3 + g
                y += bh + g

                tw4 = (w - 4*g) // 5
                tx  = x
                for key in ("A", "B", "C", "D", "E"):
                    tr = self._button(f"move_{key}", tx, y, tw4, bh)
                    self._draw_button(tr, key,
                                      active=(self.moving_portal == key),
                                      color=(180, 180, 60)
                                      if self.moving_portal == key
                                      else (60, 60, 80))
                    tx += tw4 + g
                y += bh + g

                if self.moving_portal:
                    self.screen.blit(
                        self.small_font.render(
                            f"Click map → place {self.moving_portal}",
                            True, (255, 255, 100)), (x, y))
                    y += 22
                    r = self._button("cancel_move_portal", x, y, w, bh)
                    self._draw_button(r, "✗  Cancel move",
                                      color=(160, 50, 50))
                    y += bh + g

            tool_colors = {
                "block":       (200, 200, 200),
                "fence":       C_WATER_FENCE,
                "star":        C_STAR,
                "belief_goal": C_BELIEF_GOAL,
                "erase":       (255,  80,  80),
            }
            if self.selected_algo == self.ALG_ONLINE:
                stats = [
                    (f"Tool: {self.edit_tool.upper()}",
                     tool_colors.get(self.edit_tool, (200, 200, 200))),
                    ("Vẽ mê cung hành lang", (150, 150, 150)),
                ]
            elif self.selected_algo == self.ALG_ANDOR:
                stats = [
                    (f"Tool: {self.edit_tool.upper()}",
                     tool_colors.get(self.edit_tool, (200, 200, 200))),
                    ("Map thoáng, ít vật cản", (150, 150, 150)),
                ]
            else:
                stats = [
                    (f"Tool: {self.edit_tool.upper()}",
                     tool_colors.get(self.edit_tool, (200, 200, 200))),
                    (f"Belief goals (?): {len(self.belief_goals)}",
                     C_BELIEF_GOAL),
                    (f"Stars (detector): {len(self.stars)}", C_STAR),
                ]
            for line, col in stats:
                self.screen.blit(
                    self.small_font.render(line, True, col), (x, y))
                y += 18

        else:
            y = self._sep(y, "INFO")
            for line, col in [
                ("Move: Arrow Keys", (170, 170, 170)),
                ("Back:  ESC",       (170, 170, 170)),
            ]:
                self.screen.blit(
                    self.small_font.render(line, True, col), (x, y))
                y += 18

            if self.selected_algo == self.ALG_BELIEF:
                act_b   = len(self.belief_agent.active_belief
                              - self.belief_agent.eliminated)
                elim_b  = len(self.belief_agent.eliminated)
                total_b = len(self.belief_agent.belief_goals)
                for line, col in [
                    (f"Belief pool: {total_b}", C_BELIEF_GOAL),
                    (f"Active: {act_b}  Elim: {elim_b}",
                     (200, 200, 200)),
                    (self.belief_agent.progress, (200, 200, 200)),
                    (f"Stars: {len(self.collected_stars)}"
                     f"/{len(self.stars)}", C_STAR),
                ]:
                    self.screen.blit(
                        self.small_font.render(line, True, col), (x, y))
                    y += 18
                if self.belief_agent.goal_confirmed:
                    self.screen.blit(
                        self.small_font.render(
                            f"✓ Goal: {self.belief_agent.confirmed_goal}",
                            True, C_CONFIRMED), (x, y))
                    y += 18

            elif self.selected_algo == self.ALG_ANDOR:
                y = self._sep(y, "PORTALS")
                for key in ("C1", "C2", "C3"):
                    pos = self.POINTS[key]
                    col = C_PORTAL[key]
                    self.screen.blit(
                        self.tiny_font.render(
                            f"{key}: r={pos[0]+1} c={pos[1]+1}",
                            True, col), (x, y))
                    y += 16

            else:
                self.screen.blit(
                    self.small_font.render(
                        "Fog bật khi RUN AI",
                        True, (170, 170, 170)), (x, y))
                y += 18

        back_btn_y = sh - 54
        back_btn   = pygame.Rect(x, back_btn_y, w, 44)
        self.ui_buttons["back"] = back_btn

        if not self.edit_mode:
            self._draw_stats_block(x, back_btn_y)

        self._draw_button(back_btn, "◀ BACK", color=(231, 76, 60))

        now = pygame.time.get_ticks()
        if self.toast_text:
            if now <= self.toast_until:
                self.screen.blit(
                    self.tiny_font.render(
                        self.toast_text, True, (255, 255, 160)),
                    (x, sh-16))
            else:
                self.toast_text = None

    # ==================================================================
    #  Draw
    # ==================================================================

    def draw(self):
        board, ts = self._board_rect()
        self.screen.fill((10, 12, 14))

        algo   = self.selected_algo
        bg_raw = self._bg_raw.get(algo)
        if bg_raw:
            size = (board.w, board.h)
            if self._bg_scaled_size.get(algo) != size:
                self._bg_scaled[algo] = pygame.transform.smoothscale(
                    bg_raw, size)
                self._bg_scaled_size[algo] = size
            self.screen.blit(self._bg_scaled[algo], board.topleft)
        else:
            pygame.draw.rect(self.screen, (70, 160, 80), board)

        show_all = self.edit_mode or not self.fog_enabled

        vis_blocked = (self.blocked if show_all
                       else self.blocked & self.explored)
        self._draw_water_cells(board, ts, vis_blocked, alpha=110)

        if algo == self.ALG_ANDOR:
            vis_fences = (self.fences if show_all
                          else self.fences & self.explored)
            self._draw_water_cells(board, ts, vis_fences, alpha=210)

        self._draw_all_portals(board, ts)

        if algo == self.ALG_BELIEF and self.belief_agent.pos_sequence:
            self._rebuild_belief_path_surface(board, ts)
            if self.belief_path_surface:
                self.screen.blit(self.belief_path_surface, board.topleft)

        if algo == self.ALG_BELIEF:
            if not self.edit_mode:
                self._draw_qmark_cells(board, ts, self.belief_goals)
                goal_confirmed = (
                    self.belief_agent.goal_confirmed
                    and self.belief_agent.confirmed_goal == self.GOAL
                )
                if not goal_confirmed and self.auto:
                    self._draw_qmark_cells(board, ts, {self.GOAL})
            else:
                self._draw_qmark_cells(board, ts, self.belief_goals)

        if algo == self.ALG_BELIEF:
            vis_stars = (self.stars if show_all
                         else self.stars & self.explored)
            self._draw_star_cells(board, ts, vis_stars)

        if algo == self.ALG_BELIEF and not self.edit_mode:
            goal_confirmed = (
                self.belief_agent.goal_confirmed
                and self.belief_agent.confirmed_goal == self.GOAL
            )
            show_goal = (not self.auto) or goal_confirmed
        else:
            show_goal = True

        if show_goal:
            gx, gy, _ = self._cell_to_px(*self.GOAL)
            if self.goal_img_raw:
                size = max(4, int(ts * 1.6))
                img  = self._scaled(self.goal_img_raw, (size, size))
                rect = img.get_rect(
                    center=(gx + ts//2, gy + ts//2 - ts//4))
                self.screen.blit(img, rect)
            else:
                pygame.draw.rect(self.screen, C_GOAL_MARK,
                                 (gx+2, gy+2, ts-4, ts-4), 3,
                                 border_radius=3)
                lbl = self.small_font.render("G", True, C_GOAL_MARK)
                self.screen.blit(lbl, (
                    gx+ts//2-lbl.get_width()//2,
                    gy+ts//2-lbl.get_height()//2))

        if (algo == self.ALG_BELIEF
                and self.belief_agent.goal_confirmed
                and not self.edit_mode):
            gr, gc    = self.belief_agent.confirmed_goal
            gx, gy, _ = self._cell_to_px(gr, gc)
            pygame.draw.rect(self.screen, C_CONFIRMED,
                             (gx+1, gy+1, ts-2, ts-2), 4,
                             border_radius=3)
            if self.goal_img_raw:
                size = max(4, int(ts * 1.6))
                img  = self._scaled(self.goal_img_raw, (size, size))
                rect = img.get_rect(
                    center=(gx + ts//2, gy + ts//2 - ts//4))
                self.screen.blit(img, rect)
            else:
                lbl = self.small_font.render("G!", True, C_CONFIRMED)
                self.screen.blit(lbl, (
                    gx+ts//2-lbl.get_width()//2,
                    gy+ts//2-lbl.get_height()//2))

        ax, ay, _ = self._cell_to_px(self.agent_r, self.agent_c)
        if self.start_img_raw:
            size = max(4, int(ts * 1.6))
            img  = self._scaled(self.start_img_raw, (size, size))
            if not self._agent_facing_right:
                img = pygame.transform.flip(img, True, False)
            bob  = self._bob_offset if self.auto else 0
            rect = img.get_rect(
                center=(ax + ts//2, ay + ts//2 - ts//4 + bob))
            self.screen.blit(img, rect)
        else:
            cx = ax + ts//2
            cy = ay + ts//2 + (self._bob_offset if self.auto else 0)
            pygame.draw.circle(self.screen, (20, 20, 20),
                               (cx, cy), max(4, ts//3)+1)
            pygame.draw.circle(self.screen, C_AGENT,
                               (cx, cy), max(4, ts//3))

        if self.fog_enabled and not self.edit_mode:
            fog = pygame.Surface((board.w, board.h), pygame.SRCALPHA)
            fog.fill((0, 0, 0, self.fog_alpha))
            for (r, c) in self._visible_cells():
                pygame.draw.rect(fog, (0, 0, 0, 0),
                                 (c*ts, r*ts, ts, ts))
            self.screen.blit(fog, board.topleft)

        if self.edit_mode:
            mx, my = pygame.mouse.get_pos()
            cell   = self._px_to_cell(mx, my)
            if cell:
                hr, hc    = cell
                hx, hy, _ = self._cell_to_px(hr, hc)
                if self.moving_portal:
                    col   = C_PORTAL.get(self.moving_portal, (255, 255, 0))
                    pulse = 0.5 + 0.5*math.sin(
                        pygame.time.get_ticks()/200)
                    pygame.draw.rect(self.screen, col,
                                     (hx+1, hy+1, ts-2, ts-2),
                                     3, border_radius=3)
                    pygame.draw.rect(self.screen, (255, 255, 255),
                                     (hx+3, hy+3, ts-6, ts-6),
                                     max(1, int(2*pulse)),
                                     border_radius=2)
                else:
                    tool_col = {
                        "block":       (255, 140,   0),
                        "fence":       (  0, 150, 255),
                        "star":        (255, 220,   0),
                        "belief_goal": (220,   0, 220),
                        "erase":       (255,  60,  60),
                    }.get(self.edit_tool, (255, 255, 255))
                    if self.pending_place: tool_col = (0, 255, 0)
                    pygame.draw.rect(self.screen, tool_col,
                                     (hx+1, hy+1, ts-2, ts-2),
                                     2, border_radius=2)

        self._draw_detector_popup()

        if self.show_coords:
            for c in range(self.COLS):
                t = self.tiny_font.render(str(c+1), True, (200, 200, 200))
                self.screen.blit(t, (board.x+c*ts+2, board.y-16))
            for r in range(self.ROWS):
                t = self.tiny_font.render(str(r+1), True, (200, 200, 200))
                self.screen.blit(t, (board.x-24, board.y+r*ts+2))

        self._layout_left_panel()

        self.victory_panel.update()
        self.victory_panel.draw()