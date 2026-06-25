from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
import json
import os
import requests

TOMTOM_SEARCH_URL = "https://api.tomtom.com/search/2/search"
TOMTOM_SEARCH_ALONG_ROUTE_URL = "https://api.tomtom.com/search/2/searchAlongRoute"
TOMTOM_ROUTE_URL = "https://api.tomtom.com/routing/1/calculateRoute"

MAX_DETOUR_SECONDS = 900
MAX_ROUTE_POINTS_FOR_SEARCH = 500


def get_api_key():
    return os.environ.get("TOMTOM_API_KEY")


def build_locations_param(locations):
    return ":".join(f"{loc['lat']},{loc['lon']}" for loc in locations)


def call_tomtom_search(query, api_key, lat=None, lon=None, radius=None):
    url = f"{TOMTOM_SEARCH_URL}/{quote(query, safe='')}.json"
    params = {"key": api_key, "limit": 5, "countrySet": "US"}
    if lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
        params["radius"] = radius or 50000
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def downsample_points(points, max_points):
    if len(points) <= max_points:
        return points
    step = len(points) / max_points
    return [points[int(i * step)] for i in range(max_points)]


def call_tomtom_search_along_route(query, route_points, api_key):
    url = f"{TOMTOM_SEARCH_ALONG_ROUTE_URL}/{quote(query, safe='')}.json"
    points = downsample_points(route_points, MAX_ROUTE_POINTS_FOR_SEARCH)
    resp = requests.post(
        url,
        params={"key": api_key, "maxDetourTime": MAX_DETOUR_SECONDS, "limit": 10},
        json={"route": {"points": [{"lat": p["lat"], "lon": p["lon"]} for p in points]}},
        timeout=15,
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

        lat = (query.get("lat") or [None])[0]
        lon = (query.get("lon") or [None])[0]

        try:
            result = call_tomtom_search(q, api_key, lat=lat, lon=lon)
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

        api_key = get_api_key()
        if not api_key:
            self._send(500, {"error": "TOMTOM_API_KEY is not configured on the server"})
            return

        if action == "optimize":
            locations = data.get("locations", [])
            if len(locations) < 2:
                self._send(400, {"error": "Provide at least two locations"})
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

        elif action == "search_along_route":
            search_query = (data.get("query") or "").strip()
            route_points = data.get("route", [])
            if not search_query:
                self._send(400, {"error": "Provide a query"})
                return
            if len(route_points) < 2:
                self._send(400, {"error": "Provide a route with at least two points"})
                return

            try:
                result = call_tomtom_search_along_route(search_query, route_points, api_key)
            except requests.RequestException as e:
                self._send(502, {"error": f"TomTom Search Along Route API error: {e}"})
                return

            suggestions = [
                {
                    "name": r.get("poi", {}).get("name") or r.get("address", {}).get("freeformAddress", search_query),
                    "lat": r.get("position", {}).get("lat"),
                    "lon": r.get("position", {}).get("lon"),
                    "detour_minutes": round(r.get("detourTime", 0) / 60, 1),
                }
                for r in result.get("results", [])
                if r.get("position")
            ]
            self._send(200, {"results": suggestions})

        else:
            self._send(400, {"error": f"Unsupported POST action: {action}"})
