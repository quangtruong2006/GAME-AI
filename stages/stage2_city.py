# File: stages/stage2_city.py
import pygame
import config
import os
import math
import json
import time
from collections import deque

# --- IMPORT 3 THUẬT TOÁN ĐỒ THỊ CHUẨN ---
from algorithms.informed.a_star import a_star
from algorithms.informed.greedy import greedy_search
from algorithms.informed.ida_star import ida_star

# =========================================================================
# LỚP THANH TRƯỢT SLIDER
# =========================================================================
class Slider:
    def __init__(self, rect, vmin, vmax, value, label=""):
        self.rect = pygame.Rect(rect)
        self.vmin = float(vmin)
        self.vmax = float(vmax)
        self.value = float(value)
        self.label = label
        self.dragging = False

    def _knob_x(self):
        t = (self.value - self.vmin) / (self.vmax - self.vmin) if self.vmax != self.vmin else 0.0
        t = max(0.0, min(1.0, t))
        return int(self.rect.x + t * self.rect.w)

    def handle_event(self, event):
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            knob = pygame.Rect(0, 0, 14, self.rect.h + 8)
            knob.center = (self._knob_x(), self.rect.centery)
            if self.rect.collidepoint(event.pos) or knob.collidepoint(event.pos):
                self.dragging = True
                x = event.pos[0]
                t = (x - self.rect.x) / self.rect.w if self.rect.w else 0.0
                t = max(0.0, min(1.0, t))
                self.value = self.vmin + t * (self.vmax - self.vmin)
                changed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            x = event.pos[0]
            t = (x - self.rect.x) / self.rect.w if self.rect.w else 0.0
            t = max(0.0, min(1.0, t))
            self.value = self.vmin + t * (self.vmax - self.vmin)
            changed = True
        return changed

    def draw(self, screen, font, color_track=(90, 95, 100), color_fill=(40, 110, 190), color_knob=(235, 235, 235), text_color=(230, 230, 230)):
        if self.label:
            txt = font.render(f"{self.label}: {int(self.value)}", True, text_color)
            screen.blit(txt, (self.rect.x, self.rect.y - 18))
        pygame.draw.rect(screen, color_track, self.rect, border_radius=6)
        t = (self.value - self.vmin) / (self.vmax - self.vmin) if self.vmax != self.vmin else 0.0
        t = max(0.0, min(1.0, t))
        fill = pygame.Rect(self.rect.x, self.rect.y, int(self.rect.w * t), self.rect.h)
        pygame.draw.rect(screen, color_fill, fill, border_radius=6)
        kx = self._knob_x()
        pygame.draw.circle(screen, color_knob, (kx, self.rect.centery), self.rect.h // 2 + 4)


# =========================================================================
# LỚP MÀN CHƠI CHẶNG 2 CHÍNH
# =========================================================================
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

        # --- DỮ LIỆU ĐỒ THỊ ---
        self.nodes = []      
        self.edges = {}      
        self.start_node = None
        self.goal_node = None
        self.map_file = "stage2_graph.json"
        
        self.left_panel_w = 220
        self.map_rect = pygame.Rect(self.left_panel_w, 0, self.sw - self.left_panel_w, self.sh)
        self._load_graph_data()

        # --- HÌNH ẢNH NHÂN VẬT ---
        self.start_img_raw = self._load_asset("assets/images/nobita.png")
        self.goal_img_raw = self._load_asset("assets/images/tram_tin_hieu.png")
        self.mouse_img_raw = self._load_asset("assets/images/mouse.png")

        # --- TRẠNG THÁI EDITOR ---
        self.current_tool = "ADD_NODE" 
        self.current_edge_type = 1 
        self.selected_node_for_edge = None
        self.show_editor = False 

        # --- TRẠNG THÁI AI ANIMATION ---
        self.blue = (255, 255, 0)
        self.green = (0, 255, 120)
        self.blue_thick = 6
        self.green_thick = 8
        
        self.phase = "idle"
        self.msg = "Ready."
        self.show_completion_menu = False
        
        self.search_speed = 520.0
        self.nobita_speed = 280.0
        self.slider_mouse = Slider(pygame.Rect(0,0,1,1), 150, 2500, self.search_speed, label="Search speed")
        self.slider_nobita = Slider(pygame.Rect(0,0,1,1), 40, 250, self.nobita_speed, label="Nobita speed")

        self._reset_results()
        self.selected_algorithm = "A* Search"
        self._last_ticks = pygame.time.get_ticks()
        self._load_background()

    # TẠO TỌA ĐỘ UI ĐỘNG CHO TOÀN BỘ MENU
    def _ui_rects(self):
        pad = 10
        btn_w = self.left_panel_w - 2 * pad
        y = 60
        gap = 8
        rects = {}
        
        h_alg = 30
        for alg in ["A* Search", "Greedy BFS", "IDA*"]:
            rects[alg] = pygame.Rect(pad, y, btn_w, h_alg)
            y += h_alg + gap
            
        y += 10
        h_act = 35
        for act in ["RUN AI", "CANCEL RUN", "RESET PATH"]:
            rects[act] = pygame.Rect(pad, y, btn_w, h_act)
            y += h_act + gap
            
        y += 15
        rects["slider_mouse"] = pygame.Rect(pad, y + 20, btn_w, 14)
        y += 50
        rects["slider_nobita"] = pygame.Rect(pad, y + 20, btn_w, 14)
        y += 50
        
        rects["edit_toggle"] = pygame.Rect(pad, y, btn_w, 30)
        y += 30 + gap
        
        rects["editor"] = {}
        if self.show_editor:
            h_ed = 26
            ed_gap = 6
            tools = ["ADD_NODE", "CONNECT", "DEL_NODE", "DEL_EDGE", "SET_START", "SET_GOAL"]
            for t in tools:
                rects["editor"][t] = pygame.Rect(pad, y, btn_w, h_ed)
                y += h_ed + ed_gap
            rects["editor"]["SAVE"] = pygame.Rect(pad, y + 5, btn_w, 30)
            
        rects["back"] = pygame.Rect(pad, self.sh - 50, btn_w, 40)
        return rects

    def _load_asset(self, path):
        if os.path.exists(path):
            try: return pygame.image.load(path).convert_alpha()
            except: return None
        return None

    def _load_background(self):
        bg_path = os.path.join("assets", "images", "stage2_bg.png")
        if not os.path.exists(bg_path): bg_path = os.path.join("assets", "images", "stage2_bg.jpg")
        if os.path.exists(bg_path):
            raw = pygame.image.load(bg_path).convert_alpha()
            self.bg_image = pygame.transform.smoothscale(raw, (self.map_rect.width, self.map_rect.height))
        else: self.bg_image = None

    def _get_nodes_px(self):
        return [(int(self.map_rect.x + rx * self.map_rect.width), int(self.map_rect.y + ry * self.map_rect.height)) for rx, ry in self.nodes]

    def _save_graph_data(self):
        data = {"nodes": self.nodes, "edges": self.edges, "start": self.start_node, "goal": self.goal_node}
        with open(self.map_file, 'w') as f: json.dump(data, f)
        self.msg = "Saved map successfully."

    def _load_graph_data(self):
        if os.path.exists(self.map_file):
            with open(self.map_file, 'r') as f:
                data = json.load(f)
                self.nodes = []
                for n in data.get("nodes", []):
                    if n[0] > 2.0 or n[1] > 2.0:
                        rx = (n[0] - 210) / (self.sw - 210)
                        ry = n[1] / self.sh
                        self.nodes.append((rx, ry))
                    else: self.nodes.append(tuple(n))
                
                raw_edges = data.get("edges", {})
                self.edges = {}
                for k, neighbors in raw_edges.items():
                    u = int(k)
                    self.edges[u] = {}
                    for nk, v_data in neighbors.items():
                        v_data = dict(v_data)
                        if v_data.get("type") == 8:
                            v_data["cost"] = 1 
                        self.edges[u][int(nk)] = v_data
                self.start_node = data.get("start")
                self.goal_node = data.get("goal")

    def _reset_results(self):
        self.blue_edges_done = set()
        self.green_edges_done = set()
        self.path = []
        self.visited_order = []
        self.path_cost = 0
        self.nodes_expanded = 0
        self.execution_time = "0.0 ms"
        self.mouse_visible = False
        self.mouse_route = []
        self.mouse_seg = 0
        self.mouse_t = 0.0
        self.solution_path = []
        self.nobita_seg = 0
        self.nobita_t = 0.0
        self.nobita_mode = "at_start"
        self.phase = "idle"
        self.msg = "Reset Path."

    def _get_shortest_path_unweighted(self, start, end):
        if start == end: return [start]
        q = deque([start])
        prev = {start: None}
        while q:
            curr = q.popleft()
            if curr == end: break
            if curr in self.edges:
                for nb in self.edges[curr]:
                    if nb not in prev:
                        prev[nb] = curr
                        q.append(nb)
        if end not in prev: return [start, end]
        path = []
        c = end
        while c is not None:
            path.append(c)
            c = prev[c]
        path.reverse()
        return path

    def _run_ai(self):
        if self.start_node is None or self.goal_node is None:
            self.msg = "Error: Missing N or S!"
            return
        self._reset_results()
        self.show_editor = False
        nodes_px = self._get_nodes_px()

        if self.selected_algorithm == "A* Search":
            p, v, n, t, c = a_star(nodes_px, self.edges, self.start_node, self.goal_node)
        elif self.selected_algorithm == "Greedy BFS":
            p, v, n, t, c = greedy_search(nodes_px, self.edges, self.start_node, self.goal_node)
        elif self.selected_algorithm == "IDA*":
            p, v, n, t, c = ida_star(nodes_px, self.edges, self.start_node, self.goal_node)

        self.execution_time = t
        self.nodes_expanded = n
        self.solution_path = p
        self.path_cost = c

        targets = [self.start_node] + list(v)
        if p: targets.append(self.goal_node)
        
        route = [targets[0]]
        for i in range(len(targets) - 1):
            seg = self._get_shortest_path_unweighted(targets[i], targets[i+1])
            route.extend(seg[1:])
        
        self.mouse_route = route
        self.mouse_seg = 0
        self.mouse_t = 0.0
        self.mouse_visible = True
        self.phase = "searching"
        self.msg = f"Searching ({self.selected_algorithm})..."

    def handle_events(self, events):
        ui = self._ui_rects()
        self.slider_mouse.rect = ui["slider_mouse"]
        self.slider_nobita.rect = ui["slider_nobita"]

        for event in events:
            if self.show_completion_menu:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    cx, cy = self.sw // 2, self.sh // 2
                    if pygame.Rect(cx - 100, cy - 20, 200, 40).collidepoint(event.pos):
                        self.stage_manager.stages["stage_select"].trigger_unlock_animation("stage3")
                        self.stage_manager.change_stage("stage_select")
                    elif pygame.Rect(cx - 100, cy + 30, 200, 40).collidepoint(event.pos):
                        self._reset_results()
                    elif pygame.Rect(cx - 100, cy + 80, 200, 40).collidepoint(event.pos):
                        self.stage_manager.change_stage("stage_select")
                continue
            if self.slider_mouse.handle_event(event): self.search_speed = self.slider_mouse.value
            if self.slider_nobita.handle_event(event): self.nobita_speed = self.slider_nobita.value

            if event.type == pygame.KEYDOWN and self.show_editor and self.current_tool == "CONNECT":
                if event.key in (pygame.K_1, pygame.K_KP1): self.current_edge_type = 1
                elif event.key in (pygame.K_2, pygame.K_KP2): self.current_edge_type = 2
                elif event.key in (pygame.K_3, pygame.K_KP3): self.current_edge_type = 3
                elif event.key in (pygame.K_8, pygame.K_KP8): self.current_edge_type = 8

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if event.pos[0] < self.left_panel_w:
                    if ui["back"].collidepoint(event.pos): self.stage_manager.change_stage("stage_select")
                    elif ui["RUN AI"].collidepoint(event.pos): self._run_ai()
                    elif ui["CANCEL RUN"].collidepoint(event.pos): 
                        self.phase = "idle"; self.msg = "Canceled."
                    elif ui["RESET PATH"].collidepoint(event.pos): self._reset_results()
                    
                    for alg in ["A* Search", "Greedy BFS", "IDA*"]:
                        if ui[alg].collidepoint(event.pos):
                            self.selected_algorithm = alg
                            self._reset_results()

                    if ui["edit_toggle"].collidepoint(event.pos):
                        if self.phase in ("searching", "returning", "nobita_moving"): return
                        self.show_editor = not self.show_editor
                        continue
                    if self.show_editor:
                        for tool in ["ADD_NODE", "CONNECT", "DEL_NODE", "DEL_EDGE", "SET_START", "SET_GOAL"]:
                            if ui["editor"][tool].collidepoint(event.pos):
                                self.current_tool = tool
                                self.selected_node_for_edge = None
                        if ui["editor"]["SAVE"].collidepoint(event.pos): self._save_graph_data()

                elif self.map_rect.collidepoint(event.pos) and self.show_editor and self.phase == "idle":
                    nodes_px = self._get_nodes_px()
                    clicked_node_idx = None
                    for i, (nx, ny) in enumerate(nodes_px):
                        if math.hypot(nx - event.pos[0], ny - event.pos[1]) <= 12: clicked_node_idx = i; break

                    if self.current_tool == "ADD_NODE" and clicked_node_idx is None:
                        rx = (event.pos[0] - self.map_rect.x) / self.map_rect.width
                        ry = (event.pos[1] - self.map_rect.y) / self.map_rect.height
                        self.nodes.append((rx, ry)); self.edges[len(self.nodes) - 1] = {}
                    elif self.current_tool == "CONNECT" and clicked_node_idx is not None:
                        if self.selected_node_for_edge is None: self.selected_node_for_edge = clicked_node_idx
                        elif self.selected_node_for_edge != clicked_node_idx:
                            u, v = self.selected_node_for_edge, clicked_node_idx
                            dist = int(math.hypot(nodes_px[u][0] - nodes_px[v][0], nodes_px[u][1] - nodes_px[v][1]))
                            cost = dist
                            if self.current_edge_type == 2: cost = dist * 2
                            elif self.current_edge_type == 3: cost = dist * 4
                            elif self.current_edge_type == 8: cost = 1
                            self.edges[u][v] = {"cost": cost, "type": self.current_edge_type}
                            self.edges[v][u] = {"cost": cost, "type": self.current_edge_type}
                            self.selected_node_for_edge = None 
                    elif self.current_tool == "DEL_NODE" and clicked_node_idx is not None:
                        del_idx = clicked_node_idx
                        self.nodes.pop(del_idx)
                        if del_idx in self.edges: del self.edges[del_idx]
                        for u in list(self.edges.keys()):
                            if del_idx in self.edges[u]: del self.edges[u][del_idx]
                        new_edges = {}
                        for old_u, neighbors in self.edges.items():
                            new_u = old_u - 1 if old_u > del_idx else old_u
                            new_edges[new_u] = {}
                            for old_v, data in neighbors.items():
                                new_v = old_v - 1 if old_v > del_idx else old_v
                                new_edges[new_u][new_v] = data
                        self.edges = new_edges
                        if self.start_node == del_idx: self.start_node = None
                        elif self.start_node is not None and self.start_node > del_idx: self.start_node -= 1
                        if self.goal_node == del_idx: self.goal_node = None
                        elif self.goal_node is not None and self.goal_node > del_idx: self.goal_node -= 1
                    elif self.current_tool == "DEL_EDGE" and clicked_node_idx is not None:
                        if self.selected_node_for_edge is None: self.selected_node_for_edge = clicked_node_idx
                        elif self.selected_node_for_edge != clicked_node_idx:
                            u, v = self.selected_node_for_edge, clicked_node_idx
                            if u in self.edges and v in self.edges[u]: del self.edges[u][v]
                            if v in self.edges and u in self.edges[v]: del self.edges[v][u]
                            self.selected_node_for_edge = None
                    elif self.current_tool == "SET_START" and clicked_node_idx is not None: self.start_node = clicked_node_idx
                    elif self.current_tool == "SET_GOAL" and clicked_node_idx is not None: self.goal_node = clicked_node_idx

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging_search = False
                self.dragging_nobita = False

    def update(self):
        now = pygame.time.get_ticks()
        dt = max(0.0, (now - self._last_ticks) / 1000.0)
        self._last_ticks = now

        if self.phase not in ("searching", "returning", "nobita_moving"): return
        nodes_px = self._get_nodes_px()

        def step_route(route, seg_idx, t, speed_px):
            if not route or seg_idx >= len(route) - 1: return seg_idx, t, True, None
            a, b = route[seg_idx], route[seg_idx + 1]
            ax, ay = nodes_px[a]; bx, by = nodes_px[b]
            seg_len = math.hypot(bx - ax, by - ay)
            if seg_len < 1: t = 1.0
            else: t += (speed_px * dt) / seg_len
            if t >= 1.0: return seg_idx + 1, 0.0, False, (a, b)
            return seg_idx, t, False, None

        if self.phase == "searching":
            self.mouse_seg, self.mouse_t, done, finished_edge = step_route(self.mouse_route, self.mouse_seg, self.mouse_t, self.search_speed)
            if finished_edge:
                a, b = finished_edge
                self.blue_edges_done.add((a, b) if a < b else (b, a))
            if done or (self.mouse_route and self.mouse_seg >= len(self.mouse_route) - 1):
                self.mouse_visible = False
                if not self.solution_path:
                    self.phase = "completed"; self.msg = "No path found."
                    return
                self.phase = "returning"; self.msg = "Mouse returning solution..."
                self.mouse_route = list(reversed(self.solution_path))
                self.mouse_seg = 0; self.mouse_t = 0.0; self.mouse_visible = True

        elif self.phase == "returning":
            self.mouse_seg, self.mouse_t, done, finished_edge = step_route(self.mouse_route, self.mouse_seg, self.mouse_t, self.search_speed)
            if finished_edge:
                a, b = finished_edge
                self.green_edges_done.add((a, b) if a < b else (b, a))
            if done or (self.mouse_route and self.mouse_seg >= len(self.mouse_route) - 1):
                self.mouse_visible = False
                self.phase = "nobita_moving"; self.msg = "Nobita moving..."
                self.nobita_mode = "moving"; self.nobita_seg = 0; self.nobita_t = 0.0

        elif self.phase == "nobita_moving":
            self.nobita_seg, self.nobita_t, done, finished_edge = step_route(self.solution_path, self.nobita_seg, self.nobita_t, self.nobita_speed)
            if done or (self.solution_path and self.nobita_seg >= len(self.solution_path) - 1):
                self.phase = "completed"; self.msg = "Completed."; self.nobita_mode = "at_goal"
                self.stage_manager.unlock_stage("stage3")
                self.show_completion_menu = True

    def draw(self):
        ui = self._ui_rects()
        
        self.screen.fill(self.c_bg)
        if self.bg_image: self.screen.blit(self.bg_image, (self.map_rect.x, self.map_rect.y))
        nodes_px = self._get_nodes_px()

        if self.show_editor:
            for u, neighbors in self.edges.items():
                for v, data in neighbors.items():
                    if u < v:
                        t = data["type"]
                        color = (0, 255, 255); width = 4
                        if t == 2: color = (150, 150, 150); width = 2
                        elif t == 3: color = (255, 0, 0); width = 4
                        elif t == 8: color = (255, 0, 255); width = 6
                        pygame.draw.line(self.screen, color, nodes_px[u], nodes_px[v], width)
                        pygame.draw.line(self.screen, (0, 0, 0), nodes_px[u], nodes_px[v], 1)

        for (a, b) in self.blue_edges_done:
            pygame.draw.line(self.screen, self.blue, nodes_px[a], nodes_px[b], self.blue_thick)

        for (a, b) in self.green_edges_done:
            pygame.draw.line(self.screen, self.green, nodes_px[a], nodes_px[b], self.green_thick)

        def draw_partial(route, seg_idx, t, color, thick):
            if not route or seg_idx >= len(route) - 1: return None
            a, b = route[seg_idx], route[seg_idx + 1]
            ax, ay = nodes_px[a]; bx, by = nodes_px[b]
            tt = max(0.0, min(1.0, t))
            cx, cy = ax + (bx - ax) * tt, ay + (by - ay) * tt
            pygame.draw.line(self.screen, color, (ax, ay), (cx, cy), thick)
            return (cx, cy)

        mouse_pos = None
        if self.mouse_visible:
            col = self.blue if self.phase == "searching" else self.green
            thick = self.blue_thick if self.phase == "searching" else self.green_thick
            mouse_pos = draw_partial(self.mouse_route, self.mouse_seg, self.mouse_t, col, thick)

        def blit_scaled(img_raw, center_pos, target_h, fallback_color):
            if center_pos is None: return
            if img_raw:
                w, h = img_raw.get_size()
                scale = target_h / h
                img = pygame.transform.smoothscale(img_raw, (int(w * scale), int(h * scale)))
                self.screen.blit(img, img.get_rect(center=center_pos))
            else:
                pygame.draw.circle(self.screen, fallback_color, center_pos, 10)
                pygame.draw.circle(self.screen, (0,0,0), center_pos, 10, 2)

        char_h, mouse_h = max(40, int(self.sh * 0.08)), max(22, int(self.sh * 0.045))
        
        if self.goal_node is not None: blit_scaled(self.goal_img_raw, nodes_px[self.goal_node], char_h, self.c_dora)

        nobita_pos = nodes_px[self.start_node] if self.start_node is not None else None
        if self.nobita_mode == "at_goal": nobita_pos = nodes_px[self.goal_node]
        elif self.phase == "nobita_moving" and self.solution_path and self.nobita_seg < len(self.solution_path) - 1:
            a, b = self.solution_path[self.nobita_seg], self.solution_path[self.nobita_seg + 1]
            tt = max(0.0, min(1.0, self.nobita_t))
            nobita_pos = (nodes_px[a][0] + (nodes_px[b][0] - nodes_px[a][0]) * tt, nodes_px[a][1] + (nodes_px[b][1] - nodes_px[a][1]) * tt)
        if nobita_pos: blit_scaled(self.start_img_raw, nobita_pos, char_h, self.c_nobita)

        if self.mouse_visible:
            if mouse_pos is None and self.mouse_route: mouse_pos = nodes_px[self.mouse_route[min(self.mouse_seg, len(self.mouse_route)-1)]]
            blit_scaled(self.mouse_img_raw, mouse_pos, mouse_h, (255, 255, 0))

        if self.show_editor:
            for i, pos in enumerate(nodes_px):
                pygame.draw.circle(self.screen, (200, 200, 200) if i not in (self.start_node, self.goal_node) else (255,255,255), pos, 5)
                pygame.draw.circle(self.screen, (0, 0, 0), pos, 5, 1)

        # ── VẼ MENU TRÁI ĐỒNG BỘ ──
        pygame.draw.rect(self.screen, (27, 40, 56), (0, 0, self.left_panel_w, self.sh))
        pygame.draw.line(self.screen, (0, 255, 255), (self.left_panel_w-1, 0), (self.left_panel_w-1, self.sh), 2)

        self.screen.blit(self.title_font.render("AI", True, (200, 220, 255)), (10, 10))
        self.screen.blit(self.title_font.render("ALGORITHMS", True, (200, 220, 255)), (10, 30))
        
        for alg in ["A* Search", "Greedy BFS", "IDA*"]:
            color = (50, 150, 220) if self.selected_algorithm == alg else (60, 75, 90)
            self._draw_btn_static(ui[alg], alg, color)

        self._draw_btn_static(ui["RUN AI"], "RUN AI", (46, 204, 113))
        self._draw_btn_static(ui["CANCEL RUN"], "CANCEL RUN", (231, 76, 60))
        self._draw_btn_static(ui["RESET PATH"], "RESET PATH", (155, 89, 182))

        self.slider_mouse.draw(self.screen, self.font)
        self.slider_nobita.draw(self.screen, self.font)

        toggle_txt = "[-]" if self.show_editor else "[+]"
        self._draw_btn_static(ui["edit_toggle"], f"EDIT MAP  {toggle_txt}", (52, 73, 94))

        if self.show_editor:
            tool_labels = {"ADD_NODE": "Thêm Nút", "CONNECT": "Nối Đường", "DEL_NODE": "Xóa Nút", 
                           "DEL_EDGE": "Xóa Cạnh", "SET_START": "Đặt N", "SET_GOAL": "Đặt S"}
            for t_id, text in tool_labels.items():
                color = (50, 150, 220) if self.current_tool == t_id else (60, 75, 90)
                self._draw_btn_static(ui["editor"][t_id], text, color)
            self._draw_btn_static(ui["editor"]["SAVE"], "SAVE MAP", (230, 126, 34))

        stats_y = self.sh - 180
        info_color = (200, 220, 200)
        self.screen.blit(self.font.render(f"Phase: {self.phase}", True, info_color), (10, stats_y))
        self.screen.blit(self.font.render(f"Nodes: {self.nodes_expanded}", True, info_color), (10, stats_y + 20))
        self.screen.blit(self.font.render(f"Time: {self.execution_time}", True, info_color), (10, stats_y + 40))
        self.screen.blit(self.font.render(f"Cost: {self.path_cost}", True, info_color), (10, stats_y + 60))
        self.screen.blit(self.font.render(f"{self.msg}", True, (255, 215, 0)), (10, stats_y + 85))

        self._draw_btn_static(ui["back"], "BACK", (231, 76, 60))
        if self.show_completion_menu:
            # Lớp phủ mờ đen
            overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180)) # Số 180 là độ mờ
            self.screen.blit(overlay, (0, 0))
            
            # Khung chữ nhật ở giữa
            cx, cy = self.sw // 2, self.sh // 2
            pygame.draw.rect(self.screen, (40, 50, 60), (cx - 150, cy - 100, 300, 250), border_radius=10)
            pygame.draw.rect(self.screen, (0, 255, 255), (cx - 150, cy - 100, 300, 250), width=2, border_radius=10)
            
            # Tiêu đề
            title = self.title_font.render("STAGE CLEARED!", True, (255, 215, 0))
            self.screen.blit(title, title.get_rect(center=(cx, cy - 60)))
            
            # Vẽ 3 nút bấm
            self._draw_btn_static(pygame.Rect(cx - 100, cy - 20, 200, 40), "NEXT STAGE", (46, 204, 113))
            self._draw_btn_static(pygame.Rect(cx - 100, cy + 30, 200, 40), "REPLAY", (52, 152, 219))
            self._draw_btn_static(pygame.Rect(cx - 100, cy + 80, 200, 40), "MAIN MENU", (231, 76, 60))

    def _draw_btn_static(self, rect, text, color):
        pygame.draw.rect(self.screen, color, rect, border_radius=5)
        txt = self.font.render(text, True, (255,255,255))
        self.screen.blit(txt, txt.get_rect(center=rect.center))