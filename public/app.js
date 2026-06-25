const TOMTOM_API_KEY = window.TOMTOM_API_KEY;

const map = tt.map({
  key: TOMTOM_API_KEY,
  container: "map",
  center: [-111.0937, 34.0489],
  zoom: 6,
});

const ROUTE_SOURCE_ID = "smartroute-line";

let stops = [];
let markers = [];
let lastPolyline = [];
let searchDebounce = null;
let alongRouteDebounce = null;

const searchInput = document.getElementById("search-input");
const suggestionsEl = document.getElementById("suggestions");
const stopListEl = document.getElementById("stop-list");
const resultEl = document.getElementById("result");
const trafficBannerEl = document.getElementById("traffic-banner");
const alongRouteBox = document.getElementById("along-route-box");
const alongRouteInput = document.getElementById("along-route-input");
const alongRouteSuggestionsEl = document.getElementById("along-route-suggestions");

searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  const query = searchInput.value.trim();
  if (!query) {
    suggestionsEl.innerHTML = "";
    return;
  }
  searchDebounce = setTimeout(() => fuzzySearch(query), 300);
});

async function fuzzySearch(query) {
  try {
    const center = map.getCenter();
    const params = new URLSearchParams({
      action: "search",
      q: query,
      lat: center.lat,
      lon: center.lng,
    });
    const res = await fetch(`/api/route?${params.toString()}`);
    const data = await res.json();
    renderSuggestions(data.results || []);
  } catch (err) {
    suggestionsEl.innerHTML = `<div class="suggestion-error">Search failed</div>`;
  }
}

function renderSuggestions(results) {
  suggestionsEl.innerHTML = "";
  results.forEach((r) => {
    const div = document.createElement("div");
    div.className = "suggestion";
    div.textContent = r.name;
    div.onclick = () => addStop(r);
    suggestionsEl.appendChild(div);
  });
}

function addStop(result) {
  stops.push({ name: result.name, lat: result.lat, lon: result.lon });
  searchInput.value = "";
  suggestionsEl.innerHTML = "";
  renderStops();
}

function clearMarkers() {
  markers.forEach((m) => m.remove());
  markers = [];
}

function renderStops() {
  stopListEl.innerHTML = "";
  clearMarkers();
  stops.forEach((s, i) => {
    const row = document.createElement("div");
    row.className = "stop";
    const label = i === 0 ? `${s.name} (Origin)` : s.name;
    row.innerHTML = `<span>${i + 1}. ${label}</span>`;
    const btn = document.createElement("button");
    btn.textContent = "Remove";
    btn.onclick = () => {
      stops.splice(i, 1);
      renderStops();
    };
    row.appendChild(btn);
    stopListEl.appendChild(row);

    const marker = new tt.Marker().setLngLat([s.lon, s.lat]).addTo(map);
    markers.push(marker);
  });
}

function clearRouteLayer() {
  if (map.getLayer(ROUTE_SOURCE_ID)) map.removeLayer(ROUTE_SOURCE_ID);
  if (map.getSource(ROUTE_SOURCE_ID)) map.removeSource(ROUTE_SOURCE_ID);
}

function drawRoute(points) {
  clearRouteLayer();
  if (!points.length) return;
  const coordinates = points.map((p) => [p.lon, p.lat]);

  map.addSource(ROUTE_SOURCE_ID, {
    type: "geojson",
    data: { type: "Feature", geometry: { type: "LineString", coordinates } },
  });
  map.addLayer({
    id: ROUTE_SOURCE_ID,
    type: "line",
    source: ROUTE_SOURCE_ID,
    paint: { "line-color": "#1f6f54", "line-width": 5 },
  });

  const bounds = coordinates.reduce(
    (b, c) => b.extend(c),
    new tt.LngLatBounds(coordinates[0], coordinates[0])
  );
  map.fitBounds(bounds, { padding: 60 });
}

function renderTrafficBanner(travelTimeSeconds, trafficDelaySeconds) {
  const delay = trafficDelaySeconds || 0;
  if (delay <= 0) {
    trafficBannerEl.classList.add("hidden");
    trafficBannerEl.textContent = "";
    return;
  }
  const delayMins = Math.round(delay / 60);
  trafficBannerEl.classList.remove("hidden");
  trafficBannerEl.textContent = `Live Traffic Rerouting: this trip currently includes +${delayMins} min of traffic delay, already factored into the optimized sequence.`;
}

async function optimizeRoute() {
  if (stops.length < 2) {
    resultEl.textContent = "Add at least two stops first.";
    return;
  }
  resultEl.textContent = "Optimizing with live traffic...";
  const res = await fetch("/api/route?action=optimize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ locations: stops }),
  });
  const data = await res.json();
  if (data.error) {
    resultEl.textContent = data.error;
    return;
  }
  stops = data.ordered_locations;
  lastPolyline = data.polyline || [];
  renderStops();
  drawRoute(lastPolyline);
  renderTrafficBanner(data.travel_time_seconds, data.traffic_delay_seconds);

  const km = (data.distance_meters / 1000).toFixed(1);
  const mins = Math.round(data.travel_time_seconds / 60);
  const delay = Math.round((data.traffic_delay_seconds || 0) / 60);
  resultEl.textContent = `Optimized: ${km} km, ~${mins} min (incl. ${delay} min traffic delay)`;

  alongRouteBox.classList.remove("hidden");
}

alongRouteInput.addEventListener("input", () => {
  clearTimeout(alongRouteDebounce);
  const query = alongRouteInput.value.trim();
  if (!query) {
    alongRouteSuggestionsEl.innerHTML = "";
    return;
  }
  alongRouteDebounce = setTimeout(() => searchAlongRoute(query), 350);
});

async function searchAlongRoute(query) {
  if (!lastPolyline.length) return;
  alongRouteSuggestionsEl.innerHTML = `<div class="suggestion-error">Searching...</div>`;
  try {
    const res = await fetch("/api/route?action=search_along_route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, route: lastPolyline }),
    });
    const data = await res.json();
    if (data.error) {
      alongRouteSuggestionsEl.innerHTML = `<div class="suggestion-error">${data.error}</div>`;
      return;
    }
    renderAlongRouteSuggestions(data.results || []);
  } catch (err) {
    alongRouteSuggestionsEl.innerHTML = `<div class="suggestion-error">Search failed</div>`;
  }
}

function renderAlongRouteSuggestions(results) {
  alongRouteSuggestionsEl.innerHTML = "";
  if (!results.length) {
    alongRouteSuggestionsEl.innerHTML = `<div class="suggestion-error">No matches found along this route</div>`;
    return;
  }
  results.forEach((r) => {
    const row = document.createElement("div");
    row.className = "along-route-suggestion";
    row.innerHTML = `<span>${r.name} (+${r.detour_minutes} min detour)</span>`;
    const btn = document.createElement("button");
    btn.textContent = "Add to Route";
    btn.onclick = () => addDetourStop(r);
    row.appendChild(btn);
    alongRouteSuggestionsEl.appendChild(row);
  });
}

async function addDetourStop(result) {
  stops.push({ name: result.name, lat: result.lat, lon: result.lon });
  alongRouteInput.value = "";
  alongRouteSuggestionsEl.innerHTML = "";
  await optimizeRoute();
}

document.getElementById("optimize-btn").addEventListener("click", optimizeRoute);
