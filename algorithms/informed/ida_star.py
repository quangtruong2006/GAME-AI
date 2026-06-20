import time
import math
import sys

# Nới lỏng giới hạn đệ quy của Python (Mặc định là 1000 sẽ bị tràn với map lớn)
sys.setrecursionlimit(5000)

def heuristic(nodes, u, v):
    # Tính khoảng cách đường chim bay
    return math.hypot(nodes[u][0] - nodes[v][0], nodes[u][1] - nodes[v][1])

def ida_star(nodes, edges, start, goal):
    start_time = time.perf_counter()
    
    if start is None or goal is None:
        return [], [], 0, "0.0 ms", 0

    threshold = heuristic(nodes, start, goal)
    path = [start]
    visited_order = []
    nodes_expanded = [0]

    def search(current_path, g, bound, best_g_so_far):
        current = current_path[-1]
        visited_order.append(current)
        nodes_expanded[0] += 1
        
        f = g + heuristic(nodes, current, goal)
        if f > bound: 
            return f, False
        if current == goal: 
            return f, True
        
        # QUAN TRỌNG: Cắt tỉa (Pruning)
        # Nếu đã từng đến nút này trong vòng lặp hiện tại với chi phí rẻ hơn hoặc bằng -> Bỏ qua nhánh này
        if best_g_so_far.get(current, float('inf')) <= g:
            return float('inf'), False
        best_g_so_far[current] = g
        
        min_bound = float('inf')
        if current in edges:
            # Sắp xếp các neighbor theo heuristic để ưu tiên đi về hướng đích trước
            neighbors = sorted(edges[current].items(), key=lambda x: heuristic(nodes, x[0], goal))
            for neighbor, data in neighbors:
                if neighbor not in current_path:
                    current_path.append(neighbor)
                    t, found = search(current_path, g + data["cost"], bound, best_g_so_far)
                    if found: 
                        return t, True
                    if t < min_bound: 
                        min_bound = t
                    current_path.pop()
        return min_bound, False

    while True:
        # Reset bộ nhớ tạm sau mỗi lần tăng Bound
        best_g_so_far = {}
        t, found = search(path, 0, threshold, best_g_so_far)
        
        if found: 
            break
        if t == float('inf'):
            path = []
            break
        threshold = t

    # Tính tổng chi phí
    total_cost = 0
    if len(path) > 1:
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i+1]
            total_cost += edges[u][v]["cost"]

    exec_time = f"{(time.perf_counter() - start_time)*1000:.2f} ms"
    return path, visited_order, nodes_expanded[0], exec_time, total_cost