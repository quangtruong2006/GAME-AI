from combat import Combat
from ai.algorithms import AI

class Battle:
    def __init__(self, gamestate, selected_algorithm):
        self.gamestate = gamestate
        self.algo = selected_algorithm
        self.last_action_log = ""
        self.delay_timer = 0 # Để delay lượt AI nhìn cho rõ

    def update(self):
        if self.gamestate.is_game_over():
            return
            
        curr_player = self.gamestate.get_current_player()
        
        # Vì cả 2 đều là AI chơi chung thuật toán
        best_action = AI.get_best_action(self.algo, self.gamestate, depth=2)
        
        if best_action:
            action_type = best_action['type']
            s_idx = best_action['skill_idx']
            if action_type == 'switch_and_skill':
                d_idx = best_action['dragon_idx']
                d_name = curr_player.dragons[d_idx].name
                s_name = curr_player.dragons[d_idx].skills[s_idx].name
                self.last_action_log = f"{curr_player.name} Switched to {d_name} & used {s_name}!"
            else:
                s_name = curr_player.get_active_dragon().skills[s_idx].name
                self.last_action_log = f"{curr_player.name} used {s_name}!"

            Combat.execute_action(self.gamestate, best_action, is_real_combat=True)