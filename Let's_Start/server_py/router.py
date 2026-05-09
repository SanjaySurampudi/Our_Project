"""
router.py  —  Offline road-routing using OSMnx + Dijkstra's algorithm.

Usage
-----
from router import OfflineRouter

router = OfflineRouter(center_lat, center_lng, radius_m=50000)
result = router.route(tx_lat, tx_lng, rx_lat, rx_lng)
# result keys: distance, duration, steps, geometry  (or 'error')
"""

import math
import heapq
import threading
import logging

log = logging.getLogger(__name__)

# ── optional heavy import ──────────────────────────────────────────────────────
try:
    import osmnx as ox
    import networkx as nx
    _OSMNX_AVAILABLE = True
except ImportError:
    _OSMNX_AVAILABLE = False
    log.warning("osmnx / networkx not installed — router will use straight-line fallback. "
                "Install with:  pip install osmnx networkx")


# ──────────────────────────────────────────────────────────────────────────────
#  Haversine helper
# ──────────────────────────────────────────────────────────────────────────────

def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in metres between two WGS-84 points."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi       = math.radians(lat2 - lat1)
    dlam       = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _fmt_dist(metres: float) -> str:
    return f"{metres / 1000:.1f} km" if metres >= 1000 else f"{metres:.0f} m"


def _fmt_dur(seconds: float) -> str:
    if seconds >= 3600:
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
    if seconds >= 60:
        return f"{int(seconds // 60)} min"
    return f"{int(seconds)} sec"


# ──────────────────────────────────────────────────────────────────────────────
#  Pure-Python Dijkstra on an adjacency dict
# ──────────────────────────────────────────────────────────────────────────────

def dijkstra(graph: dict, source: int, target: int):
    """
    Dijkstra shortest path on a plain adjacency dict.

    graph format:
        { node_id: [(neighbour_id, weight_metres, speed_kmh), ...], ... }

    Returns (total_metres, [node_id, ...]) or (inf, []) if unreachable.
    """
    dist   = {source: 0.0}
    prev   = {}
    heap   = [(0.0, source)]

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, math.inf):
            continue
        if u == target:
            break
        for v, w, _ in graph.get(u, []):
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))

    if target not in dist:
        return math.inf, []

    path, cur = [], target
    while cur in prev:
        path.append(cur)
        cur = prev[cur]
    path.append(source)
    path.reverse()
    return dist[target], path


# ──────────────────────────────────────────────────────────────────────────────
#  OSMnx-backed offline router
# ──────────────────────────────────────────────────────────────────────────────

