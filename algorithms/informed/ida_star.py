import time

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def ida_star(grid, start, goal):
    start_time = time.time()
    rows, cols = len(grid), len(grid[0])
    
    if grid[start[0]][start[1]] == 99 or grid[goal[0]][goal[1]] == 99:
        return [], [], 0, "0.0 ms"

    all_visited_order = []

    def search(node, g, bound, path, visited_this_round):
        f = g + heuristic(node, goal)
        if f > bound:
            return f
        if node == goal:
            return "FOUND"
            
        if node != start and node != goal and node not in visited_this_round:
            visited_this_round.append(node)
            if node not in all_visited_order:
                all_visited_order.append(node)

        min_bound = float('inf')
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = (node[0] + dr, node[1] + dc)
            if 0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols and grid[neighbor[0]][neighbor[1]] != 99:
                if neighbor not in path:
                    path.append(neighbor)
                    cost_neighbor = grid[neighbor[0]][neighbor[1]] # Cộng cost thực tế của ô lưới
                    t = search(neighbor, g + cost_neighbor, bound, path, visited_this_round)
                    if t == "FOUND":
                        return "FOUND"
                    if t < min_bound:
                        min_bound = t
                    path.pop()
        return min_bound

    bound = heuristic(start, goal)
    path = [start]
    found = False
    
    while True:
        visited_this_round = []
        t = search(start, 0, bound, path, visited_this_round)
        if t == "FOUND":
            found = True
            break
        if t == float('inf'):
            break
        bound = t

    final_path = [n for n in path if n != start and n != goal] if found else []
    end_time = time.time()
    exec_time = (end_time - start_time) * 1000
    return final_path, all_visited_order, len(all_visited_order), f"{exec_time:.2f} ms"