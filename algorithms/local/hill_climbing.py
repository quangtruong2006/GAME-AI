def step_hill_climbing(env):
    neighbors = env.get_neighbors(env.grid)
    if not neighbors:
        return None

    best_neighbor = None
    best_fitness = env.current_fitness 

    for neighbor in neighbors:
        f = env.calculate_fitness(neighbor)
        if f > best_fitness: 
            best_fitness = f
            best_neighbor = neighbor

    return best_neighbor