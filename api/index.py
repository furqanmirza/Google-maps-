from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
import json
import os
import requests

TOMTOM_SEARCH_URL = "https://api.tomtom.com/search/2/search"
TOMTOM_ROUTE_URL = "https://api.tomtom.com/routing/1/calculateRoute"


def get_api_key():
    return os.environ.get("TOMTOM_API_KEY")


def build_locations_param(locations):
    return ":".join(f"{loc['lat']},{loc['lon']}" for loc in locations)


def call_tomtom_search(query, api_key):
    url = f"{TOMTOM_SEARCH_URL}/{quote(query, safe='')}.json"
    resp = requests.get(
        url,
        params={"key": api_key, "limit": 5, "countrySet": "US"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def call_tomtom_route(locations, api_key):
    coords = build_locations_param(locations)
    url = f"{TOMTOM_ROUTE_URL}/{coords}/json"
    resp = requests.get(
        url,
        params={
            "key": api_key,
            "computeBestOrder": "true",
            "routeType": "fastest",
            "traffic": "true",
            "travelMode": "car",
            "depart": "now",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        action = (query.get("action") or [""])[0]

        if action != "search":
            self._send(400, {"error": f"Unsupported GET action: {action}"})
            return

        q = (query.get("q") or [""])[0].strip()
        if not q:
            self._send(200, {"results": []})
            return

        api_key = get_api_key()
        if not api_key:
            self._send(500, {"error": "TOMTOM_API_KEY is not configured on the server"})
            return

        try:
            result = call_tomtom_search(q, api_key)
        except requests.RequestException as e:
            self._send(502, {"error": f"TomTom Search API error: {e}"})
            return

        suggestions = [
            {
                "name": r.get("address", {}).get("freeformAddress", q),
                "lat": r.get("position", {}).get("lat"),
                "lon": r.get("position", {}).get("lon"),
            }
            for r in result.get("results", [])
            if r.get("position")
        ]
        self._send(200, {"results": suggestions})

    def do_POST(self):
        query = parse_qs(urlparse(self.path).query)
        action = (query.get("action") or ["optimize"])[0]

        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "Invalid JSON body"})
            return

        if action != "optimize":
            self._send(400, {"error": f"Unsupported POST action: {action}"})
            return

        locations = data.get("locations", [])
        if len(locations) < 2:
            self._send(400, {"error": "Provide at least two locations"})
            return

        api_key = get_api_key()
        if not api_key:
            self._send(500, {"error": "TOMTOM_API_KEY is not configured on the server"})
            return

        try:
            result = call_tomtom_route(locations, api_key)
        except requests.RequestException as e:
            self._send(502, {"error": f"TomTom Route API error: {e}"})
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
