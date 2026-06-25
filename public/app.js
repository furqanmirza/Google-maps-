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
let searchDebounce = null;

const searchInput = document.getElementById("search-input");
const suggestionsEl = document.getElementById("suggestions");
const stopListEl = document.getElementById("stop-list");
const resultEl = document.getElementById("result");

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
    const res = await fetch(`/api/route?action=search&q=${encodeURIComponent(query)}`);
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
  renderStops();
  drawRoute(data.polyline);
  const km = (data.distance_meters / 1000).toFixed(1);
  const mins = Math.round(data.travel_time_seconds / 60);
  const delay = Math.round((data.traffic_delay_seconds || 0) / 60);
  resultEl.textContent = `Optimized: ${km} km, ~${mins} min (incl. ${delay} min traffic delay)`;
}

document.getElementById("optimize-btn").addEventListener("click", optimizeRoute);
