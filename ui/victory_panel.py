# ui/victory_panel.py
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
            next_stage_id="stage2",      # ID stage tiếp theo
            next_stage_unlock="stage2",  # Stage cần unlock (thường giống nhau)
            title="CHẶNG 1 HOÀN THÀNH!",
            subtitle="Nobita đã tìm thấy Doraemon!"
        )
    
        # Trong handle_events():
        self.victory_panel.handle_events(events)
    
        # Trong update():
        self.victory_panel.update()
    
        # Trong draw() - gọi CUỐI CÙNG để vẽ đè lên:
        self.victory_panel.draw()
    """

    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager

        self.visible = False
        self.next_stage_id = None
        self.next_stage_unlock = None
        self.title_text = ""
        self.subtitle_text = ""

        # Animation xuất hiện
        self.anim_timer = 0
        self.ANIM_IN_DURATION = 30  # frames để panel bay vào

        # Fonts
        try:
            self.font_title   = pygame.font.Font(
                "assets/fonts/minecraft.ttf", 32
            )
            self.font_sub     = pygame.font.Font(
                "assets/fonts/minecraft.ttf", 16
            )
            self.font_btn     = pygame.font.Font(
                "assets/fonts/minecraft.ttf", 18
            )
        except:
            self.font_title = pygame.font.SysFont("Arial", 30, bold=True)
            self.font_sub   = pygame.font.SysFont("Arial", 15)
            self.font_btn   = pygame.font.SysFont("Arial", 16, bold=True)

        self.hovered_btn = None  # "menu" | "relay" | "next"

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────
    def show(self, next_stage_id, next_stage_unlock,
             title="THÀNH CÔNG!", subtitle=""):
        """Hiện bảng thông báo thành công."""
        self.visible           = True
        self.next_stage_id     = next_stage_id
        self.next_stage_unlock = next_stage_unlock
        self.title_text        = title
        self.subtitle_text     = subtitle
        self.anim_timer        = 0
        self.hovered_btn       = None

    def hide(self):
        self.visible = False

    # ─────────────────────────────────────────
    # Internal: tính rect panel (căn giữa màn)
    # ─────────────────────────────────────────
    def _panel_rect(self):
        sw, sh = self.screen.get_size()
        pw, ph = 520, 340
        x = sw // 2 - pw // 2
        # Animation: panel rơi từ trên xuống
        progress = min(1.0, self.anim_timer / self.ANIM_IN_DURATION)
        ease = 1 - (1 - progress) ** 3   # ease-out cubic
        target_y = sh // 2 - ph // 2
        start_y  = -ph
        y = int(start_y + (target_y - start_y) * ease)
        return pygame.Rect(x, y, pw, ph)

    def _btn_rects(self, panel_rect):
        """Trả về dict 3 nút bên trong panel."""
        bw, bh = 130, 44
        gap     = 18
        total_w = bw * 3 + gap * 2
        bx      = panel_rect.x + panel_rect.w // 2 - total_w // 2
        by      = panel_rect.y + panel_rect.h - bh - 30

        return {
            "menu":  pygame.Rect(bx,               by, bw, bh),
            "relay": pygame.Rect(bx + bw + gap,    by, bw, bh),
            "next":  pygame.Rect(bx + (bw + gap)*2, by, bw, bh),
        }

    # ─────────────────────────────────────────
    # handle_events
    # ─────────────────────────────────────────
    def handle_events(self, events):
        if not self.visible:
            return

        panel_rect = self._panel_rect()
        btns       = self._btn_rects(panel_rect)
        mouse_pos  = pygame.mouse.get_pos()

        # Hover detection
        self.hovered_btn = None
        for name, rect in btns.items():
            if rect.collidepoint(mouse_pos):
                self.hovered_btn = name

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btns["menu"].collidepoint(event.pos):
                    self.hide()
                    self.stage_manager.change_stage("menu")

                elif btns["relay"].collidepoint(event.pos):
                    self.hide()
                    # Stage tự reset khi được gọi lại
                    # (stage_manager.current_stage vẫn là stage này)
                    current = self.stage_manager.current_stage
                    if hasattr(current, "reset_path"):
                        current.reset_path()

                elif btns["next"].collidepoint(event.pos):
                    self.hide()
                    self._go_next_stage()

    def _go_next_stage(self):
        """
        Chuyển sang stage_select và kích hoạt animation vỡ khóa.
        StageManager sẽ bắt tín hiệu trigger_unlock_effect.
        """
        if self.next_stage_unlock:
            # Đặt cờ để StageManager xử lý khi đã ở stage_select
            self.stage_manager.trigger_unlock_effect = self.next_stage_unlock

        self.stage_manager.change_stage("stage_select")

    # ─────────────────────────────────────────
    # update
    # ─────────────────────────────────────────
    def update(self):
        if not self.visible:
            return
        if self.anim_timer < self.ANIM_IN_DURATION:
            self.anim_timer += 1

    # ─────────────────────────────────────────
    # draw
    # ─────────────────────────────────────────
    def draw(self):
        if not self.visible:
            return

        sw, sh    = self.screen.get_size()
        panel_rect = self._panel_rect()
        btns       = self._btn_rects(panel_rect)

        # ── Overlay tối toàn màn ──
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # ── Thân panel ──
        panel_surf = pygame.Surface(
            (panel_rect.w, panel_rect.h), pygame.SRCALPHA
        )

        # Nền gradient tối
        for i in range(panel_rect.h):
            alpha  = 230
            factor = i / panel_rect.h
            r = int(10  + 20  * factor)
            g = int(15  + 25  * factor)
            b = int(20  + 35  * factor)
            pygame.draw.line(
                panel_surf, (r, g, b, alpha),
                (0, i), (panel_rect.w, i)
            )

        # Viền neon
        pygame.draw.rect(
            panel_surf, (0, 255, 200),
            panel_surf.get_rect(), width=3, border_radius=14
        )
        self.screen.blit(panel_surf, panel_rect.topleft)

        # ── Icon ngôi sao (đơn giản vẽ bằng polygon) ──
        self._draw_stars(panel_rect)

        # ── Title ──
        title_surf = self.font_title.render(
            self.title_text, True, (255, 220, 50)
        )
        self.screen.blit(
            title_surf,
            title_surf.get_rect(
                centerx=panel_rect.centerx,
                y=panel_rect.y + 40
            )
        )

        # ── Subtitle ──
        if self.subtitle_text:
            sub_surf = self.font_sub.render(
                self.subtitle_text, True, (180, 230, 255)
            )
            self.screen.blit(
                sub_surf,
                sub_surf.get_rect(
                    centerx=panel_rect.centerx,
                    y=panel_rect.y + 90
                )
            )

        # ── Đường kẻ ngang ──
        pygame.draw.line(
            self.screen,
            (0, 180, 160),
            (panel_rect.x + 30,         panel_rect.y + 130),
            (panel_rect.x + panel_rect.w - 30, panel_rect.y + 130),
            1
        )

        # ── Stats nếu muốn (để trống, stage override nếu cần) ──
        self._draw_extra_info(panel_rect)

        # ── 3 Nút ──
        BTN_STYLES = {
            "menu":  {
                "label": "MENU",
                "color_normal": (60,  70,  80),
                "color_hover":  (90, 105, 120),
                "text_color":   (200, 220, 255),
            },
            "relay": {
                "label": "CHƠI LẠI",
                "color_normal": (30,  100, 60),
                "color_hover":  (50,  160, 90),
                "text_color":   (200, 255, 220),
            },
            "next":  {
                "label": "TIẾP THEO ▶",
                "color_normal": (20,  80,  160),
                "color_hover":  (40,  130, 230),
                "text_color":   (220, 240, 255),
            },
        }

        for name, rect in btns.items():
            style = BTN_STYLES[name]
            is_hov = (self.hovered_btn == name)
            bg = style["color_hover"] if is_hov else style["color_normal"]

            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            pygame.draw.rect(
                self.screen, (0, 200, 180), rect, width=2, border_radius=8
            )

            label = self.font_btn.render(
                style["label"], True, style["text_color"]
            )
            self.screen.blit(label, label.get_rect(center=rect.center))

    # ─────────────────────────────────────────
    # Helpers vẽ nội dung phụ (stage có thể override)
    # ─────────────────────────────────────────
    def _draw_stars(self, panel_rect):
        """Vẽ 3 ngôi sao đơn giản bằng polygon."""
        cx = panel_rect.centerx
        cy = panel_rect.y + 170
        offsets = [-70, 0, 70]
        sizes   = [18, 24, 18]

        for ox, sz in zip(offsets, sizes):
            self._draw_star(cx + ox, cy, sz, (255, 210, 30))

    def _draw_star(self, cx, cy, size, color):
        points = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            r = size if i % 2 == 0 else size * 0.45
            points.append((
                cx + r * math.cos(angle),
                cy + r * math.sin(angle)
            ))
        pygame.draw.polygon(self.screen, color, points)

    def _draw_extra_info(self, panel_rect):
        """
        Hook để stage con bổ sung thêm thông tin vào panel.
        Mặc định không vẽ gì.
        Override bằng cách tạo subclass hoặc monkey-patch.
        """
        pass