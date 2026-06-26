import random
import math
from algorithms.local.hill_climbing import step_hill_climbing

def step_simulated_annealing(env):
    if env.temperature <= 0.01: 
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