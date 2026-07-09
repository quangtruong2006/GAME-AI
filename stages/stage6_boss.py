# stage6_boss.py

import pygame
import random
import math
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'algorithms', 'adversarial'))
from minimax import minimax
from alphabeta import alphabeta
from expectimax import expectimax

ELEMENT_MULTIPLIER = {
    ("Fire", "Nature"): 2.0, ("Nature", "Fire"): 0.5,
    ("Nature", "Sea"): 2.0, ("Sea", "Nature"): 0.5,
    ("Sea", "Fire"): 2.0, ("Fire", "Sea"): 0.5
}

ELEMENT_COLORS = {
    "Fire": {"primary": (200, 80, 30), "secondary": (255, 140, 50), "glow": (255, 200, 120)},
    "Sea": {"primary": (30, 100, 200), "secondary": (64, 164, 223), "glow": (135, 206, 250)},
    "Nature": {"primary": (40, 140, 60), "secondary": (80, 200, 90), "glow": (150, 255, 160)},
}

ALGO_COLORS = {
    "Minimax": (60, 120, 210),
    "AlphaBeta": (40, 170, 90),
    "Expectimax": (180, 85, 210)
}
ALGO_LIST = ["Minimax", "AlphaBeta", "Expectimax"]


def get_mult(atk, def_):
    return ELEMENT_MULTIPLIER.get((atk, def_), 1.0)


def _find_path():
    for p in [os.path.join("assets", "images", "chang6"),
              os.path.join("assets", "image", "chang6")]:
        if os.path.isdir(p):
            return p
    return "."


ASSET_PATH = _find_path()


def load_img(fname, size=None, flip=False):
    path = os.path.join(ASSET_PATH, fname)
    if not os.path.exists(path):
        print(f"[WARN] {path}")
        return None
    try:
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        if flip:
            img = pygame.transform.flip(img, True, False)
        return img
    except Exception as e:
        print(f"[ERR] {path}: {e}")
        return None


class Assets:
    def __init__(self):
        self.bg = None
        self.dragons = {}
        self.bosses = {}

    def load(self, W, H):
        self.bg = load_img("background.png", (W, H))
        for e in ["Fire", "Sea", "Nature"]:
            self.dragons[e] = load_img(f"dragon_{e.lower()}.png")
            self.bosses[e] = load_img(f"boss_{e.lower()}.png")

    def dragon(self, e):
        return self.dragons.get(e)

    def boss(self, e):
        return self.bosses.get(e)


ASSETS = Assets()


class Pt:
    def __init__(self, x, y, col, vx, vy, sz, life):
        self.x = x
        self.y = y
        self.col = col
        self.vx = vx
        self.vy = vy
        self.sz = sz
        self.life = life
        self.ml = life

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2
        self.life -= 1

    def draw(self, s):
        if self.life <= 0:
            return
        r = max(1, int(self.sz * self.life / self.ml))
        a = int(255 * self.life / self.ml)
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.col[:3], a), (r, r), r)
        s.blit(surf, (int(self.x) - r, int(self.y) - r))


class Particles:
    def __init__(self):
        self.L = []

    def emit(self, x, y, elem, n=25):
        ec = ELEMENT_COLORS.get(elem, {"secondary": (255, 255, 255), "glow": (255, 255, 200)})
        for _ in range(n):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(2, 8)
            col = random.choice([ec["secondary"], ec["glow"], (255, 255, 255)])
            self.L.append(Pt(x, y, col, math.cos(ang) * spd, math.sin(ang) * spd,
                             random.randint(4, 10), random.randint(25, 50)))

    def heal(self, x, y):
        for _ in range(20):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(1, 5)
            col = random.choice([(80, 255, 120), (150, 255, 180), (200, 255, 220), (255, 255, 255)])
            self.L.append(Pt(x, y, col,
                             math.cos(ang) * spd, math.sin(ang) * spd - 1.5,
                             random.randint(3, 8), random.randint(30, 55)))

    def firework(self, x, y):
        col = random.choice([(255, 220, 50), (80, 200, 255), (255, 80, 150), (100, 255, 120)])
        for _ in range(18):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(3, 9)
            self.L.append(Pt(x, y, col, math.cos(ang) * spd, math.sin(ang) * spd,
                             random.randint(3, 8), random.randint(28, 52)))

    def update(self):
        self.L = [p for p in self.L if p.life > 0]
        for p in self.L:
            p.update()

    def draw(self, s):
        for p in self.L:
            p.draw(s)


class SF:
    def __init__(self, v=0.0, spd=0.1):
        self.c = self.t = float(v)
        self.s = spd

    def set(self, v):
        self.t = float(v)

    def snap(self, v):
        self.c = self.t = float(v)

    def update(self):
        self.c += (self.t - self.c) * self.s

    def get(self):
        return self.c


