import random
from database import get_element_multiplier

class Combat:
    @staticmethod
    def execute_action(gamestate, action, is_real_combat=False, force_hit=None):
        # action dict format: {'type': 'skill', 'skill_idx': 0} 
        # or {'type': 'switch_and_skill', 'dragon_idx': 1, 'skill_idx': 0}
        
        attacker = gamestate.get_current_player()
        defender = gamestate.get_waiting_player()
        
        # 1. Xử lý Switch (nếu có)
        if action['type'] == 'switch_and_skill':
            # Khóa rồng cũ
            old_dragon = attacker.get_active_dragon()
            old_dragon.switch_lock = 2
            # Đổi rồng mới
            attacker.active_index = action['dragon_idx']

        # 2. Lấy người tấn công mới và kỹ năng
        active_atk_dragon = attacker.get_active_dragon()
        skill = active_atk_dragon.skills[action['skill_idx']]
        active_def_dragon = defender.get_active_dragon()

        # 3. Tính toán Hit/Miss
        is_hit = False
        if force_hit is not None:
            is_hit = force_hit
        else:
            # Nếu là combat thật, roll random
            if is_real_combat:
                roll = random.randint(1, 100)
                is_hit = roll <= skill.accuracy
            else:
                # Trong Minimax/AlphaBeta không biết xác suất, giả định luôn trúng
                is_hit = True

        # 4. Tính toán Damage
        damage = 0
        if is_hit:
            multiplier = get_element_multiplier(active_atk_dragon.element, active_def_dragon.element)
            damage = skill.damage * multiplier
            active_def_dragon.take_damage(damage)
            
        # Kích hoạt cooldown
        skill.current_cooldown = skill.max_cooldown

        # 5. Xử lý sau lượt (Cooldown & Switch Lock)
        Combat._end_turn_updates(attacker)
        
        # 6. Kiểm tra chết & Buộc Switch
        if not active_def_dragon.alive:
            alive_indices = defender.get_alive_indices()
            if alive_indices:
                # Tạm thời tự động đẩy quái tiếp theo ra sân
                defender.active_index = alive_indices[0]

        # Đổi lượt
        gamestate.turn_count += 1

    @staticmethod
    def _end_turn_updates(player):
        for d in player.dragons:
            if d.switch_lock > 0:
                d.switch_lock -= 1
            for s in d.skills:
                if s.current_cooldown > 0:
                    s.current_cooldown -= 1