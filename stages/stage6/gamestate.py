class GameState:
    def __init__(self, player1, player2):
        self.p1 = player1
        self.p2 = player2
        self.turn_count = 0  # Chẵn: p1 đánh, Lẻ: p2 đánh

    def get_current_player(self):
        return self.p1 if self.turn_count % 2 == 0 else self.p2

    def get_waiting_player(self):
        return self.p2 if self.turn_count % 2 == 0 else self.p1

    def is_game_over(self):
        return not self.p1.has_alive_dragons() or not self.p2.has_alive_dragons()

    def get_winner(self):
        if not self.p1.has_alive_dragons(): return self.p2.name
        if not self.p2.has_alive_dragons(): return self.p1.name
        return None

    def clone(self):
        new_state = GameState(self.p1.clone(), self.p2.clone())
        new_state.turn_count = self.turn_count
        return new_state

    def get_possible_actions(self):
        actions = []
        curr_player = self.get_current_player()
        active_idx = curr_player.active_index
        active_dragon = curr_player.get_active_dragon()

        # 1. Các skill của rồng hiện tại
        for s_idx, skill in enumerate(active_dragon.skills):
            if skill.is_ready():
                actions.append({'type': 'skill', 'skill_idx': s_idx})

        # 2. Switch sang rồng khác và dùng skill
        for d_idx, dragon in enumerate(curr_player.dragons):
            if d_idx != active_idx and dragon.alive and dragon.switch_lock == 0:
                for s_idx, skill in enumerate(dragon.skills):
                    if skill.is_ready():
                        actions.append({'type': 'switch_and_skill', 'dragon_idx': d_idx, 'skill_idx': s_idx})
        return actions