class Anim:
    IDLE = "i"
    ENTER = "e"
    ATK = "a"
    DIE = "d"
    RETREAT = "r"

    def __init__(self, hx, hy, bench_x, bench_y):
        self.hx = hx
        self.hy = hy
        self.bx = bench_x
        self.by = bench_y
        self.x = float(hx)
        self.y = float(hy)
        self.alpha = 255
        self.scale = 1.0
        self.angle = 0.0
        self.state = self.IDLE
        self.t = 0
        self.cb = None

    def enter(self, cb=None):
        self.x = float(self.bx)
        self.y = float(self.by)
        self.alpha = 0
        self.scale = 0.5
        self.state = self.ENTER
        self.t = 0
        self.cb = cb

    def attack(self, tx, ty, cb=None):
        self.tx = tx
        self.ty = ty
        self.state = self.ATK
        self.t = 0
        self.cb = cb

    def retreat(self, cb=None):
        self.state = self.RETREAT
        self.t = 0
        self.cb = cb

    def die(self, cb=None):
        self.state = self.DIE
        self.t = 0
        self.cb = cb

    def busy(self):
        return self.state != self.IDLE

    def _done(self):
        if self.cb:
            c = self.cb
            self.cb = None
            c()

    def update(self):
        if self.state == self.IDLE:
            self.x = float(self.hx)
            self.y = float(self.hy)
            self.scale = 1.0
            self.angle = 0
            self.alpha = 255

        elif self.state == self.ENTER:
            self.t += 1
            p = min(1.0, self.t / 50)
            e = 1 - (1 - p) ** 3
            self.x = self.bx + (self.hx - self.bx) * e
            self.y = self.by + (self.hy - self.by) * e
            self.alpha = int(255 * e)
            self.scale = 0.5 + 0.5 * e
            if p >= 1.0:
                self.x = float(self.hx)
                self.y = float(self.hy)
                self.alpha = 255
                self.scale = 1.0
                self.state = self.IDLE
                self._done()

        elif self.state == self.ATK:
            self.t += 1
            if self.t <= 25:
                p = (self.t / 25) ** 2
                self.x = self.hx + (self.tx - self.hx) * p
                self.y = self.hy + (self.ty - self.hy) * p
                self.scale = 1.0 + 0.15 * p
            elif self.t <= 32:
                self.x = self.tx + random.randint(-5, 5)
                self.y = self.ty + random.randint(-4, 4)
                if self.t == 26:
                    self._done()
            else:
                p = min(1.0, (self.t - 32) / 22)
                e = 1 - (1 - p) ** 2
                self.x = self.tx + (self.hx - self.tx) * e
                self.y = self.ty + (self.hy - self.ty) * e
                self.scale = 1.15 - 0.15 * e
                if p >= 1.0:
                    self.x = float(self.hx)
                    self.y = float(self.hy)
                    self.scale = 1.0
                    self.state = self.IDLE

        elif self.state == self.RETREAT:
            self.t += 1
            p = min(1.0, self.t / 45)
            e = 1 - (1 - p) ** 3
            self.x = self.hx + (self.bx - self.hx) * e
            self.y = self.hy + (self.by - self.hy) * e
            self.scale = 1.0 - 0.5 * e
            self.alpha = int(255 * (1 - e * 0.3))
            if p >= 1.0:
                self.x = float(self.bx)
                self.y = float(self.by)
                self.scale = 0.5
                self.state = self.IDLE
                self._done()

        elif self.state == self.DIE:
            self.t += 1
            p = min(1.0, self.t / 40)
            self.y = self.hy + 90 * p
            self.alpha = int(255 * (1 - p))
            self.angle = -90 * p
            if p >= 1.0:
                self.state = self.IDLE
                self._done()

    def draw(self, surf, img, size):
        if img is None or self.alpha <= 0:
            return
        sw = max(1, int(size[0] * self.scale))
        sh = max(1, int(size[1] * self.scale))
        s = pygame.transform.smoothscale(img, (sw, sh))
        if abs(self.angle) > 0.3:
            s = pygame.transform.rotate(s, self.angle)
        if self.alpha < 255:
            s.set_alpha(self.alpha)
        r = s.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(s, r)


class Skill:
    def __init__(self, n, stype, dmg, acc, cd, heal=0):
        self.name = n
        self.stype = stype
        self.damage = dmg
        self.accuracy = acc
        self.max_cd = cd
        self.cd = 0
        self.heal = heal

    def clone(self):
        s = Skill(self.name, self.stype, self.damage,
                  self.accuracy, self.max_cd, self.heal)
        s.cd = self.cd
        return s

    def ready(self):
        return self.cd == 0


class Dragon:
    def __init__(self, n, e, hp):
        self.name = n
        self.element = e
        self.max_hp = hp
        self.hp = hp
        self.alive = True
        self.skills = []

    def add(self, s):
        self.skills.append(s)

    def hit(self, d):
        self.hp = max(0, self.hp - d)
        if self.hp == 0:
            self.alive = False

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def clone(self):
        d = Dragon(self.name, self.element, self.max_hp)
        d.hp = self.hp
        d.alive = self.alive
        d.skills = [s.clone() for s in self.skills]
        return d


class Player:
    def __init__(self, n):
        self.name = n
        self.dragons = []
        self.ai = 0

    def add(self, d):
        self.dragons.append(d)

    def active(self):
        return self.dragons[self.ai]

    def alive_idx(self):
        return [i for i, d in enumerate(self.dragons) if d.alive]

    def has_alive(self):
        return any(d.alive for d in self.dragons)

    def clone(self):
        p = Player(self.name)
        p.dragons = [d.clone() for d in self.dragons]
        p.ai = self.ai
        return p


def make_team(name, elems):
    p = Player(name)
    for e in elems:
        d = Dragon(f"{e} Dragon", e, 600)
        d.add(Skill("Slash", "normal", 50, 100, 0, heal=0))
        d.add(Skill("Power", "power", 75, 100, 2, heal=0))
        d.add(Skill("Heavy", "ultimate", 125, 50, 2, heal=0))
        p.add(d)
    return p


class GS:
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        self.turn = 0

    def cur(self):
        return self.p1 if self.turn % 2 == 0 else self.p2

    def opp(self):
        return self.p2 if self.turn % 2 == 0 else self.p1

    def over(self):
        return not self.p1.has_alive() or not self.p2.has_alive()

    def winner(self):
        if not self.p1.has_alive():
            return self.p2.name
        if not self.p2.has_alive():
            return self.p1.name
        return None

    def clone(self):
        g = GS(self.p1.clone(), self.p2.clone())
        g.turn = self.turn
        return g

    def actions(self):
        acts = []
        cp = self.cur()
        ad = cp.active()

        for si, s in enumerate(ad.skills):
            if s.ready():
                acts.append({"t": "skill", "si": si})

        for di, d in enumerate(cp.dragons):
            if di != cp.ai and d.alive:
                for si, s in enumerate(d.skills):
                    if s.ready():
                        acts.append({"t": "sw", "di": di, "si": si})

        return acts


def do_act(gs, act, real=False, force=None):
    atk = gs.cur()
    dfn = gs.opp()

    if act["t"] == "sw":
        atk.ai = act["di"]

    ad = atk.active()
    dd = dfn.active()
    sk = ad.skills[act["si"]]

    if force is not None:
        hit = force
    elif real:
        hit = (random.randint(1, 100) <= sk.accuracy)
    else:
        hit = True

    info = {
        "hit": hit,
        "mult": 1.0,
        "dmg": 0,
        "heal": 0,
        "ae": ad.element,
        "de": dd.element,
        "def_died": False,
        "stype": sk.stype,
        "atk_name": ad.name,
    }

    if hit:
        if sk.stype == "normal":
            dmg = 50
            info["mult"] = 1.0
        else:
            m = get_mult(ad.element, dd.element)
            dmg = int(sk.damage * m)
            info["mult"] = m

        dd.hit(dmg)
        info["dmg"] = dmg

        if sk.heal > 0:
            ad.heal(sk.heal)
            info["heal"] = sk.heal

    sk.cd = sk.max_cd + 1

    for d2 in atk.dragons:
        for s2 in d2.skills:
            if s2.cd > 0:
                s2.cd -= 1

    if not dd.alive:
        info["def_died"] = True
        al = dfn.alive_idx()
        if al:
            dfn.ai = al[0]

    gs.turn += 1
    return info


