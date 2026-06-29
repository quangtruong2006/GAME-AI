# File: stages/stage_select.py
import pygame
import config
import os
import sys
import random
import math

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

        # --- CÁC MỐC THỜI GIAN CHO HOẠT ẢNH MỞ KHÓA (đơn vị: frame) ---
        self.ANIM_SHAKE_END = 25   # 0  -> 25: ổ khóa rung lắc dữ dội
        self.ANIM_BREAK_END = 50   # 25 -> 50: ổ khóa vỡ toang
        self.ANIM_TOTAL     = 95   # 50 -> 95: đốm sáng tròn lan ra mở khóa

        # Data 6 chặng
        self.stages_info = [
            {"id": "stage1", "title": "CHẶNG 1", "sub": "TÌM LẠI DORAEMON"},
            {"id": "stage2", "title": "CHẶNG 2", "sub": "TÍN HIỆU CỦA SHIZUKA"},
            {"id": "stage3", "title": "CHẶNG 3", "sub": "LOGIC TÚI THẦN KỲ"},
            {"id": "stage4", "title": "CHẶNG 4", "sub": "VƯỢT RỪNG THỜI GIAN"},
            {"id": "stage5", "title": "CHẶNG 5", "sub": "GIẢI MÃ CỔNG THÀNH"},
            {"id": "stage6", "title": "CHẶNG 6", "sub": "CHIẾN ĐẤU VÀ GIẢI CỨU"},
        ]
        self.stage_thumbs = {}
        for stage in self.stages_info:
            img_path = os.path.join("assets", "images", f"thumb_{stage['id']}.png")
            if os.path.exists(img_path):
                # Nạp ảnh và scale cho vừa chiều ngang thẻ (180), cao 200
                raw_thumb = pygame.image.load(img_path).convert_alpha()
                self.stage_thumbs[stage["id"]] = pygame.transform.smoothscale(raw_thumb, (180, 200))
            else:
                self.stage_thumbs[stage["id"]] = None

        # --- TẠO SẴN PHIÊN BẢN MỜ (BLUR) CHO ẢNH KHI CÒN KHÓA ---
        # Kỹ thuật: scale ảnh xuống cực nhỏ rồi scale phồng to lại -> mất hết chi tiết, ra hiệu ứng mờ nhòe.
        # Làm 1 lần duy nhất lúc khởi tạo nên không tốn CPU mỗi frame khi vẽ.
        self.stage_thumbs_blurred = {}
        for stage in self.stages_info:
            img = self.stage_thumbs.get(stage["id"])
            if img:
                w, h = img.get_width(), img.get_height()
                tiny_w, tiny_h = max(1, w // 12), max(1, h // 12)
                tiny = pygame.transform.smoothscale(img, (tiny_w, tiny_h))
                self.stage_thumbs_blurred[stage["id"]] = pygame.transform.smoothscale(tiny, (w, h))
            else:
                self.stage_thumbs_blurred[stage["id"]] = None

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
            if self.anim_timer >= self.ANIM_TOTAL: # Chạy xong hết animation thì kết thúc mở khóa chính thức
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

    def _render_unlocked_face(self, rect, info):
        """Dựng sẵn toàn bộ mặt thẻ ở trạng thái ĐÃ MỞ KHÓA (ảnh nét, viền neon, chữ trắng).
        Dùng làm lớp 'lộ' dần qua đốm tròn lan rộng ở giai đoạn cuối animation."""
        face = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(face, (15, 20, 25, 255), face.get_rect(), border_radius=10)

        thumb_img = self.stage_thumbs.get(info["id"])
        if thumb_img:
            temp_thumb = thumb_img.copy()
            temp_thumb.set_alpha(255)
            face.blit(temp_thumb, (0, 0))
        else:
            pygame.draw.rect(face, (200, 230, 255), (0, 0, rect.width, rect.height - 80),
                              border_top_left_radius=10, border_top_right_radius=10)

        pygame.draw.rect(face, (0, 100, 120), (0, rect.height - 80, rect.width, 80),
                          border_bottom_left_radius=10, border_bottom_right_radius=10)
        pygame.draw.rect(face, (0, 255, 255), face.get_rect(), width=3, border_radius=10)

        title_txt = self.btn_font.render(info["title"], True, (255, 255, 255))
        face.blit(title_txt, (rect.width // 2 - title_txt.get_width() // 2, rect.height - 65))
        sub_txt = self.sub_font.render(info["sub"], True, (0, 255, 255))
        face.blit(sub_txt, (rect.width // 2 - sub_txt.get_width() // 2, rect.height - 35))
        return face

    def _draw_card(self, rect, info, is_hovered):
        card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        
        # Một stage được xem là đang khóa nếu nó không ở trong unlocked_stages và không phải đang diễn hoạt
        locked = info["id"] not in self.stage_manager.unlocked_stages
        is_animating = (info["id"] == self.animating_stage)

        # ==========================================
        # LAYER 1: VẼ NỀN TỐI DƯỚI CÙNG
        # ==========================================
        bg_alpha = 220 if (is_hovered and not locked) else 180
        pygame.draw.rect(card_surf, (15, 20, 25, bg_alpha), card_surf.get_rect(), border_radius=10)

        # ==========================================
        # LAYER 2: CHÈN ẢNH THUMBNAIL (Nếu có)
        # ==========================================
        thumb_img = self.stage_thumbs.get(info["id"])
        blurred_img = self.stage_thumbs_blurred.get(info["id"])
        # Khi còn khóa (cả lúc đứng im và lúc đang rung/vỡ) -> LUÔN dùng ảnh MỜ THẬT.
        # Đốm sáng tròn ở giai đoạn cuối animation sẽ tự "lộ" bản ảnh nét đè lên trên.
        display_thumb = blurred_img if (locked and blurred_img) else thumb_img

        if display_thumb:
            temp_thumb = display_thumb.copy()
            if locked:
                temp_thumb.set_alpha(70)   # Khóa: mờ nhòe + tối hẳn, bí ẩn
            elif is_hovered:
                temp_thumb.set_alpha(255)  # Hover: ẢNH SÁNG RỰC
            else:
                temp_thumb.set_alpha(220)  # Bình thường: Hơi dịu

            card_surf.blit(temp_thumb, (0, 0))

        # ==========================================
        # LAYER 3: VẼ CHI TIẾT ĐÈ LÊN TRÊN CÙNG
        # ==========================================
        if locked and not is_animating:
            # --- GIAO DIỆN KHÓA TĨNH (ảnh nền mờ đã vẽ ở Layer 2) ---
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
            # --- KỊCH BẢN PHIM HOẠT ẢNH VỠ KHÓA ---
            cx, cy = rect.width // 2, rect.height // 2 - 30

            if self.anim_timer < self.ANIM_SHAKE_END:
                # ===== GIAI ĐOẠN 1: RUNG LẮC DỮ DỘI TRƯỚC KHI VỠ =====
                # Biên độ rung tăng dần theo thời gian -> cảm giác ổ khóa "chịu áp lực" sắp nổ
                progress = self.anim_timer / self.ANIM_SHAKE_END
                shake_amp = 2 + int(progress * 6)
                ox = random.randint(-shake_amp, shake_amp)
                oy = random.randint(-shake_amp, shake_amp)
                self._draw_lock(card_surf, cx, cy, offset_x=ox, offset_y=oy)

                title_txt = self.btn_font.render(info["title"], True, (100, 105, 110))
                card_surf.blit(title_txt, (rect.width//2 - title_txt.get_width()//2, rect.height//2 + 30))
                words = info["sub"].split(" ")
                line1 = " ".join(words[:len(words)//2 + 1])
                line2 = " ".join(words[len(words)//2 + 1:])
                sub1 = self.sub_font.render(line1, True, (80, 85, 90))
                sub2 = self.sub_font.render(line2, True, (80, 85, 90))
                card_surf.blit(sub1, (rect.width//2 - sub1.get_width()//2, rect.height//2 + 65))
                card_surf.blit(sub2, (rect.width//2 - sub2.get_width()//2, rect.height//2 + 85))

            elif self.anim_timer < self.ANIM_BREAK_END:
                # ===== GIAI ĐOẠN 2: Ổ KHÓA VỠ TOANG =====
                p = (self.anim_timer - self.ANIM_SHAKE_END) / (self.ANIM_BREAK_END - self.ANIM_SHAKE_END)
                alpha = int((1.0 - p) * 255)
                ox = random.randint(-2, 2)
                oy = random.randint(-2, 2)
                self._draw_lock(card_surf, cx, cy, offset_x=ox, offset_y=oy, alpha=alpha, split_progress=p)

                if self.anim_timer % 3 < 2:
                    pygame.draw.line(card_surf, (255, 215, 0), (cx - 15, cy - 10), (cx + 15, cy + 20), 2)
                    pygame.draw.line(card_surf, (255, 69, 0), (cx + 10, cy - 15), (cx - 12, cy + 15), 2)

                title_txt = self.btn_font.render(info["title"], True, (100, 105, 110))
                card_surf.blit(title_txt, (rect.width//2 - title_txt.get_width()//2, rect.height//2 + 30))
                words = info["sub"].split(" ")
                line1 = " ".join(words[:len(words)//2 + 1])
                line2 = " ".join(words[len(words)//2 + 1:])
                sub1 = self.sub_font.render(line1, True, (80, 85, 90))
                sub2 = self.sub_font.render(line2, True, (80, 85, 90))
                card_surf.blit(sub1, (rect.width//2 - sub1.get_width()//2, rect.height//2 + 65))
                card_surf.blit(sub2, (rect.width//2 - sub2.get_width()//2, rect.height//2 + 85))

            else:
                # ===== GIAI ĐOẠN 3: MỘT ĐỐM SÁNG TRÒN Ở GIỮA THẺ LAN RỘNG RA -> MỞ KHÓA =====
                p = (self.anim_timer - self.ANIM_BREAK_END) / (self.ANIM_TOTAL - self.ANIM_BREAK_END)
                p = max(0.0, min(1.0, p))
                ease = p * p * (3 - 2 * p)  # smoothstep cho đốm lan mượt, không giật cục

                max_radius = math.hypot(rect.width / 2, rect.height / 2) + 10
                radius = max(1, int(ease * max_radius))

                # Dựng mặt thẻ đã mở khóa (ảnh nét, viền neon, chữ trắng)
                unlocked_face = self._render_unlocked_face(rect, info)

                # Đục một "lỗ tròn" bằng mask alpha -> chỉ phần nằm trong vòng tròn được lộ ra
                mask = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                pygame.draw.circle(mask, (255, 255, 255, 255), (rect.width // 2, rect.height // 2), radius)
                unlocked_face.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                card_surf.blit(unlocked_face, (0, 0))

                # Viền sáng (ripple) chạy theo rìa đốm tròn đang lan, mờ dần khi đốm phình to hết thẻ
                ring_alpha = int((1.0 - ease) * 255)
                if ring_alpha > 10:
                    ring_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                    pygame.draw.circle(ring_surf, (255, 255, 255, ring_alpha),
                                        (rect.width // 2, rect.height // 2), radius, width=4)
                    card_surf.blit(ring_surf, (0, 0))

        else:
            # --- GIAO DIỆN MỞ KHÓA BÌNH THƯỜNG ---
            # Nếu KHÔNG có ảnh thì mới vẽ khối màu nền xanh dương để chữa cháy
            if not thumb_img:
                pygame.draw.rect(card_surf, (200, 230, 255), (0, 0, rect.width, rect.height - 80), border_top_left_radius=10, border_top_right_radius=10)
            
            # Luôn vẽ thanh menu chứa text ở dưới cùng
            pygame.draw.rect(card_surf, (0, 100, 120), (0, rect.height - 80, rect.width, 80), border_bottom_left_radius=10, border_bottom_right_radius=10)
            pygame.draw.rect(card_surf, (0, 255, 255), card_surf.get_rect(), width=3, border_radius=10)

            title_txt = self.btn_font.render(info["title"], True, (255, 255, 255))
            card_surf.blit(title_txt, (rect.width//2 - title_txt.get_width()//2, rect.height - 65))
            
            sub_txt = self.sub_font.render(info["sub"], True, (0, 255, 255))
            card_surf.blit(sub_txt, (rect.width//2 - sub_txt.get_width()//2, rect.height - 35))

        self.screen.blit(card_surf, (rect.x, rect.y))
        
        # Viền neon khi hover
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