# File: algorithms/uninformed/bfs.py
from collections import deque
import time

def bfs(graph, start, goal):
    """
    Thuật toán BFS duyệt theo Đồ thị bám sát cấu trúc slide bài giảng.
    Kiểm tra Goal-test ngay khi sinh node con (child node).
    """
    start_time = time.time()
    
    if start not in graph or goal not in graph:
        return [], [], 0, "0.0 ms"
        
    # SỬA THEO SLIDE: Kiểm tra Goal ngay tại node khởi tạo ban đầu
    if start == goal:
        end_time = time.time()
        exec_time = (end_time - start_time) * 1000
        return [], [], 1, f"{exec_time:.2f} ms"

    # frontier <- FIFO-QUEUE với node khởi tạo ban đầu
    queue = deque([start])
    # explored <- tập các state đã khám phá (Để tối ưu kết hợp tránh lặp node trong frontier)
    visited = {start}
    parent = {start: None}      
    visited_order = []  # Lưu các node được lấy ra (frontier.REMOVE) để Pygame vẽ

    found = False
    
    while queue:
        # node <- frontier.REMOVE() (lấy node đầu tiên trong queue)
        curr = queue.popleft()
        
        # Thêm vào danh sách đã duyệt để hiển thị hiệu ứng trên giao diện
        if curr != start and curr != goal:
            visited_order.append(curr)
            
        # explored <- explored U {node.STATE}
        # Duyệt qua từng hành động/láng giềng kề cạnh: for each action in problem.ACTIONS(node.STATE)
        for neighbor in graph[curr]:
            # if child.STATE not in explored AND child not in frontier
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = curr
                
                # SỬA THEO SLIDE: if problem.GOAL-TEST(child.STATE) then return SOLUTION(child)
                if neighbor == goal:
                    found = True
                    break
                
                # frontier.INSERT(child)
                queue.append(neighbor)
                
        if found:
            break

    # Truy vết đường đi (SOLUTION)
    path = []
    if found:
        curr = goal
        while curr is not None:
            if curr != start and curr != goal:
                path.append(curr)
            curr = parent[curr]
        path.reverse()  # Đảo ngược từ Gốc -> Đích

    end_time = time.time()
    execution_time = (end_time - start_time) * 1000
    nodes_expanded = len(visited_order)

    return path, visited_order, nodes_expanded, f"{execution_time:.2f} ms"