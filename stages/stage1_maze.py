# File: stages/stage1_maze.py
import pygame
import config
import random
import math
from algorithms.uninformed.bfs import bfs
from algorithms.uninformed.dfs import dfs  # THÊM IMPORT DFS
from algorithms.uninformed.ids import ids

class Stage1Maze:
    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager

        try:
            self.font = pygame.font.Font("assets/fonts/minecraft.ttf", 20)
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 26)
        except:
            self.font = pygame.font.SysFont("Arial", 18, bold=True)
            self.title_font = pygame.font.SysFont("Arial", 24, bold=True)

        self.c_bg      = getattr(config, 'COLOR_BG',      (25, 27, 29))
        self.c_panel   = getattr(config, 'COLOR_PANEL',   (38, 41, 44))
        self.c_text    = getattr(config, 'COLOR_TEXT',    (240, 240, 240))
        self.c_nobita  = getattr(config, 'COLOR_NOBITA',  (255, 80, 80))
        self.c_dora    = getattr(config, 'COLOR_DORA',    (50, 150, 255))
        self.c_path    = getattr(config, 'COLOR_PATH',    (255, 215, 0))
        self.c_visited = getattr(config, 'COLOR_VISITED', (46, 204, 113))

        # ID cố định cho Start và Goal
        self.start_node = 0
        self.goal_node  = 1
        self.nodes  = {}
        self.graph  = {}

        # THÊM: Biến lưu thuật toán đang được chọn
        self.selected_algorithm = "BFS"  # Mặc định là BFS

        self.generate_random_graph()

        self.path           = []
        self.visited_order  = []
        self.nodes_expanded = 0
        self.execution_time = "0.0 ms"
        self.path_cost      = 0
        
        sw = screen.get_width()
        sh = screen.get_height()
        try:
            bg_raw = pygame.image.load("assets/images/stage1_bg.png").convert()
            self.bg_image = pygame.transform.scale(bg_raw, (sw, sh))
        except FileNotFoundError:
            print("[WARN] Không tìm thấy background.png, dùng màu nền mặc định")
            self.bg_image = None
        except Exception as e:
            print(f"[ERROR] Load background thất bại: {e}")
            self.bg_image = None

    # =========================================================
    # GENERATE GRAPH - Giữ nguyên không đổi
    # =========================================================
    def generate_random_graph(self):
        random.seed(42)
        self.nodes = {}
        self.graph = {}

        sw = self.screen.get_width()
        sh = self.screen.get_height()
        if sw < 100 or sh < 100:
            sw, sh = 1920, 1080

        min_x = 240 + 60
        max_x = sw - 180 - 60
        min_y = 100
        max_y = sh - 120

        self.nodes[self.start_node] = (min_x + 40, sh // 2)
        self.nodes[self.goal_node]  = (max_x - 40, sh // 2)

        num_intermediates  = 23
        min_node_distance  = 95
        attempts           = 0

        while len(self.nodes) < (num_intermediates + 2) and attempts < 10000:
            x = random.randint(min_x + 140, max_x - 140)
            y = random.randint(min_y, max_y)

            too_close = False
            for nx, ny in self.nodes.values():
                if math.hypot(x - nx, y - ny) < min_node_distance:
                    too_close = True
                    break

            if not too_close:
                node_id = len(self.nodes)
                self.nodes[node_id] = (x, y)
            attempts += 1

        for n in self.nodes:
            self.graph[n] = []

        inter_ids = list(range(2, len(self.nodes)))

        for u in inter_ids:
            ux, uy = self.nodes[u]
            distances = []
            for v in inter_ids:
                if u != v:
                    vx, vy = self.nodes[v]
                    d = math.hypot(ux - vx, uy - vy)
                    distances.append((d, v))
            distances.sort()

            for i in range(min(3, len(distances))):
                v = distances[i][1]
                if v not in self.graph[u]: self.graph[u].append(v)
                if u not in self.graph[v]: self.graph[v].append(u)

        start_x, start_y = self.nodes[self.start_node]
        start_dists = sorted([
            (math.hypot(start_x - self.nodes[v][0], start_y - self.nodes[v][1]), v)
            for v in inter_ids
        ])
        for i in range(4):
            v = start_dists[i][1]
            if v not in self.graph[self.start_node]:
                self.graph[self.start_node].append(v)
            if self.start_node not in self.graph[v]:
                self.graph[v].append(self.start_node)

        goal_x, goal_y = self.nodes[self.goal_node]
        goal_dists = sorted([
            (math.hypot(goal_x - self.nodes[v][0], goal_y - self.nodes[v][1]), v)
            for v in inter_ids
        ])
        for i in range(3):
            v = goal_dists[i][1]
            if v not in self.graph[self.goal_node]:
                self.graph[self.goal_node].append(v)
            if self.goal_node not in self.graph[v]:
                self.graph[v].append(self.goal_node)

        # Khử đảo độc lập
        while True:
            visited = set()
            queue   = [2]
            visited.add(2)
            head = 0
            while head < len(queue):
                curr = queue[head]
                head += 1
                for neighbor in self.graph[curr]:
                    if neighbor in inter_ids and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            if len(visited) == len(inter_ids):
                break

            unvisited = set(inter_ids) - visited
            min_dist  = float('inf')
            best_pair = None

            for u in visited:
                ux, uy = self.nodes[u]
                for v in unvisited:
                    vx, vy = self.nodes[v]
                    d = math.hypot(ux - vx, uy - vy)
                    if d < min_dist:
                        min_dist  = d
                        best_pair = (u, v)

            if best_pair:
                u, v = best_pair
                self.graph[u].append(v)
                self.graph[v].append(u)

    # =========================================================
    # RESET KẾT QUẢ KHI ĐỔI THUẬT TOÁN
    # =========================================================
    def _reset_results(self):
        self.path           = []
        self.visited_order  = []
        self.nodes_expanded = 0
        self.execution_time = "0.0 ms"
        self.path_cost      = 0

    # =========================================================
    # HANDLE EVENTS - Thêm xử lý click chọn thuật toán
    # =========================================================
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                sh = self.screen.get_height()

                # Nút RUN AI
                run_btn  = pygame.Rect(20, sh - 130, 200, 45)
                # Nút BACK
                back_btn = pygame.Rect(20, sh - 70,  200, 45)

                # Nút chọn thuật toán trong panel trái
                bfs_btn = pygame.Rect(10, 80,  220, 40)
                dfs_btn = pygame.Rect(10, 130, 220, 40)
                ids_btn = pygame.Rect(10, 180, 220, 40)

                # --- Click chọn thuật toán ---
                if bfs_btn.collidepoint(event.pos):
                    self.selected_algorithm = "BFS"
                    self._reset_results()

                elif dfs_btn.collidepoint(event.pos):
                    self.selected_algorithm = "DFS"
                    self._reset_results()

                elif ids_btn.collidepoint(event.pos):
                    # IDS chưa implement - giữ placeholder
                    self.selected_algorithm = "IDS"
                    self._reset_results()

                # --- Click RUN AI ---
                elif run_btn.collidepoint(event.pos):
                    self._run_selected_algorithm()

                # --- Click BACK ---
                elif back_btn.collidepoint(event.pos):
                    self.stage_manager.change_stage("menu")

    def _run_selected_algorithm(self):
        """Gọi đúng thuật toán dựa trên lựa chọn hiện tại."""
        if self.selected_algorithm == "BFS":
            self.path, self.visited_order, self.nodes_expanded, self.execution_time = bfs(
                self.graph, self.start_node, self.goal_node
            )

        elif self.selected_algorithm == "DFS":
            self.path, self.visited_order, self.nodes_expanded, self.execution_time = dfs(
                self.graph, self.start_node, self.goal_node
            )

        elif self.selected_algorithm == "IDS":
            # ĐÃ IMPLEMENT - gọi IDS thật sự
            self.path, self.visited_order, self.nodes_expanded, self.execution_time = ids(
                self.graph, self.start_node, self.goal_node
            )

        # Tính path cost
        self.path_cost = len(self.path) + 1 if self.path else 0

    def update(self):
        pass

    # =========================================================
    # DRAW - Cập nhật panel trái hiển thị thuật toán được chọn
    # =========================================================
    def draw(self):
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(self.c_bg)
        sw = self.screen.get_width()
        sh = self.screen.get_height()

        # ── PANEL TRÁI ──────────────────────────────────────
        left_panel_width = 255
        left_surface = pygame.Surface((left_panel_width, sh), pygame.SRCALPHA)
        left_surface.fill((38, 41, 44, 150))
        self.screen.blit(left_surface, (0, 0))
        pygame.draw.line(self.screen, (80, 85, 90),
                         (left_panel_width, 0), (left_panel_width, sh), 2)

        self.screen.blit(
            self.title_font.render("AI ALGORITHMS", True, self.c_text),
            (15, 30)
        )

        # Danh sách thuật toán với highlight nếu được chọn
        algorithms = [
            ("BFS Graph", "BFS", pygame.Rect(10, 80,  220, 40)),
            ("DFS Graph", "DFS", pygame.Rect(10, 130, 220, 40)),
            ("IDS Graph", "IDS", pygame.Rect(10, 180, 220, 40)),
        ]

        for label, algo_key, btn_rect in algorithms:
            if self.selected_algorithm == algo_key:
                # Highlight = nền xanh đậm + chữ trắng
                pygame.draw.rect(self.screen, (40, 110, 190), btn_rect, border_radius=5)
                text_color = self.c_text
                prefix = "> "
            else:
                # Không chọn = chữ xám
                text_color = (130, 135, 140)
                prefix = "  "

            self.screen.blit(
                self.font.render(f"{prefix}{label}", True, text_color),
                (btn_rect.x + 10, btn_rect.y + 10)
            )

        # Hiển thị thuật toán đang chạy
        self.screen.blit(
            self.font.render(f"Mode: {self.selected_algorithm}", True, (180, 180, 60)),
            (15, 230)
        )

        # Nút RUN và BACK
        run_btn  = pygame.Rect(20, sh - 130, 200, 45)
        back_btn = pygame.Rect(20, sh - 70,  200, 45)

        pygame.draw.rect(self.screen, (46, 204, 113), run_btn,  border_radius=6)
        run_text = self.font.render("RUN AI", True, (255, 255, 255))
        self.screen.blit(run_text, run_text.get_rect(center=run_btn.center))

        pygame.draw.rect(self.screen, (231, 76, 60), back_btn, border_radius=6)
        back_text = self.font.render("BACK TO MENU", True, (255, 255, 255))
        self.screen.blit(back_text, back_text.get_rect(center=back_btn.center))

        # ── VẼ CẠNH ─────────────────────────────────────────
        drawn_edges = set()
        full_path = (
            [self.start_node] + self.path + [self.goal_node]
            if self.path else []
        )

        for node_id, neighbors in self.graph.items():
            for neighbor_id in neighbors:
                edge_pair = tuple(sorted((node_id, neighbor_id)))
                if edge_pair in drawn_edges:
                    continue
                drawn_edges.add(edge_pair)

                p1 = self.nodes[node_id]
                p2 = self.nodes[neighbor_id]
                edge_color = (65, 70, 75)
                thickness  = 2

                if len(full_path) > 1:
                    for idx in range(len(full_path) - 1):
                        a, b = full_path[idx], full_path[idx + 1]
                        if (a == node_id and b == neighbor_id) or \
                           (a == neighbor_id and b == node_id):
                            edge_color = self.c_path
                            thickness  = 4
                            break

                pygame.draw.line(self.screen, edge_color, p1, p2, thickness)

        # ── VẼ NODE ─────────────────────────────────────────
        for node_id, (x, y) in self.nodes.items():
            if node_id == self.start_node:
                node_color = self.c_dora
                radius     = 17
            elif node_id == self.goal_node:
                node_color = self.c_nobita
                radius     = 17
            elif node_id in self.path:
                node_color = self.c_path
                radius     = 13
            elif node_id in self.visited_order:
                node_color = self.c_visited
                radius     = 11
            else:
                node_color = (150, 155, 160)
                radius     = 8

            pygame.draw.circle(self.screen, node_color,  (x, y), radius)
            pygame.draw.circle(self.screen, (25, 25, 25), (x, y), radius, 2)

        # ── PANEL PHẢI (STATS) ───────────────────────────────
        right_panel_width = 180
        right_surface = pygame.Surface((right_panel_width, sh), pygame.SRCALPHA)
        right_surface.fill((38, 41, 44, 150))
        self.screen.blit(right_surface, (sw - right_panel_width, 0))
        pygame.draw.line(self.screen, (80, 85, 90),
                         (sw - right_panel_width, 0), (sw - right_panel_width, sh), 2)

        rx = sw - right_panel_width + 15
        self.screen.blit(self.title_font.render("STATS",                     True, self.c_text),        (rx, 30))
        self.screen.blit(self.font.render(f"Algo: {self.selected_algorithm}", True, (200, 202, 205)),    (rx, 75))
        self.screen.blit(self.font.render(f"Nodes: {self.nodes_expanded}",   True, (200, 202, 205)),    (rx, 120))
        self.screen.blit(self.font.render(f"Time: {self.execution_time}",    True, (200, 202, 205)),    (rx, 165))
        self.screen.blit(self.font.render(f"Cost: {self.path_cost}",         True, (200, 202, 205)),    (rx, 210))