# File: stages/stage3_inventory.py
import pygame
import math
import os
import random
import json

from algorithms.local.hill_climbing import step_hill_climbing
from algorithms.local.simulated_annealing import step_simulated_annealing
from algorithms.local.local_beam_search import step_local_beam_search

class Stage3Inventory:
    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager
        self.sw = self.screen.get_width()
        self.sh = self.screen.get_height()

        try:
            self.font = pygame.font.Font("assets/fonts/minecraft.ttf", 14)
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 20)
        except:
            self.font = pygame.font.SysFont("Arial", 14, bold=True)
            self.title_font = pygame.font.SysFont("Arial", 20, bold=True)

        self.panel_w = 260
        
        # --- CẤU HÌNH LƯỚI TỰ ĐỘNG 7x7 ---
        self.start_y = 140 
        self.cols = 8      
        self.rows = 6
        # Tự động tính cell_size to nhất có thể mà KHÔNG bị tràn khỏi màn hình
        max_w = (self.sw - self.panel_w - 40) // self.cols
        max_h = (self.sh - self.start_y - 20) // self.rows
        self.cell_size = min(max_w, max_h) 
        
        self.grid_w = self.cols * self.cell_size
        self.grid_h = self.rows * self.cell_size
        
        # Căn lưới nằm vào chính giữa phần trống bên phải
        self.start_x = self.panel_w + (self.sw - self.panel_w - self.grid_w) // 2

        # --- LOAD ẢNH NỀN VŨ TRỤ ---
        try:
            bg_surface = pygame.image.load("assets/images/stage3_bg.png").convert()
            self.bg_image = pygame.transform.scale(bg_surface, (self.sw - self.panel_w, self.sh))
        except:
            self.bg_image = None

       # --- LOAD  ẢNH BẢO BỐI XỊN VÀ  ẢNH BẢO BỐI HỎNG ---
        self.item_images = {}
        self.obs_images = {}
        folder_path = os.path.join("assets", "images", "Bảo bối chặng 3")
        
        for i in range(1, 46): 
            try:
                img = pygame.image.load(os.path.join(folder_path, f"{i}.png")).convert_alpha()
                img = pygame.transform.scale(img, (int(self.cell_size * 0.8), int(self.cell_size * 0.8)))
                self.item_images[i + 9] = img 
            except: pass

        for i in range(1, 5): # Load 4 món hỏng
            try:
                img = pygame.image.load(os.path.join(folder_path, f"baoboihu{i}.png")).convert_alpha()
                img = pygame.transform.scale(img, (int(self.cell_size * 0.8), int(self.cell_size * 0.8)))
                self.obs_images[i + 100] = img # Mã 101 -> 104
            except: pass
        # --- QUẢN LÝ BẢO BỐI MỤC TIÊU ĐƯỢC CHỌN ---
        self.target_item_id = 14 # Mặc định ban đầu là Ảnh số 5 (14 - 9 = 5: Cánh cửa thần kỳ)

        # --- DỮ LIỆU MA TRẬN & AI ---
        self.selected_algorithm = "Hill Climbing"
        self.phase = "idle" 
        self.steps_count = 0
        self.current_fitness = 0

        # Khởi tạo bản đồ cố định có sẵn bẫy chữ U ban đầu
        self.grid = self._create_initial_grid()
        self.current_fitness = self.calculate_fitness(self.grid)

        self.temperature = 100.0
        self.cooling_rate = 0.90
        self.beam_states = []

        # --- TRẠNG THÁI EDITOR ---
        self.is_editing = False 
        self.edit_mode = None  # 'add_item', 'add_obs', 'set_goal', 'erase'

    def _create_initial_grid(self):
        """Khởi tạo map: Ưu tiên Load từ file JSON đã save, nếu không có mới đẻ map trống"""
        map_path = os.path.join("assets", "maps", "stage3_map.json")
        
        # 1. THỬ TÌM VÀ ĐỌC FILE ĐÃ SAVE
        if os.path.exists(map_path):
            try:
                with open(map_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved_grid = data.get("grid")
                    saved_target = data.get("target_item_id")
                    
                    # Nếu có dữ liệu bảo bối mục tiêu, load luôn
                    if saved_target is not None:
                        self.target_item_id = saved_target
                        
                    # Nếu có ma trận đã xếp, trả về ma trận đó luôn
                    if saved_grid and len(saved_grid) == self.rows and len(saved_grid[0]) == self.cols:
                        return saved_grid
            except Exception as e:
                print(f"Lỗi load map stage 3: {e}")

        # 2. NẾU KHÔNG CÓ FILE SAVE HOẶC BỊ LỖI -> TẠO MAP TRỐNG (Blank Canvas)
        grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        
        # Chỉ đặt duy nhất Cục Vàng (số 9) ở giữa hàng gần cuối cùng để làm điểm neo
        start_row = self.rows - 2
        start_col = self.cols // 2
        grid[start_row][start_col] = 9
        
        return grid

    def find_target_position(self, current_grid):
        for r in range(self.rows):
            for c in range(self.cols):
                if current_grid[r][c] == 9:
                    return r, c
        return None

    def calculate_fitness(self, current_grid):
        pos = self.find_target_position(current_grid)
        if not pos: return 0
        row_distance = pos[0] 
        if row_distance == 0: return 100 
        return 100 - (row_distance * 10)

    def get_neighbors(self, current_grid):
        neighbors = []
        pos = self.find_target_position(current_grid)
        if not pos: return neighbors
            
        r, c = pos
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                if current_grid[nr][nc] < 100:
                    new_grid = [row[:] for row in current_grid]
                    new_grid[r][c], new_grid[nr][nc] = new_grid[nr][nc], new_grid[r][c]
                    neighbors.append(new_grid)
        return neighbors
    def _get_available_items(self):
        """Quét ma trận để tìm ra danh sách các bảo bối CHƯA được đặt lên map"""
        used_items = set()
        for r in range(self.rows):
            for c in range(self.cols):
                val = self.grid[r][c]
                if 10 <= val <= 54:
                    used_items.add(val)
        
        # Đưa cả Cục Vàng (Mục tiêu hiện tại) vào danh sách ĐÃ DÙNG để không bị trùng
        used_items.add(self.target_item_id)
        
        all_items = set(range(10, 55))
        # Trừ đi những cái đã dùng sẽ ra những cái còn trống
        available = list(all_items - used_items)
        return available

    # ==========================================================
    # GIAO DIỆN VÀ SỰ KIỆN CHUỘT
    # ==========================================================
    def _get_ui_rects(self):
        ui = {
            "btn_hc": pygame.Rect(15, 60, self.panel_w - 30, 30),
            "btn_sa": pygame.Rect(15, 100, self.panel_w - 30, 30),
            "btn_beam": pygame.Rect(15, 140, self.panel_w - 30, 30),
            "btn_run": pygame.Rect(15, 190, self.panel_w - 30, 35),
            "btn_cancel": pygame.Rect(15, 235, self.panel_w - 30, 35),
            "btn_reset": pygame.Rect(15, 280, self.panel_w - 30, 35),
            "btn_select_item": pygame.Rect(15, 325, self.panel_w - 30, 30), # Nút chọn bảo bối chạy AI
            "btn_edit_toggle": pygame.Rect(15, 365, self.panel_w - 30, 30),
            "btn_back": pygame.Rect(15, self.sh - 50, self.panel_w - 30, 35)
        }
        
        if self.is_editing:
            start_y = 405
            gap = 32
            ui.update({
                "btn_add_item": pygame.Rect(15, start_y, self.panel_w - 30, 26),
                "btn_add_obs": pygame.Rect(15, start_y + gap*1, self.panel_w - 30, 26),
                "btn_set_goal": pygame.Rect(15, start_y + gap*2, self.panel_w - 30, 26),
                "btn_erase": pygame.Rect(15, start_y + gap*3, self.panel_w - 30, 26),
                "btn_save_map": pygame.Rect(15, start_y + gap*4, self.panel_w - 30, 32)
            })
            # --- TỌA ĐỘ BẢNG POPUP THÀNH CÔNG CHẶNG 3 ---
        popup_w, popup_h = 420, 220
        popup_x = (self.sw - popup_w) // 2
        popup_y = (self.sh - popup_h) // 2
        start_btn_x = popup_x + 25
        
        ui.update({
            "popup_panel": pygame.Rect(popup_x, popup_y, popup_w, popup_h),
            "btn_popup_menu": pygame.Rect(start_btn_x, popup_y + 140, 110, 40),
            "btn_popup_retry": pygame.Rect(start_btn_x + 130, popup_y + 140, 110, 40),
            "btn_popup_next": pygame.Rect(start_btn_x + 260, popup_y + 140, 110, 40)
        })
        return ui

    def handle_events(self, events):
        ui = self._get_ui_rects()
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.stage_manager.change_stage("stage_select")
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                # --- NẾU AI CHẠY XONG (PHASE COMPLETED) THÌ HIỆN POPUP CHẶN CLICK MAP ---
                if self.phase == "completed":
                    if ui["btn_popup_menu"].collidepoint(pos):
                        self.stage_manager.change_stage("stage_select")
                        return
                    elif ui["btn_popup_retry"].collidepoint(pos):
                        # Reset lại để chơi lại map cũ
                        self.grid = self._create_initial_grid()
                        self.current_fitness = self.calculate_fitness(self.grid)
                        self.steps_count = 0
                        self.phase = "idle"
                        return
                    elif ui["btn_popup_next"].collidepoint(pos):
                        # 1. Báo cho StageManager biết: "Hãy làm nổ khóa stage4 nhé!"
                        self.stage_manager.trigger_unlock_effect = "stage4"
                        
                        # 2. Quay về màn hình chọn chặng
                        self.stage_manager.change_stage("stage_select")
                        return
                
                # --- HÀNH VI TRÊN PANEL ĐIỀU KHIỂN ---
                if pos[0] < self.panel_w:
                    if ui["btn_hc"].collidepoint(pos) and self.phase not in ["running"]: self.selected_algorithm = "Hill Climbing"
                    elif ui["btn_sa"].collidepoint(pos) and self.phase not in ["running"]: self.selected_algorithm = "Simulated Annealing"
                    elif ui["btn_beam"].collidepoint(pos) and self.phase not in ["running"]: self.selected_algorithm = "Local Beam"
                    
                    elif ui["btn_run"].collidepoint(pos):
                        if self.phase in ["idle", "failed", "completed"]: self.phase = "running"
                    elif ui["btn_cancel"].collidepoint(pos):
                        if self.phase == "running": self.phase = "failed"
                    elif ui["btn_reset"].collidepoint(pos):
                        self.grid = self._create_initial_grid()
                        self.current_fitness = self.calculate_fitness(self.grid)
                        self.steps_count = 0; self.phase = "idle"; self.temperature = 100.0; self.beam_states = []
                        
                    elif ui["btn_select_item"].collidepoint(pos) and self.phase not in ["running"]:
                        # Đổi xoay vòng nhưng BỎ QUA những bảo bối đang nằm trên lưới
                        while True:
                            self.target_item_id += 1
                            if self.target_item_id > 54: self.target_item_id = 10
                            
                            # Kiểm tra xem mã mới này có đang nằm trên map không
                            is_on_map = any(self.target_item_id in row for row in self.grid)
                            if not is_on_map:
                                break # Nếu chưa có trên map thì chốt!
                    elif ui["btn_edit_toggle"].collidepoint(pos):
                        self.is_editing = not self.is_editing
                        self.edit_mode = None
                        
                    elif ui["btn_back"].collidepoint(pos):
                        self.stage_manager.change_stage("stage_select")
                        
                    if self.is_editing:
                        if "btn_add_item" in ui and ui["btn_add_item"].collidepoint(pos): self.edit_mode = "add_item"
                        elif "btn_add_obs" in ui and ui["btn_add_obs"].collidepoint(pos): self.edit_mode = "add_obs"
                        elif "btn_set_goal" in ui and ui["btn_set_goal"].collidepoint(pos): self.edit_mode = "set_goal"
                        elif "btn_erase" in ui and ui["btn_erase"].collidepoint(pos): self.edit_mode = "erase"
                        elif "btn_save_map" in ui and ui["btn_save_map"].collidepoint(pos):
                            # --- TÍNH NĂNG LƯU MAP ---
                            try:
                                map_path = os.path.join("assets", "maps", "stage3_map.json")
                                os.makedirs(os.path.dirname(map_path), exist_ok=True)
                                # Lưu ma trận và mã bảo bối đang chọn vào file
                                map_data = {"target_item_id": self.target_item_id, "grid": self.grid}
                                with open(map_path, "w", encoding="utf-8") as f:
                                    json.dump(map_data, f)
                                print(">>> [THÀNH CÔNG] Đã lưu Map Chặng 3!")
                            except Exception as e:
                                print(f"Lỗi khi lưu Map: {e}")
                            
                            self.is_editing = False # Lưu xong tự tắt menu Edit                    return 

                # --- HÀNH VI THẢ BẢO BỐI TRÊN LƯỚI MAP ---
                if pos[0] > self.panel_w and self.is_editing and self.edit_mode:
                    if self.start_x <= pos[0] <= self.start_x + self.grid_w and self.start_y <= pos[1] <= self.start_y + self.grid_h:
                        c = (pos[0] - self.start_x) // self.cell_size
                        r = (pos[1] - self.start_y) // self.cell_size
                        
                        if 0 <= r < self.rows and 0 <= c < self.cols:
                            if self.edit_mode == "add_item":
                                if self.grid[r][c] != 9: 
                                    avail = self._get_available_items()
                                    if avail: # Nếu trong kho vẫn còn bảo bối chưa lôi ra
                                        self.grid[r][c] = random.choice(avail)
                                    else:
                                        print("Đã lôi hết 25 món bảo bối ra rồi, không còn món mới đâu!")
                            elif self.edit_mode == "add_obs":
                                if self.grid[r][c] != 9:
                                    self.grid[r][c] = random.randint(101, 104)
                            elif self.edit_mode == "erase":
                                if self.grid[r][c] != 9: self.grid[r][c] = 0
                            elif self.edit_mode == "set_goal":
                                old_pos = self.find_target_position(self.grid)
                                if old_pos: self.grid[old_pos[0]][old_pos[1]] = 0
                                self.grid[r][c] = 9
                                
                            self.current_fitness = self.calculate_fitness(self.grid)
                            self.phase = "idle"

    def update(self):
        if self.phase == "running":
            current_time = pygame.time.get_ticks()
            
            # --- 1. XỬ LÝ HOẠT ẢNH TRƯỢT SWAP (SMOOTH GLIDE) ---
            if hasattr(self, 'anim_swap') and self.anim_swap:
                # Nếu đã trượt đủ 150ms -> Chốt kết quả ma trận
                if current_time - self.anim_swap["start_time"] >= 150:
                    self.grid = self.anim_swap["next_state"]
                    self.current_fitness = self.calculate_fitness(self.grid)
                    self.steps_count += 1
                    self.anim_swap = None
                    self.last_step_time = current_time 
                return # Đang trượt thì không cho AI chạy step mới
                
            if not hasattr(self, 'last_step_time'): self.last_step_time = current_time
            if current_time - self.last_step_time > 150:
                self.run_ai_step()
                self.last_step_time = current_time

    def run_ai_step(self):
        if self.phase != "running": return
        if self.current_fitness >= 100:
            self.phase = "completed"
            return

        if self.selected_algorithm == "Hill Climbing": next_state = step_hill_climbing(self)
        elif self.selected_algorithm == "Simulated Annealing": next_state = step_simulated_annealing(self)
        elif self.selected_algorithm == "Local Beam": next_state = step_local_beam_search(self)
        else: next_state = None

        if next_state:
            # --- 2. SO SÁNH TÌM RA 2 Ô VỪA ĐỔI CHỖ ĐỂ TẠO ANIMATION ---
            diffs = []
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.grid[r][c] != next_state[r][c]:
                        diffs.append({"pos": (r, c), "val": self.grid[r][c]})
                        
            if len(diffs) == 2:
                # Kích hoạt trạng thái đang trượt (Swap)
                self.anim_swap = {
                    "start_time": pygame.time.get_ticks(),
                    "item1": diffs[0], # Ô thứ nhất chứa giá trị cũ
                    "item2": diffs[1], # Ô thứ hai chứa giá trị cũ
                    "next_state": next_state # Giữ tạm ma trận mới, trượt xong mới gán
                }
            else:
                self.grid = next_state
                self.current_fitness = self.calculate_fitness(self.grid)
                self.steps_count += 1
        else:
            self.phase = "failed" 

    def _draw_single_item(self, val, x, y, float_y):
        """Hàm con hỗ trợ vẽ 1 món bảo bối (Kèm hiệu ứng Neon) để tái sử dụng lúc nó trượt"""
        # 1. VẼ BẢO BỐI XỊN (Mã 10-54)
        if 10 <= val <= 54:
            if val in self.item_images:
                offset = (self.cell_size - self.item_images[val].get_width()) // 2
                self.screen.blit(self.item_images[val], (x + offset, y + offset + float_y))
                
        # 2. VẼ BẢO BỐI HỎNG (Mã 101-104) - HIỆU ỨNG GLITCH ĐỎ
        elif 101 <= val <= 104:
            if val in self.obs_images:
                img = self.obs_images[val]
                offset = (self.cell_size - img.get_width()) // 2
                draw_x = x + offset
                draw_y = y + offset + float_y
                
                if (pygame.time.get_ticks() // 200) % 2 == 0: glow_color = (255, 20, 50, 255)
                else: glow_color = (180, 0, 0, 255)
                    
                mask = pygame.mask.from_surface(img)
                mask_surf = mask.to_surface(setcolor=glow_color, unsetcolor=(0,0,0,0))
                for dx in [-2, 0, 2]:
                    for dy in [-2, 0, 2]:
                        if dx != 0 or dy != 0:
                            self.screen.blit(mask_surf, (draw_x + dx, draw_y + dy))
                self.screen.blit(img, (draw_x, draw_y))
                
        # 3. VẼ MỤC TIÊU CỤC VÀNG (Mã 9) - HIỆU ỨNG NEON VÀNG
        elif val == 9:
            if self.target_item_id in self.item_images:
                img = self.item_images[self.target_item_id]
                offset = (self.cell_size - img.get_width()) // 2
                draw_x = x + offset
                draw_y = y + offset + float_y
                
                mask = pygame.mask.from_surface(img)
                mask_surf = mask.to_surface(setcolor=(255, 215, 0, 255), unsetcolor=(0,0,0,0))
                for dx in [-3, 0, 3]:
                    for dy in [-3, 0, 3]:
                        if dx != 0 or dy != 0:
                            self.screen.blit(mask_surf, (draw_x + dx, draw_y + dy))
                self.screen.blit(img, (draw_x, draw_y))

    def _draw_btn(self, rect, text, bg_color, is_active=False):
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=6)
        border_color = (255, 255, 255) if is_active else (100, 110, 120)
        border_width = 2 if is_active else 1
        pygame.draw.rect(self.screen, border_color, rect, width=border_width, border_radius=6)
        txt = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(txt, txt.get_rect(center=rect.center))

    def draw(self):
        # 1. Vẽ Nền
        if self.bg_image: self.screen.blit(self.bg_image, (self.panel_w, 0))
        else: self.screen.fill((10, 15, 25))

        overlay = pygame.Surface((self.sw - self.panel_w, self.sh), pygame.SRCALPHA)
        overlay.fill((10, 15, 30, 60)) 
        self.screen.blit(overlay, (self.panel_w, 0))

        # 2. Vòng lặp vẽ lưới và các món đồ NẰM IM
        for r in range(self.rows):
            for c in range(self.cols):
                x = self.start_x + c * self.cell_size
                y = self.start_y + r * self.cell_size
                rect = pygame.Rect(x, y, self.cell_size, self.cell_size)
                
                if self.is_editing:
                    pygame.draw.rect(self.screen, (0, 150, 255, 40), rect, 1)

                val = self.grid[r][c]
                float_y = math.sin(pygame.time.get_ticks() * 0.003 + r + c) * 6
                
                # CHẶN: NẾU Ô NÀY ĐANG ĐỔI CHỖ -> BỎ QUA KHÔNG VẼ Ở ĐÂY ĐỂ TRÁNH BỊ BÓNG MA
                is_swapping = False
                if hasattr(self, 'anim_swap') and self.anim_swap:
                    if (r, c) == self.anim_swap["item1"]["pos"] or (r, c) == self.anim_swap["item2"]["pos"]:
                        is_swapping = True
                        
                if not is_swapping:
                    self._draw_single_item(val, x, y, float_y)

        # 3. VẼ HAI MÓN BẢO BỐI ĐANG TRƯỢT (SWAP) ĐÈ LÊN TRÊN CÙNG (CỰC MƯỢT)
        if hasattr(self, 'anim_swap') and self.anim_swap:
            p = (pygame.time.get_ticks() - self.anim_swap["start_time"]) / 150.0
            p = max(0.0, min(1.0, p))
            # Smoothstep: Làm mượt gia tốc lúc bắt đầu và kết thúc trượt
            p = p * p * (3 - 2 * p) 
            
            r1, c1 = self.anim_swap["item1"]["pos"]
            v1 = self.anim_swap["item1"]["val"]
            
            r2, c2 = self.anim_swap["item2"]["pos"]
            v2 = self.anim_swap["item2"]["val"]
            
            x1 = self.start_x + c1 * self.cell_size
            y1 = self.start_y + r1 * self.cell_size
            
            x2 = self.start_x + c2 * self.cell_size
            y2 = self.start_y + r2 * self.cell_size
            
            # Tính toán tọa độ đang bay lơ lửng giữa chừng
            cx1 = x1 + (x2 - x1) * p
            cy1 = y1 + (y2 - y1) * p
            
            cx2 = x2 + (x1 - x2) * p
            cy2 = y2 + (y1 - y2) * p
            
            float_y = math.sin(pygame.time.get_ticks() * 0.003) * 6
            
            # Gọi lại hàm con để vẽ 2 cục đang lướt đi vù vù
            self._draw_single_item(v1, cx1, cy1, float_y)
            self._draw_single_item(v2, cx2, cy2, float_y)

        # 4. Vẽ UI Bảng Điều Khiển
        pygame.draw.rect(self.screen, (26, 34, 45), (0, 0, self.panel_w, self.sh))
        pygame.draw.line(self.screen, (0, 150, 200), (self.panel_w, 0), (self.panel_w, self.sh), 2)
        self.screen.blit(self.title_font.render("AI ALGORITHMS", True, (150, 160, 170)), (15, 20))

        ui = self._get_ui_rects()
        c_active, c_idle = (52, 152, 219), (45, 55, 70)

        self._draw_btn(ui["btn_hc"], "Hill Climbing", c_active if self.selected_algorithm == "Hill Climbing" else c_idle)
        self._draw_btn(ui["btn_sa"], "Simulated Annealing", c_active if self.selected_algorithm == "Simulated Annealing" else c_idle)
        self._draw_btn(ui["btn_beam"], "Local Beam", c_active if self.selected_algorithm == "Local Beam" else c_idle)

        self._draw_btn(ui["btn_run"], "RUN AI", (46, 204, 113))
        self._draw_btn(ui["btn_cancel"], "CANCEL RUN", (231, 76, 60))
        self._draw_btn(ui["btn_reset"], "RESET MAP", (155, 89, 182))
        
        current_item_no = self.target_item_id - 9
        self._draw_btn(ui["btn_select_item"], f"ĐỔI BẢO BỐI AI (#{current_item_no})", (241, 196, 15))

        toggle_txt = "EDIT MAP [-]" if self.is_editing else "EDIT MAP [+]"
        self._draw_btn(ui["btn_edit_toggle"], toggle_txt, (55, 65, 75))

        if self.is_editing:
            self._draw_btn(ui["btn_add_item"], "Đặt Bảo Bối", c_active if self.edit_mode == "add_item" else c_idle, self.edit_mode == "add_item")
            self._draw_btn(ui["btn_add_obs"], "Đặt Vật Cản", c_active if self.edit_mode == "add_obs" else c_idle, self.edit_mode == "add_obs")
            self._draw_btn(ui["btn_set_goal"], "Đặt Cục Vàng", c_active if self.edit_mode == "set_goal" else c_idle, self.edit_mode == "set_goal")
            self._draw_btn(ui["btn_erase"], "Cục Tẩy", c_active if self.edit_mode == "erase" else c_idle, self.edit_mode == "erase")
            self._draw_btn(ui["btn_save_map"], "SAVE MAP", (230, 126, 34))

        stats_y = self.sh - 140
        phase_color = (0, 255, 255)
        if self.phase == "completed": phase_color = (46, 204, 113)
        elif self.phase == "failed": phase_color = (231, 76, 60)

        self.screen.blit(self.font.render(f"Phase: {self.phase}", True, phase_color), (15, stats_y))
        self.screen.blit(self.font.render(f"Steps: {self.steps_count}", True, (200, 200, 200)), (15, stats_y + 25))
        self.screen.blit(self.font.render(f"Fitness: {self.current_fitness}/100", True, (200, 200, 200)), (15, stats_y + 50))

        self._draw_btn(ui["btn_back"], "BACK", (231, 76, 60))

        # 5. VẼ BẢNG POPUP CHÚC MỪNG THÀNH CÔNG LÊN TRÊN CÙNG
        if self.phase == "completed":
            shadow_bg = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
            shadow_bg.fill((10, 10, 20, 200))
            self.screen.blit(shadow_bg, (0, 0))
            
            p_rect = ui["popup_panel"]
            pygame.draw.rect(self.screen, (26, 34, 45), p_rect, border_radius=12)
            pygame.draw.rect(self.screen, (46, 204, 113), p_rect, width=3, border_radius=12) 
            
            try: big_font = pygame.font.Font("assets/fonts/minecraft.ttf", 24)
            except: big_font = pygame.font.SysFont("Arial", 24, bold=True)
                
            title_text = big_font.render("THÀNH CÔNG RỒI!", True, (46, 204, 113))
            self.screen.blit(title_text, title_text.get_rect(centerx=p_rect.centerx, y=p_rect.y + 30))
            
            info_txt = f"AI đã đưa bảo bối về miệng túi sau {self.steps_count} bước!"
            info_surface = self.font.render(info_txt, True, (220, 220, 220))
            self.screen.blit(info_surface, info_surface.get_rect(centerx=p_rect.centerx, y=p_rect.y + 85))
            
            self._draw_btn(ui["btn_popup_menu"], "MENU", (45, 55, 70))
            self._draw_btn(ui["btn_popup_retry"], "REPLAY", (155, 89, 182))
            self._draw_btn(ui["btn_popup_next"], "NEXT STAGE", (46, 204, 113))