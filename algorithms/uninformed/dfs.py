# File: algorithms/uninformed/dfs.py
import time

def dfs(graph, start, goal):
    """
    Thuật toán DFS dùng LIFO Stack bám sát slide bài giảng.
    Kiểm tra Goal-test ngay khi sinh node con (child node) - giống BFS.
    """
    start_time = time.time()

    if start not in graph or goal not in graph:
        return [], [], 0, "0.0 ms"

    # Kiểm tra goal ngay tại node ban đầu
    if start == goal:
        end_time = time.time()
        exec_time = (end_time - start_time) * 1000
        return [], [], 1, f"{exec_time:.2f} ms"

    # frontier <- LIFO stack (dùng list trong Python làm stack)
    stack = [start]
    # reached <- tập các state đã khám phá
    reached = {start}
    parent = {start: None}
    visited_order = []

    found = False

    while stack:
        # node <- POP(frontier) - lấy phần tử cuối stack
        curr = stack.pop()

        # Ghi nhận node đang được mở rộng (để vẽ hiệu ứng)
        if curr != start and curr != goal:
            visited_order.append(curr)

        # Duyệt các child (láng giềng)
        # Đảo ngược để thứ tự duyệt trực quan hơn (node đầu tiên được push sau = pop trước)
        for child in reversed(graph[curr]):
            if child not in reached:
                reached.add(child)
                parent[child] = curr

                # GOAL-TEST ngay khi sinh child - giống slide
                if child == goal:
                    found = True
                    break

                # frontier.INSERT(child) - push vào stack
                stack.append(child)

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
        path.reverse()  # Đảo ngược: Goal->Start thành Start->Goal

    end_time = time.time()
    execution_time = (end_time - start_time) * 1000
    nodes_expanded = len(visited_order)

    return path, visited_order, nodes_expanded, f"{execution_time:.2f} ms"