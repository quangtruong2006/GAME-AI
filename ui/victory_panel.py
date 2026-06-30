import pygame
import math


class VictoryPanel:
    """
    Bảng thông báo thành công dùng chung cho tất cả các stage.

    Cách dùng:
        # Trong __init__ của stage:
        from ui.victory_panel import VictoryPanel
        self.victory_panel = VictoryPanel(screen, stage_manager)

        # Khi thắng:
        self.victory_panel.show(
            next_stage_id="stage2",
            next_stage_unlock="stage2",
            title="CHẶNG 1 HOÀN THÀNH!",
            subtitle="Nobita đã tìm thấy Doraemon!",
            nodes_visited=42,     # tuỳ chọn
            path_cost=7,          # tuỳ chọn
        )

        # Trong handle_events():
        panel_action = self.victory_panel.handle_events(events)
        if panel_action == "replay":
            return          # chỉ đóng panel, giữ nguyên màn đã chạy
        if self.victory_panel.visible:
            return

        # Trong update():
        self.victory_panel.update()

        # Trong draw() – gọi CUỐI CÙNG:
        self.victory_panel.draw()
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

        # Stats hiển thị trong panel
        self.nodes_visited = None   # int hoặc None (ẩn nếu None)
        self.path_cost     = None   # int / str hoặc None

        # Animation panel rơi từ trên xuống
        self.anim_timer       = 0
        self.ANIM_IN_DURATION = 30   # frames

        # Fonts
        try:
            self.font_title = pygame.font.Font("assets/fonts/minecraft.ttf", 28)
            self.font_sub   = pygame.font.Font("assets/fonts/minecraft.ttf", 15)
            self.font_btn   = pygame.font.Font("assets/fonts/minecraft.ttf", 16)
            self.font_stat  = pygame.font.Font("assets/fonts/minecraft.ttf", 14)
            self.font_stat_label = pygame.font.Font("assets/fonts/minecraft.ttf", 12)
        except Exception:
            self.font_title      = pygame.font.SysFont("Arial", 26, bold=True)
            self.font_sub        = pygame.font.SysFont("Arial", 14)
            self.font_btn        = pygame.font.SysFont("Arial", 15, bold=True)
            self.font_stat       = pygame.font.SysFont("Arial", 14, bold=True)
            self.font_stat_label = pygame.font.SysFont("Arial", 12)

        self.hovered_btn = None   # "menu" | "replay" | "next"

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────
    def show(self, next_stage_id, next_stage_unlock,
             title="THÀNH CÔNG!", subtitle="",
             nodes_visited=None, path_cost=None):
        """Hiện bảng thắng.  nodes_visited / path_cost là tuỳ chọn."""
        self.visible            = True
        self.next_stage_id      = next_stage_id
        self.next_stage_unlock  = next_stage_unlock
        self.title_text         = title
        self.subtitle_text      = subtitle
        self.nodes_visited      = nodes_visited
        self.path_cost          = path_cost
        self.anim_timer         = 0
        self.hovered_btn        = None

    def hide(self):
        self.visible = False

    # ──────────────────────────────────────────
    # Geometry
    # ──────────────────────────────────────────
    def _panel_rect(self):
        sw, sh = self.screen.get_size()
        pw, ph = 540, 370
        x        = sw // 2 - pw // 2
        progress = min(1.0, self.anim_timer / self.ANIM_IN_DURATION)
        ease     = 1 - (1 - progress) ** 3          # ease-out cubic
        target_y = sh // 2 - ph // 2
        y        = int(-ph + (target_y + ph) * ease)
        return pygame.Rect(x, y, pw, ph)

    def _btn_rects(self, panel_rect):
        bw, bh  = 130, 44
        gap     = 16
        total_w = bw * 3 + gap * 2
        bx      = panel_rect.x + panel_rect.w // 2 - total_w // 2
        by      = panel_rect.y + panel_rect.h - bh - 24
        return {
            "menu":   pygame.Rect(bx,                  by, bw, bh),
            "replay": pygame.Rect(bx + bw + gap,       by, bw, bh),
            "next":   pygame.Rect(bx + (bw + gap) * 2, by, bw, bh),
        }

    # ──────────────────────────────────────────
    # handle_events  →  trả về action string hoặc None
    # ──────────────────────────────────────────
    def handle_events(self, events):
        """
        Trả về:
            "replay"  – người dùng bấm CHƠI LẠI  (stage chỉ cần đóng panel)
            "next"    – người dùng bấm TIẾP THEO
            "menu"    – người dùng bấm MENU
            None      – không có action
        """
        if not self.visible:
            return None

        panel_rect = self._panel_rect()
        btns       = self._btn_rects(panel_rect)
        mouse_pos  = pygame.mouse.get_pos()

        # hover
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
                    # Chỉ đóng panel – stage quyết định phải làm gì tiếp
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

    # ──────────────────────────────────────────
    # update
    # ──────────────────────────────────────────
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

        # ── overlay tối ──
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # ── thân panel (gradient tối) ──
        panel_surf = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
        for i in range(panel_rect.h):
            f = i / panel_rect.h
            r = int(10 + 20 * f)
            g = int(15 + 25 * f)
            b = int(20 + 40 * f)
            pygame.draw.line(panel_surf, (r, g, b, 235), (0, i), (panel_rect.w, i))

        # viền neon
        pygame.draw.rect(panel_surf, (0, 255, 200),
                         panel_surf.get_rect(), width=3, border_radius=14)
        self.screen.blit(panel_surf, panel_rect.topleft)

        # ── 3 ngôi sao ──
        self._draw_stars(panel_rect)

        # ── Title ──
        title_surf = self.font_title.render(self.title_text, True, (255, 220, 50))
        self.screen.blit(title_surf,
                         title_surf.get_rect(centerx=panel_rect.centerx,
                                             y=panel_rect.y + 34))

        # ── Subtitle ──
        if self.subtitle_text:
            sub_surf = self.font_sub.render(self.subtitle_text, True, (180, 230, 255))
            self.screen.blit(sub_surf,
                             sub_surf.get_rect(centerx=panel_rect.centerx,
                                               y=panel_rect.y + 76))

        # ── Đường kẻ ngang ──
        sep_y = panel_rect.y + 108
        pygame.draw.line(self.screen, (0, 180, 160),
                         (panel_rect.x + 30, sep_y),
                         (panel_rect.x + panel_rect.w - 30, sep_y), 1)

        # ── Stat cards ──
        self._draw_stat_cards(panel_rect)

        # ── Đường kẻ ngang dưới stat ──
        sep_y2 = panel_rect.y + panel_rect.h - 80
        pygame.draw.line(self.screen, (0, 130, 120),
                         (panel_rect.x + 30, sep_y2),
                         (panel_rect.x + panel_rect.w - 30, sep_y2), 1)

        # ── 3 nút ──
        self._draw_buttons(btns)

    # ──────────────────────────────────────────
    # Stat cards
    # ──────────────────────────────────────────
    def _draw_stat_cards(self, panel_rect):
        """
        Vẽ 2 thẻ thống kê: Nodes đã duyệt | Chi phí đường đi.
        Chỉ vẽ nếu giá trị được truyền vào (không None).
        """
        # Tập hợp stats cần hiển thị
        stats = []
        if self.nodes_visited is not None:
            stats.append(("Nodes duyệt", str(self.nodes_visited),
                          (100, 200, 255)))   # màu xanh dương
        if self.path_cost is not None:
            stats.append(("Chi phí", str(self.path_cost),
                          (100, 255, 160)))   # màu xanh lá

        if not stats:
            # Không có gì – vẽ ngôi sao to hơn như cũ
            return

        # ── Layout ──
        # Tối đa 2 thẻ, căn giữa panel
        n       = len(stats)
        card_w  = 180
        card_h  = 72
        card_gap = 24
        total_w  = n * card_w + (n - 1) * card_gap
        start_x  = panel_rect.centerx - total_w // 2
        card_y   = panel_rect.y + 122   # dưới subtitle + separator

        for i, (label, value, accent) in enumerate(stats):
            cx = start_x + i * (card_w + card_gap)
            card_rect = pygame.Rect(cx, card_y, card_w, card_h)

            # Nền thẻ
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            card_surf.fill((255, 255, 255, 12))
            pygame.draw.rect(card_surf, (*accent, 80),
                             card_surf.get_rect(), width=2, border_radius=8)
            self.screen.blit(card_surf, card_rect.topleft)

            # Label nhỏ phía trên
            lbl_surf = self.font_stat_label.render(label, True, (180, 180, 180))
            self.screen.blit(lbl_surf,
                             lbl_surf.get_rect(centerx=card_rect.centerx,
                                               y=card_rect.y + 10))

            # Giá trị to phía dưới  (đổi màu accent)
            val_surf = self.font_stat.render(value, True, accent)
            self.screen.blit(val_surf,
                             val_surf.get_rect(centerx=card_rect.centerx,
                                               y=card_rect.y + 36))

    # ──────────────────────────────────────────
    # Buttons
    # ──────────────────────────────────────────
    def _draw_buttons(self, btns):
        BTN_STYLES = {
            "menu": {
                "label":        "MENU",
                "color_normal": (55,  65,  75),
                "color_hover":  (85, 100, 115),
                "text_color":   (200, 220, 255),
            },
            "replay": {
                "label":        "CHƠI LẠI",
                "color_normal": (30,  100,  60),
                "color_hover":  (50,  160,  90),
                "text_color":   (200, 255, 220),
            },
            "next": {
                "label":        "TIẾP THEO ▶",
                "color_normal": (20,   80, 160),
                "color_hover":  (40,  130, 230),
                "text_color":   (220, 240, 255),
            },
        }

        for name, rect in btns.items():
            style  = BTN_STYLES[name]
            is_hov = (self.hovered_btn == name)
            bg     = style["color_hover"] if is_hov else style["color_normal"]

            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            # viền accent khi hover
            border_col = (0, 255, 200) if is_hov else (0, 150, 130)
            pygame.draw.rect(self.screen, border_col, rect,
                             width=2, border_radius=8)

            label = self.font_btn.render(style["label"], True, style["text_color"])
            self.screen.blit(label, label.get_rect(center=rect.center))

    # ──────────────────────────────────────────
    # Stars decoration
    # ──────────────────────────────────────────
    def _draw_stars(self, panel_rect):
        """3 ngôi sao nhỏ phía trên title (decorative)."""
        # Đặt sao ở góc trên panel, không che title
        cx      = panel_rect.centerx
        cy      = panel_rect.y + 18
        offsets = [-52, 0, 52]
        sizes   = [9, 13, 9]
        for ox, sz in zip(offsets, sizes):
            self._draw_star(cx + ox, cy, sz, (255, 210, 30))

    def _draw_star(self, cx, cy, size, color):
        points = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            r     = size if i % 2 == 0 else size * 0.42
            points.append((cx + r * math.cos(angle),
                           cy + r * math.sin(angle)))
        pygame.draw.polygon(self.screen, color, points)