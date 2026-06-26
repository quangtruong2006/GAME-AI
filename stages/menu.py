
import pygame
import config
import os
import sys

class VolumeSlider:
    def __init__(self, x, y, w, h, initial_val=0.5):
        self.rect = pygame.Rect(x, y, w, h)
        self.val = initial_val # Giá trị từ 0.0 đến 1.0
        self.dragging = False
        pygame.mixer.music.set_volume(self.val) # Set âm lượng ban đầu

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Tạo vùng click rộng hơn cái thanh một chút để dễ bấm
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
        self.val = max(0.0, min(1.0, rel_x / self.rect.w))
        pygame.mixer.music.set_volume(self.val) # Update thẳng vào Pygame

    def draw(self, screen, font):
        # 1. Vẽ thanh nền màu xám
        pygame.draw.rect(screen, (70, 75, 80), self.rect, border_radius=5)
        
        # 2. Vẽ thanh màu xanh thể hiện mức âm lượng hiện tại
        fill_width = int(self.rect.w * self.val)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.h)
        pygame.draw.rect(screen, (46, 204, 113), fill_rect, border_radius=5)
        
        # 3. Vẽ cục tròn (Knob) để nắm kéo
        knob_x = self.rect.x + fill_width
        pygame.draw.circle(screen, (255, 255, 255), (knob_x, self.rect.centery), self.rect.h + 2)
        
        # 4. In chữ MUSIC và phần trăm (%)
        txt = font.render(f"MUSIC: {int(self.val * 100)}%", True, (200, 220, 255))
        screen.blit(txt, (self.rect.x - txt.get_width() - 15, self.rect.centery - txt.get_height()//2))

class MainMenu:
    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager

        try:
            self.title_font = pygame.font.Font(
                "assets/fonts/minecraft.ttf", 60
            )
            self.btn_font = pygame.font.Font(
                "assets/fonts/minecraft.ttf", 24
            )
            self.sub_font = pygame.font.Font(
                "assets/fonts/minecraft.ttf", 14
            )
        except:
            self.title_font = pygame.font.SysFont(
                "Arial", 42, bold=True
            )
            self.btn_font = pygame.font.SysFont(
                "Arial", 24, bold=True
            )
            self.sub_font = pygame.font.SysFont(
                "Arial", 14
            )

        self.bg_image = None
        self._load_background()

        self.music_loaded = False
        

        self.hovered_btn = None
        self.small_font = pygame.font.SysFont("Arial", 16, bold=True)
        self.vol_slider = VolumeSlider(self.screen.get_width() - 220, self.screen.get_height() - 50, 150, 10, 0.3)
        self._load_music()
    # ======================================================
    # BACKGROUND
    # ======================================================

    def _load_background(self):
        bg_path = os.path.join(
            "assets", "images", "menu_bg.png"
        )

        if not os.path.exists(bg_path):
            bg_path = os.path.join(
                "assets", "images", "menu_bg.jpg"
            )

        if os.path.exists(bg_path):
            try:
                raw = pygame.image.load(bg_path).convert()

                self.bg_image = pygame.transform.scale(
                    raw,
                    (
                        self.screen.get_width(),
                        self.screen.get_height()
                    )
                )

            except Exception as e:
                print(e)

    # ======================================================
    # MUSIC
    # ======================================================

    def _load_music(self):

        for filename in [
            "epic_music.mp3"
        ]:

            music_path = os.path.join(
                "assets",
                "sounds",
                filename
            )

            if os.path.exists(music_path):

                try:
                    pygame.mixer.music.load(music_path)
                    pygame.mixer.music.set_volume(self.vol_slider.val) 
                    pygame.mixer.music.play(-1)

                    self.music_loaded = True
                    print(f">>> [THÀNH CÔNG] Đã phát nhạc: {music_path}")
                    return

                except Exception as e:
                    print(f">>> [LỖI PYGAME MIXER]: {e}")
            else:
                print(f">>> [CẢNH BÁO TỪ THIÊN NHIÊN]: Không tìm thấy file nhạc tại {music_path} ")

    def _stop_music(self):

        if self.music_loaded:
            pygame.mixer.music.fadeout(500)

    def _toggle_music(self):
        if not self.music_loaded:
            return

        if pygame.mixer.music.get_volume() > 0:
            pygame.mixer.music.set_volume(0)
            self.vol_slider.val = 0.0 # Ép thanh trượt thụt về 0
        else:
            pygame.mixer.music.set_volume(0.5)
            self.vol_slider.val = 0.5 # Ép thanh trượt nhảy lên mức 50%
    # ======================================================
    # BUTTONS
    # ======================================================

    def _get_buttons(self):

        sw = self.screen.get_width()
        sh = self.screen.get_height()

        play_btn = pygame.Rect(
            sw // 2 - 145,
            sh // 2 + 85,
            290,
            65
        )

        exit_btn = pygame.Rect(
            sw // 2 - 145,
            sh // 2 + 165,
            290,
            65
        )

        return play_btn, exit_btn

    # ======================================================
    # EVENTS
    # ======================================================

    def handle_events(self, events):

        play_btn, exit_btn = self._get_buttons()

        mouse_pos = pygame.mouse.get_pos()

        self.hovered_btn = None

        if play_btn.collidepoint(mouse_pos):
            self.hovered_btn = "play"

        elif exit_btn.collidepoint(mouse_pos):
            self.hovered_btn = "exit"

        for event in events:

            if event.type == pygame.MOUSEBUTTONDOWN:

                if event.button == 1:

                    if play_btn.collidepoint(event.pos):

                        #self._stop_music()
                        self.stage_manager.change_stage(
                            "stage_select"
                        )

                    elif exit_btn.collidepoint(event.pos):

                        self._stop_music()

                        pygame.quit()
                        sys.exit()

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_RETURN:

                    #self._stop_music()
                    self.stage_manager.change_stage(
                        "stage_select"
                    )

                elif event.key == pygame.K_ESCAPE:

                    self._stop_music()
                    pygame.quit()
                    sys.exit()

                elif event.key == pygame.K_m:

                    self._toggle_music()
            self.vol_slider.handle_event(event)
    # ======================================================
    # UPDATE
    # ======================================================

    def update(self):
        pass

    # ======================================================
    # DRAW TITLE
    # ======================================================

    def _draw_title(self, sw):

        title1 = self.title_font.render(
            "NOBITA",
            True,
            (0, 210, 255)
        )

        title2 = self.title_font.render(
            "RESCUE SHIZUKA",
            True,
            (255, 255, 255)
        )

        self.screen.blit(
            title1,
            (
                sw // 2 - title1.get_width() // 2,
                30
            )
        )

        self.screen.blit(
            title2,
            (
                sw // 2 - title2.get_width() // 2,
                95
            )
        )

    # ======================================================
    # SCI-FI BUTTON
    # ======================================================

    def _draw_button(
        self,
        rect,
        text,
        hovered=False
    ):

        glow_surface = pygame.Surface(
            (
                rect.width + 40,
                rect.height + 40
            ),
            pygame.SRCALPHA
        )

        glow_alpha = 90 if hovered else 40

        pygame.draw.rect(
            glow_surface,
            (0, 220, 255, glow_alpha),
            glow_surface.get_rect(),
            border_radius=18
        )

        self.screen.blit(
            glow_surface,
            (rect.x - 20, rect.y - 20)
        )

        bg_color = (
            (0, 120, 180)
            if hovered
            else
            (20, 50, 90)
        )

        pygame.draw.rect(
            self.screen,
            bg_color,
            rect,
            border_radius=12
        )

        pygame.draw.rect(
            self.screen,
            (0, 240, 255),
            rect,
            width=3,
            border_radius=12
        )

        txt = self.btn_font.render(
            text,
            True,
            (255, 255, 255)
        )

        self.screen.blit(
            txt,
            txt.get_rect(center=rect.center)
        )

    # ======================================================
    # DRAW
    # ======================================================

    def draw(self):

        sw = self.screen.get_width()
        sh = self.screen.get_height()

        if self.bg_image:

            if (
                self.bg_image.get_width() != sw
                or
                self.bg_image.get_height() != sh
            ):
                self._load_background()

            self.screen.blit(
                self.bg_image,
                (0, 0)
            )

        else:

            self.screen.fill(
                config.COLOR_BG
            )

        self._draw_title(sw)

        play_btn, exit_btn = self._get_buttons()

        self._draw_button(
            play_btn,
            "START GAME",
            self.hovered_btn == "play"
        )

        self._draw_button(
            exit_btn,
            "EXIT",
            self.hovered_btn == "exit"
        )

        hint = self.sub_font.render(
            "[ENTER] Start   [M] Mute   [ESC] Exit",
            True,
            (220, 220, 220)
        )

        self.screen.blit(
            hint,
            (
                sw // 2 - hint.get_width() // 2,
                sh - 35
            )
        )
        self.vol_slider.draw(self.screen, self.small_font)