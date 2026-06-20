import pygame
import config
import math
import json
import os
import time
from collections import deque

from algorithms.uninformed.ids import ids  # fallback cho IDS


# =========================
# Simple UI: Slider
# =========================
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
                # cập nhật value theo vị trí click ngay lập tức
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

    def draw(self, screen, font,
             color_track=(90, 95, 100),
             color_fill=(40, 110, 190),
             color_knob=(235, 235, 235),
             text_color=(230, 230, 230)):
        # label
        if self.label:
            txt = font.render(f"{self.label}: {int(self.value)}", True, text_color)
            screen.blit(txt, (self.rect.x, self.rect.y - 18))

        # track
        pygame.draw.rect(screen, color_track, self.rect, border_radius=6)

        # fill
        t = (self.value - self.vmin) / (self.vmax - self.vmin) if self.vmax != self.vmin else 0.0
        t = max(0.0, min(1.0, t))
        fill = pygame.Rect(self.rect.x, self.rect.y, int(self.rect.w * t), self.rect.h)
        pygame.draw.rect(screen, color_fill, fill, border_radius=6)

        # knob
        kx = self._knob_x()
        pygame.draw.circle(screen, color_knob, (kx, self.rect.centery), self.rect.h // 2 + 4)


class Stage1Maze:
    """
    - EDIT MAP: mở/đóng nhóm nút chỉnh map
    - RUN AI:
        + Mouse search (blue)
        + Mouse returns solution (green) về Start
        + Nobita đi từ Start -> Goal theo solution (green) và đứng ở Goal
    - CANCEL RUN: dừng animation, giữ vệt hiện tại
    - RESET PATH: xóa vệt + đưa Nobita về start
    - 2 sliders realtime: mouse speed, nobita speed
    """

    def __init__(self, screen, stage_manager):
        self.screen = screen
        self.stage_manager = stage_manager

        # Fonts
        try:
            self.font = pygame.font.Font("assets/fonts/minecraft.ttf", 18)
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 22)
        except:
            self.font = pygame.font.SysFont("Arial", 16, bold=True)
            self.title_font = pygame.font.SysFont("Arial", 20, bold=True)

        self.c_bg   = getattr(config, "COLOR_BG", (25, 27, 29))
        self.c_text = getattr(config, "COLOR_TEXT", (240, 240, 240))

        self.left_panel_width = 150
        self.pad = 10

        # background
        self.bg_raw = None
        try:
            self.bg_raw = pygame.image.load("assets/images/stage1_bg.png").convert()
        except Exception as e:
            print("[WARN] Cannot load assets/images/stage1_bg.png:", e)

        # characters/icons
        self.start_char_path = "assets/images/char_start.png"  # Nobita
        self.goal_char_path  = "assets/images/char_goal.png"
        self.mouse_icon_path = "assets/images/mouse.png"

        self.start_img_raw = None
        self.goal_img_raw = None
        self.mouse_img_raw = None

        try:
            self.start_img_raw = pygame.image.load(self.start_char_path).convert_alpha()
        except Exception as e:
            print("[WARN] Cannot load:", self.start_char_path, e)
        try:
            self.goal_img_raw = pygame.image.load(self.goal_char_path).convert_alpha()
        except Exception as e:
            print("[WARN] Cannot load:", self.goal_char_path, e)
        try:
            self.mouse_img_raw = pygame.image.load(self.mouse_icon_path).convert_alpha()
        except Exception as e:
            print("[WARN] Cannot load:", self.mouse_icon_path, e)

        # map save
        self.map_file = "assets/maps/stage1_map.json"

        # ===== Graph data =====
        self.start_node = 0
        self.goal_node = 1
        self.road_nodes_rel = {
            0: (0.10, 0.60),
            1: (0.90, 0.55),
        }
        self.road_edges = set()  # (a,b) a<b

        # editor
        self.map_edit_open = False
        self.tool = None  # add/connect/del_node/del_edge/set_start/set_goal
        self.edge_from = None

        self.node_pick_radius = 14
        self.edge_pick_threshold = 8

        # algorithm select
        self.selected_algorithm = "BFS"

        # draw style for trails
        self.blue = (52, 152, 219)
        self.green = (46, 204, 113)
        self.blue_thick = 7
        self.green_thick = 9

        # trails
        self.blue_edges_done = set()
        self.green_edges_done = set()

        # phase:
        # idle, searching, returning, nobita_moving, done
        self.phase = "idle"
        self.msg = ""

        # stats
        self.nodes_expanded = 0
        self.execution_time = "0.0 ms"
        self.path_cost = 0

        # speeds (sliders control)
        self.mouse_speed_px = 520.0
        self.nobita_speed_px = 280.0

        # ===== FIX: init sliders in __init__ so draw() never sees None =====
        self.slider_mouse = Slider(pygame.Rect(0, 0, 1, 14), 150, 2500, self.mouse_speed_px,  label="Search speed")
        self.slider_nobita = Slider(pygame.Rect(0, 0, 1, 14), 40, 250,  self.nobita_speed_px, label="Nobita speed")

        # mouse route movement (searching + returning)
        self.mouse_route = []
        self.mouse_seg = 0
        self.mouse_t = 0.0
        self.mouse_visible = False

        # solution path (start..goal)
        self.solution_path = []
        self.nobita_seg = 0
        self.nobita_t = 0.0
        self.nobita_mode = "at_start"  # at_start, moving, at_goal

        # time
        self._last_ticks = pygame.time.get_ticks()

        # load map if exists
        if os.path.exists(self.map_file):
            self.load_map(self.map_file)

    # =========================
    # Helpers
    # =========================
    def _dt(self):
        now = pygame.time.get_ticks()
        dt_ms = now - self._last_ticks
        self._last_ticks = now
        return max(0.0, dt_ms / 1000.0)

    def _get_map_rect(self):
        sw, sh = self.screen.get_size()
        return pygame.Rect(self.left_panel_width, 0, sw - self.left_panel_width, sh)

    def _rel_to_px(self, rx, ry, map_rect):
        return (int(map_rect.x + rx * map_rect.w), int(map_rect.y + ry * map_rect.h))

    def _nodes_px(self, map_rect):
        return {nid: self._rel_to_px(rx, ry, map_rect) for nid, (rx, ry) in self.road_nodes_rel.items()}

    def _get_node_at_pos(self, pos, map_rect):
        nodes_px = self._nodes_px(map_rect)
        for nid, (px, py) in nodes_px.items():
            if math.hypot(pos[0] - px, pos[1] - py) <= self.node_pick_radius:
                return nid
        return None

    def _point_segment_distance(self, p, a, b):
        px, py = p
        ax, ay = a
        bx, by = b
        abx, aby = bx - ax, by - ay
        apx, apy = px - ax, py - ay
        ab_len2 = abx * abx + aby * aby
        if ab_len2 == 0:
            return math.hypot(px - ax, py - ay)
        t = (apx * abx + apy * aby) / ab_len2
        t = max(0.0, min(1.0, t))
        cx = ax + t * abx
        cy = ay + t * aby
        return math.hypot(px - cx, py - cy)

    def _get_edge_at_pos(self, pos, map_rect):
        nodes_px = self._nodes_px(map_rect)
        best_edge = None
        best_d = float("inf")
        for (a, b) in self.road_edges:
            if a not in nodes_px or b not in nodes_px:
                continue
            d = self._point_segment_distance(pos, nodes_px[a], nodes_px[b])
            if d < best_d:
                best_d = d
                best_edge = (a, b)
        if best_edge is not None and best_d <= self.edge_pick_threshold:
            return best_edge
        return None

    def _build_graph(self):
        g = {nid: [] for nid in self.road_nodes_rel.keys()}
        for (a, b) in self.road_edges:
            if a in g and b in g:
                g[a].append(b)
                g[b].append(a)
        for k in g:
            g[k].sort()
        return g

    # -----------------------
    # BFS/DFS trace to get visited_order + solution path (start..goal)
    # -----------------------
    def _bfs_trace(self, graph, start, goal):
        start_time = time.time()
        q = deque([start])
        reached = {start}
        parent = {start: None}
        visited_order = []
        found = False

        while q:
            curr = q.popleft()
            if curr != start and curr != goal:
                visited_order.append(curr)

            for nb in graph[curr]:
                if nb not in reached:
                    reached.add(nb)
                    parent[nb] = curr
                    if nb == goal:
                        found = True
                        q.clear()
                        break
                    q.append(nb)

        path = []
        if found:
            x = goal
            while x is not None:
                path.append(x)
                x = parent.get(x)
            path.reverse()  # start..goal

        exec_ms = (time.time() - start_time) * 1000
        return path, visited_order, parent, f"{exec_ms:.2f} ms"

    def _dfs_trace(self, graph, start, goal):
        start_time = time.time()
        stack = [start]
        reached = {start}
        parent = {start: None}
        visited_order = []
        found = False

        while stack:
            curr = stack.pop()
            if curr != start and curr != goal:
                visited_order.append(curr)

            for nb in reversed(graph[curr]):
                if nb not in reached:
                    reached.add(nb)
                    parent[nb] = curr
                    if nb == goal:
                        found = True
                        stack.clear()
                        break
                    stack.append(nb)

        path = []
        if found:
            x = goal
            while x is not None:
                path.append(x)
                x = parent.get(x)
            path.reverse()

        exec_ms = (time.time() - start_time) * 1000
        return path, visited_order, parent, f"{exec_ms:.2f} ms"

    def _tree_route(self, u, v, parent):
        """Route along parent-tree edges: u -> ... -> LCA -> ... -> v"""
        if u == v:
            return [u]

        def path_to_root(x):
            out = []
            while x is not None:
                out.append(x)
                x = parent.get(x)
            return out

        pu = path_to_root(u)
        pv = path_to_root(v)
        set_pu = set(pu)

        lca = None
        for n in pv:
            if n in set_pu:
                lca = n
                break
        if lca is None:
            return [u, v]

        up = pu[:pu.index(lca) + 1]
        down = list(reversed(pv[:pv.index(lca)]))
        return up + down

    def _shortest_path(self, graph, start, goal):
        q = deque([start])
        prev = {start: None}
        while q:
            x = q.popleft()
            if x == goal:
                break
            for nb in graph[x]:
                if nb not in prev:
                    prev[nb] = x
                    q.append(nb)
        if goal not in prev:
            return [start, goal]
        out = []
        cur = goal
        while cur is not None:
            out.append(cur)
            cur = prev[cur]
        out.reverse()
        return out

    # =========================
    # Run / Cancel / Reset
    # =========================
    def cancel_run(self):
        # dừng animation, giữ trails hiện tại
        self.phase = "idle"
        self.mouse_visible = False
        self.mouse_route = []
        self.msg = "Canceled."

    def reset_path(self):
        # xóa trails + đưa Nobita về start, cho chạy lại
        self.blue_edges_done.clear()
        self.green_edges_done.clear()

        self.phase = "idle"
        self.msg = "Reset."

        self.nodes_expanded = 0
        self.execution_time = "0.0 ms"
        self.path_cost = 0

        self.mouse_visible = False
        self.mouse_route = []
        self.mouse_seg = 0
        self.mouse_t = 0.0

        self.solution_path = []
        self.nobita_seg = 0
        self.nobita_t = 0.0
        self.nobita_mode = "at_start"

    def run_selected_algorithm(self):
        self.reset_path()  # reset trails trước khi chạy

        graph = self._build_graph()
        if self.start_node not in graph or self.goal_node not in graph:
            self.msg = "Start/Goal not in graph!"
            return
        if self.start_node == self.goal_node:
            self.msg = "Start == Goal"
            self.phase = "done"
            self.nobita_mode = "at_goal"
            return

        visited_order = []

        if self.selected_algorithm == "BFS":
            path, visited_order, parent, exec_time = self._bfs_trace(graph, self.start_node, self.goal_node)
        elif self.selected_algorithm == "DFS":
            path, visited_order, parent, exec_time = self._dfs_trace(graph, self.start_node, self.goal_node)
        else:
            # IDS fallback: dùng ids.py (no parent)
            path_mid, visited_order, nodes_expanded, exec_time = ids(graph, self.start_node, self.goal_node)
            path = [self.start_node] + path_mid + ([self.goal_node] if path_mid else [])
            parent = {self.start_node: None}

        self.execution_time = exec_time
        self.nodes_expanded = len(visited_order)
        self.solution_path = path if len(path) >= 2 else []
        self.path_cost = (len(self.solution_path) - 1) if self.solution_path else 0

        # mouse search route: start -> visited nodes -> goal (if found)
        targets = [self.start_node] + list(visited_order)
        if self.solution_path:
            targets.append(self.goal_node)

        route = [targets[0]]
        if self.selected_algorithm in ("BFS", "DFS"):
            for i in range(len(targets) - 1):
                seg = self._tree_route(targets[i], targets[i + 1], parent)
                route.extend(seg[1:])
        else:
            for i in range(len(targets) - 1):
                seg = self._shortest_path(graph, targets[i], targets[i + 1])
                route.extend(seg[1:])

        self.mouse_route = route
        self.mouse_seg = 0
        self.mouse_t = 0.0
        self.mouse_visible = True

        self.phase = "searching"
        self.msg = f"Searching ({self.selected_algorithm})..."

        # unlock stage2 nếu có đường
        if self.solution_path:
            try:
                self.stage_manager.unlock_stage("stage2")
            except:
                pass

    # =========================
    # Save / Load
    # =========================
    def save_map(self, filename=None):
        if filename is None:
            filename = self.map_file
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        data = {
            "nodes_rel": {str(k): [v[0], v[1]] for k, v in self.road_nodes_rel.items()},
            "edges": [[a, b] for (a, b) in sorted(self.road_edges)],
            "start": self.start_node,
            "goal": self.goal_node,
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.msg = f"Saved: {filename}"
        print("[SAVED]", filename)

    def load_map(self, filename=None):
        if filename is None:
            filename = self.map_file
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.road_nodes_rel = {int(k): (v[0], v[1]) for k, v in data["nodes_rel"].items()}
        edges = set()
        for a, b in data.get("edges", []):
            e = (a, b) if a < b else (b, a)
            if a in self.road_nodes_rel and b in self.road_nodes_rel:
                edges.add(e)
        self.road_edges = edges

        self.start_node = int(data.get("start", 0))
        self.goal_node  = int(data.get("goal", 1))

        self.edge_from = None
        self.reset_path()
        self.msg = f"Loaded: {filename}"
        print("[LOADED]", filename)

    # =========================
    # UI layout
    # =========================
    def _ui_rects(self):
        sw, sh = self.screen.get_size()
        pad = self.pad
        panel_w = self.left_panel_width
        btn_w = panel_w - 2 * pad

        y = 70
        h = 36
        gap = 8

        bfs_btn = pygame.Rect(pad, y, btn_w, h); y += h + gap
        dfs_btn = pygame.Rect(pad, y, btn_w, h); y += h + gap
        ids_btn = pygame.Rect(pad, y, btn_w, h); y += h + gap

        run_btn = pygame.Rect(pad, y, btn_w, h); y += h + gap
        cancel_btn = pygame.Rect(pad, y, btn_w, h); y += h + gap
        reset_btn = pygame.Rect(pad, y, btn_w, h); y += h + gap

        # sliders
        slider_mouse_rect = pygame.Rect(pad, y + 20, btn_w, 14); y += 54
        slider_nobita_rect = pygame.Rect(pad, y + 20, btn_w, 14); y += 54

        edit_toggle_btn = pygame.Rect(pad, y, btn_w, h); y += h + gap

        # editor group (only when open)
        editor_rects = {}
        if self.map_edit_open:
            ed_h = 32
            ed_gap = 6
            add_btn = pygame.Rect(pad, y, btn_w, ed_h); y += ed_h + ed_gap
            connect_btn = pygame.Rect(pad, y, btn_w, ed_h); y += ed_h + ed_gap
            deln_btn = pygame.Rect(pad, y, btn_w, ed_h); y += ed_h + ed_gap
            dele_btn = pygame.Rect(pad, y, btn_w, ed_h); y += ed_h + ed_gap
            setS_btn = pygame.Rect(pad, y, btn_w, ed_h); y += ed_h + ed_gap
            setG_btn = pygame.Rect(pad, y, btn_w, ed_h); y += ed_h + ed_gap
            save_btn = pygame.Rect(pad, y, btn_w, ed_h); y += ed_h + ed_gap
            load_btn = pygame.Rect(pad, y, btn_w, ed_h); y += ed_h + ed_gap

            editor_rects = {
                "add": add_btn, "connect": connect_btn, "del_node": deln_btn, "del_edge": dele_btn,
                "set_start": setS_btn, "set_goal": setG_btn, "save": save_btn, "load": load_btn
            }

        back_btn = pygame.Rect(pad, sh - 60, btn_w, 42)

        return {
            "bfs": bfs_btn, "dfs": dfs_btn, "ids": ids_btn,
            "run": run_btn, "cancel": cancel_btn, "reset": reset_btn,
            "slider_mouse": slider_mouse_rect,
            "slider_nobita": slider_nobita_rect,
            "edit_toggle": edit_toggle_btn,
            "editor": editor_rects,
            "back": back_btn
        }

    def _draw_button(self, rect, text, active=False, color=None):
        if color is not None:
            bg = color
            tc = (255, 255, 255)
        else:
            if active:
                bg = (40, 110, 190)
                tc = (255, 255, 255)
            else:
                bg = (55, 60, 65)
                tc = (210, 210, 210)

        pygame.draw.rect(self.screen, bg, rect, border_radius=6)
        label = self.font.render(text, True, tc)
        self.screen.blit(label, label.get_rect(center=rect.center))

    # =========================
    # Events
    # =========================
    def handle_events(self, events):
        ui = self._ui_rects()
        map_rect = self._get_map_rect()

        # sync slider rect every time (important for resize + draw-before-events safety)
        self.slider_mouse.rect = ui["slider_mouse"]
        self.slider_nobita.rect = ui["slider_nobita"]

        for event in events:
            # sliders realtime
            if self.slider_mouse.handle_event(event):
                self.mouse_speed_px = self.slider_mouse.value
            if self.slider_nobita.handle_event(event):
                self.nobita_speed_px = self.slider_nobita.value

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.stage_manager.change_stage("menu")
                if event.key == pygame.K_r:
                    self.run_selected_algorithm()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # algo
                if ui["bfs"].collidepoint(event.pos):
                    self.selected_algorithm = "BFS"
                    return
                if ui["dfs"].collidepoint(event.pos):
                    self.selected_algorithm = "DFS"
                    return
                if ui["ids"].collidepoint(event.pos):
                    self.selected_algorithm = "IDS"
                    return

                # run/cancel/reset
                if ui["run"].collidepoint(event.pos):
                    self.run_selected_algorithm()
                    return
                if ui["cancel"].collidepoint(event.pos):
                    self.cancel_run()
                    return
                if ui["reset"].collidepoint(event.pos):
                    self.reset_path()
                    return

                # edit toggle
                if ui["edit_toggle"].collidepoint(event.pos):
                    # không cho mở editor khi đang chạy
                    if self.phase in ("searching", "returning", "nobita_moving"):
                        self.msg = "Can't edit while running."
                        return
                    self.map_edit_open = not self.map_edit_open
                    if not self.map_edit_open:
                        self.tool = None
                        self.edge_from = None
                    return

                # back
                if ui["back"].collidepoint(event.pos):
                    self.stage_manager.change_stage("menu")
                    return

                # if running => lock edit clicks
                if self.phase in ("searching", "returning", "nobita_moving"):
                    return

                # editor buttons if open
                if self.map_edit_open:
                    ed = ui["editor"]
                    if ed.get("add") and ed["add"].collidepoint(event.pos):
                        self.tool = "add"; self.edge_from = None; return
                    if ed.get("connect") and ed["connect"].collidepoint(event.pos):
                        self.tool = "connect"; self.edge_from = None; return
                    if ed.get("del_node") and ed["del_node"].collidepoint(event.pos):
                        self.tool = "del_node"; self.edge_from = None; return
                    if ed.get("del_edge") and ed["del_edge"].collidepoint(event.pos):
                        self.tool = "del_edge"; self.edge_from = None; return
                    if ed.get("set_start") and ed["set_start"].collidepoint(event.pos):
                        self.tool = "set_start"; self.edge_from = None; return
                    if ed.get("set_goal") and ed["set_goal"].collidepoint(event.pos):
                        self.tool = "set_goal"; self.edge_from = None; return
                    if ed.get("save") and ed["save"].collidepoint(event.pos):
                        self.save_map(); return
                    if ed.get("load") and ed["load"].collidepoint(event.pos):
                        if os.path.exists(self.map_file):
                            self.load_map()
                        else:
                            self.msg = "No saved map yet."
                        return

                # map clicks only if editor open
                if not self.map_edit_open:
                    return
                if not map_rect.collidepoint(event.pos):
                    return

                # add/connect/del...
                if self.tool == "add":
                    rx = (event.pos[0] - map_rect.x) / map_rect.w
                    ry = (event.pos[1] - map_rect.y) / map_rect.h
                    rx = max(0.0, min(1.0, rx))
                    ry = max(0.0, min(1.0, ry))
                    new_id = max(self.road_nodes_rel.keys(), default=-1) + 1
                    self.road_nodes_rel[new_id] = (rx, ry)
                    self.reset_path()
                    self.msg = f"Added node {new_id}"
                    return

                if self.tool == "del_node":
                    nid = self._get_node_at_pos(event.pos, map_rect)
                    if nid is not None and nid not in (self.start_node, self.goal_node):
                        self.road_nodes_rel.pop(nid, None)
                        self.road_edges = {e for e in self.road_edges if nid not in e}
                        self.reset_path()
                        self.msg = f"Deleted node {nid}"
                    return

                if self.tool == "set_start":
                    nid = self._get_node_at_pos(event.pos, map_rect)
                    if nid is not None:
                        self.start_node = nid
                        self.reset_path()
                        self.msg = f"Start = {nid}"
                    return

                if self.tool == "set_goal":
                    nid = self._get_node_at_pos(event.pos, map_rect)
                    if nid is not None:
                        self.goal_node = nid
                        self.reset_path()
                        self.msg = f"Goal = {nid}"
                    return

                if self.tool == "connect":
                    nid = self._get_node_at_pos(event.pos, map_rect)
                    if nid is None:
                        self.edge_from = None
                        return
                    if self.edge_from is None:
                        self.edge_from = nid
                    else:
                        a, b = self.edge_from, nid
                        e = (a, b) if a < b else (b, a)
                        self.road_edges.add(e)
                        self.edge_from = None
                        self.reset_path()
                        self.msg = f"Connected {e}"
                    return

                if self.tool == "del_edge":
                    edge = self._get_edge_at_pos(event.pos, map_rect)
                    if edge is not None:
                        a, b = edge
                        e = (a, b) if a < b else (b, a)
                        if e in self.road_edges:
                            self.road_edges.remove(e)
                            self.reset_path()
                            self.msg = f"Deleted edge {e}"
                    return

    # =========================
    # Update
    # =========================
    def update(self):
        dt = self._dt()
        map_rect = self._get_map_rect()
        nodes_px = self._nodes_px(map_rect)

        if self.phase not in ("searching", "returning", "nobita_moving"):
            return

        def step_route(route, seg_idx, t, speed_px):
            if not route or seg_idx >= len(route) - 1:
                return seg_idx, t, True, None  # done

            a = route[seg_idx]
            b = route[seg_idx + 1]
            if a not in nodes_px or b not in nodes_px:
                return seg_idx, t, True, None

            ax, ay = nodes_px[a]
            bx, by = nodes_px[b]
            seg_len = math.hypot(bx - ax, by - ay)
            if seg_len < 1:
                t = 1.0
            else:
                t += (speed_px * dt) / seg_len

            if t >= 1.0:
                return seg_idx + 1, 0.0, False, (a, b)
            return seg_idx, t, False, None

        # SEARCHING: mouse paints BLUE
        if self.phase == "searching":
            self.mouse_seg, self.mouse_t, done, finished_edge = step_route(
                self.mouse_route, self.mouse_seg, self.mouse_t, self.mouse_speed_px
            )
            if finished_edge:
                a, b = finished_edge
                e = (a, b) if a < b else (b, a)
                self.blue_edges_done.add(e)

            if done or (self.mouse_route and self.mouse_seg >= len(self.mouse_route) - 1):
                self.mouse_visible = False

                if not self.solution_path:
                    self.phase = "done"
                    self.msg = "No path found."
                    return

                # mouse returns solution to start (paint GREEN)
                self.phase = "returning"
                self.msg = "Mouse returning solution..."
                self.mouse_route = list(reversed(self.solution_path))  # goal..start
                self.mouse_seg = 0
                self.mouse_t = 0.0
                self.mouse_visible = True
                return

        # RETURNING: mouse paints GREEN
        if self.phase == "returning":
            self.mouse_seg, self.mouse_t, done, finished_edge = step_route(
                self.mouse_route, self.mouse_seg, self.mouse_t, self.mouse_speed_px
            )
            if finished_edge:
                a, b = finished_edge
                e = (a, b) if a < b else (b, a)
                self.green_edges_done.add(e)

            if done or (self.mouse_route and self.mouse_seg >= len(self.mouse_route) - 1):
                self.mouse_visible = False
                # Nobita moves start -> goal
                self.phase = "nobita_moving"
                self.msg = "Nobita moving..."
                self.nobita_mode = "moving"
                self.nobita_seg = 0
                self.nobita_t = 0.0
                return

        # NOBITA MOVING
        if self.phase == "nobita_moving":
            route = self.solution_path
            self.nobita_seg, self.nobita_t, done, finished_edge = step_route(
                route, self.nobita_seg, self.nobita_t, self.nobita_speed_px
            )
            if finished_edge:
                a, b = finished_edge
                e = (a, b) if a < b else (b, a)
                self.green_edges_done.add(e)

            if done or (route and self.nobita_seg >= len(route) - 1):
                self.phase = "done"
                self.msg = "Done."
                self.nobita_mode = "at_goal"
                return

    # =========================
    # Draw
    # =========================
    def draw(self):
        sw, sh = self.screen.get_size()
        ui = self._ui_rects()
        map_rect = self._get_map_rect()
        nodes_px = self._nodes_px(map_rect)

        # sync slider rect before draw (fix resize + draw-before-events)
        self.slider_mouse.rect = ui["slider_mouse"]
        self.slider_nobita.rect = ui["slider_nobita"]

        # background
        if self.bg_raw:
            bg = pygame.transform.scale(self.bg_raw, (sw, sh))
            self.screen.blit(bg, (0, 0))
        else:
            self.screen.fill(self.c_bg)

        # --- If editing: show graph (nodes+edges) to manipulate ---
        if self.map_edit_open:
            for (a, b) in self.road_edges:
                if a in nodes_px and b in nodes_px:
                    pygame.draw.line(self.screen, (255, 215, 0), nodes_px[a], nodes_px[b], 4)

            for nid, (x, y) in nodes_px.items():
                col = (235, 235, 235)
                r = 6
                if nid == self.start_node:
                    col, r = (80, 170, 255), 9
                if nid == self.goal_node:
                    col, r = (255, 100, 100), 9
                if self.tool == "connect" and self.edge_from == nid:
                    col, r = (255, 255, 255), 10
                pygame.draw.circle(self.screen, col, (x, y), r)
                pygame.draw.circle(self.screen, (15, 15, 15), (x, y), r, 2)

        # --- Trails ---
        for (a, b) in self.blue_edges_done:
            if a in nodes_px and b in nodes_px:
                pygame.draw.line(self.screen, self.blue, nodes_px[a], nodes_px[b], self.blue_thick)

        for (a, b) in self.green_edges_done:
            if a in nodes_px and b in nodes_px:
                pygame.draw.line(self.screen, self.green, nodes_px[a], nodes_px[b], self.green_thick)

        # --- partial segment currently being drawn by mouse ---
        def draw_partial(route, seg_idx, t, color, thick):
            if not route or seg_idx >= len(route) - 1:
                return None
            a = route[seg_idx]
            b = route[seg_idx + 1]
            if a not in nodes_px or b not in nodes_px:
                return None
            ax, ay = nodes_px[a]
            bx, by = nodes_px[b]
            tt = max(0.0, min(1.0, t))
            cx = ax + (bx - ax) * tt
            cy = ay + (by - ay) * tt
            pygame.draw.line(self.screen, color, (ax, ay), (cx, cy), thick)
            return (cx, cy)

        mouse_pos = None
        if self.mouse_visible:
            if self.phase in ("searching", "returning"):
                col = self.blue if self.phase == "searching" else self.green
                thick = self.blue_thick if self.phase == "searching" else self.green_thick
                mouse_pos = draw_partial(self.mouse_route, self.mouse_seg, self.mouse_t, col, thick)

        # --- Draw characters ---
        def blit_scaled(img_raw, center_pos, target_h):
            if not img_raw or center_pos is None:
                return
            w, h = img_raw.get_size()
            scale = target_h / h
            img = pygame.transform.smoothscale(img_raw, (int(w * scale), int(h * scale)))
            self.screen.blit(img, img.get_rect(center=center_pos))

        char_h = max(40, int(sh * 0.08))
        mouse_h = max(22, int(sh * 0.045))

        # Goal always visible
        goal_pos = nodes_px.get(self.goal_node)
        blit_scaled(self.goal_img_raw, goal_pos, char_h)

        # Nobita position
        nobita_pos = nodes_px.get(self.start_node)

        if self.nobita_mode == "at_goal":
            nobita_pos = nodes_px.get(self.goal_node)

        elif self.phase == "nobita_moving" and self.solution_path and self.nobita_seg < len(self.solution_path) - 1:
            a = self.solution_path[self.nobita_seg]
            b = self.solution_path[self.nobita_seg + 1]
            if a in nodes_px and b in nodes_px:
                ax, ay = nodes_px[a]
                bx, by = nodes_px[b]
                tt = max(0.0, min(1.0, self.nobita_t))
                nobita_pos = (ax + (bx - ax) * tt, ay + (by - ay) * tt)

        blit_scaled(self.start_img_raw, nobita_pos, char_h)

        # Mouse icon
        if self.mouse_visible and self.mouse_img_raw:
            if mouse_pos is None and self.mouse_route:
                idx = min(self.mouse_seg, len(self.mouse_route) - 1)
                mouse_pos = nodes_px.get(self.mouse_route[idx])
            blit_scaled(self.mouse_img_raw, mouse_pos, mouse_h)

        # ===== Left panel =====
        panel_w = self.left_panel_width
        left_surface = pygame.Surface((panel_w, sh), pygame.SRCALPHA)
        left_surface.fill((38, 41, 44, 160))
        self.screen.blit(left_surface, (0, 0))
        pygame.draw.line(self.screen, (80, 85, 90), (panel_w, 0), (panel_w, sh), 2)

        # Title
        self.screen.blit(self.title_font.render("AI", True, self.c_text), (15, 15))
        self.screen.blit(self.title_font.render("ALGORITHMS", True, self.c_text), (15, 40))

        # Buttons
        self._draw_button(ui["bfs"], "BFS", active=(self.selected_algorithm == "BFS"))
        self._draw_button(ui["dfs"], "DFS", active=(self.selected_algorithm == "DFS"))
        self._draw_button(ui["ids"], "IDS", active=(self.selected_algorithm == "IDS"))

        self._draw_button(ui["run"], "RUN AI", color=(46, 204, 113))
        self._draw_button(ui["cancel"], "CANCEL RUN", color=(231, 76, 60))
        self._draw_button(ui["reset"], "RESET PATH", color=(155, 89, 182))

        # Sliders
        self.slider_mouse.draw(self.screen, self.font)
        self.slider_nobita.draw(self.screen, self.font)

        # Edit toggle
        self._draw_button(
            ui["edit_toggle"],
            "EDIT MAP" + ("  [-]" if self.map_edit_open else "  [+]"),
            active=self.map_edit_open
        )

        # Editor group
        if self.map_edit_open:
            ed = ui["editor"]
            self._draw_button(ed["add"], "ADD NODE", active=(self.tool == "add"))
            self._draw_button(ed["connect"], "CONNECT", active=(self.tool == "connect"))
            self._draw_button(ed["del_node"], "DEL NODE", active=(self.tool == "del_node"))
            self._draw_button(ed["del_edge"], "DEL EDGE", active=(self.tool == "del_edge"))
            self._draw_button(ed["set_start"], "SET START", active=(self.tool == "set_start"))
            self._draw_button(ed["set_goal"], "SET GOAL", active=(self.tool == "set_goal"))
            self._draw_button(ed["save"], "SAVE")
            self._draw_button(ed["load"], "LOAD")

        # Stats
        y_stats = sh - 190
        info_color = (200, 200, 120)
        self.screen.blit(self.font.render(f"Phase: {self.phase}", True, info_color), (10, y_stats))
        self.screen.blit(self.font.render(f"Nodes: {self.nodes_expanded}", True, info_color), (10, y_stats + 20))
        self.screen.blit(self.font.render(f"Time: {self.execution_time}", True, info_color), (10, y_stats + 40))
        self.screen.blit(self.font.render(f"Cost: {self.path_cost}", True, info_color), (10, y_stats + 60))

        msg = self.msg if self.msg else ""
        self.screen.blit(self.font.render(msg, True, info_color), (10, sh - 95))

        # Back
        pygame.draw.rect(self.screen, (231, 76, 60), ui["back"], border_radius=6)
        back_text = self.font.render("BACK", True, (255, 255, 255))
        self.screen.blit(back_text, back_text.get_rect(center=ui["back"].center))