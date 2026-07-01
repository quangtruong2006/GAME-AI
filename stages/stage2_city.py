import pygame
import config
import os
import math
import json
import time
from collections import deque
from ui.victory_panel import VictoryPanel
from algorithms.informed.a_star import a_star
from algorithms.informed.greedy import greedy_search
from algorithms.informed.ida_star import ida_star


# ─────────────────────────────────────────────
# Slider (bản dùng chung – giống stage1)
# ─────────────────────────────────────────────
class Slider:
    def __init__(self, rect, vmin, vmax, value, label=""):
        self.rect = pygame.Rect(rect)
        self.vmin, self.vmax = float(vmin), float(vmax)
        self.value   = float(value)
        self.label   = label
        self.dragging = False

    def _knob_x(self):
        t = (self.value-self.vmin)/(self.vmax-self.vmin) if self.vmax!=self.vmin else 0.0
        return int(self.rect.x + max(0.0,min(1.0,t))*self.rect.w)

    def handle_event(self, event):
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            knob = pygame.Rect(0,0,14,self.rect.h+8)
            knob.center = (self._knob_x(), self.rect.centery)
            if self.rect.collidepoint(event.pos) or knob.collidepoint(event.pos):
                self.dragging = True
                t = max(0.0,min(1.0,(event.pos[0]-self.rect.x)/self.rect.w if self.rect.w else 0.0))
                self.value = self.vmin + t*(self.vmax-self.vmin); changed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            t = max(0.0,min(1.0,(event.pos[0]-self.rect.x)/self.rect.w if self.rect.w else 0.0))
            self.value = self.vmin + t*(self.vmax-self.vmin); changed = True
        return changed

    def draw(self, screen, font,
             color_track=(90,95,100), color_fill=(40,110,190),
             color_knob=(235,235,235), text_color=(230,230,230)):
        if self.label:
            screen.blit(font.render(f"{self.label}: {int(self.value)}", True, text_color),
                        (self.rect.x, self.rect.y-18))
        pygame.draw.rect(screen, color_track, self.rect, border_radius=6)
        t = max(0.0,min(1.0,(self.value-self.vmin)/(self.vmax-self.vmin) if self.vmax!=self.vmin else 0.0))
        pygame.draw.rect(screen, color_fill,
                         pygame.Rect(self.rect.x, self.rect.y, int(self.rect.w*t), self.rect.h),
                         border_radius=6)
        pygame.draw.circle(screen, color_knob, (self._knob_x(), self.rect.centery), self.rect.h//2+4)


# ─────────────────────────────────────────────
# Stage 2
# ─────────────────────────────────────────────
class Stage2City:
    """
    Chặng 2 – Đồ thị có trọng số (A* / Greedy / IDA*)
    Panel trái theo khuôn stage1: algo → actions → sliders → edit → back
    Đã thêm hiển thị "Thời gian" ở panel trái và victory panel.
    """

    PANEL_W = 200
    PAD     = 10
    BTN_H   = 34
    GAP     = 7

    BLUE     = (255, 255,   0)
    GREEN    = (  0, 255, 120)
    BLUE_TH  = 6
    GREEN_TH = 8

    def __init__(self, screen, stage_manager):
        self.screen        = screen
        self.stage_manager = stage_manager
        self.sw = screen.get_width()
        self.sh = screen.get_height()

        # fonts
        try:
            self.font       = pygame.font.Font("assets/fonts/minecraft.ttf", 14)
            self.title_font = pygame.font.Font("assets/fonts/minecraft.ttf", 18)
            self.small_font = pygame.font.Font("assets/fonts/minecraft.ttf", 12)
        except Exception:
            self.font       = pygame.font.SysFont("Arial", 14, bold=True)
            self.title_font = pygame.font.SysFont("Arial", 18, bold=True)
            self.small_font = pygame.font.SysFont("Arial", 12, bold=True)

        self.c_bg     = getattr(config,"COLOR_BG",    (10,15,25))
        self.c_nobita = getattr(config,"COLOR_NOBITA", (52,152,219))
        self.c_dora   = getattr(config,"COLOR_DORA",   (231,76,60))

        # map rect
        self.map_rect = pygame.Rect(self.PANEL_W, 0, self.sw-self.PANEL_W, self.sh)

        # graph data
        self.nodes      = []
        self.edges      = {}
        self.start_node = None
        self.goal_node  = None
        self.map_file   = os.path.join("assets","maps","stage2_graph.json")
        self._load_graph_data()

        # assets
        self.start_img_raw = self._load_asset("assets/images/nobita.png")
        self.goal_img_raw  = self._load_asset("assets/images/tram_tin_hieu.png")
        self.mouse_img_raw = self._load_asset("assets/images/mouse.png")
        self._load_background()

        # editor
        self.show_editor      = False
        self.current_tool     = "ADD_NODE"
        self.current_edge_type= 1
        self.sel_node_edge    = None

        # algo
        self.selected_algorithm = "A* Search"

        # animation state
        self.phase         = "idle"
        self.msg           = "Ready."
        self.blue_edges_done  = set()
        self.green_edges_done = set()
        self.mouse_route   = []
        self.mouse_seg     = 0; self.mouse_t = 0.0
        self.mouse_visible = False
        self.solution_path = []
        self.nobita_seg    = 0; self.nobita_t = 0.0
        self.nobita_mode   = "at_start"

        # stats
        self.nodes_expanded = 0
        self.path_cost      = 0
        self.execution_time = "0.0 µs"

        # replay snapshot
        self._snap = None

        # speeds
        self.search_speed  = 520.0
        self.nobita_speed  = 280.0

        # sliders
        self.slider_search = Slider(pygame.Rect(0,0,1,14), 150, 2500, self.search_speed,  label="Search spd")
        self.slider_nobita = Slider(pygame.Rect(0,0,1,14), 40,  600,  self.nobita_speed,  label="Nobita spd")

        self._last_ticks = pygame.time.get_ticks()
        self.victory_panel = VictoryPanel(screen, stage_manager)

    # ─────── helpers ───────
    @staticmethod
    def _load_asset(path):
        if os.path.exists(path):
            try: return pygame.image.load(path).convert_alpha()
            except: pass
        return None

    def _load_background(self):
        for ext in ("png","jpg"):
            p = os.path.join("assets","images",f"stage2_bg.{ext}")
            if os.path.exists(p):
                raw = pygame.image.load(p).convert_alpha()
                self.bg_image = pygame.transform.smoothscale(raw,(self.map_rect.w,self.map_rect.h))
                return
        self.bg_image = None

    def _nodes_px(self):
        return [(int(self.map_rect.x+rx*self.map_rect.w), int(self.map_rect.y+ry*self.map_rect.h))
                for rx,ry in self.nodes]

    def _blit_scaled(self, img, center, target_h, fallback=None):
        if center is None: return
        if img:
            w,h = img.get_size()
            s   = pygame.transform.smoothscale(img,(int(w*target_h/h),target_h))
            self.screen.blit(s, s.get_rect(center=(int(center[0]),int(center[1]))))
        elif fallback:
            pygame.draw.circle(self.screen, fallback, (int(center[0]),int(center[1])), 10)

    def _fmt_exec_time(self, ms: float) -> str:
        """Format thời gian AI: µs → ms → s"""
        if ms < 1.0:
            return f"{ms*1000:.1f} µs"
        if ms < 1000.0:
            return f"{ms:.2f} ms"
        return f"{ms/1000.0:.2f} s"

    # ─────── graph I/O ───────
    def _save_graph_data(self):
        data = {"nodes":self.nodes,"edges":self.edges,
                "start":self.start_node,"goal":self.goal_node}
        with open(self.map_file,"w") as f: json.dump(data,f)
        self.msg = "Saved."

    def _load_graph_data(self):
        if not os.path.exists(self.map_file): return
        with open(self.map_file,"r") as f: data = json.load(f)
        self.nodes = []
        for n in data.get("nodes",[]):
            if n[0]>2.0 or n[1]>2.0:
                self.nodes.append(((n[0]-210)/(self.sw-210), n[1]/self.sh))
            else: self.nodes.append(tuple(n))
        raw_e = data.get("edges",{})
        self.edges = {}
        for k,nb in raw_e.items():
            u = int(k); self.edges[u] = {}
            for nk,vd in nb.items():
                vd = dict(vd)
                if vd.get("type")==8: vd["cost"]=1
                self.edges[u][int(nk)] = vd
        self.start_node = data.get("start")
        self.goal_node  = data.get("goal")

    def _bfs_path(self, start, end):
        if start==end: return [start]
        q = deque([start]); prev = {start:None}
        while q:
            c = q.popleft()
            if c==end: break
            for nb in (self.edges.get(c) or {}):
                if nb not in prev: prev[nb]=c; q.append(nb)
        if end not in prev: return [start,end]
        out=[]; c=end
        while c is not None: out.append(c); c=prev[c]
        out.reverse(); return out

    # ─────── Reset / Cancel ───────
    def _reset_results(self):
        self.blue_edges_done.clear(); self.green_edges_done.clear()
        self.mouse_route=[]; self.mouse_seg=0; self.mouse_t=0.0; self.mouse_visible=False
        self.solution_path=[]; self.nobita_seg=0; self.nobita_t=0.0; self.nobita_mode="at_start"
        self.nodes_expanded=0; self.path_cost=0; self.execution_time="0.0 µs"
        self.phase="idle"; self.msg="Reset."; self._snap=None

    def _replay(self):
        if self._snap is None: self.msg="Chưa có replay."; return
        s = self._snap
        self.blue_edges_done.clear(); self.green_edges_done.clear()
        self.mouse_route   = list(s["mouse_route"])
        self.mouse_seg=0; self.mouse_t=0.0; self.mouse_visible=True
        self.solution_path = list(s["solution_path"])
        self.nobita_seg=0; self.nobita_t=0.0; self.nobita_mode="at_start"
        self.phase="searching"; self.msg=f"Replay ({self.selected_algorithm})..."

    # ─────── Run AI ───────
    def _run_ai(self):
        if self.start_node is None or self.goal_node is None:
            self.msg="Error: cần đặt Start và Goal!"; return
        self._reset_results()
        self.show_editor = False
        npx = self._nodes_px()

        if self.selected_algorithm == "A* Search":
            p, v, n, t, c = a_star(npx, self.edges, self.start_node, self.goal_node)
        elif self.selected_algorithm == "Greedy BFS":
            p, v, n, t, c = greedy_search(npx, self.edges, self.start_node, self.goal_node)
        else:
            p, v, n, t, c = ida_star(npx, self.edges, self.start_node, self.goal_node)

        # Xử lý thời gian (cả float lẫn string đều được)
        if isinstance(t, (int, float)):
            self.execution_time = self._fmt_exec_time(t)
        else:
            self.execution_time = str(t)

        self.nodes_expanded = n
        self.solution_path  = p
        self.path_cost      = c

        targets = [self.start_node] + list(v)
        if p: targets.append(self.goal_node)
        route = [targets[0]]
        for i in range(len(targets)-1):
            route.extend(self._bfs_path(targets[i],targets[i+1])[1:])

        self.mouse_route = route; self.mouse_seg=0; self.mouse_t=0.0
        self.mouse_visible=True; self.phase="searching"
        self.msg=f"Searching ({self.selected_algorithm})..."

        self._snap = {"mouse_route":list(route), "solution_path":list(p or [])}

    # ─────── UI rects ───────
    def _ui_rects(self):
        sh   = self.sh
        pad  = self.PAD; pw = self.PANEL_W
        bw   = pw - 2*pad
        h    = self.BTN_H; g = self.GAP
        y    = 60

        def btn(ww=None, hh=None):
            nonlocal y
            r = pygame.Rect(pad, y, ww or bw, hh or h)
            y += (hh or h)+g; return r

        algo_a  = btn(); algo_gr = btn(); algo_ida = btn()
        y += 4
        run_btn    = btn()
        cancel_btn = btn()
        reset_btn  = btn()

        y += 10
        sl_search_rect = pygame.Rect(pad, y+20, bw, 14); y += 52
        sl_nobita_rect = pygame.Rect(pad, y+20, bw, 14); y += 52

        edit_toggle = btn()

        editor_rects = {}
        if self.show_editor:
            col_w = (bw-6)//2; ed_h=28; ed_g=6
            tools  = ["ADD_NODE","CONNECT","DEL_NODE","DEL_EDGE","SET_START","SET_GOAL"]
            for i,tid in enumerate(tools):
                col=i%2; row=i//2
                editor_rects[tid] = pygame.Rect(pad+col*(col_w+6), y+row*(ed_h+ed_g), col_w, ed_h)
            rows = math.ceil(len(tools)/2)
            y += rows*(ed_h+ed_g)+4
            editor_rects["SAVE"] = pygame.Rect(pad,        y, col_w, ed_h)
            editor_rects["LOAD"] = pygame.Rect(pad+col_w+6,y, col_w, ed_h)
            y += ed_h+ed_g

        replay_btn = None
        if self.phase in ("done","completed") and self._snap:
            y += 4; replay_btn = btn()

        back_btn = pygame.Rect(pad, sh-54, bw, 44)

        return {
            "A* Search":  algo_a,
            "Greedy BFS": algo_gr,
            "IDA*":       algo_ida,
            "run":        run_btn,
            "cancel":     cancel_btn,
            "reset":      reset_btn,
            "slider_search": sl_search_rect,
            "slider_nobita": sl_nobita_rect,
            "edit_toggle":   edit_toggle,
            "editor":        editor_rects,
            "replay":        replay_btn,
            "back":          back_btn,
        }

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

    # ─────── Events ───────
    def handle_events(self, events):
        self.victory_panel.handle_events(events)
        if self.victory_panel.visible: return

        ui = self._ui_rects()
        self.slider_search.rect = ui["slider_search"]
        self.slider_nobita.rect = ui["slider_nobita"]

        for event in events:
            if self.slider_search.handle_event(event): self.search_speed = self.slider_search.value
            if self.slider_nobita.handle_event(event): self.nobita_speed = self.slider_nobita.value

            if event.type == pygame.KEYDOWN and self.show_editor and self.current_tool=="CONNECT":
                key_map = {pygame.K_1:1, pygame.K_KP1:1,
                           pygame.K_2:2, pygame.K_KP2:2,
                           pygame.K_3:3, pygame.K_KP3:3,
                           pygame.K_8:8, pygame.K_KP8:8}
                if event.key in key_map:
                    self.current_edge_type = key_map[event.key]

            if event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
                pos = event.pos

                if pos[0] < self.PANEL_W:
                    if ui["back"].collidepoint(pos):
                        self.stage_manager.change_stage("stage_select"); return

                    for alg in ("A* Search","Greedy BFS","IDA*"):
                        if ui[alg].collidepoint(pos):
                            self.selected_algorithm = alg; self._reset_results(); return

                    if ui["run"].collidepoint(pos):    self._run_ai();        return
                    if ui["cancel"].collidepoint(pos):
                        self.phase="idle"; self.msg="Canceled."; return
                    if ui["reset"].collidepoint(pos):  self._reset_results(); return

                    if ui["replay"] and ui["replay"].collidepoint(pos):
                        self._replay(); return

                    if ui["edit_toggle"].collidepoint(pos):
                        if self.phase in ("searching","returning","nobita_moving"): return
                        self.show_editor = not self.show_editor; return

                    if self.show_editor:
                        ed = ui["editor"]
                        for tid in ("ADD_NODE","CONNECT","DEL_NODE","DEL_EDGE","SET_START","SET_GOAL"):
                            if tid in ed and ed[tid].collidepoint(pos):
                                self.current_tool=tid; self.sel_node_edge=None; return
                        if "SAVE" in ed and ed["SAVE"].collidepoint(pos): self._save_graph_data(); return
                        if "LOAD" in ed and ed["LOAD"].collidepoint(pos): self._load_graph_data(); return

                elif self.map_rect.collidepoint(pos) and self.show_editor and self.phase=="idle":
                    self._handle_canvas(pos)

    def _handle_canvas(self, pos):
        npx = self._nodes_px()
        hit = None
        for i,(nx,ny) in enumerate(npx):
            if math.hypot(nx-pos[0],ny-pos[1])<=12: hit=i; break

        t = self.current_tool
        if t=="ADD_NODE" and hit is None:
            rx=(pos[0]-self.map_rect.x)/self.map_rect.w
            ry=(pos[1]-self.map_rect.y)/self.map_rect.h
            self.nodes.append((rx,ry)); self.edges[len(self.nodes)-1]={}

        elif t in ("CONNECT","DEL_EDGE") and hit is not None:
            if self.sel_node_edge is None:
                self.sel_node_edge = hit
            elif self.sel_node_edge != hit:
                u,v = self.sel_node_edge, hit
                if t=="CONNECT":
                    dist = int(math.hypot(npx[u][0]-npx[v][0], npx[u][1]-npx[v][1]))
                    cost = dist*(1 if self.current_edge_type==1 else 2 if self.current_edge_type==2 else 4)
                    if self.current_edge_type==8: cost=1
                    ed = {"cost":cost,"type":self.current_edge_type}
                    self.edges.setdefault(u,{})[v]=ed
                    self.edges.setdefault(v,{})[u]=ed
                else:
                    self.edges.get(u,{}).pop(v,None)
                    self.edges.get(v,{}).pop(u,None)
                self.sel_node_edge=None

        elif t=="DEL_NODE" and hit is not None and hit not in (self.start_node,self.goal_node):
            self.nodes.pop(hit)
            self.edges.pop(hit,None)
            for u in list(self.edges): self.edges[u].pop(hit,None)
            new_e={}
            for old_u,nb in self.edges.items():
                nu = old_u-1 if old_u>hit else old_u
                new_e[nu]={}
                for old_v,d in nb.items():
                    nv=old_v-1 if old_v>hit else old_v; new_e[nu][nv]=d
            self.edges=new_e
            if self.start_node==hit: self.start_node=None
            elif self.start_node and self.start_node>hit: self.start_node-=1
            if self.goal_node==hit: self.goal_node=None
            elif self.goal_node and self.goal_node>hit: self.goal_node-=1

        elif t=="SET_START" and hit is not None: self.start_node=hit
        elif t=="SET_GOAL"  and hit is not None: self.goal_node=hit

    # ─────── Update ───────
    def update(self):
        now = pygame.time.get_ticks()
        dt  = max(0.0,(now-self._last_ticks)/1000.0)
        self._last_ticks = now

        if self.phase not in ("searching","returning","nobita_moving"): return
        npx = self._nodes_px()

        def step(route, seg, t, spd):
            if not route or seg>=len(route)-1: return seg,t,True,None
            a,b=route[seg],route[seg+1]
            ax,ay=npx[a]; bx,by=npx[b]
            ln=math.hypot(bx-ax,by-ay)
            t += (spd*dt)/ln if ln>1 else 1.0
            if t>=1.0: return seg+1,0.0,False,(a,b)
            return seg,t,False,None

        if self.phase=="searching":
            self.mouse_seg,self.mouse_t,done,fe=step(self.mouse_route,self.mouse_seg,self.mouse_t,self.search_speed)
            if fe: a,b=fe; self.blue_edges_done.add((a,b) if a<b else (b,a))
            if done or self.mouse_seg>=len(self.mouse_route)-1:
                self.mouse_visible=False
                if not self.solution_path:
                    self.phase="done"; self.msg="No path found."; return
                self.phase="returning"; self.msg="Returning..."
                self.mouse_route=list(reversed(self.solution_path))
                self.mouse_seg=0; self.mouse_t=0.0; self.mouse_visible=True

        elif self.phase=="returning":
            self.mouse_seg,self.mouse_t,done,fe=step(self.mouse_route,self.mouse_seg,self.mouse_t,self.search_speed)
            if fe: a,b=fe; self.green_edges_done.add((a,b) if a<b else (b,a))
            if done or self.mouse_seg>=len(self.mouse_route)-1:
                self.mouse_visible=False
                self.phase="nobita_moving"; self.msg="Nobita moving..."
                self.nobita_mode="moving"; self.nobita_seg=0; self.nobita_t=0.0

        elif self.phase=="nobita_moving":
            self.nobita_seg,self.nobita_t,done,fe=step(self.solution_path,self.nobita_seg,self.nobita_t,self.nobita_speed)
            if fe: a,b=fe; self.green_edges_done.add((a,b) if a<b else (b,a))
            if done or self.nobita_seg>=len(self.solution_path)-1:
                self.phase="done"; self.msg="Done!"; self.nobita_mode="at_goal"
                self.victory_panel.show(
                    next_stage_id     = "stage3",
                    next_stage_unlock = "stage3",
                    title    = "CHẶNG 2 HOÀN THÀNH!",
                    subtitle = "Tín hiệu đã được gửi đi!",
                    nodes_visited = self.nodes_expanded,
                    path_cost     = self.path_cost,
                    exec_time     = self.execution_time,      # ← ĐÃ THÊM
                )

    # ─────── Draw ───────
    def draw(self):
        ui  = self._ui_rects()
        npx = self._nodes_px()

        self.slider_search.rect = ui["slider_search"]
        self.slider_nobita.rect = ui["slider_nobita"]

        self.screen.fill(self.c_bg)
        if self.bg_image: self.screen.blit(self.bg_image,(self.map_rect.x,self.map_rect.y))

        if self.show_editor:
            for u,nb in self.edges.items():
                for v,d in nb.items():
                    if u<v:
                        t=d["type"]
                        col=(0,255,255); w=4
                        if t==2: col=(150,150,150); w=2
                        elif t==3: col=(255,0,0);   w=4
                        elif t==8: col=(255,0,255);  w=6
                        pygame.draw.line(self.screen,col,npx[u],npx[v],w)

        for a,b in self.blue_edges_done:
            pygame.draw.line(self.screen,self.BLUE, npx[a],npx[b],self.BLUE_TH)
        for a,b in self.green_edges_done:
            pygame.draw.line(self.screen,self.GREEN,npx[a],npx[b],self.GREEN_TH)

        def draw_partial(route,seg,t,col,thick):
            if not route or seg>=len(route)-1: return None
            a,b=route[seg],route[seg+1]
            ax,ay=npx[a]; bx,by=npx[b]
            tt=max(0.0,min(1.0,t))
            cx,cy=ax+(bx-ax)*tt, ay+(by-ay)*tt
            pygame.draw.line(self.screen,col,(ax,ay),(int(cx),int(cy)),thick); return(cx,cy)

        mouse_pos=None
        if self.mouse_visible:
            col=self.BLUE if self.phase=="searching" else self.GREEN
            thick=self.BLUE_TH if self.phase=="searching" else self.GREEN_TH
            mouse_pos=draw_partial(self.mouse_route,self.mouse_seg,self.mouse_t,col,thick)

        char_h=max(40,int(self.sh*0.08)); mouse_h=max(22,int(self.sh*0.045))
        if self.goal_node is not None:
            self._blit_scaled(self.goal_img_raw, npx[self.goal_node], char_h, self.c_dora)

        nobita_pos = npx[self.start_node] if self.start_node is not None else None
        if self.nobita_mode=="at_goal": nobita_pos=npx[self.goal_node]
        elif self.phase=="nobita_moving" and self.solution_path and self.nobita_seg<len(self.solution_path)-1:
            a,b=self.solution_path[self.nobita_seg],self.solution_path[self.nobita_seg+1]
            tt=max(0.0,min(1.0,self.nobita_t))
            nobita_pos=(npx[a][0]+(npx[b][0]-npx[a][0])*tt, npx[a][1]+(npx[b][1]-npx[a][1])*tt)
        self._blit_scaled(self.start_img_raw, nobita_pos, char_h, self.c_nobita)

        if self.mouse_visible:
            if mouse_pos is None and self.mouse_route:
                mouse_pos=npx[self.mouse_route[min(self.mouse_seg,len(self.mouse_route)-1)]]
            self._blit_scaled(self.mouse_img_raw, mouse_pos, mouse_h, (255,255,0))

        if self.show_editor:
            for i,pos in enumerate(npx):
                col=(255,255,255) if i in (self.start_node,self.goal_node) else (200,200,200)
                pygame.draw.circle(self.screen,col,pos,5)
                pygame.draw.circle(self.screen,(0,0,0),pos,5,1)

        # LEFT PANEL
        panel=pygame.Surface((self.PANEL_W,self.sh),pygame.SRCALPHA)
        panel.fill((30,33,36,200))
        self.screen.blit(panel,(0,0))
        pygame.draw.line(self.screen,(70,75,80),(self.PANEL_W,0),(self.PANEL_W,self.sh),2)

        self.screen.blit(self.title_font.render("CHẶNG 2",     True,(255,200,60)),(self.PAD,10))
        self.screen.blit(self.font.render("Informed Search",True,(180,180,180)),(self.PAD,32))

        for alg in ("A* Search","Greedy BFS","IDA*"):
            self._btn(ui[alg], alg, active=(self.selected_algorithm==alg))

        is_running = self.phase in ("searching", "returning", "nobita_moving")

        self._btn(ui["run"], "▶ RUN AI", color=(46, 204, 113), disabled=is_running)
        self._btn(ui["cancel"], "■ CANCEL", color=(231, 76, 60), disabled=(not is_running))
        self._btn(ui["reset"], "↺ RESET", color=(155, 89, 182))

        self.slider_search.draw(self.screen,self.font)
        self.slider_nobita.draw(self.screen,self.font)

        lbl="EDIT MAP  [-]" if self.show_editor else "EDIT MAP  [+]"
        self._btn(ui["edit_toggle"],lbl,active=self.show_editor)

        if self.show_editor:
            ed=ui["editor"]
            lbl_map={"ADD_NODE":"ADD NODE","CONNECT":"CONNECT",
                     "DEL_NODE":"DEL NODE","DEL_EDGE":"DEL EDGE",
                     "SET_START":"SET START","SET_GOAL":"SET GOAL",
                     "SAVE":"SAVE","LOAD":"LOAD"}
            for tid,lab in lbl_map.items():
                if tid in ed: self._btn(ed[tid],lab,active=(self.current_tool==tid))

        if ui["replay"]: self._btn(ui["replay"],"⟳ REPLAY",color=(230,126,34))
        self._btn(ui["back"],"◀ BACK",color=(231,76,60))

        self._draw_stats()
        self.victory_panel.update()
        self.victory_panel.draw()

    def _draw_stats(self):
        """Stats cố định ở góc trái dưới, ngay trên nút BACK. Đã thêm Thời gian."""
        phase_label={
            "idle":          "Idle",
            "searching":     "🔍 Searching...",
            "returning":     "↩ Returning...",
            "nobita_moving": "🚶 Running...",
            "done":          "✔ Done",
            "completed":     "✔ Done",
        }.get(self.phase, self.phase)

        lines=[
            ("Trạng thái", phase_label),
            ("Nodes duyệt", str(self.nodes_expanded)),
            ("Chi phí",     str(self.path_cost)),
            ("Thời gian",   self.execution_time),          # ← ĐÃ THÊM
        ]
        line_h=18
        total_h=len(lines)*line_h+8
        back_top = self.sh-54
        y0=back_top-total_h-10

        for i,(key,val) in enumerate(lines):
            y=y0+i*line_h
            ks=self.small_font.render(f"{key}:",True,(160,160,160))
            vs=self.small_font.render(str(val), True,(255,220,80))
            self.screen.blit(ks,(self.PAD,y))
            self.screen.blit(vs,(self.PAD+ks.get_width()+4,y))