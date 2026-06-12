import time

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def greedy_search(grid, start, goal):
    start_time = time.time()
    rows, cols = len(grid), len(grid[0])
    
    if grid[start[0]][start[1]] == 99 or grid[goal[0]][goal[1]] == 99:
        return [], [], 0, "0.0 ms"

    frontier = [(heuristic(start, goal), start)]
    reached = set()
    parent = {start: None}
    visited_order = []
    found = False

    while frontier:
        frontier.sort(key=lambda x: x[0])
        _, n = frontier.pop(0)
        
        if n != start and n != goal:
            visited_order.append(n)

        if n == goal:
            found = True
            break

        reached.add(n)

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            m = (n[0] + dr, n[1] + dc)
            if 0 <= m[0] < rows and 0 <= m[1] < cols and grid[m[0]][m[1]] != 99:
                in_frontier = any(item[1] == m for item in frontier)
                if not in_frontier and m not in reached:
                    parent[m] = n
                    frontier.append((heuristic(m, goal), m))

    path = []
    if found:
        curr = goal
        while curr is not None:
            if curr != start and curr != goal:
                path.append(curr)
            curr = parent[curr]
        path.reverse()

    end_time = time.time()
    exec_time = (end_time - start_time) * 1000
    return path, visited_order, len(visited_order), f"{exec_time:.2f} ms"