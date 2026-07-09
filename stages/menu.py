import pygame
import config
import os
import sys


class VolumeSlider:
    def __init__(self, x, y, w, h, initial_val=0.5):
        self.rect = pygame.Rect(x, y, w, h)
        self.val = initial_val
        self.dragging = False
        pygame.mixer.music.set_volume(self.val)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hitbox = self.rect.inflate(20, 30)
            if hitbox.collidepoint(event.pos):
                self.dragging = True
                self._update_val(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_val(event.pos[0])

    def _update_val(self, mouse_x):
        rel_x = mouse_x - self.rect.x
        self.val = max(0.0, min(1.0, rel_x / self.rect.w if self.rect.w else 0.0))
        pygame.mixer.music.set_volume(self.val)

    def draw(self, screen, font):
        pygame.draw.rect(screen, (70, 75, 80), self.rect, border_radius=5)

        fill_width = int(self.rect.w * self.val)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.h)
        pygame.draw.rect(screen, (46, 204, 113), fill_rect, border_radius=5)

        knob_x = self.rect.x + fill_width
        pygame.draw.circle(screen, (255, 255, 255), (knob_x, self.rect.centery), self.rect.h + 2)

        txt = font.render(f"MUSIC: {int(self.val * 100)}%", True, (200, 220, 255))
        screen.blit(txt, (self.rect.x - txt.get_width() - 15, self.rect.centery - txt.get_height() // 2))


class MainMenu:
    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager

        try:
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 56)
            self.btn_font = pygame.font.Font("assets/fonts/minecraft.ttf", 24)
            self.sub_font = pygame.font.Font("assets/fonts/minecraft.ttf", 14)
        except Exception:
            self.title_font = pygame.font.SysFont("Arial", 42, bold=True)
            self.btn_font = pygame.font.SysFont("Arial", 24, bold=True)
            self.sub_font = pygame.font.SysFont("Arial", 14)

        self.small_font = pygame.font.SysFont("Arial", 16, bold=True)

        self.bg_image = None
        self._load_background()

        self.music_loaded = False
        self.hovered_btn = None

        # Settings overlay
        self.show_settings = False
        self.debug_hitboxes = False  # bấm F1 để hiện khung nút (căn chỉnh)

        # slider (rect sẽ update theo layout mỗi draw)
        self.vol_slider = VolumeSlider(0, 0, 150, 10, 0.3)

        self._load_music()

    # ======================================================
    # BACKGROUND
    # ======================================================
    def _load_background(self):
        for fn in ("menu_bg.png", "menu_bg.jpg"):
            bg_path = os.path.join("assets", "images", fn)
            if os.path.exists(bg_path):
                try:
                    raw = pygame.image.load(bg_path).convert()
                    self.bg_image = pygame.transform.smoothscale(
                        raw, (self.screen.get_width(), self.screen.get_height())
                    )
                    return
                except Exception as e:
                    print(e)

        self.bg_image = None

    # ======================================================
    # MUSIC
    # ======================================================
    def _load_music(self):
        for filename in ["epic_music.mp3"]:
            music_path = os.path.join("assets", "sounds", filename)
            if os.path.exists(music_path):
                try:
                    pygame.mixer.music.load(music_path)
                    pygame.mixer.music.set_volume(self.vol_slider.val)
                    pygame.mixer.music.play(-1)
                    self.music_loaded = True
                    print(f">>> [OK] Music: {music_path}")
                    return
                except Exception as e:
                    print(f">>> [MIXER ERROR]: {e}")
            else:
                print(f">>> [WARN] Missing music: {music_path}")

    def _stop_music(self):
        if self.music_loaded:
            pygame.mixer.music.fadeout(500)

    def _toggle_music(self):
        if not self.music_loaded:
            return
        if pygame.mixer.music.get_volume() > 0:
            pygame.mixer.music.set_volume(0)
            self.vol_slider.val = 0.0
        else:
            pygame.mixer.music.set_volume(0.5)
            self.vol_slider.val = 0.5

    # ======================================================
    # LAYOUT (hitboxes theo tỉ lệ màn hình)
    # ======================================================
    def _layout(self):
        sw, sh = self.screen.get_width(), self.screen.get_height()

        # --- 3 nút đang nằm sẵn trong ảnh ---
        # Bạn có thể chỉnh các tỷ lệ này nếu click chưa khớp.
        btn_w = int(sw * 0.24)
        btn_h = int(sh * 0.095)
        x = sw // 2 - btn_w // 2

        y_start   = int(sh * 0.34)
        y_setting = int(sh * 0.47)
        y_exit    = int(sh * 0.61)

        start_btn   = pygame.Rect(x, y_start,   btn_w, btn_h)
        setting_btn = pygame.Rect(x, y_setting, btn_w, btn_h)
        exit_btn    = pygame.Rect(x, y_exit,    btn_w, btn_h)

        # --- settings panel ---
        panel_w = int(sw * 0.46)
        panel_h = int(sh * 0.34)
        panel = pygame.Rect(sw // 2 - panel_w // 2, int(sh * 0.26), panel_w, panel_h)

        back_btn = pygame.Rect(panel.x + 18, panel.bottom - 58, 160, 40)
        slider_rect = pygame.Rect(panel.x + 80, panel.y + 110, panel.w - 140, 12)

        return start_btn, setting_btn, exit_btn, panel, back_btn, slider_rect

    # ======================================================
    # EVENTS
    # ======================================================
    def handle_events(self, events):
        start_btn, setting_btn, exit_btn, panel, back_btn, slider_rect = self._layout()

        mouse_pos = pygame.mouse.get_pos()
        self.hovered_btn = None

        if not self.show_settings:
            if start_btn.collidepoint(mouse_pos):
                self.hovered_btn = "start"
            elif setting_btn.collidepoint(mouse_pos):
                self.hovered_btn = "setting"
            elif exit_btn.collidepoint(mouse_pos):
                self.hovered_btn = "exit"

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1:
                    self.debug_hitboxes = not self.debug_hitboxes

                if event.key == pygame.K_m:
                    self._toggle_music()

                if event.key == pygame.K_ESCAPE:
                    if self.show_settings:
                        self.show_settings = False
                    else:
                        self._stop_music()
                        pygame.quit()
                        sys.exit()

                if event.key == pygame.K_RETURN and not self.show_settings:
                    self.stage_manager.change_stage("stage_select")

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.show_settings:
                    if back_btn.collidepoint(event.pos):
                        self.show_settings = False
                        continue
                else:
                    if start_btn.collidepoint(event.pos):
                        self.stage_manager.change_stage("stage_select")
                        continue
                    if setting_btn.collidepoint(event.pos):
                        self.show_settings = True
                        continue
                    if exit_btn.collidepoint(event.pos):
                        self._stop_music()
                        pygame.quit()
                        sys.exit()

            # slider chỉ nhận event khi settings đang mở
            if self.show_settings:
                self.vol_slider.rect = slider_rect
                self.vol_slider.handle_event(event)

    def update(self):
        pass

    # ======================================================
    # DRAW HELPERS
    # ======================================================
    def _draw_soft_hover(self, rect, color=(0, 240, 255)):
        """Vẽ glow nhẹ lên nút đã có sẵn trong ảnh nền."""
        t = pygame.time.get_ticks()
        pulse = 0.45 + 0.55 * abs(pygame.math.Vector2(1, 0).rotate(t * 0.12).x)

        pad = 10
        glow = pygame.Surface((rect.w + pad * 2, rect.h + pad * 2), pygame.SRCALPHA)
        a = int(60 + 70 * pulse)
        pygame.draw.rect(glow, (*color, a), glow.get_rect(), border_radius=26)
        self.screen.blit(glow, (rect.x - pad, rect.y - pad))

        pygame.draw.rect(self.screen, color, rect, width=3, border_radius=18)

    def _draw_settings_overlay(self, panel, back_btn):
        sw, sh = self.screen.get_width(), self.screen.get_height()

        # overlay
        ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        self.screen.blit(ov, (0, 0))

        # panel
        p = pygame.Surface(panel.size, pygame.SRCALPHA)
        p.fill((12, 18, 30, 210))
        self.screen.blit(p, panel.topleft)
        pygame.draw.rect(self.screen, (0, 240, 255), panel, 2, border_radius=14)

        title = self.btn_font.render("SETTING", True, (220, 245, 255))
        self.screen.blit(title, (panel.x + 18, panel.y + 18))

        hint = self.sub_font.render("[M] Mute   [ESC] Close", True, (200, 210, 220))
        self.screen.blit(hint, (panel.x + 18, panel.y + 50))

        # slider
        self.vol_slider.draw(self.screen, self.small_font)

        # back btn
        pygame.draw.rect(self.screen, (231, 76, 60), back_btn, border_radius=10)
        pygame.draw.rect(self.screen, (255, 255, 255), back_btn, 2, border_radius=10)
        txt = self.btn_font.render("BACK", True, (255, 255, 255))
        self.screen.blit(txt, txt.get_rect(center=back_btn.center))

    # ======================================================
    # DRAW
    # ======================================================
    def draw(self):
        sw = self.screen.get_width()
        sh = self.screen.get_height()

        if self.bg_image:
            if self.bg_image.get_width() != sw or self.bg_image.get_height() != sh:
                self._load_background()
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(getattr(config, "COLOR_BG", (20, 20, 25)))

        start_btn, setting_btn, exit_btn, panel, back_btn, slider_rect = self._layout()

        # hover highlight (menu chính)
        if not self.show_settings:
            if self.hovered_btn == "start":
                self._draw_soft_hover(start_btn, (0, 240, 255))
            elif self.hovered_btn == "setting":
                self._draw_soft_hover(setting_btn, (180, 90, 255))
            elif self.hovered_btn == "exit":
                self._draw_soft_hover(exit_btn, (255, 90, 140))

            hint = self.sub_font.render("[ENTER] Start   [M] Mute   [ESC] Exit", True, (235, 235, 235))
            self.screen.blit(hint, (sw // 2 - hint.get_width() // 2, sh - 35))

        # settings overlay
        if self.show_settings:
            self.vol_slider.rect = slider_rect
            self._draw_settings_overlay(panel, back_btn)

        # debug hitboxes
        if self.debug_hitboxes:
            for r, col in [(start_btn, (0, 255, 255)), (setting_btn, (255, 255, 0)), (exit_btn, (255, 0, 255))]:
                pygame.draw.rect(self.screen, col, r, 2)