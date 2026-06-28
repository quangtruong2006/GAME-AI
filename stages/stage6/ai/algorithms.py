# stage6/ai/algorithms.py
from evaluation import evaluate_state
from combat import Combat

class AI:
    @staticmethod
    def get_best_action(algo_name, gamestate, depth=2):
        is_p1 = (gamestate.turn_count % 2 == 0)
        
        if algo_name == "Minimax":
            _, action = AI._minimax(gamestate, depth, True, is_p1)
        elif algo_name == "AlphaBeta":
            _, action = AI._alphabeta(gamestate, depth, float('-inf'), float('inf'), True, is_p1)
        elif algo_name == "Expectimax":
            _, action = AI._expectimax(gamestate, depth, True, is_p1)
        return action

    @staticmethod
    def _minimax(state, depth, is_maximizing, is_p1_perspective):
        if depth == 0 or state.is_game_over():
            return evaluate_state(state, is_p1_perspective), None

        actions = state.get_possible_actions()
        best_action = actions[0] if actions else None

        if is_maximizing:
            max_eval = float('-inf')
            for action in actions:
                sim_state = state.clone()
                Combat.execute_action(sim_state, action, is_real_combat=False, force_hit=True)
                eval_val, _ = AI._minimax(sim_state, depth - 1, False, is_p1_perspective)
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_action = action
            return max_eval, best_action
        else:
            min_eval = float('inf')
            for action in actions:
                sim_state = state.clone()
                Combat.execute_action(sim_state, action, is_real_combat=False, force_hit=True)
                eval_val, _ = AI._minimax(sim_state, depth - 1, True, is_p1_perspective)
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_action = action
            return min_eval, best_action

    @staticmethod
    def _alphabeta(state, depth, alpha, beta, is_maximizing, is_p1_perspective):
        if depth == 0 or state.is_game_over():
            return evaluate_state(state, is_p1_perspective), None

        actions = state.get_possible_actions()
        best_action = actions[0] if actions else None

        if is_maximizing:
            max_eval = float('-inf')
            for action in actions:
                sim_state = state.clone()
                Combat.execute_action(sim_state, action, is_real_combat=False, force_hit=True)
                eval_val, _ = AI._alphabeta(sim_state, depth - 1, alpha, beta, False, is_p1_perspective)
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_action = action
                alpha = max(alpha, eval_val)
                if beta <= alpha: break
            return max_eval, best_action
        else:
            min_eval = float('inf')
            for action in actions:
                sim_state = state.clone()
                Combat.execute_action(sim_state, action, is_real_combat=False, force_hit=True)
                eval_val, _ = AI._alphabeta(sim_state, depth - 1, alpha, beta, True, is_p1_perspective)
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_action = action
                beta = min(beta, eval_val)
                if beta <= alpha: break
            return min_eval, best_action

    @staticmethod
    def _expectimax(state, depth, is_maximizing, is_p1_perspective):
        if depth == 0 or state.is_game_over():
            return evaluate_state(state, is_p1_perspective), None

        actions = state.get_possible_actions()
        best_action = actions[0] if actions else None

        if is_maximizing:
            max_eval = float('-inf')
            for action in actions:
                eval_val = AI._chance_node(state, action, depth, False, is_p1_perspective)
                if eval_val > max_eval:
                    max_eval = eval_val
                    best_action = action
            return max_eval, best_action
        else:
            min_eval = float('inf')
            # Thường Expectimax phe địch (nếu địch k dùng Expectimax thì giả định địch là min)
            # Ở đây đơn giản hóa địch vẫn chọn action tối ưu nhất của địch.
            for action in actions:
                eval_val = AI._chance_node(state, action, depth, True, is_p1_perspective)
                if eval_val < min_eval:
                    min_eval = eval_val
                    best_action = action
            return min_eval, best_action

    @staticmethod
    def _chance_node(state, action, depth, next_is_max, is_p1_perspective):
        curr_player = state.get_current_player()
        dragon_idx = action['dragon_idx'] if action['type'] == 'switch_and_skill' else curr_player.active_index
        skill = curr_player.dragons[dragon_idx].skills[action['skill_idx']]
        
        acc = skill.accuracy / 100.0
        
        # Nhánh Hit
        state_hit = state.clone()
        Combat.execute_action(state_hit, action, is_real_combat=False, force_hit=True)
        eval_hit, _ = AI._expectimax(state_hit, depth - 1, next_is_max, is_p1_perspective)
        
        # Nhánh Miss
        eval_miss = 0
        if acc < 1.0:
            state_miss = state.clone()
            Combat.execute_action(state_miss, action, is_real_combat=False, force_hit=False)
            eval_miss, _ = AI._expectimax(state_miss, depth - 1, next_is_max, is_p1_perspective)
            
        return (acc * eval_hit) + ((1.0 - acc) * eval_miss)