import time
import math
import heapq

def heuristic(nodes, u, v):
    # Tính khoảng cách đường chim bay giữa 2 Nút trên bản đồ
    return math.hypot(nodes[u][0] - nodes[v][0], nodes[u][1] - nodes[v][1])

def a_star(nodes, edges, start, goal):
    start_time = time.perf_counter()
    
    # Kiểm tra nếu chưa đặt điểm Start hoặc Goal
    if start is None or goal is None:
        return [], [], 0, "0.0 ms", 0

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(nodes, start, goal)}
    visited_order = []
    nodes_expanded = 0

    while open_set:
        # Lấy node có f_score nhỏ nhất ra khỏi hàng đợi
        current = heapq.heappop(open_set)[1]
        visited_order.append(current)
        nodes_expanded += 1

        # Nếu tìm thấy đích (Shizuka)
        if current == goal:
            path = []
            curr_trace = current
            while curr_trace in came_from:
                path.append(curr_trace)
                curr_trace = came_from[curr_trace]
            path.append(start)
            path.reverse()
            
            exec_time = f"{(time.perf_counter() - start_time)*1000:.2f} ms"
            return path, visited_order, nodes_expanded, exec_time, g_score[goal]

        # Duyệt qua các con đường (edges) nối với node hiện tại
        if current in edges:
            for neighbor, data in edges[current].items():
                # data["cost"] chính là chi phí kẹt xe/quốc lộ/metro mà ông đã set
                tentative_g_score = g_score[current] + data["cost"]
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(nodes, neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

    # Chạy hết map mà không thấy đường (bị cụt)
    exec_time = f"{(time.perf_counter() - start_time)*1000:.2f} ms"
    return [], visited_order, nodes_expanded, exec_time, 0