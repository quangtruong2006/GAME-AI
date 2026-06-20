import time
import math
import heapq

def heuristic(nodes, u, v):
    return math.hypot(nodes[u][0] - nodes[v][0], nodes[u][1] - nodes[v][1])

def greedy_search(nodes, edges, start, goal):
    start_time = time.perf_counter()
    
    if start is None or goal is None:
        return [], [], 0, "0.0 ms", 0

    open_set = []
    heapq.heappush(open_set, (heuristic(nodes, start, goal), start))
    came_from = {}
    visited = set([start])
    visited_order = []
    nodes_expanded = 0

    while open_set:
        current = heapq.heappop(open_set)[1]
        visited_order.append(current)
        nodes_expanded += 1

        if current == goal:
            path = []
            total_cost = 0
            curr_trace = current
            while curr_trace in came_from:
                prev = came_from[curr_trace]
                total_cost += edges[prev][curr_trace]["cost"]
                path.append(curr_trace)
                curr_trace = prev
            path.append(start)
            path.reverse()
            
            exec_time = f"{(time.perf_counter() - start_time)*1000:.2f} ms"
            return path, visited_order, nodes_expanded, exec_time, total_cost

        if current in edges:
            for neighbor in edges[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    came_from[neighbor] = current
                    heapq.heappush(open_set, (heuristic(nodes, neighbor, goal), neighbor))

    exec_time = f"{(time.perf_counter() - start_time)*1000:.2f} ms"
    return [], visited_order, nodes_expanded, exec_time, 0