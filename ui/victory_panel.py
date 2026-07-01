import pygame
import math


class VictoryPanel:
    """
    Bảng thông báo thành công dùng chung cho tất cả các stage.
    ĐÃ TĂNG CỠ CHỮ RẤT TO cho 3 thông số (gấp đôi so với bản trước).
    """

    # ──────────────────────────────────────────
    # Khởi tạo
    # ──────────────────────────────────────────
    def __init__(self, screen, stage_manager):
        self.screen        = screen
        self.stage_manager = stage_manager

        self.visible            = False
        self.next_stage_id      = None
        self.next_stage_unlock  = None
        self.title_text         = ""
        self.subtitle_text      = ""

        self.nodes_visited = None
        self.path_cost     = None
        self.exec_time     = None

        self.anim_timer       = 0
        self.ANIM_IN_DURATION = 35

        # Fonts - ĐÃ TĂNG CỠ CHỮ RẤT TO
        try:
            self.font_title      = pygame.font.Font("assets/fonts/minecraft.ttf", 32)
            self.font_sub        = pygame.font.Font("assets/fonts/minecraft.ttf", 18)
            self.font_btn        = pygame.font.Font("assets/fonts/minecraft.ttf", 18)
            self.font_stat_label = pygame.font.Font("assets/fonts/minecraft.ttf", 22)   # Tăng mạnh
            self.font_stat       = pygame.font.Font("assets/fonts/minecraft.ttf", 44)   # TO GẤP ĐÔI
        except Exception:
            self.font_title      = pygame.font.SysFont("Arial", 32, bold=True)
            self.font_sub        = pygame.font.SysFont("Arial", 18, bold=True)
            self.font_btn        = pygame.font.SysFont("Arial", 18, bold=True)
            self.font_stat_label = pygame.font.SysFont("Arial", 22, bold=True)
            self.font_stat       = pygame.font.SysFont("Arial", 44, bold=True)

        self.hovered_btn = None

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────
    def show(self, next_stage_id, next_stage_unlock,
             title="THÀNH CÔNG!", subtitle="",
             nodes_visited=None, path_cost=None, exec_time=None):
        self.visible            = True
        self.next_stage_id      = next_stage_id
        self.next_stage_unlock  = next_stage_unlock
        self.title_text         = title
        self.subtitle_text      = subtitle
        self.nodes_visited      = nodes_visited
        self.path_cost          = path_cost
        self.exec_time          = exec_time
        self.anim_timer         = 0
        self.hovered_btn        = None

    def hide(self):
        self.visible = False

    # ──────────────────────────────────────────
    # Geometry
    # ──────────────────────────────────────────
    def _panel_rect(self):
        sw, sh = self.screen.get_size()

        n_stats = sum(1 for v in (self.nodes_visited, self.path_cost, self.exec_time) if v is not None)
        ph = 420 if n_stats <= 2 else 480          # Tăng chiều cao panel
        pw = 680 if n_stats == 3 else 600           # Rộng hơn khi có 3 thẻ

        x        = sw // 2 - pw // 2
        progress = min(1.0, self.anim_timer / self.ANIM_IN_DURATION)
        ease     = 1 - (1 - progress) ** 3
        target_y = sh // 2 - ph // 2
        y        = int(-ph + (target_y + ph) * ease)
        return pygame.Rect(x, y, pw, ph)

    def _btn_rects(self, panel_rect):
        bw, bh  = 140, 52
        gap     = 20
        total_w = bw * 3 + gap * 2
        bx      = panel_rect.x + panel_rect.w // 2 - total_w // 2
        by      = panel_rect.y + panel_rect.h - bh - 35
        return {
            "menu":   pygame.Rect(bx,                   by, bw, bh),
            "replay": pygame.Rect(bx + bw + gap,        by, bw, bh),
            "next":   pygame.Rect(bx + (bw + gap) * 2,  by, bw, bh),
        }

    # ──────────────────────────────────────────
    # handle_events
    # ──────────────────────────────────────────
    def handle_events(self, events):
        if not self.visible:
            return None

        panel_rect = self._panel_rect()
        btns       = self._btn_rects(panel_rect)
        mouse_pos  = pygame.mouse.get_pos()

        self.hovered_btn = None
        for name, rect in btns.items():
            if rect.collidepoint(mouse_pos):
                self.hovered_btn = name

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btns["menu"].collidepoint(event.pos):
                    self.hide()
                    self.stage_manager.change_stage("stage_select")
                    return "menu"
                elif btns["replay"].collidepoint(event.pos):
                    self.hide()
                    return "replay"
                elif btns["next"].collidepoint(event.pos):
                    self.hide()
                    self._go_next_stage()
                    return "next"
        return None

    def _go_next_stage(self):
        if self.next_stage_unlock:
            self.stage_manager.trigger_unlock_effect = self.next_stage_unlock
        self.stage_manager.change_stage("stage_select")

    def update(self):
        if not self.visible:
            return
        if self.anim_timer < self.ANIM_IN_DURATION:
            self.anim_timer += 1

    # ──────────────────────────────────────────
    # draw
    # ──────────────────────────────────────────
    def draw(self):
        if not self.visible:
            return

        sw, sh     = self.screen.get_size()
        panel_rect = self._panel_rect()
        btns       = self._btn_rects(panel_rect)

        # Overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        # Panel body
        panel_surf = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
        for i in range(panel_rect.h):
            f = i / panel_rect.h
            r = int(12 + 22 * f)
            g = int(18 + 28 * f)
            b = int(25 + 45 * f)
            pygame.draw.line(panel_surf, (r, g, b, 240), (0, i), (panel_rect.w, i))

        pygame.draw.rect(panel_surf, (0, 255, 200), panel_surf.get_rect(), width=5, border_radius=18)
        self.screen.blit(panel_surf, panel_rect.topleft)

        self._draw_stars(panel_rect)

        # Title
        title_surf = self.font_title.render(self.title_text, True, (255, 230, 60))
        self.screen.blit(title_surf, title_surf.get_rect(centerx=panel_rect.centerx, y=panel_rect.y + 38))

        # Subtitle
        if self.subtitle_text:
            sub_surf = self.font_sub.render(self.subtitle_text, True, (180, 240, 255))
            self.screen.blit(sub_surf, sub_surf.get_rect(centerx=panel_rect.centerx, y=panel_rect.y + 85))

        # Separator
        sep_y = panel_rect.y + 125
        pygame.draw.line(self.screen, (0, 200, 180),
                         (panel_rect.x + 50, sep_y),
                         (panel_rect.x + panel_rect.w - 50, sep_y), 3)

        self._draw_stat_cards(panel_rect)

        sep_y2 = panel_rect.y + panel_rect.h - 95
        pygame.draw.line(self.screen, (0, 140, 130),
                         (panel_rect.x + 50, sep_y2),
                         (panel_rect.x + panel_rect.w - 50, sep_y2), 3)

        self._draw_buttons(btns)

    # ──────────────────────────────────────────
    # Stat cards - TO GẤP ĐÔI
    # ──────────────────────────────────────────
    def _draw_stat_cards(self, panel_rect):
        stats = []
        if self.nodes_visited is not None:
            stats.append(("Nodes duyệt", str(self.nodes_visited), (100, 200, 255)))
        if self.path_cost is not None:
            stats.append(("Chi phí", str(self.path_cost), (100, 255, 160)))
        if self.exec_time is not None:
            stats.append(("Thời gian", str(self.exec_time), (255, 215, 80)))

        if not stats:
            return

        n        = len(stats)
        card_w   = 190 if n == 3 else 210
        card_h   = 138                                      # Tăng mạnh chiều cao
        card_gap = 22
        total_w  = n * card_w + (n - 1) * card_gap
        start_x  = panel_rect.centerx - total_w // 2
        card_y   = panel_rect.y + 155

        for i, (label, value, accent) in enumerate(stats):
            cx        = start_x + i * (card_w + card_gap)
            card_rect = pygame.Rect(cx, card_y, card_w, card_h)

            # Nền thẻ
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            card_surf.fill((255, 255, 255, 18))
            pygame.draw.rect(card_surf, (*accent, 100),
                             card_surf.get_rect(), width=4, border_radius=16)
            self.screen.blit(card_surf, card_rect.topleft)

            # Label
            lbl_surf = self.font_stat_label.render(label, True, (210, 210, 210))
            self.screen.blit(lbl_surf,
                             lbl_surf.get_rect(centerx=card_rect.centerx, y=card_rect.y + 18))

            # Giá trị TO GẤP ĐÔI
            val_surf = self.font_stat.render(value, True, accent)
            self.screen.blit(val_surf,
                             val_surf.get_rect(centerx=card_rect.centerx, y=card_rect.y + 58))

    # ──────────────────────────────────────────
    # Buttons
    # ──────────────────────────────────────────
    def _draw_buttons(self, btns):
        BTN_STYLES = {
            "menu":   {"label": "MENU",          "color_normal": (55, 65, 75),   "color_hover": (85, 100, 115),   "text_color": (200, 220, 255)},
            "replay": {"label": "CHƠI LẠI",      "color_normal": (30, 100, 60),  "color_hover": (50, 160, 90),    "text_color": (200, 255, 220)},
            "next":   {"label": "TIẾP THEO ▶",   "color_normal": (20, 80, 160),  "color_hover": (40, 130, 230),   "text_color": (220, 240, 255)},
        }

        for name, rect in btns.items():
            style = BTN_STYLES[name]
            is_hov = (self.hovered_btn == name)
            bg = style["color_hover"] if is_hov else style["color_normal"]

            pygame.draw.rect(self.screen, bg, rect, border_radius=12)
            border_col = (0, 255, 200) if is_hov else (0, 170, 140)
            pygame.draw.rect(self.screen, border_col, rect, width=4, border_radius=12)

            label = self.font_btn.render(style["label"], True, style["text_color"])
            self.screen.blit(label, label.get_rect(center=rect.center))

    # ──────────────────────────────────────────
    # Stars
    # ──────────────────────────────────────────
    def _draw_stars(self, panel_rect):
        cx = panel_rect.centerx
        cy = panel_rect.y + 20
        offsets = [-65, 0, 65]
        sizes = [11, 16, 11]
        for ox, sz in zip(offsets, sizes):
            self._draw_star(cx + ox, cy, sz, (255, 220, 50))

    def _draw_star(self, cx, cy, size, color):
        points = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            r = size if i % 2 == 0 else size * 0.42
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        pygame.draw.polygon(self.screen, color, points)