def evaluate(gs, p1p):
    if gs.over():
        w = gs.winner()
        good = (w == gs.p1.name and p1p) or (w != gs.p1.name and not p1p)
        return 999999 if good else -999999

    my = gs.p1 if p1p else gs.p2
    op = gs.p2 if p1p else gs.p1

    score = 0

    my_alive = len(my.alive_idx())
    op_alive = len(op.alive_idx())
    score += (my_alive - op_alive) * 2000

    my_hp = sum(d.hp for d in my.dragons if d.alive)
    op_hp = sum(d.hp for d in op.dragons if d.alive)
    score += (my_hp - op_hp)

    md = my.active()
    od = op.active()
    my_mult = get_mult(md.element, od.element)
    op_mult = get_mult(od.element, md.element)

    if my_mult == 2.0:
        score += 500
    if op_mult == 2.0:
        score -= 500

    if md.hp < md.max_hp * 0.3:
        score -= 200

    ready_skills = sum(1 for s in md.skills if s.ready())
    score += ready_skills * 30

    for d in my.dragons:
        if d.alive and d != md:
            counter_mult = get_mult(d.element, od.element)
            if counter_mult == 2.0:
                score += 150

    return score


class AI:
    @staticmethod
    def act(algo, gs, depth=2):
        is_p1 = (gs.turn % 2 == 0)
        if algo == "Minimax":
            _, action = minimax(gs, depth, True, is_p1)
            return action
        elif algo == "AlphaBeta":
            _, action = alphabeta(gs, depth, float('-inf'), float('inf'), True, is_p1)
            return action
        elif algo == "Expectimax":
            _, action = expectimax(gs, depth, True, is_p1)
            return action


def lerp_c(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def grad_rect(surf, c1, c2, rect, vert=True):
    n = rect.h if vert else rect.w
    for i in range(n):
        t = i / max(1, n - 1)
        c = lerp_c(c1, c2, t)
        if vert:
            pygame.draw.line(surf, c, (rect.x, rect.y + i), (rect.x + rect.w, rect.y + i))
        else:
            pygame.draw.line(surf, c, (rect.x + i, rect.y), (rect.x + i, rect.y + rect.h))


def shdw_rect(surf, col, rect, r=10, sh=3):
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (0, 0, 0, 70), (0, 0, rect.w, rect.h), border_radius=r)
    surf.blit(s, (rect.x + sh, rect.y + sh))
    pygame.draw.rect(surf, col, rect, border_radius=r)


PW = 240
CCW = 210


