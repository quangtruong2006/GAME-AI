# File: algorithms/uninformed/ids.py
import time

# Hằng số trạng thái trả về của DEPTH-LIMITED-SEARCH
FAILURE = "failure"
CUTOFF  = "cutoff"

def depth_limited_search(graph, start, goal, limit, visited_order):
    """
    function DEPTH-LIMITED-SEARCH(problem, l) returns a node or failure or cutoff
    Bám sát slide bài giảng:
      - frontier <- LIFO stack với NODE(problem.INITIAL)
      - result   <- failure
      - while not IS-EMPTY(frontier):
          node <- POP(frontier)
          if IS-GOAL(node) then return node
          if DEPTH(node) >= l then result <- cutoff
          else if not IS-CYCLE(node):
              for each child in EXPAND(node): add child to frontier
      - return result
    
    Mỗi phần tử trong stack là tuple: (node_id, depth, path_so_far, ancestors_set)
      - node_id      : ID node hiện tại
      - depth        : Độ sâu hiện tại tính từ start
      - path_so_far  : Danh sách node từ start đến node hiện tại (để truy vết)
      - ancestors    : Tập các node tổ tiên (IS-CYCLE check)
    """
    # frontier <- LIFO stack với node khởi tạo ban đầu
    # Stack lưu: (node_id, depth, path_so_far, ancestors_set)
    frontier = [(start, 0, [start], {start})]

    # result <- failure
    result = FAILURE

    while frontier:
        # node <- POP(frontier)
        node_id, depth, path_so_far, ancestors = frontier.pop()

        # if problem.IS-GOAL(node.STATE) then return node
        if node_id == goal:
            return path_so_far, visited_order, "found"

        # if DEPTH(node) >= l then result <- cutoff
        if depth >= limit:
            result = CUTOFF

        # else if not IS-CYCLE(node) do
        else:
            # Ghi nhận node đang được mở rộng (để vẽ hiệu ứng Pygame)
            if node_id != start and node_id != goal:
                if node_id not in visited_order:
                    visited_order.append(node_id)

            # for each child in EXPAND(problem, node) do
            #   add child to frontier
            # Đảo ngược để thứ tự duyệt trực quan (node đầu tiên pop ra trước)
            for child in reversed(graph[node_id]):
                # IS-CYCLE: kiểm tra child có nằm trong đường đi tổ tiên không
                if child not in ancestors:
                    new_path      = path_so_far + [child]
                    new_ancestors = ancestors | {child}
                    frontier.append((child, depth + 1, new_path, new_ancestors))

    # return result (failure hoặc cutoff)
    return None, visited_order, result


def ids(graph, start, goal):
    start_time = time.perf_counter()

    if start not in graph or goal not in graph:
        return [], [], 0, 0.0

    if start == goal:
        return [], [], 1, (time.perf_counter() - start_time) * 1000.0

    all_visited_order = []

    for depth_limit in range(len(graph) + 1):
        visited_order_this_round = []
        path_found, visited_this, status = depth_limited_search(
            graph, start, goal, depth_limit, visited_order_this_round
        )

        for v in visited_this:
            if v not in all_visited_order:
                all_visited_order.append(v)

        if status == "found":
            path_middle = [n for n in path_found if n != start and n != goal]
            exec_ms = (time.perf_counter() - start_time) * 1000.0
            return path_middle, all_visited_order, len(all_visited_order), exec_ms

        elif status == FAILURE:
            exec_ms = (time.perf_counter() - start_time) * 1000.0
            return [], all_visited_order, len(all_visited_order), exec_ms

    exec_ms = (time.perf_counter() - start_time) * 1000.0
    return [], all_visited_order, len(all_visited_order), exec_ms