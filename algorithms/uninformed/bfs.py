from collections import deque
import time


def _build_trace(prev_path, curr_path):
    """
    Trả về list các node cần đi từ prev_path[-1] đến curr_path[-1].
    Tìm common prefix → backtrack lên common ancestor → đi xuống target.
    
    Ví dụ:
      prev_path = [A, B, D]
      curr_path = [A, C]
      common    = [A]  → LCA = A
      backtrack : D → B → A  (đảo ngược phần khác nhau của prev)
      forward   : A → C      (phần khác nhau của curr)
      result    = [D, B, A, C]  (không bao gồm điểm xuất phát D)
      → thực ra trả về [B, A, C]
    """
    # Tìm độ dài prefix chung
    common_len = 0
    for i in range(min(len(prev_path), len(curr_path))):
        if prev_path[i] == curr_path[i]:
            common_len = i + 1
        else:
            break

    # Phần cần backtrack (sau common prefix, trong prev_path), đảo ngược
    backtrack = list(reversed(prev_path[common_len:]))  # không bao gồm LCA

    # LCA node
    lca = prev_path[common_len - 1] if common_len > 0 else None

    # Phần forward (sau common prefix, trong curr_path)
    forward = curr_path[common_len:]  # không bao gồm LCA

    # Kết quả: backtrack → LCA → forward
    # backtrack đã không bao gồm LCA, forward không bao gồm LCA
    result = backtrack
    if lca is not None:
        result = result + [lca] + forward
    else:
        result = result + forward

    return result


def bfs(graph, start, goal):
    start_time = time.perf_counter()

    if start not in graph or goal not in graph:
        return [], [], [], 0, 0.0

    if start == goal:
        return ([start], [], [start], 1,
                (time.perf_counter() - start_time) * 1000.0)

    queue        = deque([(start, [start])])
    visited      = {start}
    expand_order = []
    mouse_trace  = [start]
    prev_path    = [start]   # path_so_far của node vừa xử lý

    found         = False
    solution_path = []

    while queue:
        curr, path_so_far = queue.popleft()
        expand_order.append(curr)

        # Xây trace từ prev_path đến path_so_far
        steps = _build_trace(prev_path, path_so_far)
        mouse_trace.extend(steps)
        prev_path = path_so_far

        if curr == goal:
            found         = True
            solution_path = path_so_far
            break

        for neighbor in graph.get(curr, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path_so_far + [neighbor]))

    visited_order = [n for n in expand_order if n != start]
    exec_ms = (time.perf_counter() - start_time) * 1000.0
    return solution_path, visited_order, mouse_trace, len(visited_order), exec_ms