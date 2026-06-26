# algorithms/complex_environments/and_or_search.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Iterable

Pos = Tuple[int, int]   # (r,c)


@dataclass(frozen=True)
class PortalDef:
    """Portal at position pos.
    - If actions_to is not None => controllable portal (OR choice): action -> destination
    - If outcomes is not None => nondet portal (AND outcomes): single action "TP" -> set(destinations)
    """
    name: str
    pos: Pos
    actions_to: Optional[Dict[str, Pos]] = None     # controllable
    outcomes: Optional[List[Pos]] = None            # nondeterministic (random outcomes)
    action_name: str = "TP"                         # action label for nondet portals


class NondetGridProblem:
    def __init__(
        self,
        rows: int,
        cols: int,
        start: Pos,
        goal: Pos,
        blocked: Set[Pos],
        portals: List[PortalDef],
    ):
        self.rows = rows
        self.cols = cols
        self.start = start
        self.goal = goal
        self.blocked = set(blocked)

        self.portal_at: Dict[Pos, PortalDef] = {p.pos: p for p in portals}

    def goal_test(self, s: Pos) -> bool:
        return s == self.goal

    def in_bounds(self, s: Pos) -> bool:
        r, c = s
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_free(self, s: Pos) -> bool:
        return self.in_bounds(s) and (s not in self.blocked)

    def actions(self, s: Pos) -> List[str]:
        """Return list of action labels from state s."""
        if not self.is_free(s):
            return []

        acts: List[str] = []

        # movement (deterministic)
        r, c = s
        moves = [
            ("U", (r - 1, c)),
            ("D", (r + 1, c)),
            ("L", (r, c - 1)),
            ("R", (r, c + 1)),
        ]
        for a, ns in moves:
            if self.is_free(ns):
                acts.append(a)

        # portal actions (may be deterministic choice or nondet)
        p = self.portal_at.get(s)
        if p:
            if p.actions_to:
                # controllable choices (OR)
                for act in p.actions_to.keys():
                    acts.append(act)
            elif p.outcomes:
                # nondeterministic (AND outcomes)
                acts.append(p.action_name)

        return acts

    def results(self, s: Pos, a: str) -> List[Pos]:
        """Return list of possible next states after action a in s."""
        if a in ("U", "D", "L", "R"):
            r, c = s
            if a == "U": ns = (r - 1, c)
            elif a == "D": ns = (r + 1, c)
            elif a == "L": ns = (r, c - 1)
            else: ns = (r, c + 1)
            return [ns] if self.is_free(ns) else []

        p = self.portal_at.get(s)
        if not p:
            return []

        # controllable portal action: a maps to a single destination
        if p.actions_to and a in p.actions_to:
            dest = p.actions_to[a]
            return [dest] if self.is_free(dest) else []

        # nondet portal action: one action -> multiple outcomes
        if p.outcomes and a == p.action_name:
            out = [x for x in p.outcomes if self.is_free(x)]
            return out

        return []


class AndOrSearch:
    """
    AND-OR SEARCH (AIMA):
    - OR node: choose an action
    - AND node: action may lead to multiple possible next states; must solve ALL
    Returns a policy: Dict[state] = action
    Not necessarily optimal; aims for a contingent plan that guarantees reaching goal.
    """

    def __init__(self, problem: NondetGridProblem, max_expansions: int = 50000):
        self.problem = problem
        self.max_expansions = max_expansions
        self.expansions = 0

        self.policy: Dict[Pos, str] = {}
        self.failed: Set[Pos] = set()

    def plan(self) -> Optional[Dict[Pos, str]]:
        ok = self._or_search(self.problem.start, path=[])
        return self.policy if ok else None

    def _or_search(self, s: Pos, path: List[Pos]) -> bool:
        if self.problem.goal_test(s):
            return True

        if s in path:
            return False  # avoid loops (acyclic plan)

        if s in self.failed:
            return False

        self.expansions += 1
        if self.expansions > self.max_expansions:
            return False

        acts = self.problem.actions(s)
        if not acts:
            self.failed.add(s)
            return False

        # heuristic order: prefer moves that reduce Manhattan to goal
        def manhattan(p: Pos, q: Pos) -> int:
            return abs(p[0] - q[0]) + abs(p[1] - q[1])

        def act_key(a: str) -> int:
            rs = self.problem.results(s, a)
            if not rs:
                return 10**9
            # optimistic: best successor distance
            return min(manhattan(ns, self.problem.goal) for ns in rs)

        acts.sort(key=act_key)

        for a in acts:
            outcomes = self.problem.results(s, a)
            if not outcomes:
                continue

            # try this action; must solve all outcomes (AND)
            if self._and_search(outcomes, path + [s]):
                # store in policy; ensure consistent
                prev = self.policy.get(s)
                if prev is None:
                    self.policy[s] = a
                elif prev != a:
                    # conflict => fail this branch
                    continue
                return True

        self.failed.add(s)
        return False

    def _and_search(self, states: List[Pos], path: List[Pos]) -> bool:
        for s in states:
            if not self._or_search(s, path):
                return False
        return True