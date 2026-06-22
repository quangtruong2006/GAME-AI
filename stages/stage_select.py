# File: stages/stage_select.py
import pygame
import config
import os
import sys
import random

class StageSelect:
    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager

        # Font chữ
        try:
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 40)
            self.btn_font = pygame.font.Font("assets/fonts/minecraft.ttf", 20)
            self.sub_font = pygame.font.Font("assets/fonts/minecraft.ttf", 13)
        except:
            self.title_font = pygame.font.SysFont("Arial", 36, bold=True)
            self.btn_font = pygame.font.SysFont("Arial", 18, bold=True)
            self.sub_font = pygame.font.SysFont("Arial", 12)

        self.bg_image = None
        self._load_background()
        self.hovered_btn = None

        # --- BIẾN QUẢN LÝ HOẠT ẢNH VỠ KHÓA TRANSTITION ---
        self.animating_stage = None
        self.anim_timer = 0

        # Data 6 chặng
        self.stages_info = [
            {"id": "stage1", "title": "CHẶNG 1", "sub": "ĐÁNH THỨC KÝ ỨC"},
            {"id": "stage2", "title": "CHẶNG 2", "sub": "TRUY TÌM DẤU VẾT SHIZUKA"},
            {"id": "stage3", "title": "CHẶNG 3", "sub": "KHÔI PHỤC KHO BẢO BỐI"},
            {"id": "stage4", "title": "CHẶNG 4", "sub": "VƯỢT RỪNG THỜI GIAN"},
            {"id": "stage5", "title": "CHẶNG 5", "sub": "PHÁ HỆ THỐNG PHONG ẤN"},
            {"id": "stage6", "title": "CHẶNG 6", "sub": "GIẢI CỨU SHIZUKA"},
        ]

    def trigger_unlock_animation(self, stage_id):
        """Hàm kích hoạt ngòi nổ vỡ khóa từ stage khác gọi sang"""
        self.animating_stage = stage_id
        self.anim_timer = 0

    def _load_background(self):
        bg_path = os.path.join("assets", "images", "select_bg.png")
        if os.path.exists(bg_path):
            try:
                raw = pygame.image.load(bg_path).convert()
                self.bg_image = pygame.transform.smoothscale(raw, (self.screen.get_width(), self.screen.get_height()))
            except:
                pass

    def _get_buttons(self):
        sw = self.screen.get_width()
        sh = self.screen.get_height()
        buttons = []

        card_w, card_h = 180, 280
        gap = 25
        total_width = (card_w * 6) + (gap * 5)
        start_x = sw // 2 - total_width // 2
        start_y = sh // 2 - card_h // 2 + 20

        for i, stage in enumerate(self.stages_info):
            x = start_x + i * (card_w + gap)
            y = start_y
            rect = pygame.Rect(x, y, card_w, card_h)
            buttons.append({"rect": rect, "info": stage})

        back_btn = pygame.Rect(30, sh - 70, 150, 40)
        return buttons, back_btn

    def handle_events(self, events):
        if self.animating_stage: 
            return # Khi đang nổ khóa thì đóng băng sự kiện chuột cho người xem tập trung ngắm hiệu ứng

        buttons, back_btn = self._get_buttons()
        mouse_pos = pygame.mouse.get_pos()
        self.hovered_btn = None

        for btn in buttons:
            if btn["rect"].collidepoint(mouse_pos):
                self.hovered_btn = btn["info"]["id"]
                
        if back_btn.collidepoint(mouse_pos):
            self.hovered_btn = "back"

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in buttons:
                    if btn["rect"].collidepoint(event.pos):
                        if btn["info"]["id"] in self.stage_manager.unlocked_stages:
                            self.stage_manager.change_stage(btn["info"]["id"])

                if back_btn.collidepoint(event.pos):
                    self.stage_manager.change_stage("menu")

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.stage_manager.change_stage("menu")

    def update(self):
        # Tăng biến đếm thời gian của hoạt ảnh theo từng frame hình
        if self.animating_stage:
            self.anim_timer += 1
            if self.anim_timer >= 90: # Chạy xong 90 frame thì kết thúc mở khóa chính thức
                self.stage_manager.unlock_stage(self.animating_stage)
                self.animating_stage = None
                self.anim_timer = 0

    def _draw_lock(self, surface, center_x, center_y, offset_x=0, offset_y=0, alpha=255, split_progress=0.0):
        # Vẽ quai ổ khóa (vòng cung)
        quai_y_shift = int(split_progress * -35) # Tách mảnh vỡ bay lên trên
        quai_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.arc(quai_surf, (120, 125, 130, alpha), (8, 0, 24, 24), 0, 3.14159, 4)
        surface.blit(quai_surf, (center_x - 20 + offset_x, center_y - 20 + offset_y + quai_y_shift))

        # Vẽ thân ổ khóa
        if split_progress == 0:
            # Lúc chưa vỡ vẽ khối đặc bình thường
            pygame.draw.rect(surface, (120, 125, 130, alpha), (center_x - 18 + offset_x, center_y - 5 + offset_y, 36, 26), border_radius=4)
            pygame.draw.circle(surface, (40, 45, 50, alpha), (center_x + offset_x, center_y + 8 + offset_y), 4)
            pygame.draw.rect(surface, (40, 45, 50, alpha), (center_x - 2 + offset_x, center_y + 8 + offset_y, 4, 8))
        else:
            # Giai đoạn vỡ vụn: Thân khóa vỡ đôi dạt sang hai bên tả hữu
            half_x_shift = int(split_progress * 25)
            # Mảnh Trái
            pygame.draw.rect(surface, (120, 125, 130, alpha), (center_x - 18 + offset_x - half_x_shift, center_y - 5 + offset_y, 18, 26), border_top_left_radius=4, border_bottom_left_radius=4)
            # Mảnh Phải
            pygame.draw.rect(surface, (120, 125, 130, alpha), (center_x + offset_x + half_x_shift, center_y - 5 + offset_y, 18, 26), border_top_right_radius=4, border_bottom_right_radius=4)

    def _draw_card(self, rect, info, is_hovered):
        card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        
        # Một stage được xem là đang khóa nếu nó không ở trong unlocked_stages và không phải đang diễn hoạt hoạt ảnh vỡ
        locked = info["id"] not in self.stage_manager.unlocked_stages
        is_animating = (info["id"] == self.animating_stage)

        bg_alpha = 220 if (is_hovered and not locked) else 180
        pygame.draw.rect(card_surf, (15, 20, 25, bg_alpha), card_surf.get_rect(), border_radius=10)

        if locked and not is_animating:
            # ================= GIAO DIỆN KHÓA TĨNH TỰ NHIÊN =================
            self._draw_lock(card_surf, rect.width // 2, rect.height // 2 - 30)
            title_txt = self.btn_font.render(info["title"], True, (100, 105, 110))
            card_surf.blit(title_txt, (rect.width//2 - title_txt.get_width()//2, rect.height//2 + 30))
            
            words = info["sub"].split(" ")
            line1 = " ".join(words[:len(words)//2 + 1])
            line2 = " ".join(words[len(words)//2 + 1:])
            sub1 = self.sub_font.render(line1, True, (80, 85, 90))
            sub2 = self.sub_font.render(line2, True, (80, 85, 90))
            card_surf.blit(sub1, (rect.width//2 - sub1.get_width()//2, rect.height//2 + 65))
            card_surf.blit(sub2, (rect.width//2 - sub2.get_width()//2, rect.height//2 + 85))

        elif is_animating:
            # ================= KỊCH BẢN PHIM HOẠT ẢNH VỠ KHÓA DỰA VÀO TIMER =================
            cx, cy = rect.width // 2, rect.height // 2 - 30
            
            if self.anim_timer < 30:
                # GIAO ĐOẠN 1: Khóa rung lắc kịch liệt + vẽ tia nứt điện sấm sét nổ tung
                ox = random.randint(-3, 3)
                oy = random.randint(-3, 3)
                self._draw_lock(card_surf, cx, cy, offset_x=ox, offset_y=oy)
                
                # Vẽ tia nứt vàng chớp nháy đè lên ổ khóa
                if self.anim_timer % 4 < 2:
                    pygame.draw.line(card_surf, (255, 215, 0), (cx - 15, cy - 10), (cx + 15, cy + 20), 2)
                    pygame.draw.line(card_surf, (255, 69, 0), (cx + 10, cy - 15), (cx - 12, cy + 15), 2)
                
                title_txt = self.btn_font.render(info["title"], True, (100, 105, 110))
                card_surf.blit(title_txt, (rect.width//2 - title_txt.get_width()//2, rect.height//2 + 30))

            elif self.anim_timer < 60:
                # GIAI ĐOẠN 2: Ổ khóa vỡ tan bành bắn tung tóe dạt ra xa + mờ mịt biến mất
                p = (self.anim_timer - 30) / 30.0 # Tiến độ vỡ từ 0.0 -> 1.0
                alpha = int((1.0 - p) * 255)
                self._draw_lock(card_surf, cx, cy, alpha=alpha, split_progress=p)
                
                title_txt = self.btn_font.render(info["title"], True, (100, 105, 110))
                card_surf.blit(title_txt, (rect.width//2 - title_txt.get_width()//2, rect.height//2 + 30))

            else:
                # GIAI ĐOẠN 3: Thẻ bừng sáng phát ra làn sóng xung kích Shockwave
                p = (self.anim_timer - 60) / 30.0 # Tiến độ phát sáng 0.0 -> 1.0
                glow_alpha = int(p * 255)
                
                # Đổ dải màu phát sáng lung linh dần lên
                pygame.draw.rect(card_surf, (200, 230, 255, int(p * 220)), (0, 0, rect.width, rect.height - 80), border_top_left_radius=10, border_top_right_radius=10)
                pygame.draw.rect(card_surf, (0, 100, 120, int(p * 220)), (0, rect.height - 80, rect.width, 80), border_bottom_left_radius=10, border_bottom_right_radius=10)
                pygame.draw.rect(card_surf, (0, 255, 255, glow_alpha), card_surf.get_rect(), width=3, border_radius=10)
                
                # Sóng sáng tròn bùng nổ tỏa rộng mờ dần ra rìa card
                wave_r = int(p * 140)
                wave_alpha = int((1.0 - p) * 200)
                wave_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                pygame.draw.circle(wave_surf, (255, 255, 255, wave_alpha), (rect.width // 2, rect.height // 2), wave_r, width=5)
                card_surf.blit(wave_surf, (0,0))

                title_txt = self.btn_font.render(info["title"], True, (255, 255, 255))
                card_surf.blit(title_txt, (rect.width//2 - title_txt.get_width()//2, rect.height - 65))

            # Vẽ chữ phụ đề tóm tắt chặng
            sub_txt = self.sub_font.render(info["sub"], True, (0, 255, 255) if self.anim_timer > 60 else (80, 85, 90))
            card_surf.blit(sub_txt, (rect.width//2 - sub_txt.get_width()//2, rect.height - 35))

        else:
            # ================= GIAO DIỆN MỞ KHÓA SÁNG SỦA BÌNH THƯỜNG =================
            pygame.draw.rect(card_surf, (200, 230, 255), (0, 0, rect.width, rect.height - 80), border_top_left_radius=10, border_top_right_radius=10)
            pygame.draw.rect(card_surf, (0, 255, 255), card_surf.get_rect(), width=3, border_radius=10)
            pygame.draw.rect(card_surf, (0, 100, 120), (0, rect.height - 80, rect.width, 80), border_bottom_left_radius=10, border_bottom_right_radius=10)

            title_txt = self.btn_font.render(info["title"], True, (255, 255, 255))
            card_surf.blit(title_txt, (rect.width//2 - title_txt.get_width()//2, rect.height - 65))
            
            sub_txt = self.sub_font.render(info["sub"], True, (0, 255, 255))
            card_surf.blit(sub_txt, (rect.width//2 - sub_txt.get_width()//2, rect.height - 35))

        self.screen.blit(card_surf, (rect.x, rect.y))
        if is_hovered and not locked:
            pygame.draw.rect(self.screen, (0, 255, 255), rect, width=4, border_radius=10)

    def draw(self):
        sw, sh = self.screen.get_width(), self.screen.get_height()

        if self.bg_image:
            if self.bg_image.get_width() != sw or self.bg_image.get_height() != sh:
                self._load_background()
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(config.COLOR_BG)

        dark_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 100))
        self.screen.blit(dark_overlay, (0, 0))

        title = self.title_font.render("CHỌN CHẶNG", True, (255, 255, 255))
        tx = sw // 2 - title.get_width() // 2
        ty = 60
        self.screen.blit(title, (tx, ty))
        
        pygame.draw.line(self.screen, (0, 200, 255), (tx - 150, ty + 25), (tx - 20, ty + 25), 2)
        pygame.draw.line(self.screen, (0, 200, 255), (tx + title.get_width() + 20, ty + 25), (tx + title.get_width() + 150, ty + 25), 2)

        buttons, back_btn = self._get_buttons()
        for btn in buttons:
            self._draw_card(btn["rect"], btn["info"], self.hovered_btn == btn["info"]["id"])

        back_bg = (30, 40, 50, 200) if self.hovered_btn == "back" else (15, 20, 25, 200)
        back_surf = pygame.Surface((back_btn.width, back_btn.height), pygame.SRCALPHA)
        pygame.draw.rect(back_surf, back_bg, back_surf.get_rect(), border_radius=8)
        pygame.draw.rect(back_surf, (100, 150, 200), back_surf.get_rect(), width=1, border_radius=8)
        self.screen.blit(back_surf, (back_btn.x, back_btn.y))
        
        back_txt = self.btn_font.render("<- QUAY LẠI", True, (200, 220, 255))
        self.screen.blit(back_txt, back_txt.get_rect(center=back_btn.center))