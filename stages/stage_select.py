# File: stages/stage_select.py
import pygame
import config
import os
import sys

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

        # Data 6 chặng (Khóa từ chặng 2 trở đi)
        self.stages_info = [
            {"id": "stage1", "title": "CHẶNG 1", "sub": "ĐÁNH THỨC KÝ ỨC", "locked": False},
            {"id": "stage2", "title": "CHẶNG 2", "sub": "TRUY TÌM DẤU VẾT SHIZUKA", "locked": True},
            {"id": "stage3", "title": "CHẶNG 3", "sub": "KHÔI PHỤC KHO BẢO BỐI", "locked": True},
            {"id": "stage4", "title": "CHẶNG 4", "sub": "VƯỢT RỪNG THỜI GIAN", "locked": True},
            {"id": "stage5", "title": "CHẶNG 5", "sub": "PHÁ HỆ THỐNG PHONG ẤN", "locked": True},
            {"id": "stage6", "title": "CHẶNG 6", "sub": "GIẢI CỨU SHIZUKA", "locked": True},
        ]

    def _load_background(self):
        
        bg_path = os.path.join("assets", "images", "select_bg.png")
        if os.path.exists(bg_path):
            try:
                raw = pygame.image.load(bg_path).convert()
                self.bg_image = pygame.transform.smoothscale(
                    raw, (self.screen.get_width(), self.screen.get_height())
                )
            except:
                pass

    def _get_buttons(self):
        sw = self.screen.get_width()
        sh = self.screen.get_height()
        buttons = []

        # Kích thước 1 thẻ
        card_w, card_h = 180, 280
        gap = 25
        
        # Căn giữa 6 thẻ trên 1 hàng ngang
        total_width = (card_w * 6) + (gap * 5)
        start_x = sw // 2 - total_width // 2
        start_y = sh // 2 - card_h // 2 + 20

        for i, stage in enumerate(self.stages_info):
            x = start_x + i * (card_w + gap)
            y = start_y
            rect = pygame.Rect(x, y, card_w, card_h)
            buttons.append({"rect": rect, "info": stage})

        # Nút Quay Lại (Góc dưới trái y như mẫu)
        back_btn = pygame.Rect(30, sh - 70, 150, 40)
        
        return buttons, back_btn

    def handle_events(self, events):
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
                # Click chặng
                for btn in buttons:
                    if btn["rect"].collidepoint(event.pos):
                        # Kiểm tra xem ID của chặng có nằm trong danh sách đã mở khóa chưa
                        if btn["info"]["id"] in self.stage_manager.unlocked_stages:
                            self.stage_manager.change_stage(btn["info"]["id"])

                # Click Back
                if back_btn.collidepoint(event.pos):
                    self.stage_manager.change_stage("menu")

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.stage_manager.change_stage("menu")

    def update(self):
        pass

    def _draw_lock(self, surface, center_x, center_y):
        # Vẽ thân ổ khóa
        pygame.draw.rect(surface, (120, 125, 130), (center_x - 18, center_y - 5, 36, 26), border_radius=4)
        # Vẽ quai ổ khóa (vòng cung)
        pygame.draw.arc(surface, (120, 125, 130), (center_x - 12, center_y - 20, 24, 24), 0, 3.14159, 4)
        # Vẽ lỗ khóa
        pygame.draw.circle(surface, (40, 45, 50), (center_x, center_y + 8), 4)
        pygame.draw.rect(surface, (40, 45, 50), (center_x - 2, center_y + 8, 4, 8))

    def _draw_card(self, rect, info, is_hovered):
        # Tạo Surface trong suốt cho thẻ
        card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        #Tự động check trạng thái khóa dựa vào StageManager
        locked = info["id"] not in self.stage_manager.unlocked_stages
        
        # Nền thẻ (đen mờ)
        bg_alpha = 220 if (is_hovered and not locked) else 180
        pygame.draw.rect(card_surf, (15, 20, 25, bg_alpha), card_surf.get_rect(), border_radius=10)

        if locked:
            # === GIAO DIỆN KHÓA ===
            # Vẽ ổ khóa ở giữa (nửa trên)
            self._draw_lock(card_surf, rect.width // 2, rect.height // 2 - 30)
            
            # Chữ mờ
            title_txt = self.btn_font.render(info["title"], True, (100, 105, 110))
            sub_txt = self.sub_font.render(info["sub"], True, (80, 85, 90))
            
            card_surf.blit(title_txt, (rect.width//2 - title_txt.get_width()//2, rect.height//2 + 30))
            
            # Tự động chia dòng chữ phụ nếu dài
            words = info["sub"].split(" ")
            line1 = " ".join(words[:len(words)//2 + 1])
            line2 = " ".join(words[len(words)//2 + 1:])
            
            sub1 = self.sub_font.render(line1, True, (80, 85, 90))
            sub2 = self.sub_font.render(line2, True, (80, 85, 90))
            card_surf.blit(sub1, (rect.width//2 - sub1.get_width()//2, rect.height//2 + 65))
            card_surf.blit(sub2, (rect.width//2 - sub2.get_width()//2, rect.height//2 + 85))

        else:
            # === GIAO DIỆN MỞ KHÓA ===
            # Giả lập khu vực ảnh thumbnail ở nửa trên (Màu xám sáng/xanh dương)
            pygame.draw.rect(card_surf, (200, 230, 255), (0, 0, rect.width, rect.height - 80), border_top_left_radius=10, border_top_right_radius=10)
            
            # Viền Cyan phát sáng
            pygame.draw.rect(card_surf, (0, 255, 255), card_surf.get_rect(), width=3, border_radius=10)
            
            # Khối màu Cyan phía dưới để chứa chữ (Giống viền của mẫu)
            pygame.draw.rect(card_surf, (0, 100, 120), (0, rect.height - 80, rect.width, 80), border_bottom_left_radius=10, border_bottom_right_radius=10)

            # Chữ sáng
            title_txt = self.btn_font.render(info["title"], True, (255, 255, 255))
            card_surf.blit(title_txt, (rect.width//2 - title_txt.get_width()//2, rect.height - 65))
            
            sub_txt = self.sub_font.render(info["sub"], True, (0, 255, 255))
            card_surf.blit(sub_txt, (rect.width//2 - sub_txt.get_width()//2, rect.height - 35))

        # In thẻ lên màn hình chính
        self.screen.blit(card_surf, (rect.x, rect.y))
        
        # Glow effect nếu hover vào thẻ đang mở
        if is_hovered and not locked:
            pygame.draw.rect(self.screen, (0, 255, 255), rect, width=4, border_radius=10)

    def draw(self):
        sw, sh = self.screen.get_width(), self.screen.get_height()

        # 1. Background
        if self.bg_image:
            if self.bg_image.get_width() != sw or self.bg_image.get_height() != sh:
                self._load_background()
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(config.COLOR_BG)

        # Làm tối nhẹ background để nổi bật UI
        dark_overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 100))
        self.screen.blit(dark_overlay, (0, 0))

        # 2. Tiêu đề "CHỌN CHẶNG" ở giữa có gạch ngang
        title = self.title_font.render("CHỌN CHẶNG", True, (255, 255, 255))
        tx = sw // 2 - title.get_width() // 2
        ty = 60
        self.screen.blit(title, (tx, ty))
        
        # Vẽ 2 đường line 2 bên chữ giống hệt ảnh mẫu
        pygame.draw.line(self.screen, (0, 200, 255), (tx - 150, ty + 25), (tx - 20, ty + 25), 2)
        pygame.draw.line(self.screen, (0, 200, 255), (tx + title.get_width() + 20, ty + 25), (tx + title.get_width() + 150, ty + 25), 2)

        # 3. Các thẻ chặng
        buttons, back_btn = self._get_buttons()
        for btn in buttons:
            self._draw_card(btn["rect"], btn["info"], self.hovered_btn == btn["info"]["id"])

        # 4. Nút Back (<- QUAY LẠI) ở góc dưới trái
        back_bg = (30, 40, 50, 200) if self.hovered_btn == "back" else (15, 20, 25, 200)
        back_surf = pygame.Surface((back_btn.width, back_btn.height), pygame.SRCALPHA)
        pygame.draw.rect(back_surf, back_bg, back_surf.get_rect(), border_radius=8)
        pygame.draw.rect(back_surf, (100, 150, 200), back_surf.get_rect(), width=1, border_radius=8)
        self.screen.blit(back_surf, (back_btn.x, back_btn.y))
        
        back_txt = self.btn_font.render("<- QUAY LẠI", True, (200, 220, 255))
        self.screen.blit(back_txt, back_txt.get_rect(center=back_btn.center))