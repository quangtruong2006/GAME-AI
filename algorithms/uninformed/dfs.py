import time


def _build_trace(prev_path, curr_path):
    """
    Tính các bước đi từ prev_path[-1] đến curr_path[-1].
    """
    common_len = 0
    for i in range(min(len(prev_path), len(curr_path))):
        if prev_path[i] == curr_path[i]:
            common_len = i + 1
        else:
            break

    backtrack = list(reversed(prev_path[common_len:]))
    lca       = prev_path[common_len - 1] if common_len > 0 else None
    forward   = curr_path[common_len:]

    if lca is not None:
        return backtrack + [lca] + forward
    return backtrack + forward


def dfs(graph, start, goal):
    start_time = time.perf_counter()

    if start not in graph or goal not in graph:
        return [], [], [], 0, 0.0

    if start == goal:
        return ([start], [], [start], 1,
                (time.perf_counter() - start_time) * 1000.0)

    stack     = [(start, [start])]
    reached   = {start}

    expand_order  = []
    mouse_trace   = [start]
    prev_path     = [start]
    found         = False
    solution_path = []

    while stack:
        curr, path_so_far = stack.pop()
        expand_order.append(curr)

        steps = _build_trace(prev_path, path_so_far)
        mouse_trace.extend(steps)
        prev_path = path_so_far

        if curr == goal:
            found         = True
            solution_path = path_so_far
            break

        for child in reversed(graph.get(curr, [])):
            if child not in reached:
                reached.add(child)
                stack.append((child, path_so_far + [child]))

    visited_order = [n for n in expand_order if n != start]
    exec_ms = (time.perf_counter() - start_time) * 1000.0
    return solution_path, visited_order, mouse_trace, len(visited_order), exec_ms