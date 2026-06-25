from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.error
import urllib.request

TOMTOM_ROUTE_URL = "https://api.tomtom.com/routing/1/calculateRoute"


def build_locations_param(locations):
    return ":".join(f"{loc['lat']},{loc['lon']}" for loc in locations)


def call_tomtom_route(locations, api_key):
    coords = build_locations_param(locations)
    params = {
        "key": api_key,
        "computeBestOrder": "true",
        "routeType": "fastest",
        "traffic": "true",
        "travelMode": "car",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{TOMTOM_ROUTE_URL}/{coords}/json?{query}"
    with urllib.request.urlopen(urllib.request.Request(url), timeout=15) as resp:
        return json.loads(resp.read().decode())


def extract_optimized_order(route, fallback_len):
    waypoints = route.get("optimizedWaypoints")
    if not waypoints:
        return list(range(fallback_len))
    ordered = sorted(waypoints, key=lambda w: w["optimizedIndex"])
    return [w["providedIndex"] for w in ordered]


def extract_polyline(route):
    return [
        {"lat": p["latitude"], "lon": p["longitude"]}
        for leg in route.get("legs", [])
        for p in leg.get("points", [])
    ]


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

        locations = data.get("locations", [])
        if len(locations) < 2:
            self._send(400, {"error": "Provide at least two locations"})
            return

        api_key = os.environ.get("TOMTOM_API_KEY")
        if not api_key:
            self._send(500, {"error": "TOMTOM_API_KEY is not configured on the server"})
            return

        try:
            result = call_tomtom_route(locations, api_key)
        except urllib.error.HTTPError as e:
            self._send(e.code, {"error": f"TomTom API error: {e.read().decode()}"})
            return
        except urllib.error.URLError as e:
            self._send(502, {"error": f"Failed to reach TomTom API: {e.reason}"})
            return

        routes = result.get("routes", [])
        if not routes:
            self._send(502, {"error": "No route returned by TomTom"})
            return

        route = routes[0]
        summary = route.get("summary", {})
        optimized_order = extract_optimized_order(route, len(locations))
        ordered_locations = [locations[i] for i in optimized_order]

        self._send(200, {
            "optimized_order": optimized_order,
            "ordered_locations": ordered_locations,
            "polyline": extract_polyline(route),
            "distance_meters": summary.get("lengthInMeters"),
            "travel_time_seconds": summary.get("travelTimeInSeconds"),
            "traffic_delay_seconds": summary.get("trafficDelayInSeconds"),
        })
