from http.server import BaseHTTPRequestHandler
import json
import math

POIS = [
    {"name": "Grand Canyon South Rim", "lat": 36.0544, "lng": -112.1401},
    {"name": "Antelope Canyon", "lat": 36.8619, "lng": -111.4042},
    {"name": "Horseshoe Bend", "lat": 36.8791, "lng": -111.5103},
    {"name": "Sedona Red Rocks", "lat": 34.8697, "lng": -111.7610},
    {"name": "Saguaro National Park", "lat": 32.2967, "lng": -110.7400},
    {"name": "Tombstone Historic District", "lat": 31.7107, "lng": -110.0693},
    {"name": "Desert Botanical Garden", "lat": 33.4626, "lng": -111.9450},
    {"name": "Montezuma Castle", "lat": 34.6126, "lng": -111.8385},
    {"name": "Meteor Crater", "lat": 35.0276, "lng": -111.0227},
    {"name": "Lake Powell", "lat": 36.9359, "lng": -111.4839},
    {"name": "Tucson Mountain Park", "lat": 32.2417, "lng": -111.1490},
    {"name": "Petrified Forest National Park", "lat": 34.9100, "lng": -109.8068},
]

EARTH_RADIUS_KM = 6371.0


def haversine(a, b):
    lat1, lng1, lat2, lng2 = map(math.radians, [a["lat"], a["lng"], b["lat"], b["lng"]])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(h))


def build_matrix(points):
    n = len(points)
    return [[haversine(points[i], points[j]) for j in range(n)] for i in range(n)]


def path_length(order, matrix):
    return sum(matrix[order[i]][order[i + 1]] for i in range(len(order) - 1))


def nearest_neighbor(matrix, start=0):
    n = len(matrix)
    visited = {start}
    order = [start]
    while len(order) < n:
        last = order[-1]
        nxt = min((j for j in range(n) if j not in visited), key=lambda j: matrix[last][j])
        visited.add(nxt)
        order.append(nxt)
    return order


def two_opt(order, matrix):
    n = len(order)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 2):
            for j in range(i + 1, n - 1):
                a, b, c, d = order[i - 1], order[i], order[j], order[j + 1]
                delta = (matrix[a][c] + matrix[b][d]) - (matrix[a][b] + matrix[c][d])
                if delta < -1e-9:
                    order[i:j + 1] = reversed(order[i:j + 1])
                    improved = True
    return order


def solve_tsp(points, lock_first=True):
    matrix = build_matrix(points)
    start = 0 if lock_first else 0
    order = nearest_neighbor(matrix, start)
    order = two_opt(order, matrix)
    return order, path_length(order, matrix)


def point_to_segment_distance_km(p, a, b):
    ax, ay, bx, by, px, py = a["lng"], a["lat"], b["lng"], b["lat"], p["lng"], p["lat"]
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        closest = a
    else:
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        closest = {"lat": ay + t * dy, "lng": ax + t * dx}
    return haversine(p, closest)


def suggest_pois(route_points, max_detour_km=40, limit=5):
    existing = {(round(pt["lat"], 3), round(pt["lng"], 3)) for pt in route_points}
    suggestions = []
    for poi in POIS:
        key = (round(poi["lat"], 3), round(poi["lng"], 3))
        if key in existing:
            continue
        best = min(
            point_to_segment_distance_km(poi, route_points[i], route_points[i + 1])
            for i in range(len(route_points) - 1)
        ) if len(route_points) > 1 else haversine(poi, route_points[0])
        if best <= max_detour_km:
            suggestions.append({**poi, "detour_km": round(best, 2)})
    suggestions.sort(key=lambda s: s["detour_km"])
    return suggestions[:limit]


def best_insertion(order, matrix, poi_index):
    n = len(order)
    best_cost, best_pos = float("inf"), 1
    for i in range(1, n):
        a, b = order[i - 1], order[i]
        added = matrix[a][poi_index] + matrix[poi_index][b] - matrix[a][b]
        if added < best_cost:
            best_cost, best_pos = added, i
    tail_a = order[-1]
    added_tail = matrix[tail_a][poi_index]
    if added_tail < best_cost:
        best_cost, best_pos = added_tail, n
    new_order = order[:best_pos] + [poi_index] + order[best_pos:]
    return new_order, best_cost


class handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "Invalid JSON body"})
            return

        action = data.get("action", "optimize")
        locations = data.get("locations", [])

        if len(locations) < 2:
            self._send(400, {"error": "Provide at least two locations"})
            return

        if action == "optimize":
            order, total_km = solve_tsp(locations)
            ordered = [locations[i] for i in order]
            suggestions = suggest_pois(ordered)
            self._send(200, {
                "order": order,
                "ordered_locations": ordered,
                "total_distance_km": round(total_km, 2),
                "suggested_pois": suggestions,
            })

        elif action == "add_poi":
            poi = data.get("poi")
            if not poi:
                self._send(400, {"error": "Missing poi"})
                return
            points = locations + [poi]
            matrix = build_matrix(points)
            base_order = list(range(len(locations)))
            new_order, added_km = best_insertion(base_order, matrix, len(locations))
            new_order = two_opt(new_order, matrix)
            ordered = [points[i] for i in new_order]
            self._send(200, {
                "order": new_order,
                "ordered_locations": ordered,
                "total_distance_km": round(path_length(new_order, matrix), 2),
                "added_detour_km": round(added_km, 2),
            })

        else:
            self._send(400, {"error": f"Unknown action: {action}"})
