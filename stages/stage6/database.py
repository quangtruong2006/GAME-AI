from dragon import Dragon
from skill import Skill
from player import Player

ELEMENT_MULTIPLIER = {
    ("Earth", "Water"): 2.0, ("Water", "Earth"): 0.5,
    ("Water", "Electric"): 2.0, ("Electric", "Water"): 0.5,
    ("Electric", "War"): 2.0, ("War", "Electric"): 0.5,
    ("War", "Earth"): 2.0, ("Earth", "War"): 0.5
}

def get_element_multiplier(atk_elem, def_elem):
    return ELEMENT_MULTIPLIER.get((atk_elem, def_elem), 1.0)

def create_base_skills():
    return [
        Skill("Attack",       50,  100, 0),  # Đòn thường, luôn sẵn sàng
        Skill("Power Strike", 75,  100, 3),  # Skill 1: dame 75, acc 100%, cd 3
        Skill("Heavy Strike", 125,  50, 3),  # Skill 2: dame 125, acc 50%, cd 3
    ]

def create_team(name, elements):
    player = Player(name)
    for i, elem in enumerate(elements):
        d = Dragon(f"{elem} Entity {i+1}", elem, 200)
        for s in create_base_skills():
            d.add_skill(s)
        player.add_dragon(d)
    return player

def get_player_team():
    return create_team("Nobita", ["Earth", "Water", "Electric", "War"])

def get_boss_team():
    # Boss thứ tự ngược lại để có sự đa dạng
    return create_team("Boss", ["Water", "Electric", "War", "Earth"])