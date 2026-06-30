# File: stages/stage3_inventory.py
import pygame
import math
import os
import random
import json
from ui.victory_panel import VictoryPanel
from algorithms.local.hill_climbing import step_hill_climbing
from algorithms.local.simulated_annealing import step_simulated_annealing
from algorithms.local.local_beam_search import step_local_beam_search


# ─────────────────────────────────────────────
# Slider (giống stage1/2)
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


# ─────────────────────────────────────────────
# Stage 3
# ─────────────────────────────────────────────
class Stage3Inventory:
    """
    Chặng 3 – Local Search trên lưới bảo bối.
    Panel trái theo khuôn stage1/2.
    """

    PANEL_W = 220
    PAD     = 12
    BTN_H   = 32
    GAP     = 7

    def __init__(self, screen, stage_manager):
        self.screen        = screen
        self.stage_manager = stage_manager
        self.sw = screen.get_width()
        self.sh = screen.get_height()

        # ── fonts ──
        try:
            self.font       = pygame.font.Font("assets/fonts/minecraft.ttf", 14)
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 18)
            self.small_font = pygame.font.Font("assets/fonts/minecraft.ttf", 12)
        except Exception:
            self.font       = pygame.font.SysFont("Arial", 14, bold=True)
            self.title_font = pygame.font.SysFont("Arial", 18, bold=True)
            self.small_font = pygame.font.SysFont("Arial", 12, bold=True)

        # ── lưới ──
        self.cols      = 8
        self.rows      = 6
        self.start_y   = 130
        max_w          = (self.sw - self.PANEL_W - 40) // self.cols
        max_h          = (self.sh - self.start_y - 20) // self.rows
        self.cell_size = min(max_w, max_h)
        self.grid_w    = self.cols * self.cell_size
        self.grid_h    = self.rows * self.cell_size
        self.start_x   = self.PANEL_W + (self.sw - self.PANEL_W - self.grid_w) // 2

        # ── background ──
        try:
            bg = pygame.image.load("assets/images/stage3_bg.png").convert()
            self.bg_image = pygame.transform.scale(bg, (self.sw - self.PANEL_W, self.sh))
        except Exception:
            self.bg_image = None

        # ── item images ──
        self.item_images = {}
        self.obs_images  = {}
        folder = os.path.join("assets", "images", "Bảo bối chặng 3")
        sz = int(self.cell_size * 0.8)
        for i in range(1, 46):
            try:
                img = pygame.image.load(os.path.join(folder, f"{i}.png")).convert_alpha()
                self.item_images[i + 9] = pygame.transform.scale(img, (sz, sz))
            except Exception:
                pass
        for i in range(1, 5):
            try:
                img = pygame.image.load(os.path.join(folder, f"baoboihu{i}.png")).convert_alpha()
                self.obs_images[i + 100] = pygame.transform.scale(img, (sz, sz))
            except Exception:
                pass

        # ── algo & state ──
        self.selected_algorithm = "Hill Climbing"
        self.phase              = "idle"
        self.steps_count        = 0
        self.current_fitness    = 0
        self.target_item_id     = 14

        self.temperature   = 100.0
        self.cooling_rate  = 0.90
        self.beam_states   = []
        self.anim_swap     = None
        self.last_step_time = 0

        # ── AI step speed slider ──
        self.step_delay_ms = 200.0
        self.slider_speed  = Slider(
            pygame.Rect(0, 0, 1, 14),
            vmin=50, vmax=1000, value=self.step_delay_ms,
            label="AI speed (ms)"
        )

        # ── editor ──
        self.is_editing = False
        self.edit_mode  = None

        # ── map ──
        self.grid            = self._create_initial_grid()
        self.current_fitness = self.calculate_fitness(self.grid)

        self.victory_panel = VictoryPanel(screen, stage_manager)

    # ─────────────────────────────────────────
    # Map helpers
    # ─────────────────────────────────────────
    def _create_initial_grid(self):
        map_path = os.path.join("assets", "maps", "stage3_map.json")
        if os.path.exists(map_path):
            try:
                with open(map_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                saved_grid   = data.get("grid")
                saved_target = data.get("target_item_id")
                if saved_target is not None:
                    self.target_item_id = saved_target
                if saved_grid and len(saved_grid) == self.rows and len(saved_grid[0]) == self.cols:
                    return saved_grid
            except Exception as e:
                print(f"Lỗi load map stage3: {e}")

        grid = [[0] * self.cols for _ in range(self.rows)]
        grid[self.rows - 2][self.cols // 2] = 9
        return grid

    def find_target_position(self, g):
        for r in range(self.rows):
            for c in range(self.cols):
                if g[r][c] == 9:
                    return r, c
        return None

    def calculate_fitness(self, g):
        pos = self.find_target_position(g)
        if not pos:
            return 0
        return 100 if pos[0] == 0 else 100 - pos[0] * 10

    def get_neighbors(self, g):
        neighbors = []
        pos = self.find_target_position(g)
        if not pos:
            return neighbors
        r, c = pos
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols and g[nr][nc] < 100:
                ng = [row[:] for row in g]
                ng[r][c], ng[nr][nc] = ng[nr][nc], ng[r][c]
                neighbors.append(ng)
        return neighbors

    def _get_available_items(self):
        used = {self.target_item_id}
        for row in self.grid:
            for v in row:
                if 10 <= v <= 54:
                    used.add(v)
        return list(set(range(10, 55)) - used)

    def _save_map(self):
        path = os.path.join("assets", "maps", "stage3_map.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"target_item_id": self.target_item_id, "grid": self.grid}, f)
        print("[Stage3] Map saved.")

    # ─────────────────────────────────────────
    # Reset
    # ─────────────────────────────────────────
    def _full_reset(self):
        """Reset hoàn toàn: load lại map từ file, xóa stats."""
        self.grid            = self._create_initial_grid()
        self.current_fitness = self.calculate_fitness(self.grid)
        self.steps_count     = 0
        self.phase           = "idle"
        self.temperature     = 100.0
        self.beam_states     = []
        self.anim_swap       = None

    # ─────────────────────────────────────────
    # UI rects (khuôn stage1)
    # ─────────────────────────────────────────
    def _ui_rects(self):
        pad  = self.PAD
        pw   = self.PANEL_W
        bw   = pw - 2 * pad
        h    = self.BTN_H
        g    = self.GAP
        sh   = self.sh
        y    = 55

        def btn(hh=None):
            nonlocal y
            r = pygame.Rect(pad, y, bw, hh or h)
            y += (hh or h) + g
            return r

        # algo
        hc_btn   = btn()
        sa_btn   = btn()
        beam_btn = btn()

        # actions
        y += 4
        run_btn    = btn()
        cancel_btn = btn()
        reset_btn  = btn()

        # slider tốc độ AI
        y += 10
        slider_rect = pygame.Rect(pad, y + 20, bw, 14)
        y += 50

        # đổi bảo bối mục tiêu
        y += 4
        select_item_btn = btn()

        # edit toggle
        edit_toggle = btn()

        # editor group (2 cột)
        editor_rects = {}
        if self.is_editing:
            col_w  = (bw - 6) // 2
            ed_h   = 28
            ed_g   = 6
            tools  = ["add_item", "add_obs", "set_goal", "erase"]
            for i, tid in enumerate(tools):
                col = i % 2
                row = i // 2
                editor_rects[tid] = pygame.Rect(
                    pad + col * (col_w + 6),
                    y + row * (ed_h + ed_g),
                    col_w, ed_h
                )
            rows_used = math.ceil(len(tools) / 2)
            y += rows_used * (ed_h + ed_g) + 4
            # save
            editor_rects["save"] = pygame.Rect(pad, y, bw, ed_h)
            y += ed_h + ed_g

        back_btn = pygame.Rect(pad, sh - 54, bw, 44)

        return {
            "hc":          hc_btn,
            "sa":          sa_btn,
            "beam":        beam_btn,
            "run":         run_btn,
            "cancel":      cancel_btn,
            "reset":       reset_btn,
            "slider":      slider_rect,
            "select_item": select_item_btn,
            "edit_toggle": edit_toggle,
            "editor":      editor_rects,
            "back":        back_btn,
        }

    # ─────────────────────────────────────────
    # Draw button helper
    # ─────────────────────────────────────────
    def _btn(self, rect, text, color=(55, 60, 65), active=False, disabled=False):
        if disabled:
            bg     = (70, 70, 70)
            border = (90, 90, 90)
            fg     = (150, 150, 150)
        else:
            bg     = color if not active else tuple(min(255, v + 40) for v in color)
            border = (255, 255, 255) if active else (80, 85, 90)
            fg     = (255, 255, 255)

        pygame.draw.rect(self.screen, bg, rect, border_radius=6)
        pygame.draw.rect(self.screen, border, rect, width=1, border_radius=6)
        lbl = self.font.render(text, True, fg)
        self.screen.blit(lbl, lbl.get_rect(center=rect.center))

    # ─────────────────────────────────────────
    # Status text
    # ─────────────────────────────────────────
    def _status_text(self):
        return {
            "idle":      "Idle",
            "running":   "🔍 Running...",
            "completed": "✔ Completed",
        }.get(self.phase, self.phase)

    # ─────────────────────────────────────────
    # Stats block (góc trái dưới, trên BACK)
    # ─────────────────────────────────────────
    def _draw_stats(self, back_rect):
        lines = [
            ("Trạng thái", self._status_text()),
            ("Bước",       str(self.steps_count)),
            ("Fitness",    f"{self.current_fitness}/100"),
        ]
        line_h  = 18
        total_h = len(lines) * line_h + 4
        y0      = back_rect.top - total_h - 10

        for i, (k, v) in enumerate(lines):
            y    = y0 + i * line_h
            ks   = self.small_font.render(f"{k}:", True, (160, 160, 160))
            vs   = self.small_font.render(v,       True, (255, 220, 80))
            self.screen.blit(ks, (self.PAD, y))
            self.screen.blit(vs, (self.PAD + ks.get_width() + 4, y))

    # ─────────────────────────────────────────
    # Events
    # ─────────────────────────────────────────
    def handle_events(self, events):
        # ── Victory panel xử lý trước ──
        panel_action = self.victory_panel.handle_events(events)
        if panel_action == "replay":
            # ✅ FIX: Chỉ đóng panel, KHÔNG tự động chạy lại
            return
        if self.victory_panel.visible:
            return

        ui = self._ui_rects()
        # sync slider
        self.slider_speed.rect = ui["slider"]

        for event in events:
            # slider
            if self.slider_speed.handle_event(event):
                self.step_delay_ms = self.slider_speed.value

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.stage_manager.change_stage("stage_select")

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                # ── panel ──
                if pos[0] < self.PANEL_W:

                    # algo select
                    if ui["hc"].collidepoint(pos) and self.phase != "running":
                        self.selected_algorithm = "Hill Climbing"
                        return
                    if ui["sa"].collidepoint(pos) and self.phase != "running":
                        self.selected_algorithm = "Simulated Annealing"
                        return
                    if ui["beam"].collidepoint(pos) and self.phase != "running":
                        self.selected_algorithm = "Local Beam"
                        return

                    # actions
                    if ui["run"].collidepoint(pos):
                        if self.phase in ("idle", "completed"):
                            self.steps_count     = 0
                            self.temperature     = 100.0
                            self.beam_states     = []
                            self.anim_swap       = None
                            self.last_step_time  = 0
                            self.phase           = "running"
                        return

                    if ui["cancel"].collidepoint(pos):
                        # ✅ FIX: Chỉ dừng AI, không hiện overlay thất bại
                        if self.phase == "running":
                            self.phase = "idle"
                        return

                    if ui["reset"].collidepoint(pos):
                        self._full_reset()
                        return

                    # đổi bảo bối mục tiêu
                    if ui["select_item"].collidepoint(pos) and self.phase != "running":
                        for _ in range(45):
                            self.target_item_id += 1
                            if self.target_item_id > 54:
                                self.target_item_id = 10
                            if not any(self.target_item_id in row for row in self.grid):
                                break
                        return

                    # edit toggle
                    if ui["edit_toggle"].collidepoint(pos):
                        self.is_editing = not self.is_editing
                        self.edit_mode  = None
                        return

                    # back
                    if ui["back"].collidepoint(pos):
                        self.stage_manager.change_stage("stage_select")
                        return

                    # editor buttons
                    if self.is_editing:
                        ed = ui["editor"]
                        for tid in ("add_item", "add_obs", "set_goal", "erase"):
                            if tid in ed and ed[tid].collidepoint(pos):
                                self.edit_mode = tid
                                return
                        if "save" in ed and ed["save"].collidepoint(pos):
                            self._save_map()
                            self.is_editing = False
                            return

                # ── canvas ──
                elif (self.is_editing and self.edit_mode and
                      self.start_x <= pos[0] <= self.start_x + self.grid_w and
                      self.start_y <= pos[1] <= self.start_y + self.grid_h):
                    c = (pos[0] - self.start_x) // self.cell_size
                    r = (pos[1] - self.start_y) // self.cell_size
                    if 0 <= r < self.rows and 0 <= c < self.cols:
                        self._handle_canvas_click(r, c)

    def _handle_canvas_click(self, r, c):
        if self.edit_mode == "add_item":
            if self.grid[r][c] != 9:
                avail = self._get_available_items()
                if avail:
                    self.grid[r][c] = random.choice(avail)
        elif self.edit_mode == "add_obs":
            if self.grid[r][c] != 9:
                self.grid[r][c] = random.randint(101, 104)
        elif self.edit_mode == "erase":
            if self.grid[r][c] != 9:
                self.grid[r][c] = 0
        elif self.edit_mode == "set_goal":
            old = self.find_target_position(self.grid)
            if old:
                self.grid[old[0]][old[1]] = 0
            self.grid[r][c] = 9
        self.current_fitness = self.calculate_fitness(self.grid)
        self.phase = "idle"

    # ─────────────────────────────────────────
    # Update
    # ─────────────────────────────────────────
    def update(self):
        if self.phase != "running":
            return
        now = pygame.time.get_ticks()

        # đang có animation swap
        if self.anim_swap:
            if now - self.anim_swap["start_time"] >= 150:
                self.grid            = self.anim_swap["next_state"]
                self.current_fitness = self.calculate_fitness(self.grid)
                self.steps_count    += 1
                self.anim_swap       = None
                self.last_step_time  = now
            return

        if now - self.last_step_time > int(self.step_delay_ms):
            self.run_ai_step()
            self.last_step_time = now

    def run_ai_step(self):
        if self.phase != "running":
            return

        # ✅ Kiểm tra thắng
        if self.current_fitness >= 100:
            self.phase = "completed"
            self.victory_panel.show(
                next_stage_id     = "stage4",
                next_stage_unlock = "stage4",
                title    = "CHẶNG 3 HOÀN THÀNH!",
                subtitle = f"Thu thập sau {self.steps_count} bước!",
                nodes_visited = self.steps_count,
                path_cost     = self.steps_count,
            )
            return

        if self.selected_algorithm == "Hill Climbing":
            next_state = step_hill_climbing(self)
        elif self.selected_algorithm == "Simulated Annealing":
            next_state = step_simulated_annealing(self)
        elif self.selected_algorithm == "Local Beam":
            next_state = step_local_beam_search(self)
        else:
            next_state = None

        if next_state:
            diffs = [{"pos": (r, c), "val": self.grid[r][c]}
                     for r in range(self.rows)
                     for c in range(self.cols)
                     if self.grid[r][c] != next_state[r][c]]
            if len(diffs) == 2:
                self.anim_swap = {
                    "start_time": pygame.time.get_ticks(),
                    "item1":      diffs[0],
                    "item2":      diffs[1],
                    "next_state": next_state,
                }
            else:
                self.grid            = next_state
                self.current_fitness = self.calculate_fitness(self.grid)
                self.steps_count    += 1
        else:
            # ✅ AI bị kẹt → dừng lại, KHÔNG hiện overlay
            self.phase = "idle"

    # ─────────────────────────────────────────
    # Draw helpers
    # ─────────────────────────────────────────
    def _draw_single_item(self, val, x, y, float_y):
        if 10 <= val <= 54:
            img = self.item_images.get(val)
            if img:
                off = (self.cell_size - img.get_width()) // 2
                self.screen.blit(img, (x + off, y + off + float_y))

        elif 101 <= val <= 104:
            img = self.obs_images.get(val)
            if img:
                off  = (self.cell_size - img.get_width()) // 2
                dx_, dy_ = x + off, y + off + float_y
                gc   = (255, 20, 50, 255) if (pygame.time.get_ticks() // 200) % 2 == 0 else (180, 0, 0, 255)
                mask = pygame.mask.from_surface(img)
                ms   = mask.to_surface(setcolor=gc, unsetcolor=(0, 0, 0, 0))
                for ddx in (-2, 0, 2):
                    for ddy in (-2, 0, 2):
                        if ddx or ddy:
                            self.screen.blit(ms, (dx_ + ddx, dy_ + ddy))
                self.screen.blit(img, (dx_, dy_))

        elif val == 9:
            img = self.item_images.get(self.target_item_id)
            if img:
                off  = (self.cell_size - img.get_width()) // 2
                dx_, dy_ = x + off, y + off + float_y
                mask = pygame.mask.from_surface(img)
                ms   = mask.to_surface(setcolor=(255, 215, 0, 255), unsetcolor=(0, 0, 0, 0))
                for ddx in (-3, 0, 3):
                    for ddy in (-3, 0, 3):
                        if ddx or ddy:
                            self.screen.blit(ms, (dx_ + ddx, dy_ + ddy))
                self.screen.blit(img, (dx_, dy_))

    # ─────────────────────────────────────────
    # Draw
    # ─────────────────────────────────────────
    def draw(self):
        ui = self._ui_rects()

        # sync slider rect
        self.slider_speed.rect = ui["slider"]

        # ── background ──
        if self.bg_image:
            self.screen.blit(self.bg_image, (self.PANEL_W, 0))
        else:
            self.screen.fill((10, 15, 25))
        ov = pygame.Surface((self.sw - self.PANEL_W, self.sh), pygame.SRCALPHA)
        ov.fill((10, 15, 30, 60))
        self.screen.blit(ov, (self.PANEL_W, 0))

        # ── lưới items ──
        now_t = pygame.time.get_ticks()
        for r in range(self.rows):
            for c in range(self.cols):
                x   = self.start_x + c * self.cell_size
                y   = self.start_y + r * self.cell_size
                val = self.grid[r][c]
                fy  = math.sin(now_t * 0.003 + r + c) * 6

                # bỏ qua ô đang swap
                is_swapping = False
                if self.anim_swap:
                    if ((r, c) == self.anim_swap["item1"]["pos"] or
                            (r, c) == self.anim_swap["item2"]["pos"]):
                        is_swapping = True

                if not is_swapping:
                    if self.is_editing:
                        pygame.draw.rect(self.screen, (0, 150, 255),
                                         pygame.Rect(x, y, self.cell_size, self.cell_size), 1)
                    self._draw_single_item(val, x, y, int(fy))

        # ── swap animation ──
        if self.anim_swap:
            p  = (now_t - self.anim_swap["start_time"]) / 150.0
            p  = max(0.0, min(1.0, p))
            p  = p * p * (3 - 2 * p)   # smoothstep
            r1, c1 = self.anim_swap["item1"]["pos"]
            v1     = self.anim_swap["item1"]["val"]
            r2, c2 = self.anim_swap["item2"]["pos"]
            v2     = self.anim_swap["item2"]["val"]
            x1 = self.start_x + c1 * self.cell_size
            y1 = self.start_y + r1 * self.cell_size
            x2 = self.start_x + c2 * self.cell_size
            y2 = self.start_y + r2 * self.cell_size
            fy = math.sin(now_t * 0.003) * 6
            self._draw_single_item(v1, x1 + (x2 - x1) * p, y1 + (y2 - y1) * p, int(fy))
            self._draw_single_item(v2, x2 + (x1 - x2) * p, y2 + (y1 - y2) * p, int(fy))

        # ════════════════════════════════
        # LEFT PANEL (khuôn stage1)
        # ════════════════════════════════
        panel = pygame.Surface((self.PANEL_W, self.sh), pygame.SRCALPHA)
        panel.fill((30, 33, 36, 210))
        self.screen.blit(panel, (0, 0))
        pygame.draw.line(self.screen, (70, 75, 80),
                         (self.PANEL_W, 0), (self.PANEL_W, self.sh), 2)

        # title
        self.screen.blit(self.title_font.render("CHẶNG 3",       True, (255, 200, 60)),
                         (self.PAD, 10))
        self.screen.blit(self.font.render("Local Search", True, (180, 180, 180)),
                         (self.PAD, 32))

        # algo
        self._btn(ui["hc"],   "Hill Climbing",
                  (40, 110, 190) if self.selected_algorithm == "Hill Climbing" else (55, 60, 65))
        self._btn(ui["sa"],   "Sim. Annealing",
                  (40, 110, 190) if self.selected_algorithm == "Simulated Annealing" else (55, 60, 65))
        self._btn(ui["beam"], "Local Beam",
                  (40, 110, 190) if self.selected_algorithm == "Local Beam" else (55, 60, 65))

        # actions
        self._btn(ui["run"], "▶ RUN AI",
                color=(46, 204, 113),
                disabled=(self.phase == "running"))

        # giống chặng 5: idle -> disabled (đen/xám), running -> đỏ
        self._btn(ui["cancel"], "■ CANCEL",
                color=(231, 76, 60),
                disabled=(self.phase != "running"))

        self._btn(ui["reset"], "↺ RESET MAP",
                color=(155, 89, 182))

        # slider tốc độ
        self.slider_speed.draw(self.screen, self.font)

        # đổi bảo bối
        item_no = self.target_item_id - 9
        self._btn(ui["select_item"], f"MỤC TIÊU #{item_no}", color=(241, 196, 15))

        # edit toggle
        lbl_edit = "EDIT MAP  [-]" if self.is_editing else "EDIT MAP  [+]"
        self._btn(ui["edit_toggle"], lbl_edit,
                  (40, 110, 190) if self.is_editing else (55, 60, 65))

        # editor 2 cột
        if self.is_editing:
            ed = ui["editor"]
            lbl_map = {
                "add_item": "Đặt BB",
                "add_obs":  "Vật cản",
                "set_goal": "Cục Vàng",
                "erase":    "Tẩy",
                "save":     "SAVE MAP",
            }
            for tid, lbl in lbl_map.items():
                if tid in ed:
                    self._btn(ed[tid], lbl,
                              (40, 110, 190) if self.edit_mode == tid else (55, 60, 65))

        # back
        self._btn(ui["back"], "◀ BACK", color=(231, 76, 60))

        # stats góc trái dưới
        self._draw_stats(ui["back"])

        # ── Victory panel ──
        self.victory_panel.update()
        self.victory_panel.draw()