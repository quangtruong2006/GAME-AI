# File: stages/stage5_seal.py
import pygame
import math
import os
import json
import random
import config

try:
    from algorithms.csp.pure_backtracking import solve_pure_backtracking
    from algorithms.csp.forward_checking import solve_backtracking_fc
    from algorithms.csp.min_conflicts import solve_min_conflicts
except ImportError as e:
    print(f"[CẢNH BÁO] Chưa tìm thấy file thuật toán: {e}")

class Stage5Seal:
    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager
        self.sw, self.sh = screen.get_width(), screen.get_height()
        
        try:
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 20)
            self.font = pygame.font.Font("assets/fonts/minecraft.ttf", 14)
        except:
            self.title_font = pygame.font.SysFont("Arial", 20, bold=True)
            self.font = pygame.font.SysFont("Arial", 14, bold=True)
            
        self.panel_w = 320 # Nới rộng panel một chút để chứa các nút to như trong ảnh
        self.bg_image = None
        self._load_background()
        
        # --- TÍNH TOÁN KÍCH THƯỚC LƯỚI FULL MÀN HÌNH ---
        self.start_y = 60   # Nhích lưới lên cao một chút cho đỡ trống
        self.cols = 15      # Tăng gần gấp đôi số cột
        self.rows = 9       # Tăng số hàng để tràn xuống dưới
        
        # Thu hẹp lề (padding) lại còn 40 để lưới bung ra hết cỡ
        max_w = (self.sw - self.panel_w - 40) // self.cols
        max_h = (self.sh - self.start_y - 40) // self.rows
        
        self.cell_size = min(max_w, max_h)
        self.grid_w = self.cols * self.cell_size
        self.grid_h = self.rows * self.cell_size
        self.start_x = self.panel_w + (self.sw - self.panel_w - self.grid_w) // 2

        self._load_assets()
        self.grid = self._create_initial_grid()
        self.map_file = os.path.join("assets", "maps", "stage5_map.json")
        self.load_map()

        self.selected_algorithm = "Pure BT"
        self.phase = "idle" 
        self.solver_generator = None
        self.last_step_time = 0
        self.step_delay = 200 
        self.steps_count = 0
        self.is_editing = False
        self.edit_mode = "add_obs"

        # --- ĐỒNG BỘ UI VỚI CHẶNG 1: slider tốc độ + đo thời gian chạy ---
        self.speed_min = 0      # delay thấp nhất (chạy nhanh nhất)
        self.speed_max = 500    # delay cao nhất (chạy chậm nhất)
        self.dragging_speed = False
        self.run_start_time = 0
        self.run_elapsed_ms = 0

    def _load_background(self):
        bg_path = os.path.join("assets", "images", "stage5_bg.png")
        if os.path.exists(bg_path):
            try:
                raw = pygame.image.load(bg_path).convert()
                self.bg_image = pygame.transform.smoothscale(raw, (self.sw - self.panel_w, self.sh))
            except: pass
    def _load_assets(self):
        """Hàm tự động tải và scale ảnh PNG cho vừa khít ô lưới ổ khóa"""
        self.item_images = {}
        # Quy ước file ảnh: 1 (gương /), 2 (gương \), 3 (đá), 8 (súng), 9 (lõi đích)
        files = {
            1: "mirror1.png",
            2: "mirror2.png", 
            3: "block.png", 
            8: "source.png", 
            9: "core.png"
        }
        for val, filename in files.items():
            path = os.path.join("assets", "images", filename)
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    # Thu phóng ảnh vừa đúng bằng kích thước ô lưới
                    self.item_images[val] = pygame.transform.smoothscale(img, (self.cell_size, self.cell_size))
                except Exception as e:
                    print(f"[CẢNH BÁO] Lỗi load ảnh {filename}: {e}")
                    self.item_images[val] = None
            else:
                self.item_images[val] = None
    def _create_initial_grid(self):
        grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        grid[1][1] = 8    # Súng Laser ở góc Trái-Trên
        grid[7][13] = 9   # Lõi Đích ở góc Phải-Dưới
        # Rải vài cục đá chặn đường giữa
        grid[4][7] = grid[5][8] = grid[3][10] = grid[6][4] = 3 
        return grid
        
    def _generate_random_map(self):
        """Hàm cho nút Vàng: Random rải đá khắp bản đồ"""
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] not in [8, 9]: # Trừ súng và đích
                    self.grid[r][c] = 3 if random.random() < 0.2 else 0

    def load_map(self):
        if os.path.exists(self.map_file):
            try:
                with open(self.map_file, "r") as f:
                    saved_grid = json.load(f)["grid"]
                    # Chỉ load map nếu kích thước file save khớp với kích thước lưới hiện tại
                    if len(saved_grid) == self.rows and len(saved_grid[0]) == self.cols:
                        self.grid = saved_grid
                    else:
                        print("[INFO] Kích thước Map cũ không khớp (8x6 vs 15x9). Dùng Map mặc định mới!")
            except: pass

    def save_map(self):
        if not os.path.exists(os.path.dirname(self.map_file)): os.makedirs(os.path.dirname(self.map_file))
        with open(self.map_file, "w") as f: json.dump({"grid": self.grid}, f)

    def _get_ui_rects(self):
        ui = {}
        cx = self.panel_w // 2
        btn_w = 260
        
        # --- BỐ CỤC UI CHUẨN XỊN 100% NHƯ ẢNH ÔNG GỬI ---
        ui["btn_pure_bt"] = pygame.Rect(cx - btn_w//2, 60, btn_w, 35)
        ui["btn_fc"] = pygame.Rect(cx - btn_w//2, 105, btn_w, 35)
        ui["btn_min_conf"] = pygame.Rect(cx - btn_w//2, 150, btn_w, 35)
        
        ui["btn_run"] = pygame.Rect(cx - btn_w//2, 200, btn_w, 40)
        ui["btn_cancel"] = pygame.Rect(cx - btn_w//2, 250, btn_w, 40)
        ui["btn_reset"] = pygame.Rect(cx - btn_w//2, 300, btn_w, 40)
        ui["btn_random_map"] = pygame.Rect(cx - btn_w//2, 350, btn_w, 35) # Nút Vàng
        
        ui["btn_edit_toggle"] = pygame.Rect(cx - btn_w//2, 395, btn_w, 35)
        
        # Chức năng Edit (Chỉ hiện khi toggle)
        ui["btn_add_obs"] = pygame.Rect(cx - btn_w//2, 440, btn_w//2 - 5, 30)
        ui["btn_erase"] = pygame.Rect(cx + 5, 440, btn_w//2 - 5, 30)
        ui["btn_set_src"] = pygame.Rect(cx - btn_w//2, 480, btn_w//2 - 5, 30)
        ui["btn_set_goal"] = pygame.Rect(cx + 5, 480, btn_w//2 - 5, 30)
        ui["btn_save_map"] = pygame.Rect(cx - btn_w//2, 520, btn_w, 35)

        # --- SLIDER TỐC ĐỘ (đồng bộ kiểu "Search speed" của chặng 1) ---
        speed_track_y = self.sh - 195
        ui["speed_slider"] = pygame.Rect(cx - btn_w//2, speed_track_y - 3, btn_w, 6)

        ui["btn_back"] = pygame.Rect(cx - btn_w//2, self.sh - 60, btn_w, 40)
        return ui

    # -------------------------
    # SLIDER TỐC ĐỘ: helper chuyển đổi giá trị <-> vị trí con trượt
    # -------------------------
    def _speed_to_handle_x(self, track_rect):
        span = self.speed_max - self.speed_min
        t = 1.0 - (self.step_delay - self.speed_min) / span if span else 0
        t = max(0.0, min(1.0, t))
        return track_rect.x + int(t * track_rect.width)

    def _handle_x_to_speed(self, x, track_rect):
        t = (x - track_rect.x) / track_rect.width if track_rect.width else 0
        t = max(0.0, min(1.0, t))
        delay = self.speed_max - t * (self.speed_max - self.speed_min)
        return int(round(delay / 10.0) * 10)

    def handle_events(self, events):
        ui = self._get_ui_rects()
        pos = pygame.mouse.get_pos()
        slider_hit_rect = ui["speed_slider"].inflate(0, 24)  # vùng bắt chuột rộng hơn cho dễ kéo

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.phase == "completed":
                    pw, ph = 420, 220
                    px, py = (self.sw - pw)//2, (self.sh - ph)//2
                    if pygame.Rect(px + 25, py + 140, 110, 40).collidepoint(pos): self.stage_manager.change_stage("stage_select")
                    elif pygame.Rect(px + 155, py + 140, 110, 40).collidepoint(pos): self.phase, self.steps_count = "idle", 0
                    elif pygame.Rect(px + 285, py + 140, 110, 40).collidepoint(pos):
                        self.stage_manager.trigger_unlock_effect = "stage6"
                        self.stage_manager.change_stage("stage_select")
                    return

                if ui["btn_pure_bt"].collidepoint(pos): self.selected_algorithm = "Pure BT"
                elif ui["btn_fc"].collidepoint(pos): self.selected_algorithm = "Forward Checking"
                elif ui["btn_min_conf"].collidepoint(pos): self.selected_algorithm = "Min-Conflicts"
                elif slider_hit_rect.collidepoint(pos):
                    self.dragging_speed = True
                    self.step_delay = self._handle_x_to_speed(pos[0], ui["speed_slider"])
                elif ui["btn_run"].collidepoint(pos) and self.phase == "idle":
                    sr, sc = -1, -1
                    for r in range(self.rows):
                        for c in range(self.cols):
                            if self.grid[r][c] == 8: sr, sc = r, c
                            
                    if sr != -1:
                        self.phase = "running"
                        self.steps_count = 0
                        self.run_start_time = pygame.time.get_ticks()
                        self.run_elapsed_ms = 0
                        try:
                            if self.selected_algorithm == "Pure BT":
                                self.solver_generator = solve_pure_backtracking(self.grid, self.rows, self.cols, sr, sc)
                            elif self.selected_algorithm == "Forward Checking":
                                self.solver_generator = solve_backtracking_fc(self.grid, self.rows, self.cols, sr, sc)
                            elif self.selected_algorithm == "Min-Conflicts":
                                self.solver_generator = solve_min_conflicts(self.grid, self.rows, self.cols, sr, sc)
                        except Exception as e: print(f"[LỖI THUẬT TOÁN] {e}")

                elif ui["btn_cancel"].collidepoint(pos) or ui["btn_reset"].collidepoint(pos):
                    self.phase = "idle"
                    self.solver_generator = None
                    
                    # 1. Dọn dẹp sạch sẽ mọi tấm gương (mã 1, 2) do AI đặt trên bản đồ
                    for r in range(self.rows):
                        for c in range(self.cols):
                            if self.grid[r][c] in [1, 2]:
                                self.grid[r][c] = 0
                                
                    # 2. Sau đó mới load lại bản đồ gốc từ file (nếu có)
                    self.load_map()
                    
                elif ui["btn_random_map"].collidepoint(pos) and self.phase == "idle":
                    self._generate_random_map()

                elif ui["btn_back"].collidepoint(pos): self.stage_manager.change_stage("stage_select")
                
                elif ui["btn_edit_toggle"].collidepoint(pos): self.is_editing = not self.is_editing
                elif self.is_editing:
                    if ui["btn_add_obs"].collidepoint(pos): self.edit_mode = "add_obs"
                    elif ui["btn_erase"].collidepoint(pos): self.edit_mode = "erase"
                    elif ui["btn_set_src"].collidepoint(pos): self.edit_mode = "set_source"
                    elif ui["btn_set_goal"].collidepoint(pos): self.edit_mode = "set_goal"
                    elif ui["btn_save_map"].collidepoint(pos): 
                        self.save_map()
                        self.phase = "đã lưu map!"

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging_speed = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                # Bấm mũi tên LÊN -> Giảm delay -> Chạy NHANH HƠN
                    self.step_delay = max(self.speed_min, self.step_delay - 50)
                    print(f"[INFO] Tốc độ hiện tại: {self.step_delay}ms / bước")
                
                elif event.key == pygame.K_DOWN:
                # Bấm mũi tên XUỐNG -> Tăng delay -> Chạy CHẬM LẠI
                    self.step_delay = min(self.speed_max, self.step_delay + 50)
                    print(f"[INFO] Tốc độ hiện tại: {self.step_delay}ms / bước")

        # --- Các trạng thái "đang giữ chuột" cần kiểm tra MỖI FRAME,
        #     không phụ thuộc việc frame đó có phát sinh event rời rạc
        #     hay không (vd: giữ chuột đứng yên vẫn phải tiếp tục kéo) ---
        if self.dragging_speed and pygame.mouse.get_pressed()[0]:
            self.step_delay = self._handle_x_to_speed(pos[0], ui["speed_slider"])

        if self.is_editing and pygame.mouse.get_pressed()[0] and pos[0] > self.panel_w:
            c, r = (pos[0] - self.start_x) // self.cell_size, (pos[1] - self.start_y) // self.cell_size
            if 0 <= r < self.rows and 0 <= c < self.cols:
                if self.edit_mode == "add_obs": self.grid[r][c] = 3
                elif self.edit_mode == "erase": self.grid[r][c] = 0
                elif self.edit_mode == "set_source": self.grid[r][c] = 8
                elif self.edit_mode == "set_goal": self.grid[r][c] = 9

    def update(self):
        if self.phase == "running":
            self.run_elapsed_ms = pygame.time.get_ticks() - self.run_start_time

        if self.phase == "running" and self.solver_generator:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_step_time > self.step_delay:
                try:
                    res = next(self.solver_generator)
                    self.last_step_time = current_time
                    if res == "update": self.steps_count += 1
                    elif res is True: self.phase = "completed"
                    elif res is False: self.phase = "failed"
                except StopIteration: pass
                except Exception as e:
                    print(f"[LỖI CẬP NHẬT UI] {e}")
                    self.phase = "failed"

    def _calculate_laser_path(self):
        pts, sr, sc = [], -1, -1
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == 8: sr, sc = r, c
        if sr == -1: return pts

        r, c, dr, dc = sr, sc, 0, 1
        visited = set()
        while 0 <= r < self.rows and 0 <= c < self.cols:
            if (r, c, dr, dc) in visited: break
            visited.add((r, c, dr, dc))
            pts.append((self.start_x + c * self.cell_size + self.cell_size // 2, self.start_y + r * self.cell_size + self.cell_size // 2))
            val = self.grid[r][c]
            if val in (3, 9): break
            if val == 1: dr, dc = -dc, -dr
            elif val == 2: dr, dc = dc, dr
            r, c = r + dr, c + dc
        return pts

    def _draw_btn(self, rect, text, bg_color, is_active=False):
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=6)
        border_color = (255, 255, 255) if is_active else (100, 110, 120)
        pygame.draw.rect(self.screen, border_color, rect, width=2 if is_active else 1, border_radius=6)
        txt = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(txt, txt.get_rect(center=rect.center))

    def _draw_speed_slider(self, track_rect):
        """Slider kéo tốc độ AI - đồng bộ phong cách 'Search speed' của chặng 1"""
        label = self.font.render(f"AI Speed: {self.step_delay}ms / bước", True, (200, 200, 200))
        self.screen.blit(label, (track_rect.x, track_rect.y - 22))

        # rãnh trượt
        pygame.draw.rect(self.screen, (40, 45, 60), track_rect, border_radius=3)

        handle_x = self._speed_to_handle_x(track_rect)
        filled = pygame.Rect(track_rect.x, track_rect.y, max(0, handle_x - track_rect.x), track_rect.height)
        pygame.draw.rect(self.screen, (0, 160, 255), filled, border_radius=3)

        pygame.draw.circle(self.screen, (255, 255, 255), (handle_x, track_rect.centery), 9)
        pygame.draw.circle(self.screen, (0, 220, 255), (handle_x, track_rect.centery), 9, width=2)

    def _draw_circuit_decoration(self, rect):
        """Hoa văn mạch điện trang trí lấp khoảng trống panel - đồng bộ cảm giác với chặng 1"""
        if rect.height < 40 or rect.width < 40:
            return
        line_color = (35, 85, 105)
        dot_color = (60, 150, 170)
        cx = rect.centerx
        top_y = rect.y + 12
        bottom_y = rect.bottom - 12

        # đường trục dọc chính
        pygame.draw.line(self.screen, line_color, (cx, top_y), (cx, bottom_y), 1)
        pygame.draw.circle(self.screen, dot_color, (cx, top_y), 3, width=1)
        pygame.draw.circle(self.screen, dot_color, (cx, bottom_y), 3, width=1)

        branches = [0.18, 0.42, 0.66, 0.88]
        lengths = [50, 35, 60, 30]
        for i, f in enumerate(branches):
            y = top_y + int(f * (bottom_y - top_y))
            direction = -1 if i % 2 == 0 else 1
            end_x = cx + direction * lengths[i]
            pygame.draw.line(self.screen, line_color, (cx, y), (end_x, y), 1)
            pygame.draw.circle(self.screen, dot_color, (end_x, y), 3, width=1)
            pygame.draw.circle(self.screen, dot_color, (cx, y), 2)

    def _draw_laser_glow(self, pts):
        """Vẽ tia laser đa tầng tạo hiệu ứng Bloom phát sáng rực rỡ"""
        if len(pts) < 2: return
        
        # 1. Tầng ngoài cùng: Vầng sáng (Glow) mờ ảo
        # Tạo một Surface trong suốt để vẽ hiệu ứng lóa sáng
        glow_surf = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        pygame.draw.lines(glow_surf, (255, 0, 0, 40), False, pts, width=15)
        pygame.draw.lines(glow_surf, (255, 0, 0, 70), False, pts, width=8)
        self.screen.blit(glow_surf, (0, 0))
        
        # 2. Tầng giữa: Tia laser năng lượng đỏ rực
        pygame.draw.lines(self.screen, (255, 50, 50), False, pts, width=4)
        
        # 3. Tầng lõi: Sợi dây năng lượng trắng (Core) tạo cảm giác cực nóng
        pygame.draw.lines(self.screen, (255, 200, 200), False, pts, width=1)
    def draw(self):
        # --- 1. NỀN KHÔNG GIAN SÂU (DEEP SPACE) ---
        self.screen.fill((5, 8, 15)) # Tím đen cực sâu
        
        # Nếu có ảnh nền thì blit đè lên nhưng cho mờ mờ thôi
        if self.bg_image:
            self.bg_image.set_alpha(100)
            self.screen.blit(self.bg_image, (self.panel_w, 0))

        # --- 2. VẼ LƯỚI MA TRẬN NĂNG LƯỢNG VÀ ẢNH BẢO BỐI ---
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = self.start_x + c * self.cell_size, self.start_y + r * self.cell_size
                rect = pygame.Rect(x, y, self.cell_size, self.cell_size)
                
                # Vẽ ô lưới mờ ảo của ổ khóa
                if self.is_editing:
                    pygame.draw.rect(self.screen, (0, 100, 200, 50), rect, 1)
                
                val = self.grid[r][c]
                cx, cy = x + self.cell_size//2, y + self.cell_size//2
                
                if val != 0:
                    # NẾU CÓ ẢNH PNG -> DÁN ẢNH LÊN Ô LƯỚI
                    if hasattr(self, 'item_images') and self.item_images.get(val):
                        self.screen.blit(self.item_images[val], (x, y))
                    
                    # NẾU KHÔNG CÓ ẢNH -> DÙNG LẠI ĐỒ HỌA NEON DỰ PHÒNG
                    else:
                        if val == 3: # Vật cản đá
                            inner = rect.inflate(-15, -15)
                            pygame.draw.rect(self.screen, (30, 35, 50), inner, border_radius=8)
                            pygame.draw.rect(self.screen, (0, 255, 255), inner, width=2, border_radius=8)
                        elif val == 8: # Súng Laser 
                            rad = int(math.sin(pygame.time.get_ticks() * 0.01) * 5) + 20
                            pygame.draw.circle(self.screen, (255, 0, 0, 100), (cx, cy), rad + 10, 2)
                            pygame.draw.circle(self.screen, (255, 50, 50), (cx, cy), 18)
                            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), 8)
                        elif val == 9: # Lõi Đích
                            time_val = pygame.time.get_ticks() * 0.005
                            for i in range(3):
                                s_rad = (time_val + i) % 3 * 15
                                s_alpha = max(0, 150 - s_rad * 3)
                                s = pygame.Surface((100, 100), pygame.SRCALPHA)
                                pygame.draw.circle(s, (0, 255, 200, s_alpha), (50, 50), s_rad, 2)
                                self.screen.blit(s, (cx - 50, cy - 50))
                            pygame.draw.rect(self.screen, (0, 255, 255), (cx-15, cy-15, 30, 30), border_radius=4)
                        elif val == 1: # Gương /
                            pygame.draw.line(self.screen, (0, 200, 255), (x+15, y+self.cell_size-15), (x+self.cell_size-15, y+15), 6)
                        elif val == 2: # Gương \
                            pygame.draw.line(self.screen, (0, 200, 255), (x+15, y+15), (x+self.cell_size-15, y+self.cell_size-15), 6)

        # --- 3. VẼ TIA LASER ĐẲNG CẤP ---
        laser_pts = self._calculate_laser_path()
        self._draw_laser_glow(laser_pts)
        for r in range(self.rows):
            for c in range(self.cols):
                val = self.grid[r][c]
                # Chỉ lấy súng (8) và đích (9) vẽ đè lên để che gốc tia laser
                if val in [8, 9]:
                    x, y = self.start_x + c * self.cell_size, self.start_y + r * self.cell_size
                    if hasattr(self, 'item_images') and self.item_images.get(val):
                        self.screen.blit(self.item_images[val], (x, y))
        # --- 4. THANH UI BÊN TRÁI (DARK MODE CAO CẤP) ---
        pygame.draw.rect(self.screen, (10, 12, 18), (0, 0, self.panel_w, self.sh))
        pygame.draw.line(self.screen, (0, 255, 255), (self.panel_w, 0), (self.panel_w, self.sh), 2)
        
        # Tiêu đề với hiệu ứng đổ bóng chìm
        title_surf = self.title_font.render("CSP NEURAL LINK", True, (0, 255, 255))
        self.screen.blit(title_surf, (20, 25))
        
        # Cập nhật lại các nút bấm với màu sắc Cyberpunk
        ui = self._get_ui_rects()
        c_neon_blue = (0, 160, 255)
        c_neon_green = (50, 255, 120)
        c_neon_red = (255, 50, 80)
        c_neon_purple = (180, 50, 255)
        c_neon_yellow = (255, 200, 0)
        c_dark = (25, 30, 45)

        self._draw_btn(ui["btn_pure_bt"], "PURE BACKTRACKING", c_neon_blue if self.selected_algorithm == "Pure BT" else c_dark, self.selected_algorithm == "Pure BT")
        self._draw_btn(ui["btn_fc"], "FORWARD CHECKING", c_neon_blue if self.selected_algorithm == "Forward Checking" else c_dark, self.selected_algorithm == "Forward Checking")
        self._draw_btn(ui["btn_min_conf"], "MIN-CONFLICTS", c_neon_blue if self.selected_algorithm == "Min-Conflicts" else c_dark, self.selected_algorithm == "Min-Conflicts")
        
        self._draw_btn(ui["btn_run"], "RUN AI", c_neon_green)
        self._draw_btn(ui["btn_cancel"], "CANCEL RUN", c_neon_red)
        self._draw_btn(ui["btn_reset"], "RESET PATH", c_neon_purple)
        self._draw_btn(ui["btn_random_map"], "RANDOMIZE GRID", c_neon_yellow)

        toggle_txt = "EDIT MAP [-]" if self.is_editing else "EDIT MAP [+]"
        self._draw_btn(ui["btn_edit_toggle"], toggle_txt, (55, 65, 75))
        
        if self.is_editing:
            c_active = (0, 160, 255)  # Màu Neon Blue khi đang chọn
            c_idle = (25, 30, 45)     # Màu tối khi không chọn

            self._draw_btn(ui["btn_add_obs"], "Đá Cản", c_active if self.edit_mode=="add_obs" else c_idle, self.edit_mode=="add_obs")
            self._draw_btn(ui["btn_erase"], "Tẩy", c_active if self.edit_mode=="erase" else c_idle, self.edit_mode=="erase")
            self._draw_btn(ui["btn_set_src"], "Súng Laze", c_active if self.edit_mode=="set_source" else c_idle, self.edit_mode=="set_source")
            self._draw_btn(ui["btn_set_goal"], "Đích", c_active if self.edit_mode=="set_goal" else c_idle, self.edit_mode=="set_goal")
            self._draw_btn(ui["btn_save_map"], "LƯU MAP", (230, 126, 34))

        # --- KHOẢNG TRỐNG GIỮA PANEL: lấp bằng hoa văn circuit (đồng bộ chặng 1) ---
        content_bottom = ui["btn_save_map"].bottom if self.is_editing else ui["btn_edit_toggle"].bottom
        deco_top = content_bottom + 15
        deco_bottom = ui["speed_slider"].y - 28
        if deco_bottom > deco_top:
            deco_rect = pygame.Rect(self.panel_w // 2 - 130, deco_top, 260, deco_bottom - deco_top)
            self._draw_circuit_decoration(deco_rect)

        # --- SLIDER TỐC ĐỘ (thay cho 2 nút SLOWER/FASTER cũ) ---
        self._draw_speed_slider(ui["speed_slider"])

        # --- KHỐI THỐNG KÊ (mở rộng thêm Time + Loaded map, đồng bộ chặng 1) ---
        stats_y = self.sh - 160
        p_color = (50, 255, 120) if self.phase == "completed" else ((255, 50, 80) if self.phase == "failed" else (0, 255, 255))
        self.screen.blit(self.font.render(f"Phase: {self.phase.lower()}", True, p_color), (15, stats_y))
        self.screen.blit(self.font.render(f"Steps: {self.steps_count}", True, (200, 200, 200)), (15, stats_y + 21))
        self.screen.blit(self.font.render(f"Time: {self.run_elapsed_ms} ms", True, (200, 200, 200)), (15, stats_y + 42))

        loaded_txt = f"Loaded: {self.map_file}"
        if len(loaded_txt) > 34:
            loaded_txt = loaded_txt[:31] + "..."
        self.screen.blit(self.font.render(loaded_txt, True, (130, 150, 170)), (15, stats_y + 63))
        
        self._draw_btn(ui["btn_back"], "BACK", (255, 50, 80))

        # (Phần vẽ Popup chiến thắng giữ nguyên...)

        if self.phase == "completed":
            shadow = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
            shadow.fill((10, 10, 20, 190))
            self.screen.blit(shadow, (0, 0))
            
            pw, ph = 420, 220
            px, py = (self.sw - pw)//2, (self.sh - ph)//2
            pygame.draw.rect(self.screen, (26, 34, 45), (px, py, pw, ph), border_radius=12)
            pygame.draw.rect(self.screen, (0, 255, 255), (px, py, pw, ph), width=3, border_radius=12) 
            
            t_txt = self.title_font.render("THÀNH CÔNG RỒI!", True, (0, 255, 255))
            self.screen.blit(t_txt, t_txt.get_rect(centerx=px + pw//2, y=py + 30))
            self._draw_btn(pygame.Rect(px + 25, py + 140, 110, 40), "MENU", (45, 55, 70))
            self._draw_btn(pygame.Rect(px + 155, py + 140, 110, 40), "REPLAY", (155, 89, 182))
            self._draw_btn(pygame.Rect(px + 285, py + 140, 110, 40), "NEXT STAGE", (46, 204, 113))