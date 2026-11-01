"""Core DAA algorithms used by the Smart Blood Bank demo."""

import heapq

# Standard red-cell transfusion compatibility table.
# A recipient can receive red cells from the listed donor blood groups.
COMPATIBILITY = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
}

def blood_compatible(donor_group, recipient_group):
    """Return True if donor red blood cells are compatible with recipient."""
    return donor_group in COMPATIBILITY.get(recipient_group, [])

def dijkstra(graph, start, goal):
    """Dijkstra shortest path. Edge weights represent illustrative distance in km."""
    if start not in graph or goal not in graph:
        return None, []
    distances = {node: float("inf") for node in graph}
    previous = {}
    distances[start] = 0
    heap = [(0, start)]
    while heap:
        current_distance, node = heapq.heappop(heap)
        if current_distance != distances[node]:
            continue
        if node == goal:
            break
        for neighbor, weight in graph[node].items():
            candidate = current_distance + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                previous[neighbor] = node
                heapq.heappush(heap, (candidate, neighbor))
    if distances[goal] == float("inf"):
        return None, []
    path = []
    node = goal
    while node != start:
        path.append(node)
        node = previous[node]
    path.append(start)
    path.reverse()
    return distances[goal], path

class DonorBST:
    """Binary Search Tree keyed by donor ID; inorder traversal returns ID order."""
    class Node:
        def __init__(self, donor):
            self.donor = donor
            self.left = None
            self.right = None

    def __init__(self):
        self.root = None

    def insert(self, donor):
        def add(node, donor):
            if node is None:
                return self.Node(donor)
            if donor["id"] < node.donor["id"]:
                node.left = add(node.left, donor)
            else:
                node.right = add(node.right, donor)
            return node
        self.root = add(self.root, donor)

    def search(self, donor_id):
        return bst_search(self.root, donor_id)

    def height(self):
        def h(n):
            return 0 if n is None else 1 + max(h(n.left), h(n.right))
        return h(self.root)

    def inorder(self):
        result = []
        def walk(node):
            if node:
                walk(node.left)
                result.append(node.donor)
                walk(node.right)
        walk(self.root)
        return result

class EmergencyPriorityQueue:
    """Max-priority queue implemented with heapq (higher urgency = higher priority)."""
    def __init__(self):
        self._heap = []
        self._counter = 0

    def push(self, request):
        self._counter += 1
        heapq.heappush(self._heap, (-request["urgency"], self._counter, request))

    def pop(self):
        return heapq.heappop(self._heap)[2] if self._heap else None

def sort_donors_by_distance(donors):
    """Merge sort by distance, then by donor ID for stable deterministic ranking."""
    if len(donors) <= 1:
        return donors
    mid = len(donors) // 2
    left = sort_donors_by_distance(donors[:mid])
    right = sort_donors_by_distance(donors[mid:])
    result, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        a = (left[i]["distance"], left[i]["id"])
        b = (right[j]["distance"], right[j]["id"])
        if a <= b:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    return result + left[i:] + right[j:]


# ---------------------------------------------------------------------------
# Extended algorithms (added features)
# ---------------------------------------------------------------------------
import time
import random
from collections import deque
from datetime import date, datetime

DONATION_GAP_DAYS = 90   # minimum gap between whole-blood donations (demo rule)


def bst_search(root, donor_id):
    """Iterative BST search by donor ID. Average O(log n), worst O(n)."""
    steps, node = 0, root
    while node:
        steps += 1
        if donor_id == node.donor["id"]:
            return node.donor, steps
        node = node.left if donor_id < node.donor["id"] else node.right
    return None, steps


def binary_search_by_name(sorted_donors, prefix):
    """Binary search (lower bound) on a name-sorted list, returns all names starting
    with `prefix`. O(log n + k)."""
    prefix = prefix.lower()
    lo, hi = 0, len(sorted_donors)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_donors[mid]["name"].lower() < prefix:
            lo = mid + 1
        else:
            hi = mid
    out = []
    while lo < len(sorted_donors) and sorted_donors[lo]["name"].lower().startswith(prefix):
        out.append(sorted_donors[lo]); lo += 1
    return out


def bfs_path(graph, start, goal):
    """Breadth-first search: path with the fewest roads (hops), ignoring km. O(V+E)."""
    if start not in graph or goal not in graph:
        return None, []
    prev, seen, q = {}, {start}, deque([start])
    while q:
        node = q.popleft()
        if node == goal:
            break
        for nb in graph[node]:
            if nb not in seen:
                seen.add(nb); prev[nb] = node; q.append(nb)
    if goal not in seen:
        return None, []
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    path.reverse()
    return len(path) - 1, path


def path_length(graph, path):
    return sum(graph[a][b] for a, b in zip(path, path[1:]))


def floyd_warshall(graph):
    """All-pairs shortest paths. O(V^3). Returns (nodes, matrix)."""
    nodes = sorted(graph)
    idx = {n: i for i, n in enumerate(nodes)}
    inf = float("inf")
    d = [[inf] * len(nodes) for _ in nodes]
    for n in nodes:
        d[idx[n]][idx[n]] = 0
        for nb, w in graph[n].items():
            d[idx[n]][idx[nb]] = w
    for k in range(len(nodes)):
        for i in range(len(nodes)):
            for j in range(len(nodes)):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return nodes, d


