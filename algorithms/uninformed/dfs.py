import time

def dfs(graph, start, goal):
    start_time = time.perf_counter()

    if start not in graph or goal not in graph:
        return [], [], 0, 0.0

    if start == goal:
        return [], [], 1, (time.perf_counter() - start_time) * 1000.0

    stack = [start]
    reached = {start}
    parent = {start: None}
    visited_order = []

    found = False
    while stack:
        curr = stack.pop()
        if curr != start and curr != goal:
            visited_order.append(curr)

        for child in reversed(graph.get(curr, [])):
            if child not in reached:
                reached.add(child)
                parent[child] = curr

                if child == goal:
                    found = True
                    break
                stack.append(child)
        if found:
            break

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