def layout(W, H):
    arena_x = PW + CCW
    arena_w = W - CCW - arena_x
    arena_cx = arena_x + arena_w // 2
    arena_cy = H // 2
    gap = min(130, arena_w // 4)
    p1fx = arena_cx - gap
    p2fx = arena_cx + gap
    fy = arena_cy - 20
    card_h = (H - 120) // 3
    p1_cards, p2_cards = [], []
    for i in range(3):
        cy = 110 + card_h * i + card_h // 2
        p1_cards.append((PW + CCW // 2, cy))
        p2_cards.append((W - CCW // 2, cy))
    return {
        "arena_x": arena_x, "arena_w": arena_w,
        "arena_cx": arena_cx, "arena_cy": arena_cy,
        "p1fx": p1fx, "p2fx": p2fx, "fy": fy,
        "p1_cards": p1_cards, "p2_cards": p2_cards,
        "card_h": card_h,
    }


class Stage6Boss:
    def __init__(self, screen, stage_manager=None):
        self.screen = screen
        self.sm = stage_manager
        self.W, self.H = screen.get_size()

        self.f11 = pygame.font.SysFont("Segoe UI", 11, bold=True)
        self.f13 = pygame.font.SysFont("Segoe UI", 13, bold=True)
        self.f15 = pygame.font.SysFont("Segoe UI", 15, bold=True)
        self.f18 = pygame.font.SysFont("Segoe UI", 18, bold=True)
        self.f22 = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.f32 = pygame.font.SysFont("Segoe UI", 32, bold=True)

        ASSETS.load(self.W, self.H)

        self.ptc = Particles()
        self.tick = 0
        self.auto = False
        self.ltick = pygame.time.get_ticks()
        self.shake_t = 0
        self.shake_a = 0
        self.flash_c = (255, 255, 255)
        self.flash_v = 0
        self.hp_sm = [SF(1.0, 0.07) for _ in range(6)]

        self.locked = False
        self.log = " ⚔️  Battle has begun!"
        self.switch_timer = 0
        self.pending_attack = None
        self.last_dmg_info = None
        self.last_heal_info = None

        self.algo_p1 = "Minimax"
        self.algo_p2 = "Minimax"
        self.first_turn = 0

        self._build_btns()
        self.reset()

    def _build_btns(self):
        bw = PW - 24
        hbw = (bw - 4) // 2
        col1_x = 12
        col2_x = 12 + hbw + 4

        self.b_back = pygame.Rect(12, 12, bw, 34)

        algo_start_y = 100
        algo_step = 36
        self.b_algos_p1 = {}
        self.b_algos_p2 = {}
        for i, algo in enumerate(ALGO_LIST):
            y = algo_start_y + i * algo_step
            self.b_algos_p1[algo] = pygame.Rect(col1_x, y, hbw, 30)
            self.b_algos_p2[algo] = pygame.Rect(col2_x, y, hbw, 30)

        ft_y = algo_start_y + len(ALGO_LIST) * algo_step + 10
        self.b_first_p1 = pygame.Rect(col1_x, ft_y, hbw, 28)
        self.b_first_p2 = pygame.Rect(col2_x, ft_y, hbw, 28)

        self.divider_y = ft_y + 36

        self.b_auto = pygame.Rect(12, self.H - 90, bw, 40)
        self.b_step = pygame.Rect(12, self.H - 44, bw, 32)

    def reset(self):
        elems = ["Fire", "Sea", "Nature"]
        self.gs = GS(make_team("Nobita", elems),
                     make_team("Boss", elems))
        self.gs.turn = self.first_turn
        self.log = " ⚔️  Battle has begun!"
        self.locked = False
        self.switch_timer = 0
        self.pending_attack = None
        self.last_dmg_info = None
        self.last_heal_info = None
        for i in range(6):
            self.hp_sm[i].snap(1.0)

        self.LO = layout(self.W, self.H)
        LO = self.LO

        self.anims = {}
        for i in range(3):
            cx, cy = LO["p1_cards"][i]
            self.anims[("p1", i)] = Anim(LO["p1fx"], LO["fy"], cx, cy)
        for i in range(3):
            cx, cy = LO["p2_cards"][i]
            self.anims[("p2", i)] = Anim(LO["p2fx"], LO["fy"], cx, cy)

        self._sync_positions()

    def _sync_positions(self):
        LO = self.LO
        for i in range(3):
            a1 = self.anims[("p1", i)]
            if i == self.gs.p1.ai:
                a1.hx = LO["p1fx"]
                a1.hy = LO["fy"]
                a1.x = float(a1.hx)
                a1.y = float(a1.hy)
            else:
                cx, cy = LO["p1_cards"][i]
                a1.hx = a1.bx = cx
                a1.hy = a1.by = cy
                a1.x = float(cx)
                a1.y = float(cy)
            a1.alpha = 255
            a1.scale = 1.0
            a1.state = Anim.IDLE

            a2 = self.anims[("p2", i)]
            if i == self.gs.p2.ai:
                a2.hx = LO["p2fx"]
                a2.hy = LO["fy"]
                a2.x = float(a2.hx)
                a2.y = float(a2.hy)
            else:
                cx, cy = LO["p2_cards"][i]
                a2.hx = a2.bx = cx
                a2.hy = a2.by = cy
                a2.x = float(cx)
                a2.y = float(cy)
            a2.alpha = 255
            a2.scale = 1.0
            a2.state = Anim.IDLE

    def handle_events(self, events):
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                if self.b_back.collidepoint(mx, my):
                    if self.sm:
                        self.sm.change_stage("stage_select")
                    return

                changed = False
                for algo, rect in self.b_algos_p1.items():
                    if rect.collidepoint(mx, my):
                        self.algo_p1 = algo
                        changed = True
                for algo, rect in self.b_algos_p2.items():
                    if rect.collidepoint(mx, my):
                        self.algo_p2 = algo
                        changed = True
                if self.b_first_p1.collidepoint(mx, my):
                    self.first_turn = 0
                    changed = True
                if self.b_first_p2.collidepoint(mx, my):
                    self.first_turn = 1
                    changed = True
                if changed:
                    self.reset()
                    return

                if self.b_auto.collidepoint(mx, my):
                    self.auto = not self.auto
                if self.b_step.collidepoint(mx, my):
                    self._step()

    def _get_algo(self):
        return self.algo_p1 if self.gs.turn % 2 == 0 else self.algo_p2

    def _step(self):
        if self.locked or self.gs.over() or self.switch_timer > 0:
            return
        act = AI.act(self._get_algo(), self.gs, depth=1)
        if not act:
            return
        self.locked = True
        self._animate(act)

    def _animate(self, act):
        gs = self.gs
        cp = gs.cur()
        opp = gs.opp()
        side = "p1" if cp is gs.p1 else "p2"
        opp_s = "p2" if side == "p1" else "p1"
        old_ai = cp.ai

        if act["t"] == "sw":
            new_i = act["di"]
            old_anim = self.anims[(side, old_ai)]
            new_anim = self.anims[(side, new_i)]

            def after_retreat():
                cp.ai = new_i
                LO = self.LO
                cx_old, cy_old = (LO["p1_cards"][old_ai] if side == "p1"
                                  else LO["p2_cards"][old_ai])
                old_anim.hx = old_anim.bx = cx_old
                old_anim.hy = old_anim.by = cy_old
                old_anim.x = float(cx_old)
                old_anim.y = float(cy_old)

                arena_x = LO["p1fx"] if side == "p1" else LO["p2fx"]
                arena_y = LO["fy"]
                new_anim.hx = arena_x
                new_anim.hy = arena_y

                def after_enter():
                    self.switch_timer = 15
                    self.pending_attack = (side, new_i, opp_s, opp.ai, act)

                new_anim.enter(after_enter)

            old_anim.retreat(after_retreat)
        else:
            self._do_atk(side, old_ai, opp_s, opp.ai, act)

    def _do_atk(self, aside, ai, dside, di, act):
        aa = self.anims[(aside, ai)]
        da = self.anims[(dside, di)]

        def on_hit():
            real_act = dict(act)
            if real_act["t"] == "sw":
                real_act["t"] = "skill"
            info = do_act(self.gs, real_act, real=True)

            p_atk = self.gs.p1 if aside == "p1" else self.gs.p2
            atk_dragon = p_atk.dragons[ai]
            sk_name = atk_dragon.skills[act["si"]].name
            algo_used = self.algo_p1 if aside == "p1" else self.algo_p2

            if not info["hit"]:
                dmg_str = "MISS!"
            else:
                if info["stype"] == "normal":
                    dmg_str = f"{int(info['dmg'])} dmg"
                else:
                    m = info["mult"]
                    if m >= 2.0:
                        dmg_str = f"{int(info['dmg'])} dmg (STRONG!)"
                    elif m <= 0.5:
                        dmg_str = f"{int(info['dmg'])} dmg (weak)"
                    else:
                        dmg_str = f"{int(info['dmg'])} dmg"
                if info.get("heal", 0) > 0:
                    dmg_str += f"  +{info['heal']}HP healed"

            if act["t"] == "sw":
                self.log = (f" 🔄 [{p_atk.name}|{algo_used}]"
                            f" → {atk_dragon.name} & {sk_name}: {dmg_str}")
            else:
                self.log = (f" 🗡️ [{p_atk.name}|{algo_used}]"
                            f" {atk_dragon.name} › {sk_name}: {dmg_str}")

            self.last_dmg_info = {
                "hit": info["hit"],
                "dmg": info["dmg"],
                "stype": info["stype"],
                "mult": info["mult"],
                "x": int(da.x),
                "y": int(da.y) - 50,
                "tick": self.tick,
            }

            if info.get("heal", 0) > 0:
                atk_anim = self.anims[(aside, ai)]
                self.last_heal_info = {
                    "heal": info["heal"],
                    "x": int(atk_anim.x),
                    "y": int(atk_anim.y) - 50,
                    "tick": self.tick,
                }
                self.ptc.heal(int(atk_anim.x), int(atk_anim.y))

            if info["hit"]:
                self.shake_t = 18 if info["mult"] >= 2 else 12
                self.shake_a = 8 if info["mult"] >= 2 else 5
                self.flash_v = 130 if info["mult"] >= 2 else 60
                self.flash_c = (ELEMENT_COLORS.get(info["ae"], {})
                                .get("glow", (255, 255, 255)))
                self.ptc.emit(int(da.x), int(da.y), info["ae"], 30)

            for i, d in enumerate(self.gs.p1.dragons):
                self.hp_sm[i].set(d.hp / d.max_hp)
            for i, d in enumerate(self.gs.p2.dragons):
                self.hp_sm[3 + i].set(d.hp / d.max_hp)

            self._post(info, dside, di)

        aa.attack(da.x, da.y, cb=on_hit)

    def _post(self, info, dside, di):
        if info["def_died"]:
            da = self.anims[(dside, di)]

            def ad():
                p = self.gs.p1 if dside == "p1" else self.gs.p2
                ni = p.ai
                if ni != di:
                    na = self.anims[(dside, ni)]
                    LO = self.LO
                    na.hx = LO["p1fx"] if dside == "p1" else LO["p2fx"]
                    na.hy = LO["fy"]

                    def af():
                        self.locked = False

                    na.enter(cb=af)
                else:
                    self.locked = False

            da.die(cb=ad)
        else:
            self.locked = False

    def update(self):
        self.tick += 1
        if self.shake_t > 0:
            self.shake_t -= 1
        if self.flash_v > 0:
            self.flash_v = max(0, self.flash_v - 8)
        self.ptc.update()
        for s in self.hp_sm:
            s.update()
        for a in self.anims.values():
            a.update()

        if self.switch_timer > 0:
            self.switch_timer -= 1
            if self.switch_timer == 0 and self.pending_attack:
                side, new_i, opp_s, opp_ai, act = self.pending_attack
                self.pending_attack = None
                self._do_atk(side, new_i, opp_s, opp_ai, act)

        now = pygame.time.get_ticks()
        if (self.auto and not self.gs.over()
                and not self.locked and self.switch_timer == 0):
            if now - self.ltick > 900:
                self._step()
                self.ltick = now

    def T(self, txt, font, col, x, y, cx=False, sh=False):
        if sh:
            s = font.render(txt, True, (0, 0, 0))
            r = s.get_rect()
            if cx:
                r.center = (x + 2, y + 2)
            else:
                r.topleft = (x + 2, y + 2)
            self.screen.blit(s, r)
        s = font.render(txt, True, col)
        r = s.get_rect()
        if cx:
            r.center = (x, y)
        else:
            r.topleft = (x, y)
        self.screen.blit(s, r)

    def btn(self, rect, label, active=False, danger=False, accent=None, font=None):
        if font is None:
            font = self.f13
        mx, my = pygame.mouse.get_pos()
        hov = rect.collidepoint(mx, my)
        if active:
            bg = accent or (60, 120, 210)
            bd = (255, 255, 255)
        elif hov and danger:
            bg = (140, 40, 40)
            bd = (200, 80, 80)
        elif hov:
            bg = (72, 80, 96)
            bd = (140, 140, 140)
        elif danger:
            bg = (78, 24, 24)
            bd = (130, 50, 50)
        else:
            bg = (42, 46, 58)
            bd = (65, 70, 88)
        shdw_rect(self.screen, bg, rect, r=7, sh=2)
        pygame.draw.rect(self.screen, bd, rect, 2, border_radius=7)
        self.T(label, font, (235, 235, 235), rect.centerx, rect.centery, cx=True)

    def hpbar(self, x, y, w, h, ratio, elem, lbl="", team="p1"):
        c_fill = (50, 200, 80) if team == "p1" else (200, 50, 50)
        c_glow = (120, 255, 150) if team == "p1" else (255, 120, 120)
        pygame.draw.rect(self.screen, (22, 22, 28), (x, y, w, h), border_radius=h // 2)
        fw = max(0, int(w * ratio))
        if fw > 0:
            grad_rect(self.screen, c_fill, c_glow,
                      pygame.Rect(x, y, fw, h), vert=False)
        pygame.draw.rect(self.screen, (6, 6, 6), (x, y, w, h), 2, border_radius=h // 2)
        if lbl:
            self.T(lbl, self.f11, (240, 240, 240), x + w // 2, y + h // 2, cx=True)

    def draw_panel(self):
        r = pygame.Rect(0, 0, PW, self.H)
        grad_rect(self.screen, (16, 18, 26), (26, 30, 42), r)
        pygame.draw.line(self.screen, (52, 58, 76), (PW, 0), (PW, self.H), 2)

        self.btn(self.b_back, " ◀ BACK", danger=True, font=self.f13)

        bw = PW - 24
        hbw = (bw - 4) // 2
        col1_cx = 12 + hbw // 2
        col2_cx = 12 + hbw + 4 + hbw // 2
        c_nobita = (100, 180, 255)
        c_boss = (255, 110, 110)

        self.T("NOBITA", self.f11, c_nobita, col1_cx, 54, cx=True)
        self.T("BOSS", self.f11, c_boss, col2_cx, 54, cx=True)
        pygame.draw.line(self.screen, c_nobita, (12, 64), (12 + hbw, 64), 2)
        pygame.draw.line(self.screen, c_boss, (12 + hbw + 4, 64), (12 + hbw + 4 + hbw, 64), 2)
        self.T("Algorithm", self.f11, (80, 95, 115), PW // 2, 76, cx=True)

        for algo in ALGO_LIST:
            ac = ALGO_COLORS[algo]
            self.btn(self.b_algos_p1[algo], algo,
                     active=(self.algo_p1 == algo), accent=ac, font=self.f11)
            self.btn(self.b_algos_p2[algo], algo,
                     active=(self.algo_p2 == algo), accent=ac, font=self.f11)

        ft_y = self.b_first_p1.y
        self.T("Goes First", self.f11, (80, 95, 115), PW // 2, ft_y - 10, cx=True)
        self.btn(self.b_first_p1, "Nobita 1st",
                 active=(self.first_turn == 0), accent=(50, 110, 200), font=self.f11)
        self.btn(self.b_first_p2, "Boss 1st",
                 active=(self.first_turn == 1), accent=(180, 55, 55), font=self.f11)

        dy = self.divider_y + 6
        pygame.draw.line(self.screen, (52, 58, 76), (10, dy), (PW - 10, dy), 1)

        ly = dy + 8
        self.T("Skill Rules", self.f11, (160, 160, 200), PW // 2, ly, cx=True)
        ly += 14
        legend = [
            ("Slash", "50 dmg  • 100% • CD 0", (180, 180, 120)),
            ("Power", "75 dmg  • 100% • CD 3 turns", (200, 140, 80)),
            ("Heavy", "125 dmg • 50%  • CD 3 turns", (160, 100, 220)),
            ("SW", "Free switch, no lock", (100, 180, 255)),
        ]
        for lname, ldesc, lcol in legend:
            self.T(f"• {lname}:", self.f11, lcol, 14, ly)
            self.T(ldesc, self.f11, (160, 165, 180), 62, ly)
            ly += 13

        pygame.draw.line(self.screen, (52, 58, 76), (10, ly + 2), (PW - 10, ly + 2), 1)
        sy = ly + 8
        p1 = self.gs.p1
        p2 = self.gs.p2
        rows = [
            ("Turn", str(self.gs.turn), str(self.gs.turn)),
            ("HP", str(int(sum(d.hp for d in p1.dragons if d.alive))),
             str(int(sum(d.hp for d in p2.dragons if d.alive)))),
            ("Alive", f"{len(p1.alive_idx())}/3", f"{len(p2.alive_idx())}/3"),
        ]
        for lb, v1, v2 in rows:
            self.T(lb, self.f11, (80, 95, 115), PW // 2, sy, cx=True)
            s1 = self.f11.render(v1, True, c_nobita)
            self.screen.blit(s1, (14, sy))
            s2 = self.f11.render(v2, True, c_boss)
            self.screen.blit(s2, (PW - 14 - s2.get_width(), sy))
            sy += 16

        descs = {
            "Minimax": "Worst-case optimal",
            "AlphaBeta": "Pruned — faster",
            "Expectimax": "Handles acc randomness",
        }
        pygame.draw.line(self.screen, (52, 58, 76),
                         (10, self.H - 108), (PW - 10, self.H - 108), 1)
        self.T(f"P1: {descs.get(self.algo_p1, '')}", self.f11,
               c_nobita, PW // 2, self.H - 98, cx=True)
        self.T(f"P2: {descs.get(self.algo_p2, '')}", self.f11,
               c_boss, PW // 2, self.H - 84, cx=True)

        ac = (42, 148, 68) if self.auto else None
        self.btn(self.b_auto,
                 " ⏹ STOP" if self.auto else " ▶ AUTO",
                 active=self.auto, accent=ac, font=self.f13)
        self.btn(self.b_step, "→  STEP", font=self.f13)

    def draw_card(self, dragon, side, idx, hpi):
        LO = self.LO
        cpos = LO["p1_cards"][idx] if side == "p1" else LO["p2_cards"][idx]
        cx, cy = cpos
        cw = CCW - 10
        ch = LO["card_h"] - 8
        rect = pygame.Rect(cx - cw // 2, cy - ch // 2, cw, ch)

        p = self.gs.p1 if side == "p1" else self.gs.p2
        is_act = (p.ai == idx)
        ec = ELEMENT_COLORS.get(dragon.element, {})

        if not dragon.alive:
            bg = (28, 28, 32)
            bd = (48, 48, 54)
        elif is_act:
            bg = lerp_c(ec.get("primary", (50, 80, 110)), (16, 20, 28), 0.35)
            bd = ec.get("glow", (200, 200, 200))
        else:
            bg = (34, 38, 50)
            bd = (58, 64, 84)

        shdw_rect(self.screen, bg, rect, r=9, sh=3)
        pygame.draw.rect(self.screen, bd, rect,
                         3 if is_act else 1, border_radius=9)

        PAD = 4
        ix = rect.x + PAD
        iy = rect.y + PAD
        iw = rect.w - PAD * 2
        ih = rect.h - PAD * 2
        img_w = int(iw * 0.40)
        img_h = min(img_w, ih - 4)
        img = (ASSETS.dragon(dragon.element) if side == "p1"
               else ASSETS.boss(dragon.element))
        irx = ix
        iry = iy + (ih - img_h) // 2

        if img:
            sc2 = pygame.transform.smoothscale(img, (img_w, img_h))
            if not dragon.alive:
                sc2.set_alpha(55)
            self.screen.blit(sc2, (irx, iry))
        else:
            pygame.draw.circle(self.screen, ec.get("primary", (80, 80, 80)),
                               (irx + img_w // 2, iry + img_h // 2), img_w // 2 - 2)

        fx = ix + img_w + 4
        fy2 = iy
        fw = rect.right - PAD - fx
        if fw < 30:
            fw = 30
        ly = fy2

        badge = pygame.Rect(fx, ly, min(fw, 32), 14)
        pygame.draw.rect(self.screen, ec.get("primary", (55, 55, 65)),
                         badge, border_radius=3)
        self.T(dragon.element[:3].upper(), self.f11,
               ec.get("glow", (255, 255, 255)),
               badge.centerx, badge.centery, cx=True)
        ly += 16

        nc = (210, 215, 225) if dragon.alive else (65, 65, 72)
        fs = self.f11.render(dragon.name, True, nc)
        if fs.get_width() <= fw:
            self.screen.blit(fs, (fx, ly))
        else:
            self.screen.blit(
                self.f11.render(dragon.element[:4], True, nc), (fx, ly))
        ly += 13

        self.hpbar(fx, ly, max(8, fw), 11,
                   self.hp_sm[hpi].get(), dragon.element,
                   f"{int(dragon.hp)}/{dragon.max_hp}", team=side)
        ly += 14

        sk_count = len(dragon.skills)
        if sk_count > 0:
            sw2 = max(1, (fw - (sk_count - 1) * 2) // sk_count)
            sh2 = 13
            if ly + sh2 <= rect.bottom - 2:
                for si, sk in enumerate(dragon.skills):
                    sx2 = fx + si * (sw2 + 2)
                    rdy = sk.ready() and dragon.alive
                    sc3 = (lerp_c(ec.get("primary", (45, 45, 65)), (16, 20, 28), 0.5)
                           if rdy else (28, 31, 41))
                    stc = ec.get("glow", (185, 185, 185)) if rdy else (68, 68, 80)
                    sr = pygame.Rect(sx2, ly, sw2, sh2)
                    pygame.draw.rect(self.screen, sc3, sr, border_radius=3)
                    pygame.draw.rect(self.screen,
                                     ec.get("primary", (52, 52, 72)) if rdy else (45, 47, 57),
                                     sr, 1, border_radius=3)
                    lbl_txt = sk.name[:3] if rdy else f"C{sk.cd}"
                    self.T(lbl_txt, self.f11, stc,
                           sr.centerx, sr.centery, cx=True)

        if not dragon.alive:
            ov = pygame.Surface((cw, ch), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 100))
            self.screen.blit(ov, rect.topleft)
            self.T("💀", self.f18, (180, 50, 50),
                   rect.centerx, rect.centery, cx=True)

    def draw_fighter(self, side, idx):
        LO = self.LO
        p = self.gs.p1 if side == "p1" else self.gs.p2
        d = p.dragons[idx]
        a = self.anims[(side, idx)]
        ec = ELEMENT_COLORS.get(d.element, {})
        img = (ASSETS.dragon(d.element) if side == "p1"
               else ASSETS.boss(d.element))
        fsz = (120, 120)
        a.draw(self.screen, img, fsz)

        bw = 140
        bh = 13
        bx = int(a.x) - bw // 2
        by = int(a.y) - fsz[1] // 2 - 24
        self.hpbar(bx, by, bw, bh,
                   self.hp_sm[idx if side == "p1" else 3 + idx].get(),
                   d.element, f"{int(d.hp)}/{d.max_hp}", team=side)
        self.T(d.name, self.f13, ec.get("glow", (220, 220, 220)),
               int(a.x), by - 15, cx=True, sh=True)

        sk_y = int(a.y) + fsz[1] // 2 + 6
        sk_w = 38
        total = len(d.skills) * (sk_w + 2) - 2
        sk_x0 = int(a.x) - total // 2

        for si, sk in enumerate(d.skills):
            sx = sk_x0 + si * (sk_w + 2)
            rdy = sk.ready() and d.alive
            bg2 = (lerp_c(ec.get("primary", (45, 45, 65)), (16, 20, 28), 0.5)
                   if rdy else (32, 35, 45))
            stc = ec.get("glow", (200, 200, 200)) if rdy else (72, 72, 82)
            sr = pygame.Rect(sx, sk_y, sk_w, 16)
            pygame.draw.rect(self.screen, bg2, sr, border_radius=4)
            pygame.draw.rect(self.screen,
                             ec.get("primary", (58, 58, 78)) if rdy else (48, 50, 60),
                             sr, 1, border_radius=4)
            lbl = sk.name[:5] if rdy else f"C{sk.cd}"
            self.T(lbl, self.f13, stc, sr.centerx, sr.centery, cx=True)
            acc_col = (180, 220, 100) if sk.accuracy == 100 else (220, 160, 80)
            self.T(f"{sk.accuracy}%", self.f11, acc_col,
                   sr.centerx, sr.bottom + 8, cx=True)

    def draw_damage_popup(self):
        if self.last_dmg_info:
            info = self.last_dmg_info
            age = self.tick - info["tick"]
            if age > 70:
                self.last_dmg_info = None
            else:
                alpha = max(0, 255 - age * 3)
                fy2 = info["y"] - age * 1.2

                if not info["hit"]:
                    txt = "MISS"
                    col = (180, 100, 255)
                    font = self.f32
                else:
                    dmg_val = str(int(info["dmg"]))
                    if info["stype"] == "normal":
                        txt = dmg_val
                        col = (255, 165, 50)
                        font = self.f22
                    elif info["mult"] >= 2.0:
                        txt = f"STRONG\n{dmg_val}"
                        col = (255, 60, 60)
                        font = self.f22
                    elif info["mult"] <= 0.5:
                        txt = f"weak\n{dmg_val}"
                        col = (255, 255, 100)
                        font = self.f22
                    else:
                        txt = dmg_val
                        col = (255, 165, 50)
                        font = self.f22

                lines = txt.split('\n')
                start_y = int(fy2) - len(lines) * 13
                for i, line in enumerate(lines):
                    surf = font.render(line, True, col)
                    surf.set_alpha(alpha)
                    r = surf.get_rect(center=(info["x"], start_y + i * 26))
                    sh_s = font.render(line, True, (0, 0, 0))
                    sh_s.set_alpha(alpha // 2)
                    sr = sh_s.get_rect(center=(info["x"] + 2, start_y + i * 26 + 2))
                    self.screen.blit(sh_s, sr)
                    self.screen.blit(surf, r)

        if self.last_heal_info:
            info = self.last_heal_info
            age = self.tick - info["tick"]
            if age > 70:
                self.last_heal_info = None
            else:
                alpha = max(0, 255 - age * 3)
                fy2 = info["y"] - age * 1.0
                txt = f"+{info['heal']} HP"
                col = (80, 255, 140)
                font = self.f22
                surf = font.render(txt, True, col)
                surf.set_alpha(alpha)
                r = surf.get_rect(center=(info["x"], int(fy2)))
                sh_s = font.render(txt, True, (0, 0, 0))
                sh_s.set_alpha(alpha // 2)
                sr = sh_s.get_rect(center=(info["x"] + 2, int(fy2) + 2))
                self.screen.blit(sh_s, sr)
                self.screen.blit(surf, r)

    def draw_badges(self, ox, oy):
        LO = self.LO
        p1 = self.gs.p1
        al1 = len(p1.alive_idx())
        br1 = pygame.Rect(PW + 4 + ox, 6 + oy, CCW - 8, 26)
        bg1 = (22, 52, 22) if p1.has_alive() else (52, 18, 18)
        bd1 = (70, 180, 70) if p1.has_alive() else (180, 55, 55)
        shdw_rect(self.screen, bg1, br1, r=7, sh=2)
        pygame.draw.rect(self.screen, bd1, br1, 2, border_radius=7)
        ac1 = ALGO_COLORS.get(self.algo_p1, (100, 100, 100))
        self.T(f"Nobita [{al1}/3] | {self.algo_p1}",
               self.f11, (220, 232, 220), br1.centerx, br1.centery, cx=True)
        pygame.draw.rect(self.screen, ac1,
                         pygame.Rect(br1.x + 4, br1.bottom + 2, br1.w - 8, 3),
                         border_radius=2)

        p2 = self.gs.p2
        al2 = len(p2.alive_idx())
        bx2 = self.W - CCW + 4 + ox
        br2 = pygame.Rect(bx2, 6 + oy, CCW - 8, 26)
        bg2 = (22, 52, 22) if p2.has_alive() else (52, 18, 18)
        bd2 = (70, 180, 70) if p2.has_alive() else (180, 55, 55)
        shdw_rect(self.screen, bg2, br2, r=7, sh=2)
        pygame.draw.rect(self.screen, bd2, br2, 2, border_radius=7)
        ac2 = ALGO_COLORS.get(self.algo_p2, (100, 100, 100))
        self.T(f"Boss [{al2}/3] | {self.algo_p2}",
               self.f11, (232, 220, 220), br2.centerx, br2.centery, cx=True)
        pygame.draw.rect(self.screen, ac2,
                         pygame.Rect(br2.x + 4, br2.bottom + 2, br2.w - 8, 3),
                         border_radius=2)

    def draw_log(self, ox, oy):
        LO = self.LO
        lw = min(LO["arena_w"] - 20, 560)
        lh = 40
        lx = LO["arena_x"] + (LO["arena_w"] - lw) // 2 + ox
        ly = 10 + oy
        r = pygame.Rect(lx, ly, lw, lh)
        p = abs(math.sin(self.tick * 0.04))
        bc = (int(55 + 55 * p), int(28 + 28 * p), 195)
        shdw_rect(self.screen, (16, 20, 30), r, r=10, sh=4)
        pygame.draw.rect(self.screen, bc, r, 2, border_radius=10)
        self.T(self.log, self.f13, (210, 210, 252),
               r.centerx, r.centery, cx=True, sh=True)

    def draw_turn_indicator(self):
        LO = self.LO
        cur = self.gs.cur()
        is_p1 = (self.gs.turn % 2 == 0)
        algo = self.algo_p1 if is_p1 else self.algo_p2
        ac = ALGO_COLORS.get(algo, (160, 160, 160))
        tr = pygame.Rect(LO["arena_cx"] - 110, self.H - 50, 220, 36)
        shdw_rect(self.screen, (20, 24, 34), tr, r=9, sh=2)
        pygame.draw.rect(self.screen, ac, tr, 2, border_radius=9)
        self.T(f"Turn {self.gs.turn} — {cur.name} [{algo}]",
               self.f13, ac, tr.centerx, tr.centery, cx=True)

    def draw_winner(self):
        ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 185))
        self.screen.blit(ov, (0, 0))
        w = self.gs.winner()
        p = abs(math.sin(self.tick * 0.04))
        gold = lerp_c((165, 118, 16), (252, 218, 68), p)
        bw, bh = 520, 210
        bx = self.W // 2 - bw // 2
        by = self.H // 2 - bh // 2
        br = pygame.Rect(bx, by, bw, bh)
        shdw_rect(self.screen, (18, 22, 32), br, r=16, sh=7)
        pygame.draw.rect(self.screen, gold, br, 4, border_radius=16)
        self.T("🏆  WINNER", self.f22, (165, 138, 48),
               self.W // 2, by + 44, cx=True, sh=True)
        self.T(w.upper(), self.f32, gold,
               self.W // 2, by + 96, cx=True, sh=True)
        info = (f"Nobita: {self.algo_p1}  vs  Boss: {self.algo_p2}"
                f"  |  {'Nobita' if self.first_turn == 0 else 'Boss'} went first")
        self.T(info, self.f11, (180, 180, 200), self.W // 2, by + 148, cx=True)
        self.T("Change algo or first-turn → auto restart",
               self.f11, (130, 130, 155), self.W // 2, by + 168, cx=True)
        if self.tick % 13 == 0:
            self.ptc.firework(
                random.randint(PW + CCW + 40, self.W - CCW - 40),
                random.randint(80, self.H - 80))

    def draw(self):
        ox = (int(math.sin(self.tick * 2) * self.shake_a)
              if self.shake_t > 0 else 0)
        oy = (int(math.cos(self.tick * 2) * self.shake_a * 0.4)
              if self.shake_t > 0 else 0)
        LO = self.LO

        self.screen.fill((10, 10, 14))

        if ASSETS.bg:
            bg_s = pygame.transform.smoothscale(
                ASSETS.bg, (LO["arena_w"], self.H))
            self.screen.blit(bg_s, (LO["arena_x"] + ox, oy))
        else:
            ar = pygame.Rect(LO["arena_x"] + ox, oy, LO["arena_w"], self.H)
            grad_rect(self.screen, (16, 18, 26), (24, 28, 40), ar)

        se = pygame.Surface((280, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(se, (0, 0, 0, 55), (0, 0, 280, 22))
        self.screen.blit(se, (LO["arena_cx"] - 140 + ox, LO["fy"] + 58 + oy))

        self.draw_panel()

        for col_x in [PW, self.W - CCW]:
            cs = pygame.Surface((CCW, self.H), pygame.SRCALPHA)
            cs.fill((10, 12, 20, 185))
            self.screen.blit(cs, (col_x, 0))
            pygame.draw.line(self.screen, (55, 60, 80),
                             (col_x, 0), (col_x, self.H), 1)
            pygame.draw.line(self.screen, (55, 60, 80),
                             (col_x + CCW, 0), (col_x + CCW, self.H), 1)

        self.draw_badges(ox, oy)

        for i, d in enumerate(self.gs.p1.dragons):
            if i != self.gs.p1.ai:
                self.draw_card(d, "p1", i, i)
        for i, d in enumerate(self.gs.p2.dragons):
            if i != self.gs.p2.ai:
                self.draw_card(d, "p2", i, 3 + i)

        self.draw_card(self.gs.p1.dragons[self.gs.p1.ai],
                       "p1", self.gs.p1.ai, self.gs.p1.ai)
        self.draw_card(self.gs.p2.dragons[self.gs.p2.ai],
                       "p2", self.gs.p2.ai, 3 + self.gs.p2.ai)

        for i in range(3):
            if self.anims[("p1", i)].busy() or i == self.gs.p1.ai:
                self.draw_fighter("p1", i)
        for i in range(3):
            if self.anims[("p2", i)].busy() or i == self.gs.p2.ai:
                self.draw_fighter("p2", i)

        self.draw_damage_popup()
        self.draw_log(ox, oy)
        self.draw_turn_indicator()
        self.ptc.draw(self.screen)

        if self.flash_v > 0:
            fl = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            fl.fill((*self.flash_c, self.flash_v))
            self.screen.blit(fl, (0, 0))

        if self.gs.over():
            self.draw_winner()


def main():
    pygame.init()
    screen = pygame.display.set_mode((1280, 780), pygame.RESIZABLE)
    pygame.display.set_caption("⚔️  Dragon Battle — Stage 6")
    clock = pygame.time.Clock()
    stage = Stage6Boss(screen)

    while True:
        events = pygame.event.get()
        for e in events:
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            if e.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(e.size, pygame.RESIZABLE)
                stage.screen = screen
                stage.W, stage.H = e.size
                stage._build_btns()
                stage.LO = layout(stage.W, stage.H)
                stage._sync_positions()
        stage.handle_events(events)
        stage.update()
        stage.draw()
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()