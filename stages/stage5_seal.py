# File: stages/stage5_seal.py
import pygame
import math
import os
import json
import random
from ui.victory_panel import VictoryPanel

try:
    from algorithms.csp.pure_backtracking import solve_pure_backtracking
    from algorithms.csp.forward_checking import solve_backtracking_fc
    from algorithms.csp.min_conflicts import solve_min_conflicts
except ImportError as e:
    print(f"[CẢNH BÁO] Chưa tìm thấy file thuật toán: {e}")


# ─────────────────────────────────────────────
# Slider (giống stage1/2/3/4)
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
                         pygame.Rect(self.rect.x, self.rect.y,
                                     int(self.rect.w * t), self.rect.h),
                         border_radius=6)
        pygame.draw.circle(screen, color_knob,
                           (self._knob_x(), self.rect.centery),
                           self.rect.h // 2 + 4)


# ─────────────────────────────────────────────
# Stage 5
# ─────────────────────────────────────────────
class Stage5Seal:

    def __init__(self, screen, stage_manager):
        self.screen        = screen
        self.stage_manager = stage_manager
        self.sw, self.sh   = screen.get_width(), screen.get_height()

        # ── fonts ──
        try:
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 18)
            self.font       = pygame.font.Font("assets/fonts/minecraft.ttf", 14)
            self.small_font = pygame.font.Font("assets/fonts/minecraft.ttf", 12)
        except Exception:
            self.title_font = pygame.font.SysFont("Arial", 18, bold=True)
            self.font       = pygame.font.SysFont("Arial", 14, bold=True)
            self.small_font = pygame.font.SysFont("Arial", 12)

        # ── layout ──
        self.left_w  = 220
        self.start_y = 60
        self.cols    = 15
        self.rows    = 9

        max_w = (self.sw - self.left_w - 40) // self.cols
        max_h = (self.sh - self.start_y - 40) // self.rows
        self.cell_size = min(max_w, max_h)
        self.grid_w    = self.cols * self.cell_size
        self.grid_h    = self.rows * self.cell_size
        self.start_x   = self.left_w + (self.sw - self.left_w - self.grid_w) // 2

        # ── background ──
        self.bg_image = None
        self._load_background()

        # ── assets ──
        self._load_assets()

        # ── map ──
        self.grid     = self._create_initial_grid()
        self.map_file = os.path.join("assets", "maps", "stage5_map.json")
        self.load_map()

        # ── state ──
        self.selected_algorithm = "Pure BT"
        self.phase              = "idle"
        self.solver_generator   = None
        self.last_step_time     = 0
        self.steps_count        = 0
        self.is_editing         = False
        self.edit_mode          = "add_obs"

        # ── speed slider ──
        self.step_delay_ms = 200.0
        self.slider_speed  = Slider(
            pygame.Rect(0, 0, 1, 14),
            vmin=50, vmax=800, value=self.step_delay_ms,
            label="AI speed (ms)"
        )

        # ── timing ──
        self.run_start_time = 0
        self.run_elapsed_ms = 0

        # ── UI ──
        self.ui_buttons  = {}
        self.victory_panel = VictoryPanel(screen, stage_manager)

    # ==================================================================
    #  Asset / map helpers
    # ==================================================================

    def _load_background(self):
        bg_path = os.path.join("assets", "images", "stage5_bg.png")
        if os.path.exists(bg_path):
            try:
                raw = pygame.image.load(bg_path).convert()
                self.bg_image = pygame.transform.smoothscale(
                    raw, (self.sw - self.left_w, self.sh))
            except Exception:
                pass

    def _load_assets(self):
        self.item_images = {}
        files = {
            1: "mirror1.png", 2: "mirror2.png",
            3: "block.png",   8: "source.png", 9: "core.png",
        }
        for val, filename in files.items():
            path = os.path.join("assets", "images", filename)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    self.item_images[val] = pygame.transform.smoothscale(
                        img, (self.cell_size, self.cell_size))
                except Exception as e:
                    print(f"[WARN] {filename}: {e}")
                    self.item_images[val] = None
            else:
                self.item_images[val] = None

    def _create_initial_grid(self):
        grid = [[0]*self.cols for _ in range(self.rows)]
        grid[1][1]   = 8
        grid[7][13]  = 9
        grid[4][7] = grid[5][8] = grid[3][10] = grid[6][4] = 3
        return grid

    def _generate_random_map(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] not in [8, 9]:
                    self.grid[r][c] = 3 if random.random() < 0.2 else 0

    def load_map(self):
        if os.path.exists(self.map_file):
            try:
                with open(self.map_file, "r") as f:
                    saved = json.load(f)["grid"]
                if len(saved) == self.rows and len(saved[0]) == self.cols:
                    self.grid = saved
            except Exception:
                pass

    def save_map(self):
        os.makedirs(os.path.dirname(self.map_file), exist_ok=True)
        with open(self.map_file, "w") as f:
            json.dump({"grid": self.grid}, f)

    # ==================================================================
    #  Laser
    # ==================================================================

    def _calculate_laser_path(self):
        pts, sr, sc = [], -1, -1
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == 8:
                    sr, sc = r, c
        if sr == -1:
            return pts

        r, c, dr, dc = sr, sc, 0, 1
        visited = set()
        while 0 <= r < self.rows and 0 <= c < self.cols:
            if (r, c, dr, dc) in visited:
                break
            visited.add((r, c, dr, dc))
            pts.append((
                self.start_x + c * self.cell_size + self.cell_size // 2,
                self.start_y + r * self.cell_size + self.cell_size // 2,
            ))
            val = self.grid[r][c]
            if val in (3, 9):
                break
            if val == 1:
                dr, dc = -dc, -dr
            elif val == 2:
                dr, dc = dc, dr
            r, c = r + dr, c + dc
        return pts

    def _draw_laser_glow(self, pts):
        if len(pts) < 2:
            return
        glow = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        pygame.draw.lines(glow, (255, 0, 0, 40),  False, pts, width=15)
        pygame.draw.lines(glow, (255, 0, 0, 70),  False, pts, width=8)
        self.screen.blit(glow, (0, 0))
        pygame.draw.lines(self.screen, (255, 50, 50),   False, pts, width=4)
        pygame.draw.lines(self.screen, (255, 200, 200), False, pts, width=1)

    # ==================================================================
    #  UI helpers (đồng bộ stage4)
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
        self.screen.blit(txt, (rect.x + 10,
                               rect.y + (rect.h - txt.get_height()) // 2))

    def _sep(self, y, label=""):
        pygame.draw.line(self.screen, (70, 80, 90),
                         (10, y + 6), (self.left_w - 10, y + 6), 1)
        if label:
            t = self.small_font.render(label, True, (140, 150, 160))
            self.screen.blit(t, (14, y - 1))
        return y + 18

    def _draw_stats_block(self, x, back_y):
        p_color = (
            (50, 255, 120) if self.phase == "completed" else
            (255, 50, 80)  if self.phase == "failed"    else
            (255, 220, 80)
        )
        lines = [
            ("Phase",  self.phase,           p_color),
            ("Steps",  str(self.steps_count), (255, 220, 80)),
            ("Time",   f"{self.run_elapsed_ms} ms", (255, 220, 80)),
        ]
        line_h  = 18
        total_h = len(lines) * line_h + 4
        y0      = back_y - total_h - 10

        for i, (k, v, vc) in enumerate(lines):
            y  = y0 + i * line_h
            ks = self.small_font.render(f"{k}:", True, (160, 160, 160))
            vs = self.small_font.render(v,       True, vc)
            self.screen.blit(ks, (x, y))
            self.screen.blit(vs, (x + ks.get_width() + 4, y))

    # ==================================================================
    #  Left panel layout (đồng bộ stage4)
    # ==================================================================

    def _layout_left_panel(self):
        sw, sh = self.screen.get_size()

        # nền panel
        panel = pygame.Surface((self.left_w, sh), pygame.SRCALPHA)
        panel.fill((22, 28, 32, 235))
        self.screen.blit(panel, (0, 0))

        # theme bar (cyan cho CSP)
        theme_bar = pygame.Surface((self.left_w, 6))
        theme_bar.fill((0, 220, 220))
        self.screen.blit(theme_bar, (0, 0))

        pygame.draw.line(self.screen, (0, 220, 220),
                         (self.left_w, 0), (self.left_w, sh), 2)

        self.ui_buttons.clear()
        x, y = 12, 14
        w    = self.left_w - 24
        bh   = 32
        g    = 7

        # tiêu đề
        self.screen.blit(
            self.title_font.render("CSP NEURAL LINK", True, (0, 220, 220)),
            (x, y))
        y += 26
        self.screen.blit(
            self.small_font.render("Constraint Satisfaction", True, (140, 160, 160)),
            (x, y))
        y += 20

        # ── ALGORITHM ──
        y = self._sep(y, "ALGORITHM")
        tab_w = (w - 2*g) // 3
        tx    = x
        for key, label in [
            ("Pure BT",          "PURE BT"),
            ("Forward Checking", "FC"),
            ("Min-Conflicts",    "MIN-C"),
        ]:
            r = self._button(f"alg_{key}", tx, y, tab_w, bh)
            self._draw_button(r, label,
                              active=(self.selected_algorithm == key),
                              disabled=(self.phase == "running"),
                              color=(0, 160, 220) if self.selected_algorithm == key
                                    else None)
            tx += tab_w + g
        y += bh + g

        # ── CONTROL ──
        y = self._sep(y, "CONTROL")
        r = self._button("run_ai", x, y, w, bh)
        self._draw_button(r, "▶  RUN AI",
                          disabled=(self.phase == "running"),
                          color=(35, 155, 85) if self.phase != "running" else None)
        y += bh + g

        hw = (w - g) // 2
        r  = self._button("cancel_ai", x, y, hw, bh)
        self._draw_button(r, "■  CANCEL",
                          disabled=(self.phase != "running"),
                          color=(190, 60, 60) if self.phase == "running" else None)
        r2 = self._button("reset", x + hw + g, y, hw, bh)
        self._draw_button(r2, "↺  RESET", color=(110, 60, 160))
        y += bh + g

        # ── SPEED ──
        y = self._sep(y, "SPEED")
        self.slider_speed.rect = pygame.Rect(x, y + 20, w, 14)
        self.slider_speed.draw(self.screen, self.font)
        y += 52

        # ── MAP EDITOR ──
        y = self._sep(y, "MAP EDITOR")
        r = self._button("edit_toggle", x, y, w, bh)
        if not self.is_editing:
            self._draw_button(r, "✏  EDIT MAP")
        else:
            self._draw_button(r, "💾  SAVE & EXIT",
                              active=True, color=(40, 120, 60))
        y += bh + g

        if self.is_editing:
            y = self._sep(y, "TOOLS")
            tw = (w - g) // 2
            tx = x
            for key, lbl, col in [
                ("add_obs",    "Đá Cản",   (80,  60, 40)),
                ("erase",      "Tẩy",      (160, 50, 50)),
            ]:
                tr = self._button(f"tool_{key}", tx, y, tw, bh)
                self._draw_button(tr, lbl,
                                  active=(self.edit_mode == key),
                                  color=col)
                tx += tw + g
            y += bh + g

            tx = x
            for key, lbl, col in [
                ("set_source", "Súng Laze", (200,  40,  40)),
                ("set_goal",   "Đích",      (  0, 160, 160)),
            ]:
                tr = self._button(f"tool_{key}", tx, y, tw, bh)
                self._draw_button(tr, lbl,
                                  active=(self.edit_mode == key),
                                  color=col)
                tx += tw + g
            y += bh + g

            # nút Random Map nằm trong edit
            r_rand = self._button("random_map", x, y, w, bh)
            self._draw_button(r_rand, "🎲  RANDOM MAP", color=(200, 150, 0))
            y += bh + g

        # ── BACK + STATS ──
        back_btn_y = sh - 54
        back_btn   = pygame.Rect(x, back_btn_y, w, 44)
        self.ui_buttons["back"] = back_btn
        self._draw_stats_block(x, back_btn_y)
        self._draw_button(back_btn, "◀ BACK", color=(231, 76, 60))

    # ==================================================================
    #  Events
    # ==================================================================

    def handle_events(self, events):
        # Victory panel
        panel_action = self.victory_panel.handle_events(events)
        if panel_action == "replay":
            self.phase          = "idle"
            self.solver_generator = None
            self.steps_count    = 0
            self.run_elapsed_ms = 0
            return
        if self.victory_panel.visible:
            return

        for event in events:
            # slider
            if self.slider_speed.handle_event(event):
                self.step_delay_ms = self.slider_speed.value
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.stage_manager.change_stage("stage_select")
                elif event.key == pygame.K_UP:
                    self.step_delay_ms = max(50,  self.step_delay_ms - 50)
                elif event.key == pygame.K_DOWN:
                    self.step_delay_ms = min(800, self.step_delay_ms + 50)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if not self.ui_buttons:
                    self._layout_left_panel()

                # ── panel trái ──
                if pos[0] < self.left_w:
                    for name, rect in self.ui_buttons.items():
                        if not rect.collidepoint(pos):
                            continue

                        # algo
                        if name.startswith("alg_") and self.phase != "running":
                            self.selected_algorithm = name[4:]
                            return

                        # run
                        if name == "run_ai" and self.phase == "idle":
                            sr, sc = -1, -1
                            for r in range(self.rows):
                                for c in range(self.cols):
                                    if self.grid[r][c] == 8:
                                        sr, sc = r, c
                            if sr != -1:
                                self.phase          = "running"
                                self.steps_count    = 0
                                self.run_start_time = pygame.time.get_ticks()
                                self.run_elapsed_ms = 0
                                try:
                                    if self.selected_algorithm == "Pure BT":
                                        self.solver_generator = solve_pure_backtracking(
                                            self.grid, self.rows, self.cols, sr, sc)
                                    elif self.selected_algorithm == "Forward Checking":
                                        self.solver_generator = solve_backtracking_fc(
                                            self.grid, self.rows, self.cols, sr, sc)
                                    elif self.selected_algorithm == "Min-Conflicts":
                                        self.solver_generator = solve_min_conflicts(
                                            self.grid, self.rows, self.cols, sr, sc)
                                except Exception as e:
                                    print(f"[LỖI] {e}")
                            return

                        # cancel
                        if name == "cancel_ai":
                            self.phase            = "idle"
                            self.solver_generator = None
                            return

                        # reset
                        if name == "reset":
                            self.phase            = "idle"
                            self.solver_generator = None
                            self.victory_panel.visible = False
                            for r in range(self.rows):
                                for c in range(self.cols):
                                    if self.grid[r][c] in [1, 2]:
                                        self.grid[r][c] = 0
                            self.load_map()
                            return

                        # random map
                        if name == "random_map":
                            self._generate_random_map()
                            return

                        # edit toggle
                        if name == "edit_toggle":
                            if self.is_editing:
                                self.save_map()
                            self.is_editing = not self.is_editing
                            self.edit_mode  = "add_obs"
                            return

                        # tools
                        if name.startswith("tool_") and self.is_editing:
                            self.edit_mode = name[5:]
                            return

                        # back
                        if name == "back":
                            self.stage_manager.change_stage("stage_select")
                            return

                # ── canvas (edit) ──
                elif self.is_editing:
                    c = (pos[0] - self.start_x) // self.cell_size
                    r = (pos[1] - self.start_y) // self.cell_size
                    if 0 <= r < self.rows and 0 <= c < self.cols:
                        if self.edit_mode == "add_obs":    self.grid[r][c] = 3
                        elif self.edit_mode == "erase":    self.grid[r][c] = 0
                        elif self.edit_mode == "set_source": self.grid[r][c] = 8
                        elif self.edit_mode == "set_goal": self.grid[r][c] = 9

            # giữ chuột để vẽ liên tục
            elif event.type == pygame.MOUSEMOTION:
                if self.is_editing and pygame.mouse.get_pressed()[0]:
                    pos = event.pos
                    if pos[0] > self.left_w:
                        c = (pos[0] - self.start_x) // self.cell_size
                        r = (pos[1] - self.start_y) // self.cell_size
                        if 0 <= r < self.rows and 0 <= c < self.cols:
                            if self.edit_mode == "add_obs":      self.grid[r][c] = 3
                            elif self.edit_mode == "erase":      self.grid[r][c] = 0
                            elif self.edit_mode == "set_source": self.grid[r][c] = 8
                            elif self.edit_mode == "set_goal":   self.grid[r][c] = 9

    # ==================================================================
    #  Update
    # ==================================================================

    def update(self):
        if self.phase == "running":
            self.run_elapsed_ms = pygame.time.get_ticks() - self.run_start_time

        if self.phase == "running" and self.solver_generator:
            now = pygame.time.get_ticks()
            if now - self.last_step_time > int(self.step_delay_ms):
                try:
                    res = next(self.solver_generator)
                    self.last_step_time = now
                    if res == "update":
                        self.steps_count += 1
                    elif res is True:
                        self.phase = "completed"
                        laser_path      = self._calculate_laser_path()
                        final_path_cost = max(0, len(laser_path) - 1)
                        self.victory_panel.show(
                            next_stage_id     = "stage6",
                            next_stage_unlock = "stage6",
                            title    = "CHẶNG 5 HOÀN THÀNH!",
                            subtitle = f"Độ dài đường truyền: {final_path_cost} ô!",
                            nodes_visited = self.steps_count,
                            path_cost     = final_path_cost,
                        )
                    elif res is False:
                        self.phase = "failed"
                except StopIteration:
                    pass
                except Exception as e:
                    print(f"[LỖI UPDATE] {e}")
                    self.phase = "failed"

    # ==================================================================
    #  Draw
    # ==================================================================

    def draw(self):
        # ── nền ──
        self.screen.fill((5, 8, 15))
        if self.bg_image:
            self.bg_image.set_alpha(100)
            self.screen.blit(self.bg_image, (self.left_w, 0))

        # ── lưới + items ──
        for r in range(self.rows):
            for c in range(self.cols):
                x   = self.start_x + c * self.cell_size
                y   = self.start_y + r * self.cell_size
                rect = pygame.Rect(x, y, self.cell_size, self.cell_size)

                if self.is_editing:
                    pygame.draw.rect(self.screen, (0, 100, 200), rect, 1)

                val    = self.grid[r][c]
                cx, cy = x + self.cell_size//2, y + self.cell_size//2

                if val != 0:
                    img = self.item_images.get(val)
                    if img:
                        self.screen.blit(img, (x, y))
                    else:
                        # fallback neon
                        if val == 3:
                            inner = rect.inflate(-15, -15)
                            pygame.draw.rect(self.screen, (30, 35, 50), inner, border_radius=8)
                            pygame.draw.rect(self.screen, (0, 255, 255), inner, 2, border_radius=8)
                        elif val == 8:
                            rad = int(math.sin(pygame.time.get_ticks()*0.01)*5)+20
                            pygame.draw.circle(self.screen, (255, 50, 50), (cx, cy), 18)
                            pygame.draw.circle(self.screen, (255,255,255), (cx, cy),  8)
                        elif val == 9:
                            pygame.draw.rect(self.screen, (0,255,255),
                                             (cx-15, cy-15, 30, 30), border_radius=4)
                        elif val == 1:
                            pygame.draw.line(self.screen, (0,200,255),
                                             (x+15, y+self.cell_size-15),
                                             (x+self.cell_size-15, y+15), 6)
                        elif val == 2:
                            pygame.draw.line(self.screen, (0,200,255),
                                             (x+15, y+15),
                                             (x+self.cell_size-15, y+self.cell_size-15), 6)

        # ── laser ──
        laser_pts = self._calculate_laser_path()
        self._draw_laser_glow(laser_pts)

        # vẽ đè súng & đích lên trên laser
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] in [8, 9]:
                    x   = self.start_x + c * self.cell_size
                    y   = self.start_y + r * self.cell_size
                    img = self.item_images.get(self.grid[r][c])
                    if img:
                        self.screen.blit(img, (x, y))

        # ── panel trái ──
        self._layout_left_panel()

        # ── victory panel ──
        self.victory_panel.update()
        self.victory_panel.draw()