def step_local_beam_search(env):
    if not hasattr(env, 'beam_states') or not env.beam_states:
        env.beam_states = [env.grid]
        env.k_beam = 3 

    all_neighbors = []
    for state in env.beam_states:
        neighbors = env.get_neighbors(state)
        all_neighbors.extend(neighbors)

    if not all_neighbors:
        return None

    scored_neighbors = []
    for n in all_neighbors:
        scored_neighbors.append((env.calculate_fitness(n), n))

    scored_neighbors.sort(key=lambda x: x[0], reverse=True)

    next_beam = []
    seen = [] 
    for score, state in scored_neighbors:
        if state not in seen:
            seen.append(state)
            next_beam.append(state)
        if len(next_beam) == env.k_beam: 
            break
            
    env.beam_states = next_beam
    return env.beam_states[0] if env.beam_states else None