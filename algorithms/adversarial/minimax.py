# GAME-AI/algorithms/adversarial/minimax.py

def minimax(gamestate, depth, is_maximizing, is_p1_perspective):
    if depth == 0 or gamestate.over():
        return evaluate(gamestate, is_p1_perspective), None
    
    actions = gamestate.actions()
    if not actions:
        return evaluate(gamestate, is_p1_perspective), None
    
    best_action = actions[0]
    best_score = float('-inf') if is_maximizing else float('inf')
    
    for action in actions:
        sim = gamestate.clone()
        execute_action(sim, action)
        score, _ = minimax(sim, depth - 1, not is_maximizing, is_p1_perspective)
        
        if is_maximizing:
            if score > best_score:
                best_score = score
                best_action = action
        else:
            if score < best_score:
                best_score = score
                best_action = action
    
    return best_score, best_action


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


def get_mult(atk, def_):
    multiplier = {
        ("Fire", "Nature"): 2.0, ("Nature", "Fire"): 0.5,
        ("Nature", "Sea"): 2.0, ("Sea", "Nature"): 0.5,
        ("Sea", "Fire"): 2.0, ("Fire", "Sea"): 0.5
    }
    return multiplier.get((atk, def_), 1.0)


def execute_action(gs, act):
    atk = gs.cur()
    dfn = gs.opp()

    if act["t"] == "sw":
        atk.ai = act["di"]

    ad = atk.active()
    dd = dfn.active()
    sk = ad.skills[act["si"]]

    hit = True

    if hit:
        if sk.stype == "normal":
            dmg = 50
        else:
            m = get_mult(ad.element, dd.element)
            dmg = int(sk.damage * m)

        dd.hit(dmg)

    sk.cd = sk.max_cd + 1

    for d2 in atk.dragons:
        for s2 in d2.skills:
            if s2.cd > 0:
                s2.cd -= 1

    if not dd.alive:
        al = dfn.alive_idx()
        if al:
            dfn.ai = al[0]

    gs.turn += 1