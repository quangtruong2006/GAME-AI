from collections import deque
import time

def bfs(graph, start, goal):
    start_time = time.perf_counter()
    
    if start not in graph or goal not in graph:
        return [], [], 0, 0.0
        
    if start == goal:
        return [], [], 1, (time.perf_counter() - start_time) * 1000.0

    queue = deque([start])
    visited = {start}
    parent = {start: None}
    visited_order = []

    found = False
    while queue:
        curr = queue.popleft()
        if curr != start and curr != goal:
            visited_order.append(curr)
            
        for neighbor in graph[curr]:
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = curr
                
                if neighbor == goal:
                    found = True
                    break
                queue.append(neighbor)
        if found:
            break

    # Truy vết đường đi
    path = []
    if found:
        curr = goal
        while curr is not None:
            path.append(curr)
            curr = parent.get(curr)
        path.reverse()

    exec_ms = (time.perf_counter() - start_time) * 1000.0
    nodes_expanded = len(visited_order)
    return path, visited_order, nodes_expanded, exec_ms