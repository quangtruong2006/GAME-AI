import pygame
import config
import math
import json
import os
import time
from collections import deque
from ui.victory_panel import VictoryPanel

# Import từ các file algorithm (đây là yêu cầu của bạn)
from algorithms.uninformed.bfs import bfs
from algorithms.uninformed.dfs import dfs
from algorithms.uninformed.ids import ids


# ─────────────────────────────────────────────
# Slider
# ─────────────────────────────────────────────
class Slider:
    def __init__(self, rect, vmin, vmax, value, label=""):
        self.rect   = pygame.Rect(rect)
        self.vmin   = float(vmin)
        self.vmax   = float(vmax)
        self.value  = float(value)
        self.label  = label
        self.dragging = False

    def _knob_x(self):
        t = (self.value - self.vmin) / (self.vmax - self.vmin) if self.vmax != self.vmin else 0.0
        return int(self.rect.x + max(0.0, min(1.0, t)) * self.rect.w)

    def handle_event(self, event):
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            knob = pygame.Rect(0, 0, 14, self.rect.h + 8)
            knob.center = (self._knob_x(), self.rect.centery)
            if self.rect.collidepoint(event.pos) or knob.collidepoint(event.pos):
                self.dragging = True
                t = max(0.0, min(1.0, (event.pos[0] - self.rect.x) / self.rect.w if self.rect.w else 0.0))
                self.value  = self.vmin + t * (self.vmax - self.vmin)
                changed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            t = max(0.0, min(1.0, (event.pos[0] - self.rect.x) / self.rect.w if self.rect.w else 0.0))
            self.value  = self.vmin + t * (self.vmax - self.vmin)
            changed = True
        return changed

    def draw(self, screen, font,
             color_track=(90, 95, 100), color_fill=(40, 110, 190),
             color_knob=(235, 235, 235), text_color=(230, 230, 230)):
        if self.label:
            screen.blit(font.render(f"{self.label}: {int(self.value)}", True, text_color),
                        (self.rect.x, self.rect.y - 18))
        pygame.draw.rect(screen, color_track, self.rect, border_radius=6)
        t = max(0.0, min(1.0, (self.value - self.vmin) / (self.vmax - self.vmin) if self.vmax != self.vmin else 0.0))
        pygame.draw.rect(screen, color_fill,
                         pygame.Rect(self.rect.x, self.rect.y, int(self.rect.w * t), self.rect.h),
                         border_radius=6)
        pygame.draw.circle(screen, color_knob, (self._knob_x(), self.rect.centery), self.rect.h // 2 + 4)


# ─────────────────────────────────────────────
# Stage 1
# ─────────────────────────────────────────────
class Stage1Maze:
    """
    Chặng 1 – Mê cung đồ thị (BFS / DFS / IDS)
    Panel trái chuẩn: algo btns → RUN/CANCEL/RESET → sliders → EDIT MAP (2 cột) → BACK
    Sau khi done: hiện stats + nút REPLAY
    REPLAY: quay lại xem animation đã chạy (không reset)
    """

    PANEL_W = 200
    PAD     = 10
    BTN_H   = 34
    GAP     = 7

    # màu trails
    BLUE    = (52,  152, 219)
    GREEN   = (46,  204, 113)
    BLUE_TH = 7
    GREEN_TH= 9

    def __init__(self, screen, stage_manager):
        self.screen        = screen
        self.stage_manager = stage_manager

        # ── fonts ──
        try:
            self.font       = pygame.font.Font("assets/fonts/minecraft.ttf", 14)
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 18)
            self.small_font = pygame.font.Font("assets/fonts/minecraft.ttf", 12)
        except Exception:
            self.font       = pygame.font.SysFont("Arial", 14, bold=True)
            self.title_font = pygame.font.SysFont("Arial", 18, bold=True)
            self.small_font = pygame.font.SysFont("Arial", 12, bold=True)

        self.c_bg   = getattr(config, "COLOR_BG",   (25, 27, 29))
        self.c_text = getattr(config, "COLOR_TEXT",  (240, 240, 240))

        # ── assets ──
        self.bg_raw         = self._try_load("assets/images/stage1_bg.png")
        self.start_img_raw  = self._try_load("assets/images/char_start.png")
        self.goal_img_raw   = self._try_load("assets/images/char_goal.png")
        self.mouse_img_raw  = self._try_load("assets/images/mouse.png")

        # ── map ──
        self.map_file       = "assets/maps/stage1_map.json"
        self.start_node     = 0
        self.goal_node      = 1
        self.road_nodes_rel = {0: (0.10, 0.60), 1: (0.90, 0.55)}
        self.road_edges     = set()

        # ── editor ──
        self.map_edit_open  = False
        self.tool           = None
        self.edge_from      = None
        self.node_pick_r    = 14
        self.edge_pick_thr  = 8

        # ── algo ──
        self.selected_algorithm = "BFS"

        # ── trails ──
        self.blue_edges_done  = set()
        self.green_edges_done = set()

        # ── phase: idle / searching / returning / nobita_moving / done ──
        self.phase = "idle"
        self.msg   = ""

        # ── stats ──
        self.nodes_expanded = 0
        self.path_cost      = 0
        self.execution_time = "0.0 µs"

        # ── speeds ──
        self.mouse_speed_px  = 520.0
        self.nobita_speed_px = 280.0

        # ── sliders (rect placeholder; synced in _ui_rects) ──
        self.slider_search = Slider(pygame.Rect(0,0,1,14), 150, 2500, self.mouse_speed_px,  label="Search spd")
        self.slider_nobita = Slider(pygame.Rect(0,0,1,14), 40,  600,  self.nobita_speed_px, label="Nobita spd")

        # ── mouse route ──
        self.mouse_route   = []
        self.mouse_seg     = 0
        self.mouse_t       = 0.0
        self.mouse_visible = False

        # ── nobita ──
        self.solution_path = []
        self.nobita_seg    = 0
        self.nobita_t      = 0.0
        self.nobita_mode   = "at_start"   # at_start / moving / at_goal

        # ── replay snapshot ──
        self._snap = None

        self._last_ticks = pygame.time.get_ticks()

        if os.path.exists(self.map_file):
            self.load_map(self.map_file)

        self.victory_panel = VictoryPanel(screen, stage_manager)

    # ─────────────────────────────────────────
    # helpers
    # ─────────────────────────────────────────
    @staticmethod
    def _try_load(path):
        try:
            img = pygame.image.load(path)
            return img.convert_alpha()
        except Exception as e:
            print(f"[WARN] Cannot load {path}: {e}")
            return None

    def _dt(self):
        now  = pygame.time.get_ticks()
        dt   = max(0.0, (now - self._last_ticks) / 1000.0)
        self._last_ticks = now
        return min(dt, 0.05)   # clamp để tránh nhảy quá xa khi lag

    def _fmt_exec_time(self, ms: float) -> str:
        """Format thời gian AI: µs → ms → s"""
        if ms < 1.0:
            return f"{ms*1000:.1f} µs"
        if ms < 1000.0:
            return f"{ms:.2f} ms"
        return f"{ms/1000.0:.2f} s"

    def _map_rect(self):
        sw, sh = self.screen.get_size()
        return pygame.Rect(self.PANEL_W, 0, sw - self.PANEL_W, sh)

    def _rel2px(self, rx, ry, mr):
        return (int(mr.x + rx * mr.w), int(mr.y + ry * mr.h))

    def _nodes_px(self, mr):
        return {nid: self._rel2px(rx, ry, mr) for nid, (rx, ry) in self.road_nodes_rel.items()}

    def _node_at(self, pos, mr):
        for nid, (px, py) in self._nodes_px(mr).items():
            if math.hypot(pos[0]-px, pos[1]-py) <= self.node_pick_r:
                return nid
        return None

    @staticmethod
    def _pt_seg_dist(p, a, b):
        px,py = p; ax,ay = a; bx,by = b
        abx,aby = bx-ax, by-ay
        apx,apy = px-ax, py-ay
        l2 = abx*abx + aby*aby
        if l2 == 0:
            return math.hypot(px-ax, py-ay)
        t  = max(0.0, min(1.0, (apx*abx+apy*aby)/l2))
        return math.hypot(px-(ax+t*abx), py-(ay+t*aby))

    def _edge_at(self, pos, mr):
        npx = self._nodes_px(mr)
        best, best_d = None, float("inf")
        for (a,b) in self.road_edges:
            if a in npx and b in npx:
                d = self._pt_seg_dist(pos, npx[a], npx[b])
                if d < best_d:
                    best_d = d; best = (a,b)
        return best if best and best_d <= self.edge_pick_thr else None

    def _build_graph(self):
        g = {nid: [] for nid in self.road_nodes_rel}
        for (a,b) in self.road_edges:
            if a in g and b in g:
                g[a].append(b); g[b].append(a)
        for k in g: g[k].sort()
        return g

    def _shortest_path(self, graph, start, goal):
        q = deque([start]); prev = {start: None}
        while q:
            x = q.popleft()
            if x == goal: break
            for nb in graph[x]:
                if nb not in prev: prev[nb] = x; q.append(nb)
        if goal not in prev: return [start, goal]
        out = []; c = goal
        while c is not None: out.append(c); c = prev[c]
        out.reverse(); return out

    # ─────────────────────────────────────────
    # Run / Cancel / Reset
    # ─────────────────────────────────────────
    def cancel_run(self):
        self.phase = "idle"
        self.mouse_visible = False
        self.mouse_route   = []
        self.msg = "Canceled."

    def reset_path(self):
        self.blue_edges_done.clear()
        self.green_edges_done.clear()
        self.phase = "idle"; self.msg = "Reset."
        self.nodes_expanded = 0; self.path_cost = 0
        self.execution_time = "0.0 µs"
        self.mouse_visible = False; self.mouse_route = []
        self.mouse_seg = 0; self.mouse_t = 0.0
        self.solution_path = []; self.nobita_seg = 0
        self.nobita_t = 0.0; self.nobita_mode = "at_start"
        self._snap = None

    def _replay(self):
        """Khôi phục snapshot để quan sát lại animation đã chạy."""
        if self._snap is None:
            self.msg = "Chưa có lần chạy nào để replay."
            return
        s = self._snap
        self.blue_edges_done  = set(s["blue"])
        self.green_edges_done = set(s["green"])
        self.mouse_route   = list(s["mouse_route"])
        self.mouse_seg     = 0;   self.mouse_t = 0.0
        self.mouse_visible = True
        self.solution_path = list(s["solution_path"])
        self.nobita_seg    = 0;   self.nobita_t = 0.0
        self.nobita_mode   = "at_start"
        self.blue_edges_done.clear()
        self.green_edges_done.clear()
        self.phase = "searching"
        self.msg   = f"Replay ({self.selected_algorithm})..."

    def run_selected_algorithm(self):
        self.reset_path()
        graph = self._build_graph()
        if self.start_node not in graph or self.goal_node not in graph:
            self.msg = "Start/Goal not in graph!"; return
        if self.start_node == self.goal_node:
            self.msg = "Start == Goal"
            self.phase = "done"; self.nobita_mode = "at_goal"
            self.execution_time = "0.0 µs"; return

        if self.selected_algorithm == "BFS":
            path, visited, mouse_trace, nodes_expanded, exec_ms = bfs(
                graph, self.start_node, self.goal_node)
        elif self.selected_algorithm == "DFS":
            path, visited, mouse_trace, nodes_expanded, exec_ms = dfs(
                graph, self.start_node, self.goal_node)
        else:  # IDS
            path, visited, mouse_trace, nodes_expanded, exec_ms = ids(
                graph, self.start_node, self.goal_node)

        self.execution_time = (self._fmt_exec_time(exec_ms)
                            if isinstance(exec_ms, (int, float)) else str(exec_ms))
        self.nodes_expanded  = nodes_expanded
        self.solution_path   = path if len(path) >= 2 else []
        self.path_cost       = len(self.solution_path) - 1 if self.solution_path else 0

        self.mouse_route   = mouse_trace
        self.mouse_seg     = 0
        self.mouse_t       = 0.0
        self.mouse_visible = True
        self.phase         = "searching"
        self.msg           = f"Searching ({self.selected_algorithm})..."

        self._snap = {
            "blue":          set(),
            "green":         set(),
            "mouse_route":   list(mouse_trace),
            "solution_path": list(self.solution_path),
        }

    # ─────────────────────────────────────────
    # Save / Load map
    # ─────────────────────────────────────────
    def save_map(self, fn=None):
        fn = fn or self.map_file
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        data = {
            "nodes_rel": {str(k): list(v) for k,v in self.road_nodes_rel.items()},
            "edges":     [[a,b] for a,b in sorted(self.road_edges)],
            "start": self.start_node, "goal": self.goal_node,
        }
        with open(fn,"w",encoding="utf-8") as f: json.dump(data,f,indent=2)
        self.msg = f"Saved: {fn}"

    def load_map(self, fn=None):
        fn = fn or self.map_file
        with open(fn,"r",encoding="utf-8") as f: data = json.load(f)
        self.road_nodes_rel = {int(k):(v[0],v[1]) for k,v in data["nodes_rel"].items()}
        edges = set()
        for a,b in data.get("edges",[]):
            e = (a,b) if a<b else (b,a)
            if a in self.road_nodes_rel and b in self.road_nodes_rel:
                edges.add(e)
        self.road_edges = edges
        self.start_node = int(data.get("start",0))
        self.goal_node  = int(data.get("goal",1))
        self.edge_from  = None
        self.reset_path()
        self.msg = f"Loaded: {fn}"

    # ─────────────────────────────────────────
    # UI layout
    # ─────────────────────────────────────────
    def _ui_rects(self):
        sw, sh = self.screen.get_size()
        pad  = self.PAD
        pw   = self.PANEL_W
        bw   = pw - 2*pad
        h    = self.BTN_H
        g    = self.GAP
        y    = 60

        def btn(width=None, height=None):
            nonlocal y
            r = pygame.Rect(pad, y, width or bw, height or h)
            y += (height or h) + g
            return r

        algo_bfs = btn(); algo_dfs = btn(); algo_ids = btn()
        y += 4
        run_btn    = btn()
        cancel_btn = btn()
        reset_btn  = btn()

        y += 10
        sl_search_rect = pygame.Rect(pad, y+20, bw, 14); y += 52
        sl_nobita_rect = pygame.Rect(pad, y+20, bw, 14); y += 52

        edit_toggle = btn()

        editor_rects = {}
        if self.map_edit_open:
            col_w   = (bw - 6) // 2
            ed_h    = 30
            ed_g    = 6
            tools   = ["add","connect","del_node","del_edge","set_start","set_goal"]
            labels  = ["ADD NODE","CONNECT","DEL NODE","DEL EDGE","SET START","SET GOAL"]
            for i,(tid,lab) in enumerate(zip(tools,labels)):
                col  = i % 2
                row  = i // 2
                rx   = pad + col*(col_w+6)
                ry   = y   + row*(ed_h+ed_g)
                editor_rects[tid] = pygame.Rect(rx, ry, col_w, ed_h)
            rows_used = math.ceil(len(tools)/2)
            y += rows_used*(ed_h+ed_g) + 4
            editor_rects["save"] = pygame.Rect(pad,           y, col_w, ed_h)
            editor_rects["load"] = pygame.Rect(pad+col_w+6,   y, col_w, ed_h)
            y += ed_h + ed_g

        replay_btn = None
        if self.phase == "done" and self._snap:
            y += 4
            replay_btn = btn()

        back_btn = pygame.Rect(pad, sh - 54, bw, 44)

        return {
            "bfs": algo_bfs, "dfs": algo_dfs, "ids": algo_ids,
            "run": run_btn, "cancel": cancel_btn, "reset": reset_btn,
            "slider_search": sl_search_rect,
            "slider_nobita": sl_nobita_rect,
            "edit_toggle":   edit_toggle,
            "editor":        editor_rects,
            "replay":        replay_btn,
            "back":          back_btn,
        }

    # ─────────────────────────────────────────
    # Draw helpers
    # ─────────────────────────────────────────
    def _btn(self, rect, text, active=False, color=None, disabled=False):
        if disabled:
            bg     = (70, 70, 70)
            border = (90, 90, 90)
            fg     = (150, 150, 150)
        else:
            bg     = color if color else ((40, 110, 190) if active else (55, 60, 65))
            border = (255, 255, 255) if active else (80, 85, 90)
            fg     = (255, 255, 255)

        pygame.draw.rect(self.screen, bg, rect, border_radius=6)
        pygame.draw.rect(self.screen, border, rect, width=1, border_radius=6)
        lbl = self.font.render(text, True, fg)
        self.screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _blit_scaled(self, img, center, target_h, offset_y=0):
        if img is None or center is None: return
        w, h = img.get_size()
        img2 = pygame.transform.smoothscale(img, (int(w*target_h/h), target_h))
        r    = img2.get_rect(center=(int(center[0]), int(center[1])+offset_y))
        self.screen.blit(img2, r)

    # ─────────────────────────────────────────
    # Events
    # ─────────────────────────────────────────
    def handle_events(self, events):
        self.victory_panel.handle_events(events)
        if self.victory_panel.visible: return

        ui = self._ui_rects()
        self.slider_search.rect = ui["slider_search"]
        self.slider_nobita.rect = ui["slider_nobita"]

        mr = self._map_rect()

        for event in events:
            if self.slider_search.handle_event(event): self.mouse_speed_px  = self.slider_search.value
            if self.slider_nobita.handle_event(event): self.nobita_speed_px = self.slider_nobita.value

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.stage_manager.change_stage("stage_select")
                if event.key == pygame.K_r:
                    self.run_selected_algorithm()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                for key in ("bfs","dfs","ids"):
                    if ui[key].collidepoint(pos):
                        self.selected_algorithm = key.upper()
                        return

                if ui["run"].collidepoint(pos):    self.run_selected_algorithm(); return
                if ui["cancel"].collidepoint(pos): self.cancel_run();             return
                if ui["reset"].collidepoint(pos):  self.reset_path();             return

                if ui["replay"] and ui["replay"].collidepoint(pos):
                    self._replay(); return

                if ui["edit_toggle"].collidepoint(pos):
                    if self.phase in ("searching","returning","nobita_moving"):
                        self.msg = "Can't edit while running."; return
                    self.map_edit_open = not self.map_edit_open
                    if not self.map_edit_open:
                        self.tool = None; self.edge_from = None
                    return

                if ui["back"].collidepoint(pos):
                    self.stage_manager.change_stage("stage_select"); return

                if self.phase in ("searching","returning","nobita_moving"): return

                if self.map_edit_open:
                    ed = ui["editor"]
                    for tid in ("add","connect","del_node","del_edge","set_start","set_goal"):
                        if tid in ed and ed[tid].collidepoint(pos):
                            self.tool = tid; self.edge_from = None; return
                    if "save" in ed and ed["save"].collidepoint(pos): self.save_map(); return
                    if "load" in ed and ed["load"].collidepoint(pos):
                        self.load_map() if os.path.exists(self.map_file) else setattr(self,"msg","No saved map."); return

                if not self.map_edit_open: return
                if not mr.collidepoint(pos): return
                self._handle_canvas_click(pos, mr)

    def _handle_canvas_click(self, pos, mr):
        tool = self.tool
        if tool == "add":
            rx = max(0.0, min(1.0, (pos[0]-mr.x)/mr.w))
            ry = max(0.0, min(1.0, (pos[1]-mr.y)/mr.h))
            nid = max(self.road_nodes_rel.keys(), default=-1) + 1
            self.road_nodes_rel[nid] = (rx, ry)
            self.reset_path(); self.msg = f"Added node {nid}"; return

        nid = self._node_at(pos, mr)
        if tool == "del_node":
            if nid is not None and nid not in (self.start_node, self.goal_node):
                self.road_nodes_rel.pop(nid, None)
                self.road_edges = {e for e in self.road_edges if nid not in e}
                self.reset_path(); self.msg = f"Deleted node {nid}"
            return
        if tool == "set_start":
            if nid is not None: self.start_node = nid; self.reset_path(); self.msg = f"Start={nid}"
            return
        if tool == "set_goal":
            if nid is not None: self.goal_node  = nid; self.reset_path(); self.msg = f"Goal={nid}"
            return
        if tool == "connect":
            if nid is None: self.edge_from = None; return
            if self.edge_from is None: self.edge_from = nid
            else:
                a,b = self.edge_from, nid
                e   = (a,b) if a<b else (b,a)
                self.road_edges.add(e)
                self.edge_from = None
                self.reset_path(); self.msg = f"Connected {e}"
            return
        if tool == "del_edge":
            edge = self._edge_at(pos, mr)
            if edge:
                a,b = edge; e = (a,b) if a<b else (b,a)
                self.road_edges.discard(e); self.reset_path(); self.msg = f"Deleted edge {e}"
            return

    # ─────────────────────────────────────────
    # Update
    # ─────────────────────────────────────────
    def update(self):
        dt   = self._dt()
        mr   = self._map_rect()
        npx  = self._nodes_px(mr)

        if self.phase not in ("searching","returning","nobita_moving"):
            return

        def step(route, seg, t, spd):
            if not route or seg >= len(route)-1:
                return seg, t, True, None
            a,b   = route[seg], route[seg+1]
            if a not in npx or b not in npx: return seg,t,True,None
            ax,ay = npx[a]; bx,by = npx[b]
            ln    = math.hypot(bx-ax, by-ay)
            t    += (spd*dt) / ln if ln>1 else 1.0
            if t >= 1.0: return seg+1, 0.0, False, (a,b)
            return seg, t, False, None

        if self.phase == "searching":
            self.mouse_seg, self.mouse_t, done, fe = step(
                self.mouse_route, self.mouse_seg, self.mouse_t, self.mouse_speed_px)
            if fe:
                a,b = fe; self.blue_edges_done.add((a,b) if a<b else (b,a))
            if done or self.mouse_seg >= len(self.mouse_route)-1:
                self.mouse_visible = False
                if not self.solution_path:
                    self.phase = "done"; self.msg = "No path found."; return
                self.phase = "returning"; self.msg = "Returning solution..."
                self.mouse_route = list(reversed(self.solution_path))
                self.mouse_seg = 0; self.mouse_t = 0.0; self.mouse_visible = True
            return

        if self.phase == "returning":
            self.mouse_seg, self.mouse_t, done, fe = step(
                self.mouse_route, self.mouse_seg, self.mouse_t, self.mouse_speed_px)
            if fe:
                a,b = fe; self.green_edges_done.add((a,b) if a<b else (b,a))
            if done or self.mouse_seg >= len(self.mouse_route)-1:
                self.mouse_visible = False
                self.phase = "nobita_moving"; self.msg = "Nobita moving..."
                self.nobita_mode = "moving"; self.nobita_seg = 0; self.nobita_t = 0.0
            return

        if self.phase == "nobita_moving":
            self.nobita_seg, self.nobita_t, done, fe = step(
                self.solution_path, self.nobita_seg, self.nobita_t, self.nobita_speed_px)
            if fe:
                a,b = fe; self.green_edges_done.add((a,b) if a<b else (b,a))
            if done or self.nobita_seg >= len(self.solution_path)-1:
                self.phase = "done"; self.msg = "Done!"
                self.nobita_mode = "at_goal"
                self.victory_panel.show(
                    next_stage_id     = "stage2",
                    next_stage_unlock = "stage2",
                    title    = "CHẶNG 1 HOÀN THÀNH!",
                    subtitle = "Nobita đã tìm thấy Doraemon!",
                    nodes_visited = self.nodes_expanded,
                    path_cost     = self.path_cost,
                    exec_time     = self.execution_time,
                )

    # ─────────────────────────────────────────
    # Draw
    # ─────────────────────────────────────────
    def draw(self):
        sw, sh = self.screen.get_size()
        ui  = self._ui_rects()
        mr  = self._map_rect()
        npx = self._nodes_px(mr)

        self.slider_search.rect = ui["slider_search"]
        self.slider_nobita.rect = ui["slider_nobita"]

        self.screen.fill(self.c_bg)
        if self.bg_raw:
            bg = pygame.transform.scale(self.bg_raw, (mr.w, mr.h))
            self.screen.blit(bg, (mr.x, mr.y))

        if self.map_edit_open:
            for (a,b) in self.road_edges:
                if a in npx and b in npx:
                    pygame.draw.line(self.screen,(255,215,0),npx[a],npx[b],4)
            for nid,(x,y) in npx.items():
                col,r = (235,235,235),6
                if nid == self.start_node: col,r = (80,170,255),9
                if nid == self.goal_node:  col,r = (255,100,100),9
                if self.tool=="connect" and self.edge_from==nid: col,r=(255,255,255),10
                pygame.draw.circle(self.screen,col,(x,y),r)
                pygame.draw.circle(self.screen,(15,15,15),(x,y),r,2)

        for (a,b) in self.blue_edges_done:
            if a in npx and b in npx:
                pygame.draw.line(self.screen,self.BLUE,npx[a],npx[b],self.BLUE_TH)
        for (a,b) in self.green_edges_done:
            if a in npx and b in npx:
                pygame.draw.line(self.screen,self.GREEN,npx[a],npx[b],self.GREEN_TH)

        def draw_partial(route, seg, t, col, thick):
            if not route or seg >= len(route)-1: return None
            a,b = route[seg], route[seg+1]
            if a not in npx or b not in npx: return None
            ax,ay = npx[a]; bx,by = npx[b]
            tt = max(0.0,min(1.0,t))
            cx,cy = ax+(bx-ax)*tt, ay+(by-ay)*tt
            pygame.draw.line(self.screen,col,(ax,ay),(int(cx),int(cy)),thick)
            return (cx,cy)

        mouse_pos = None
        if self.mouse_visible:
            col   = self.BLUE  if self.phase=="searching" else self.GREEN
            thick = self.BLUE_TH if self.phase=="searching" else self.GREEN_TH
            mouse_pos = draw_partial(self.mouse_route, self.mouse_seg, self.mouse_t, col, thick)

        char_h  = max(40, int(sh*0.08))
        mouse_h = max(22, int(sh*0.045))

        self._blit_scaled(self.goal_img_raw,  npx.get(self.goal_node),  char_h,  -25)

        nobita_pos = npx.get(self.start_node)
        if self.nobita_mode == "at_goal":
            nobita_pos = npx.get(self.goal_node)
        elif self.phase == "nobita_moving" and self.solution_path and self.nobita_seg < len(self.solution_path)-1:
            a,b = self.solution_path[self.nobita_seg], self.solution_path[self.nobita_seg+1]
            if a in npx and b in npx:
                ax,ay = npx[a]; bx,by = npx[b]
                tt = max(0.0,min(1.0,self.nobita_t))
                nobita_pos = (ax+(bx-ax)*tt, ay+(by-ay)*tt)
        self._blit_scaled(self.start_img_raw, nobita_pos, char_h, -25)

        if self.mouse_visible and self.mouse_img_raw:
            if mouse_pos is None and self.mouse_route:
                idx = min(self.mouse_seg, len(self.mouse_route)-1)
                mouse_pos = npx.get(self.mouse_route[idx])
            self._blit_scaled(self.mouse_img_raw, mouse_pos, mouse_h)

        # LEFT PANEL
        panel = pygame.Surface((self.PANEL_W, sh), pygame.SRCALPHA)
        panel.fill((30, 33, 36, 200))
        self.screen.blit(panel, (0,0))
        pygame.draw.line(self.screen,(70,75,80),(self.PANEL_W,0),(self.PANEL_W,sh),2)

        self.screen.blit(self.title_font.render("CHẶNG 1", True, (255,200,60)), (self.PAD,10))
        self.screen.blit(self.font.render("Maze / Graph", True, (180,180,180)),  (self.PAD,32))

        self._btn(ui["bfs"],"BFS", active=(self.selected_algorithm=="BFS"))
        self._btn(ui["dfs"],"DFS", active=(self.selected_algorithm=="DFS"))
        self._btn(ui["ids"],"IDS", active=(self.selected_algorithm=="IDS"))

        is_running = self.phase in ("searching", "returning", "nobita_moving")

        self._btn(ui["run"], "▶ RUN AI", color=(46, 204, 113), disabled=is_running)
        self._btn(ui["cancel"], "■ CANCEL", color=(231, 76, 60), disabled=(not is_running))
        self._btn(ui["reset"], "↺ RESET PATH", color=(155, 89, 182))

        self.slider_search.draw(self.screen, self.font)
        self.slider_nobita.draw(self.screen, self.font)

        lbl_edit = "EDIT MAP  [-]" if self.map_edit_open else "EDIT MAP  [+]"
        self._btn(ui["edit_toggle"], lbl_edit, active=self.map_edit_open)

        if self.map_edit_open:
            ed = ui["editor"]
            labels = {
                "add": "ADD NODE", "connect": "CONNECT", "del_node": "DEL NODE",
                "del_edge": "DEL EDGE", "set_start": "SET START", "set_goal": "SET GOAL",
                "save": "SAVE", "load": "LOAD",
            }
            for tid, lbl in labels.items():
                if tid in ed:
                    self._btn(ed[tid], lbl, active=(self.tool==tid))

        if ui["replay"]:
            self._btn(ui["replay"], "⟳ REPLAY", color=(230,126,34))

        self._btn(ui["back"], "◀ BACK", color=(231,76,60))

        self._draw_stats(sh, ui["back"])

        self.victory_panel.update()
        self.victory_panel.draw()

    def _draw_stats(self, sh, back_rect):
        phase_label = {
            "idle":          "Idle",
            "searching":     "🔍 Searching...",
            "returning":     "↩ Returning...",
            "nobita_moving": "🚶 Running...",
            "done":          "✔ Done",
        }.get(self.phase, self.phase)

        lines = [
            ("Trạng thái",  phase_label),
            ("Nodes duyệt", str(self.nodes_expanded)),
            ("Chi phí",     str(self.path_cost)),
            ("Thời gian",   self.execution_time),
        ]
        line_h = 18
        total_h = len(lines) * line_h + 8
        y0 = back_rect.top - total_h - 10

        for i, (key, val) in enumerate(lines):
            y = y0 + i * line_h
            k_surf = self.small_font.render(f"{key}:", True, (160,160,160))
            v_surf = self.small_font.render(str(val), True, (255,220,80))
            self.screen.blit(k_surf, (self.PAD, y))
            self.screen.blit(v_surf, (self.PAD + k_surf.get_width() + 4, y))