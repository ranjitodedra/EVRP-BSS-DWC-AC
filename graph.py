"""
graph.py — Graph representation, JSON loading, and Dijkstra shortest-path.
Nodes: depot, customer, intersection, charging_station, electric_road_start/end.
Edges: normal (bidirectional) and electric (directional start→end only).
"""

import json
import heapq
from typing import Dict, List, Optional, Tuple


class Node:
    """A node in the routing graph."""

    __slots__ = ("id", "type", "segment")

    def __init__(self, id: str, type: str, segment: Optional[int] = None):
        self.id = id
        self.type = type          # depot | customer | intersection | charging_station | electric_road_start | electric_road_end
        self.segment = segment    # only for electric road boundary nodes

    def __repr__(self):
        return f"Node({self.id}, {self.type})"


class Edge:
    """A directed edge in the routing graph."""

    __slots__ = ("src", "dst", "distance", "traffic_factor", "type")

    def __init__(self, src: str, dst: str, distance: float,
                 traffic_factor: float, edge_type: str):
        self.src = src
        self.dst = dst
        self.distance = distance          # km
        self.traffic_factor = traffic_factor
        self.type = edge_type             # "normal" or "electric"

    def __repr__(self):
        return f"Edge({self.src}→{self.dst}, {self.distance}km, tf={self.traffic_factor}, {self.type})"


class Graph:
    """Routing graph with adjacency-list representation."""

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.adj: Dict[str, List[Edge]] = {}   # node_id → outgoing edges

    # ── loading ──────────────────────────────────────────

    @classmethod
    def from_json(cls, path: str) -> "Graph":
        with open(path, "r") as f:
            data = json.load(f)
        g = cls()
        g._load_nodes(data["nodes"])
        g._load_edges(data["edges"])
        return g

    def _load_nodes(self, node_list: list):
        for n in node_list:
            node = Node(n["id"], n["type"], n.get("segment"))
            self.nodes[node.id] = node
            self.adj.setdefault(node.id, [])

    def _load_edges(self, edge_list: list):
        for e in edge_list:
            src, dst = e["from"], e["to"]
            dist = float(e["distance"])
            tf = float(e["traffic_factor"])
            etype = e["type"]

            # Forward edge always
            self.adj.setdefault(src, []).append(Edge(src, dst, dist, tf, etype))

            # Normal roads are bidirectional (add reverse edge)
            if etype == "normal":
                self.adj.setdefault(dst, []).append(Edge(dst, src, dist, tf, etype))
            # Electric roads are directional — no reverse

    # ── queries ──────────────────────────────────────────

    def get_depot(self) -> str:
        for n in self.nodes.values():
            if n.type == "depot":
                return n.id
        raise ValueError("No depot node found in graph")

    def get_customers(self) -> List[str]:
        return sorted(
            [n.id for n in self.nodes.values() if n.type == "customer"],
            key=lambda x: x  # natural sort
        )

    def get_charging_stations(self) -> List[str]:
        return [n.id for n in self.nodes.values() if n.type == "charging_station"]

    def get_neighbors(self, node_id: str) -> List[Edge]:
        return self.adj.get(node_id, [])

    def get_edge(self, src: str, dst: str) -> Optional[Edge]:
        for e in self.adj.get(src, []):
            if e.dst == dst:
                return e
        return None

    # ── Dijkstra ─────────────────────────────────────────

    def dijkstra(self, source: str, target: str) -> Tuple[List[str], float]:
        """
        Shortest path (by distance) from source to target.
        Returns (path_as_list_of_node_ids, total_distance).
        If unreachable, returns ([], inf).
        """
        dist: Dict[str, float] = {nid: float("inf") for nid in self.nodes}
        prev: Dict[str, Optional[str]] = {nid: None for nid in self.nodes}
        dist[source] = 0.0
        pq = [(0.0, source)]

        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if u == target:
                break
            for edge in self.adj.get(u, []):
                nd = d + edge.distance
                if nd < dist[edge.dst]:
                    dist[edge.dst] = nd
                    prev[edge.dst] = u
                    heapq.heappush(pq, (nd, edge.dst))

        if dist[target] == float("inf"):
            return [], float("inf")

        # reconstruct path
        path = []
        cur = target
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path, dist[target]

    def shortest_path_edges(self, source: str, target: str) -> Tuple[List[Edge], float]:
        """Return the list of Edge objects along the shortest path and total distance."""
        path, total_dist = self.dijkstra(source, target)
        if not path or len(path) < 2:
            return [], total_dist
        edges = []
        for i in range(len(path) - 1):
            edge = self.get_edge(path[i], path[i + 1])
            if edge is None:
                return [], float("inf")
            edges.append(edge)
        return edges, total_dist

    def distance_matrix(self, node_ids: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Precompute shortest-path distances between all pairs in node_ids.
        Returns nested dict: matrix[i][j] = shortest distance from i to j.
        """
        matrix: Dict[str, Dict[str, float]] = {}
        for src in node_ids:
            matrix[src] = {}
            for dst in node_ids:
                if src == dst:
                    matrix[src][dst] = 0.0
                else:
                    _, d = self.dijkstra(src, dst)
                    matrix[src][dst] = d
        return matrix
