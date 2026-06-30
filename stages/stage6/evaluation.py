from database import get_element_multiplier

def evaluate_state(gamestate, is_p1_perspective):
    if gamestate.is_game_over():
        winner = gamestate.get_winner()
        if winner == gamestate.p1.name: return 999999 if is_p1_perspective else -999999
        else: return -999999 if is_p1_perspective else 999999

    my_p = gamestate.p1 if is_p1_perspective else gamestate.p2
    opp_p = gamestate.p2 if is_p1_perspective else gamestate.p1

    my_d = my_p.get_active_dragon()
    opp_d = opp_p.get_active_dragon()

    my_total_hp = sum(d.current_hp for d in my_p.dragons if d.alive)
    opp_total_hp = sum(d.current_hp for d in opp_p.dragons if d.alive)
    
    my_alive_count = len(my_p.get_alive_indices())
    opp_alive_count = len(opp_p.get_alive_indices())

    elem_advantage = get_element_multiplier(my_d.element, opp_d.element)
    elem_disadvantage = get_element_multiplier(opp_d.element, my_d.element)

    score = 0
    score += (my_total_hp - opp_total_hp)
    score += (my_alive_count * 1000) - (opp_alive_count * 1000)
    
    if elem_advantage == 2.0: score += 100
    if elem_disadvantage == 2.0: score -= 50

    # Skill buff: thưởng điểm khi skill sẵn sàng, Heavy Strike thưởng nhiều hơn vì dame cao
    if my_d.skills[1].is_ready(): score += 30  # Power Strike  (dame 75,  acc 100%)
    if my_d.skills[2].is_ready(): score += 50  # Heavy Strike  (dame 125, acc  50%)

    return score