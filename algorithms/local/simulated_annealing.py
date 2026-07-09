import random
import math
from algorithms.local.hill_climbing import step_hill_climbing

def step_simulated_annealing(env):
    # ════════════════════════════════════════════
    # Khởi tạo tham số lần đầu (nếu chưa có)
    # ════════════════════════════════════════════
    if not hasattr(env, 'temperature'):
        env.temperature = 1000.0
        env.cooling_rate = 0.995
        env.min_temperature = 0.01
    
    # Nếu có temperature nhưng chưa có min_temperature
    if not hasattr(env, 'min_temperature'):
        env.min_temperature = 0.01
    
    # Nếu có temperature nhưng chưa có cooling_rate
    if not hasattr(env, 'cooling_rate'):
        env.cooling_rate = 0.995
    
    # ════════════════════════════════════════════
    # Chuyển sang Hill Climbing khi T quá thấp
    # ════════════════════════════════════════════
    if env.temperature <= env.min_temperature: 
        return step_hill_climbing(env)

    neighbors = env.get_neighbors(env.grid)
    if not neighbors:
        return None

    next_state = random.choice(neighbors)
    next_fitness = env.calculate_fitness(next_state)

    delta = next_fitness - env.current_fitness

    chosen_state = None
    if delta > 0:
        chosen_state = next_state
    else:
        p = math.exp(delta / env.temperature)
        if random.uniform(0, 1) < p:
            chosen_state = next_state 
        else:
            chosen_state = env.grid 
    
    env.temperature *= env.cooling_rate
    return chosen_state