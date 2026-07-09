import time

FAILURE = "failure"
CUTOFF  = "cutoff"


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


def _depth_limited_search(graph, start, goal, limit):
    frontier      = [(start, 0, [start])]
    result        = FAILURE
    visited_order = []
    mouse_trace   = [start]
    prev_path     = [start]

    while frontier:
        node_id, depth, path_so_far = frontier.pop()

        steps = _build_trace(prev_path, path_so_far)
        mouse_trace.extend(steps)
        prev_path = path_so_far

        if node_id == goal:
            return path_so_far, visited_order, mouse_trace, "found"

        if depth >= limit:
            result = CUTOFF
            continue

        if node_id != start:
            visited_order.append(node_id)

        ancestors = set(path_so_far)
        for child in reversed(graph.get(node_id, [])):
            if child not in ancestors:
                frontier.append((child, depth + 1, path_so_far + [child]))

    return None, visited_order, mouse_trace, result


def ids(graph, start, goal):
    start_time = time.perf_counter()

    if start not in graph or goal not in graph:
        return [], [], [], 0, 0.0

    if start == goal:
        return ([start], [], [start], 1,
                (time.perf_counter() - start_time) * 1000.0)

    all_visited_order = []
    all_mouse_trace   = [start]

    for depth_limit in range(len(graph) + 1):
        path_found, visited_this, trace_this, status = _depth_limited_search(
            graph, start, goal, depth_limit
        )

        all_visited_order.extend(visited_this)

        if status == "found":
            # Ghép trace (bỏ start vì đã có)
            all_mouse_trace.extend(trace_this[1:])
            exec_ms = (time.perf_counter() - start_time) * 1000.0
            return (path_found, all_visited_order, all_mouse_trace,
                    len(all_visited_order), exec_ms)

        # Chưa xong: thêm trace vòng này
        all_mouse_trace.extend(trace_this[1:])

        # Backtrack về start để bắt đầu vòng lặp depth mới
        # Đi ngược lại trace_this từ cuối về start
        if all_mouse_trace[-1] != start:
            back = list(reversed(trace_this[1:]))  # bỏ start ở cuối vì đã sẽ là điểm đến
            all_mouse_trace.extend(back)
            # Đảm bảo kết thúc ở start
            if all_mouse_trace[-1] != start:
                all_mouse_trace.append(start)

        if status == FAILURE:
            exec_ms = (time.perf_counter() - start_time) * 1000.0
            return ([], all_visited_order, all_mouse_trace,
                    len(all_visited_order), exec_ms)

    exec_ms = (time.perf_counter() - start_time) * 1000.0
    return [], all_visited_order, all_mouse_trace, len(all_visited_order), exec_ms