# File: stages/stage2_city.py
import pygame
import config
import os
from algorithms.informed.greedy import greedy_search
from algorithms.informed.a_star import a_star
from algorithms.informed.ida_star import ida_star

class Stage2City:
    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager
        sh = self.screen.get_height()

        try:
            self.font = pygame.font.Font("assets/fonts/minecraft.ttf", 16)
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 22)
        except:
            self.font = pygame.font.SysFont("Arial", 16, bold=True)
            self.title_font = pygame.font.SysFont("Arial", 22, bold=True)

        # Định nghĩa cố định nút bấm ở đây để đồng bộ cả file
        self.run_btn = pygame.Rect(20, sh - 140, 200, 50)
        self.back_btn = pygame.Rect(20, sh - 70,  200, 50)

        self.c_bg      = getattr(config, 'COLOR_BG',      (10, 15, 25))
        self.c_text    = getattr(config, 'COLOR_TEXT',    (240, 240, 240))
        self.c_path    = getattr(config, 'COLOR_PATH',    (255, 215, 0))
        self.c_nobita  = getattr(config, 'COLOR_NOBITA',  (52, 152, 219))
        self.c_dora    = getattr(config, 'COLOR_DORA',    (231, 76, 60))
        
        self.terrains = {
            1:  {"name": "Đường thường (1)", "color": (40, 50, 65, 0)},
            3:  {"name": "Đường kẹt xe (3)", "color": (255, 100, 50, 120)},
            5:  {"name": "Cầu vượt (5)",     "color": (0, 255, 255, 100)},
            8:  {"name": "Cổng dịch chuyển", "color": (180, 50, 255, 120)},
            99: {"name": "Tòa nhà (Chặn)",   "color": (20, 25, 35, 220)}
        }
        self.current_brush = 99

        self.tile_size = getattr(config, 'TILE_SIZE', 40)
        self.rows = 20
        self.cols = 26
        self.grid = [[1 for _ in range(self.cols)] for _ in range(self.rows)]
        
        self.start_node = (3, 3)
        self.goal_node = (16, 22)

        left_panel_w = 240
        right_panel_w = 220
        self.grid_offset_x = left_panel_w + (self.screen.get_width() - left_panel_w - right_panel_w - (self.cols * self.tile_size)) // 2
        self.grid_offset_y = (self.screen.get_height() - (self.rows * self.tile_size)) // 2

        self._load_background()
        self._generate_default_walls()
        self.selected_algorithm = "A*"
        self._reset_results()

    def _load_background(self):
        bg_path = os.path.join("assets", "images", "stage2_bg.png")
        if not os.path.exists(bg_path):
            bg_path = os.path.join("assets", "images", "stage2_bg.jpg")
        if os.path.exists(bg_path):
            try:
                raw = pygame.image.load(bg_path).convert_alpha()
                self.bg_image = pygame.transform.smoothscale(
                    raw, (self.cols * self.tile_size, self.rows * self.tile_size)
                )
            except:
                self.bg_image = None

    def _generate_default_walls(self):
        for r in range(5, 15):
            self.grid[r][8] = 99
            self.grid[r][18] = 99
        for c in range(8, 14):
            self.grid[10][c] = 99
        for r in range(6, 10):
            self.grid[r][12] = 3
        for c in range(14, 18):
            self.grid[15][c] = 5

    def _reset_results(self):
        self.path = []
        self.visited_order = []
        self.nodes_expanded = 0
        self.execution_time = "0.0 ms"
        self.path_cost = 0

    def _get_brush_rects(self, sw, sh):
        rx = sw - 210
        start_y = 260
        rects = {}
        for i, (val, info) in enumerate(self.terrains.items()):
            rects[val] = pygame.Rect(rx, start_y + 40 + i * 45, 190, 35)
        return rects

    def handle_events(self, events):
        sw = self.screen.get_width()
        sh = self.screen.get_height()
        brush_rects = self._get_brush_rects(sw, sh)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                greedy_btn = pygame.Rect(10, 80,  220, 45)
                astar_btn  = pygame.Rect(10, 140, 220, 45)
                ida_btn    = pygame.Rect(10, 200, 220, 45)
                clear_btn  = pygame.Rect(10, 280, 220, 45)

                if greedy_btn.collidepoint(event.pos):
                    self.selected_algorithm = "Greedy"
                    self._reset_results()
                elif astar_btn.collidepoint(event.pos):
                    self.selected_algorithm = "A*"
                    self._reset_results()
                elif ida_btn.collidepoint(event.pos):
                    self.selected_algorithm = "IDA*"
                    self._reset_results()
                elif clear_btn.collidepoint(event.pos):
                    self.grid = [[1 for _ in range(self.cols)] for _ in range(self.rows)]
                    self._reset_results()
                elif self.run_btn.collidepoint(event.pos): # Sử dụng biến chung
                    self._run_selected_algorithm()
                elif self.back_btn.collidepoint(event.pos): # Sử dụng biến chung
                    self.stage_manager.change_stage("stage_select")

                for val, rect in brush_rects.items():
                    if rect.collidepoint(event.pos):
                        self.current_brush = val

            if pygame.mouse.get_pressed()[0]: 
                mx, my = pygame.mouse.get_pos()
                col = (mx - self.grid_offset_x) // self.tile_size
                row = (my - self.grid_offset_y) // self.tile_size
                if 0 <= row < self.rows and 0 <= col < self.cols:
                    if (row, col) != self.start_node and (row, col) != self.goal_node:
                        self.grid[row][col] = self.current_brush
                        self._reset_results()

            if pygame.mouse.get_pressed()[2]: 
                mx, my = pygame.mouse.get_pos()
                col = (mx - self.grid_offset_x) // self.tile_size
                row = (my - self.grid_offset_y) // self.tile_size
                if 0 <= row < self.rows and 0 <= col < self.cols:
                    if (row, col) != self.start_node and (row, col) != self.goal_node:
                        self.grid[row][col] = 1
                        self._reset_results()

    def _run_selected_algorithm(self):
        if self.selected_algorithm == "Greedy":
            self.path, self.visited_order, self.nodes_expanded, self.execution_time = greedy_search(
                self.grid, self.start_node, self.goal_node
            )
        elif self.selected_algorithm == "A*":
            self.path, self.visited_order, self.nodes_expanded, self.execution_time = a_star(
                self.grid, self.start_node, self.goal_node
            )
        elif self.selected_algorithm == "IDA*":
            self.path, self.visited_order, self.nodes_expanded, self.execution_time = ida_star(
                self.grid, self.start_node, self.goal_node
            )

        self.path_cost = 0
        for node in self.path:
            self.path_cost += self.grid[node[0]][node[1]]
        if self.path and self.goal_node not in self.path:
            self.path_cost += self.grid[self.goal_node[0]][self.goal_node[1]]
            
        if len(self.path) > 0:
            self.stage_manager.unlock_stage("stage3")

    def update(self):
        pass

    def draw(self):
        self.screen.fill(self.c_bg)
        sw = self.screen.get_width()
        sh = self.screen.get_height()
        ts = self.tile_size
        ox = self.grid_offset_x
        oy = self.grid_offset_y

        if self.bg_image:
            self.screen.blit(self.bg_image, (ox, oy))
        else:
            pygame.draw.rect(self.screen, (10, 15, 20), (ox, oy, self.cols * ts, self.rows * ts))

        grid_surface = pygame.Surface((self.cols * ts, self.rows * ts), pygame.SRCALPHA)

        for r in range(self.rows):
            for c in range(self.cols):
                val = self.grid[r][c]
                rect = pygame.Rect(c * ts, r * ts, ts, ts)
                
                if val != 1:
                    color_info = self.terrains[val]["color"]
                    if val == 99:
                        pygame.draw.rect(grid_surface, color_info, rect)
                        pygame.draw.rect(grid_surface, (0, 150, 255, 100), rect, 2)
                    else:
                        pygame.draw.rect(grid_surface, color_info, rect)

                pygame.draw.rect(grid_surface, (50, 60, 70, 80), rect, 1)

        for (r, c) in self.visited_order:
            if (r, c) != self.start_node and (r, c) != self.goal_node:
                center = (c * ts + ts // 2, r * ts + ts // 2)
                pygame.draw.circle(grid_surface, (46, 204, 113, 180), center, 5)

        if len(self.path) > 0:
            full_path = [self.start_node] + self.path + [self.goal_node]
            path_points = [(c * ts + ts // 2, r * ts + ts // 2) for r, c in full_path]
            if len(path_points) > 1:
                pygame.draw.lines(grid_surface, self.c_path, False, path_points, 4)
            for p in path_points:
                pygame.draw.circle(grid_surface, (255, 255, 255), p, 4)

        self.screen.blit(grid_surface, (ox, oy))

        sr, sc = self.start_node
        start_rect = pygame.Rect(ox + sc * ts, oy + sr * ts, ts, ts)
        pygame.draw.rect(self.screen, self.c_nobita, start_rect, border_radius=8)
        n_txt = self.title_font.render("N", True, (255, 255, 255))
        self.screen.blit(n_txt, n_txt.get_rect(center=start_rect.center))

        gr, gc = self.goal_node
        goal_rect = pygame.Rect(ox + gc * ts, oy + gr * ts, ts, ts)
        pygame.draw.rect(self.screen, self.c_dora, goal_rect, border_radius=8)
        s_txt = self.title_font.render("S", True, (255, 255, 255))
        self.screen.blit(s_txt, s_txt.get_rect(center=goal_rect.center))

        # LEFT PANEL
        left_panel_width = 240
        pygame.draw.rect(self.screen, (25, 30, 35), (0, 0, left_panel_width, sh))
        pygame.draw.line(self.screen, (60, 70, 80), (left_panel_width, 0), (left_panel_width, sh), 2)
        
        self.screen.blit(self.title_font.render("INFORMED AI", True, (0, 200, 255)), (20, 30))

        algorithms = [
            ("Greedy BFS", "Greedy", pygame.Rect(10, 80,  220, 45)),
            ("A* Search", "A*", pygame.Rect(10, 140, 220, 45)),
            ("IDA* Search", "IDA*", pygame.Rect(10, 200, 220, 45)),
        ]
        for label, algo_key, btn_rect in algorithms:
            is_sel = (self.selected_algorithm == algo_key)
            color = (0, 120, 180) if is_sel else (40, 45, 50)
            pygame.draw.rect(self.screen, color, btn_rect, border_radius=8)
            if is_sel:
                pygame.draw.rect(self.screen, (0, 255, 255), btn_rect, 2, border_radius=8)
            txt = self.font.render(label, True, (255, 255, 255) if is_sel else (150, 160, 170))
            self.screen.blit(txt, (btn_rect.x + 15, btn_rect.y + 12))

        clear_btn = pygame.Rect(10, 280, 220, 45)
        pygame.draw.rect(self.screen, (120, 40, 40), clear_btn, border_radius=8)
        txt = self.font.render("Khôi phục bản đồ", True, (255, 200, 200))
        self.screen.blit(txt, txt.get_rect(center=clear_btn.center))

        pygame.draw.rect(self.screen, (0, 180, 100), self.run_btn,  border_radius=8)
        run_text = self.title_font.render("CHẠY AI", True, (255, 255, 255))
        self.screen.blit(run_text, run_text.get_rect(center=self.run_btn.center))

        pygame.draw.rect(self.screen, (180, 60, 60), self.back_btn, border_radius=8)
        back_text = self.title_font.render("QUAY LẠI", True, (255, 255, 255))
        self.screen.blit(back_text, back_text.get_rect(center=self.back_btn.center))

        # RIGHT PANEL
        right_panel_width = 220
        rx = sw - right_panel_width
        pygame.draw.rect(self.screen, (25, 30, 35), (rx, 0, right_panel_width, sh))
        pygame.draw.line(self.screen, (60, 70, 80), (rx, 0), (rx, sh), 2)

        self.screen.blit(self.title_font.render("THỐNG KÊ", True, (0, 200, 255)), (rx + 20, 30))
        
        stat_y = 80
        stats = [
            (f"Chi phí: {self.path_cost}", (255, 215, 0)),
            (f"Duyệt: {self.nodes_expanded} nodes", (180, 220, 255)),
            (f"T/gian: {self.execution_time}", (180, 220, 255))
        ]
        for txt, color in stats:
            self.screen.blit(self.font.render(txt, True, color), (rx + 20, stat_y))
            stat_y += 35

        self.screen.blit(self.title_font.render("CÔNG CỤ VẼ", True, (0, 200, 255)), (rx + 20, 240))
        
        brush_rects = self._get_brush_rects(sw, sh)
        for val, rect in brush_rects.items():
            is_selected = (self.current_brush == val)
            bg_color = (60, 70, 80) if is_selected else (35, 40, 45)
            pygame.draw.rect(self.screen, bg_color, rect, border_radius=6)
            if is_selected:
                pygame.draw.rect(self.screen, (0, 255, 255), rect, 2, border_radius=6)
            
            color_box = pygame.Rect(rect.x + 8, rect.y + 8, 20, 20)
            if val == 99:
                pygame.draw.rect(self.screen, self.terrains[val]["color"], color_box, border_radius=3)
            else:
                pygame.draw.rect(self.screen, self.terrains[val]["color"][:3], color_box, border_radius=3)
            pygame.draw.rect(self.screen, (100, 100, 100), color_box, 1, border_radius=3)
            
            text_color = (255, 255, 255) if is_selected else (150, 160, 170)
            self.screen.blit(self.font.render(self.terrains[val]["name"], True, text_color), (rect.x + 38, rect.y + 8))

        hint_y = sh - 90
        self.screen.blit(self.font.render("Chuột Trái: Vẽ", True, (120, 130, 140)), (rx + 20, hint_y))
        self.screen.blit(self.font.render("Chuột Phải: Xóa", True, (120, 130, 140)), (rx + 20, hint_y + 25))