def prim_mst(graph, start=None):
    """Prim's Minimum Spanning Tree - cheapest set of roads connecting every
    location. O(E log V). Returns (edges, total_km)."""
    if not graph:
        return [], 0
    start = start or next(iter(graph))
    visited, edges, total = {start}, [], 0
    heap = [(w, start, nb) for nb, w in graph[start].items()]
    heapq.heapify(heap)
    while heap and len(visited) < len(graph):
        w, a, b = heapq.heappop(heap)
        if b in visited:
            continue
        visited.add(b); edges.append((a, b, w)); total += w
        for nb, w2 in graph[b].items():
            if nb not in visited:
                heapq.heappush(heap, (w2, b, nb))
    return edges, total


def quick_sort(items, key=lambda x: x):
    """Randomised quick sort. Average O(n log n), worst O(n^2)."""
    if len(items) <= 1:
        return list(items)
    pivot = key(items[random.randrange(len(items))])
    less = [x for x in items if key(x) < pivot]
    equal = [x for x in items if key(x) == pivot]
    more = [x for x in items if key(x) > pivot]
    return quick_sort(less, key) + equal + quick_sort(more, key)


def bubble_sort(items, key=lambda x: x):
    """Bubble sort with early exit. O(n^2) - included as a baseline."""
    a = list(items)
    for i in range(len(a)):
        swapped = False
        for j in range(len(a) - 1 - i):
            if key(a[j]) > key(a[j + 1]):
                a[j], a[j + 1] = a[j + 1], a[j]; swapped = True
        if not swapped:
            break
    return a


def merge_sort(items, key=lambda x: x):
    """Generic merge sort. O(n log n), stable."""
    if len(items) <= 1:
        return list(items)
    mid = len(items) // 2
    l, r = merge_sort(items[:mid], key), merge_sort(items[mid:], key)
    out, i, j = [], 0, 0
    while i < len(l) and j < len(r):
        if key(l[i]) <= key(r[j]):
            out.append(l[i]); i += 1
        else:
            out.append(r[j]); j += 1
    return out + l[i:] + r[j:]


def benchmark_sorts(sizes=(100, 500, 1000, 2000), seed=42):
    """Time merge / quick / bubble / built-in sort on random data (milliseconds)."""
    rng = random.Random(seed)
    result = {"sizes": list(sizes), "Merge Sort": [], "Quick Sort": [],
              "Bubble Sort": [], "Python sorted()": []}
    for n in sizes:
        data = [rng.randint(0, 100000) for _ in range(n)]
        for name, fn in (("Merge Sort", merge_sort), ("Quick Sort", quick_sort),
                         ("Bubble Sort", bubble_sort), ("Python sorted()", sorted)):
            t = time.perf_counter(); fn(data)
            result[name].append(round((time.perf_counter() - t) * 1000, 3))
    return result


def days_since(iso_date, today=None):
    if not iso_date:
        return None
    today = today or date.today()
    return (today - datetime.strptime(iso_date, "%Y-%m-%d").date()).days


def is_eligible(donor, today=None):
    """Donor must be flagged available AND >= 90 days since last donation."""
    if not donor.get("available", False):
        return False
    d = days_since(donor.get("last_donation"), today)
    return d is None or d >= DONATION_GAP_DAYS


def next_eligible_date(donor):
    from datetime import timedelta
    if not donor.get("last_donation"):
        return None
    return (datetime.strptime(donor["last_donation"], "%Y-%m-%d").date()
            + timedelta(days=DONATION_GAP_DAYS)).isoformat()


def allocation_order(recipient_group):
    """Greedy ordering of donor groups for a recipient: use the exact match first,
    then the groups that can serve the FEWEST other recipients, so the scarce
    universal donor (O-) is conserved for last."""
    options = list(COMPATIBILITY[recipient_group])
    def versatility(g):
        return sum(1 for r in COMPATIBILITY if blood_compatible(g, r))
    return sorted(options, key=lambda g: (g != recipient_group, versatility(g)))


def greedy_allocate(inventory, recipient_group, units):
    """Greedy stock allocation. Returns (plan, shortfall). plan = [(group, n)]."""
    plan, need = [], units
    for g in allocation_order(recipient_group):
        take = min(inventory.get(g, 0), need)
        if take:
            plan.append((g, take)); need -= take
        if need == 0:
            break
    return plan, need


def knapsack_camp(candidates, budget):
    """0/1 knapsack (DP, O(n*W)): choose donors to invite to a donation camp.
    candidates: list of dicts with 'cost' (int) and 'value' (int units expected).
    Returns (best_value, chosen_list)."""
    n = len(candidates)
    dp = [[0] * (budget + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        c, v = candidates[i - 1]["cost"], candidates[i - 1]["value"]
        for w in range(budget + 1):
            dp[i][w] = dp[i - 1][w]
            if c <= w and dp[i - 1][w - c] + v > dp[i][w]:
                dp[i][w] = dp[i - 1][w - c] + v
    chosen, w = [], budget
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            chosen.append(candidates[i - 1]); w -= candidates[i - 1]["cost"]
    chosen.reverse()
    return dp[n][budget], chosen