class OfflineRouter:
    """
    Downloads an OSM road graph once (around a centre point), caches it in
    memory, and answers route queries purely offline using Dijkstra.

    Parameters
    ----------
    center_lat, center_lng : float   – centre of the area to cache
    radius_m               : float   – radius around the centre to download (metres)
                                       Increase for longer possible routes.
    network_type           : str     – 'drive' (default) | 'walk' | 'bike'
    """

    def __init__(
        self,
        center_lat:   float,
        center_lng:   float,
        radius_m:     float = 50_000,
        network_type: str   = "drive",
    ):
        self._center      = (center_lat, center_lng)
        self._radius_m    = radius_m
        self._net_type    = network_type
        self._G           = None          # NetworkX DiGraph
        self._adj         = {}            # plain adjacency dict for Dijkstra
        self._node_coords = {}            # node_id -> (lat, lng)
        self._lock        = threading.Lock()
        self._ready       = False
        self._load_error  = None

        # Start background download so first route call is faster
        t = threading.Thread(target=self._download, daemon=True)
        t.start()

    # ------------------------------------------------------------------
    def _download(self):
        if not _OSMNX_AVAILABLE:
            self._load_error = "osmnx not installed"
            return
        try:
            log.info("Downloading OSM road graph (radius=%.0f m) …", self._radius_m)
            G = ox.graph_from_point(
                self._center,
                dist=self._radius_m,
                network_type=self._net_type,
                simplify=True,
            )
            # Add travel-time edge attribute (seconds) using speed data
            G = ox.add_edge_speeds(G)
            G = ox.add_edge_travel_times(G)

            adj        = {}
            node_coords = {}

            for node_id, data in G.nodes(data=True):
                node_coords[node_id] = (data["y"], data["x"])  # lat, lng

            for u, v, data in G.edges(data=True):
                length_m = data.get("length", 0.0)
                speed    = data.get("speed_kph", 30.0)
                adj.setdefault(u, []).append((v, length_m, speed))

            with self._lock:
                self._G           = G
                self._adj         = adj
                self._node_coords = node_coords
                self._ready       = True
            log.info("OSM graph loaded: %d nodes, %d edges",
                     len(node_coords), sum(len(v) for v in adj.values()))
        except Exception as exc:
            self._load_error = str(exc)
            log.error("Failed to load OSM graph: %s", exc)

    # ------------------------------------------------------------------
    def _nearest_node(self, lat: float, lng: float) -> int:
        """Return the graph node closest to (lat, lng) — pure-Python fallback."""
        best_id, best_d = None, math.inf
        for node_id, (nlat, nlng) in self._node_coords.items():
            d = haversine_m(lat, lng, nlat, nlng)
            if d < best_d:
                best_d, best_id = d, node_id
        return best_id

    # ------------------------------------------------------------------
    def route(
        self,
        tx_lat: float, tx_lng: float,
        rx_lat: float, rx_lng: float,
    ) -> dict:
        """
        Calculate a route from TX to RX.

        Returns a dict with keys:
            distance  str   e.g. "12.4 km"
            duration  str   e.g. "18 min"
            steps     list  of human-readable turn instructions
            geometry  list  of [lat, lng] pairs for the polyline
            error     str   (only present on failure)
        """
        straight_m = haversine_m(tx_lat, tx_lng, rx_lat, rx_lng)

        # ── wait up to 30 s for graph to be ready ─────────────────────
        if not self._ready:
            if self._load_error:
                return self._straight_line_result(tx_lat, tx_lng, rx_lat, rx_lng,
                                                  f"Graph unavailable: {self._load_error}")
            # Still loading — give a straight-line answer with a note
            return self._straight_line_result(tx_lat, tx_lng, rx_lat, rx_lng,
                                              "Road graph still loading — showing straight line")

        try:
            with self._lock:
                adj        = self._adj
                node_coords = self._node_coords

            # Nearest nodes via OSMnx if available, else pure-Python
            if _OSMNX_AVAILABLE and self._G is not None:
                src = ox.nearest_nodes(self._G, tx_lng, tx_lat)
                dst = ox.nearest_nodes(self._G, rx_lng, rx_lat)
            else:
                src = self._nearest_node(tx_lat, tx_lng)
                dst = self._nearest_node(rx_lat, rx_lng)

            dist_m, path = dijkstra(adj, src, dst)

            if not path or dist_m == math.inf:
                return self._straight_line_result(
                    tx_lat, tx_lng, rx_lat, rx_lng,
                    "No road path found — showing straight line")

            # Build geometry
            geometry = [list(node_coords[n]) for n in path]

            # Estimate travel time (assume 40 km/h avg where speed unknown)
            AVG_SPEED_MS = 40_000 / 3600
            duration_s   = dist_m / AVG_SPEED_MS

            # Build simple turn-by-turn steps (bearing-based)
            steps = _build_steps(path, node_coords, adj)

            return {
                "distance": _fmt_dist(dist_m),
                "duration": _fmt_dur(duration_s),
                "steps":    steps,
                "geometry": geometry,
            }

        except Exception as exc:
            log.exception("Route error")
            return self._straight_line_result(
                tx_lat, tx_lng, rx_lat, rx_lng, str(exc))

    # ------------------------------------------------------------------
    @staticmethod
    def _straight_line_result(
        tx_lat, tx_lng, rx_lat, rx_lng, note=""
    ) -> dict:
        d = haversine_m(tx_lat, tx_lng, rx_lat, rx_lng)
        dur = d / (40_000 / 3600)
        step = f"Straight line to destination ({_fmt_dist(d)})"
        if note:
            step = f"{note}. {step}"
        return {
            "distance": _fmt_dist(d),
            "duration": _fmt_dur(dur),
            "steps":    [step],
            "geometry": [[tx_lat, tx_lng], [rx_lat, rx_lng]],
        }


# ──────────────────────────────────────────────────────────────────────────────
#  Simple bearing-based step builder
# ──────────────────────────────────────────────────────────────────────────────

_COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _bearing(lat1, lng1, lat2, lng2) -> float:
    dL = math.radians(lng2 - lng1)
    x  = math.sin(dL) * math.cos(math.radians(lat2))
    y  = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) \
         - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dL)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _compass(deg: float) -> str:
    return _COMPASS[int((deg + 22.5) / 45) % 8]


def _build_steps(path, node_coords, adj, min_segment_m=200) -> list:
    """Merge short segments and emit human-readable steps."""
    if len(path) < 2:
        return ["Arrive at destination"]

    steps      = []
    seg_dist   = 0.0
    prev_bear  = None

    steps.append(f"Head {_compass(_bearing(*node_coords[path[0]], *node_coords[path[1]]))} from start")

    for i in range(len(path) - 1):
        la1, ln1 = node_coords[path[i]]
        la2, ln2 = node_coords[path[i + 1]]
        seg_m    = haversine_m(la1, ln1, la2, ln2)
        bear     = _bearing(la1, ln1, la2, ln2)

        seg_dist += seg_m

        if prev_bear is not None and seg_dist >= min_segment_m:
            diff = (bear - prev_bear + 360) % 360
            if diff > 30 and diff < 330:
                turn = "right" if diff <= 180 else "left"
                steps.append(f"Turn {turn} — continue {_compass(bear)} ({_fmt_dist(seg_dist)})")
                seg_dist = 0.0

        prev_bear = bear

    if seg_dist > 0:
        steps.append(f"Continue {_fmt_dist(seg_dist)}")
    steps.append("Arrive at destination")
    return steps
