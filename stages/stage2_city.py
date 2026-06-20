# File: stages/stage2_city.py
import pygame
import config
import os
import math
import json

# --- IMPORT 3 THUẬT TOÁN ĐỒ THỊ CHUẨN ---
from algorithms.informed.a_star import a_star
from algorithms.informed.greedy import greedy_search
from algorithms.informed.ida_star import ida_star

class Stage2City:
    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager
        
        self.sw = self.screen.get_width()
        self.sh = self.screen.get_height()

        try:
            self.font = pygame.font.Font("assets/fonts/minecraft.ttf", 14)
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 18)
        except:
            self.font = pygame.font.SysFont("Arial", 14, bold=True)
            self.title_font = pygame.font.SysFont("Arial", 18, bold=True)

        self.c_bg      = getattr(config, 'COLOR_BG',      (10, 15, 25))
        self.c_nobita  = getattr(config, 'COLOR_NOBITA',  (52, 152, 219))
        self.c_dora    = getattr(config, 'COLOR_DORA',    (231, 76, 60))

        # --- CẤU TRÚC DỮ LIỆU ĐỒ THỊ ---
        self.nodes = []      
        self.edges = {}      
        self.start_node = None
        self.goal_node = None

        self.map_file = "stage2_graph.json"
        self._load_graph_data()

        # Mặc định vào game sẽ ẨN đồ thị nút/cạnh đi cho đẹp, chỉ hiện ảnh nền và N/S, bấm G để bật lại
        self.show_graph = False 
        
        self.left_panel_w = 210
        # Bản đồ mở rộng tối đa, chiếm trọn toàn bộ phần không gian còn lại sang bên phải
        self.map_rect = pygame.Rect(self.left_panel_w, 0, self.sw - self.left_panel_w, self.sh)

        self._load_background()
        self.selected_algorithm = "A* Search"
        self._reset_results()

        # UI Buttons gọn gàng ở thanh bên trái
        self.btn_run = pygame.Rect(10, 200, 190, 40)
        self.btn_back = pygame.Rect(10, self.sh - 60, 190, 40)

    def _load_background(self):
        bg_path = os.path.join("assets", "images", "stage2_bg.png")
        if not os.path.exists(bg_path): bg_path = os.path.join("assets", "images", "stage2_bg.jpg")
        if os.path.exists(bg_path):
            raw = pygame.image.load(bg_path).convert_alpha()
            # Tự động co giãn ảnh nền khít khao theo kích thước bản đồ mới rộng hơn
            self.bg_image = pygame.transform.smoothscale(raw, (self.map_rect.width, self.map_rect.height))
        else:
            self.bg_image = None

    def _load_graph_data(self):
        if os.path.exists(self.map_file):
            with open(self.map_file, 'r') as f:
                data = json.load(f)
                self.nodes = [tuple(n) for n in data.get("nodes", [])]
                raw_edges = data.get("edges", {})
                self.edges = {}
                for k, neighbors in raw_edges.items():
                    u = int(k)
                    self.edges[u] = {}
                    for nk, v_data in neighbors.items():
                        v = int(nk)
                        if isinstance(v_data, int): self.edges[u][v] = {"cost": v_data, "type": 1}
                        else: self.edges[u][v] = v_data
                self.start_node = data.get("start")
                self.goal_node = data.get("goal")

    def _reset_results(self):
        self.path = []
        self.visited_order = []
        self.path_cost = 0
        self.nodes_expanded = 0
        self.execution_time = "0.0 ms"

    def _run_ai(self):
        if self.start_node is None or self.goal_node is None:
            print("[LỖI] Chưa cấu hình điểm N và S trên map!")
            return
        
        self._reset_results()
        
        if self.selected_algorithm == "A* Search":
            p, v, n, t, c = a_star(self.nodes, self.edges, self.start_node, self.goal_node)
        elif self.selected_algorithm == "Greedy BFS":
            p, v, n, t, c = greedy_search(self.nodes, self.edges, self.start_node, self.goal_node)
        elif self.selected_algorithm == "IDA*":
            p, v, n, t, c = ida_star(self.nodes, self.edges, self.start_node, self.goal_node)

        self.path = p
        self.visited_order = v
        self.nodes_expanded = n
        self.execution_time = t
        self.path_cost = c

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                # Giữ lại duy nhất phím G để ông hoặc cô giáo thích xăm soi cấu trúc đồ thị thì bật lên
                if event.key == pygame.K_g: 
                    self.show_graph = not self.show_graph

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Chỉ tiếp nhận tương tác click trên thanh Menu bên trái
                if event.pos[0] < self.left_panel_w:
                    if self.btn_back.collidepoint(event.pos): 
                        self.stage_manager.change_stage("stage_select")
                    elif self.btn_run.collidepoint(event.pos): 
                        self._run_ai()
                    
                    # Click chuyển đổi thuật toán nhanh
                    algs_rects = [("A* Search", 60), ("Greedy BFS", 100), ("IDA*", 140)]
                    for label, y in algs_rects:
                        if pygame.Rect(10, y, 190, 35).collidepoint(event.pos):
                            self.selected_algorithm = label
                            self._reset_results()

    def update(self):
        pass

    def draw(self):
        self.screen.fill(self.c_bg)

        # ── 1. VẼ MAP VÀ HÌNH NỀN KHỔNG LỒ ──
        if self.bg_image:
            self.screen.blit(self.bg_image, (self.map_rect.x, self.map_rect.y))

        # ── 2. VẼ ĐỒ THỊ GIAO THÔNG (CHỈ VẼ KHI BẬT PHÍM G) ──
        if self.show_graph:
            for u, neighbors in self.edges.items():
                for v, data in neighbors.items():
                    if u < v: 
                        t = data["type"]
                        color = (0, 255, 255)
                        width = 4
                        if t == 2: color = (150, 150, 150); width = 2
                        elif t == 3: color = (255, 0, 0); width = 4
                        elif t == 8: color = (255, 0, 255); width = 6 
                        pygame.draw.line(self.screen, color, self.nodes[u], self.nodes[v], width)
                        pygame.draw.line(self.screen, (0, 0, 0), self.nodes[u], self.nodes[v], 1)

        # LUÔN VẼ ĐƯỜNG ĐI CỦA AI TÌM ĐƯỢC (ĐƯỜNG PHÁT SÁNG XANH LÁ)
        if len(self.path) > 1:
            for i in range(len(self.path) - 1):
                u = self.path[i]
                v = self.path[i+1]
                pygame.draw.line(self.screen, (0, 0, 0), self.nodes[u], self.nodes[v], 8)
                pygame.draw.line(self.screen, (0, 255, 0), self.nodes[u], self.nodes[v], 4)

        # VẼ ĐIỂM NOBITA VÀ SHIZUKA VÀO ĐÚNG TỌA ĐỘ TRÊN ĐỒ THỊ
        if self.show_graph:
            for i, pos in enumerate(self.nodes):
                color = (200, 200, 200)
                radius = 6
                if i in self.path: color = (0, 255, 0); radius = 8
                if i == self.start_node: color = self.c_nobita; radius = 10
                elif i == self.goal_node: color = self.c_dora; radius = 10

                pygame.draw.circle(self.screen, color, pos, radius)
                pygame.draw.circle(self.screen, (0, 0, 0), pos, radius, 2)

                if i == self.start_node: self.screen.blit(self.font.render("N", True, (255,255,255)), (pos[0]-4, pos[1]-18))
                elif i == self.goal_node: self.screen.blit(self.font.render("S", True, (255,255,255)), (pos[0]-4, pos[1]-18))
        else:
            # Khi ẩn đồ thị, giao diện cực sạch, chỉ vẽ đúng 2 cục Start và Goal
            if self.start_node is not None and self.start_node < len(self.nodes):
                pos = self.nodes[self.start_node]
                pygame.draw.circle(self.screen, self.c_nobita, pos, 10)
                pygame.draw.circle(self.screen, (0, 0, 0), pos, 10, 2)
                self.screen.blit(self.font.render("N", True, (255,255,255)), (pos[0]-4, pos[1]-18))
            
            if self.goal_node is not None and self.goal_node < len(self.nodes):
                pos = self.nodes[self.goal_node]
                pygame.draw.circle(self.screen, self.c_dora, pos, 10)
                pygame.draw.circle(self.screen, (0, 0, 0), pos, 10, 2)
                self.screen.blit(self.font.render("S", True, (255,255,255)), (pos[0]-4, pos[1]-18))

        # ── 3. VẼ UI THANH MENU BÊN TRÁI DUY NHẤT ──
        pygame.draw.rect(self.screen, (30, 35, 45), (0, 0, self.left_panel_w, self.sh))
        pygame.draw.line(self.screen, (0, 255, 255), (self.left_panel_w-1, 0), (self.left_panel_w-1, self.sh), 2)

        self.screen.blit(self.title_font.render("AI ALGORITHMS", True, (0, 200, 255)), (10, 20))
        
        algs = [("A* Search", 60), ("Greedy BFS", 100), ("IDA*", 140)]
        for label, y in algs:
            color = (0, 120, 180) if self.selected_algorithm == label else (50, 60, 70)
            pygame.draw.rect(self.screen, color, (10, y, 190, 35), border_radius=5)
            self.screen.blit(self.font.render(label, True, (255,255,255)), (20, y + 8))

        pygame.draw.rect(self.screen, (0, 200, 100), self.btn_run, border_radius=5)
        self.screen.blit(self.title_font.render("RUN AI", True, (0,0,0)), (70, 210))

        # TOÀN BỘ BẢNG THỐNG KÊ KẾT QUẢ ĐÃ ĐƯỢC CHUYỂN SANG ĐÂY
        self.screen.blit(self.title_font.render("THỐNG KÊ AI", True, (255, 255, 0)), (10, 275))
        
        stats = [
            (f"Chi phí: {self.path_cost}", (255, 215, 0)),
            (f"Duyệt: {self.nodes_expanded} nodes", (180, 220, 255)),
            (f"T/gian: {self.execution_time}", (180, 220, 255))
        ]
        stat_y = 310
        for txt, color in stats:
            self.screen.blit(self.font.render(txt, True, color), (20, stat_y))
            stat_y += 30

        # Gợi ý phím tắt nhỏ ở dưới bảng thống kê
        self.screen.blit(self.font.render("-> Phím G: Ẩn/Hiện Đồ Thị", True, (120, 130, 140)), (10, stat_y + 20))

        pygame.draw.rect(self.screen, (180, 60, 60), self.btn_back, border_radius=5)
        self.screen.blit(self.title_font.render("BACK", True, (255,255,255)), (75, self.sh - 50))