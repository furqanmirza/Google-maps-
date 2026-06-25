const map = L.map("map").setView([34.0489, -111.0937], 7);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

let stops = [];
let routeLine = null;
let markers = [];

const stopListEl = document.getElementById("stop-list");
const poiListEl = document.getElementById("poi-list");
const resultEl = document.getElementById("result");

function renderStops() {
  stopListEl.innerHTML = "";
  stops.forEach((s, i) => {
    const row = document.createElement("div");
    row.className = "stop";
    row.innerHTML = `<span>${i + 1}. ${s.name}</span>`;
    const btn = document.createElement("button");
    btn.textContent = "Remove";
    btn.onclick = () => {
      stops.splice(i, 1);
      renderStops();
    };
    row.appendChild(btn);
    stopListEl.appendChild(row);
  });
}

function clearMapLayers() {
  markers.forEach((m) => map.removeLayer(m));
  markers = [];
  if (routeLine) {
    map.removeLayer(routeLine);
    routeLine = null;
  }
}

function drawRoute(ordered) {
  clearMapLayers();
  const latlngs = ordered.map((p) => [p.lat, p.lng]);
  ordered.forEach((p, i) => {
    const marker = L.marker([p.lat, p.lng]).addTo(map).bindPopup(`${i + 1}. ${p.name}`);
    markers.push(marker);
  });
  routeLine = L.polyline(latlngs, { color: "#1f6f54", weight: 4 }).addTo(map);
  map.fitBounds(routeLine.getBounds(), { padding: [40, 40] });
}

function renderPois(pois) {
  poiListEl.innerHTML = "";
  if (!pois.length) {
    poiListEl.innerHTML = "<p style='font-size:.8rem;color:#666;'>No nearby detours found.</p>";
    return;
  }
  pois.forEach((p) => {
    const row = document.createElement("div");
    row.className = "poi";
    row.innerHTML = `<span>${p.name} (+${p.detour_km} km)</span>`;
    const btn = document.createElement("button");
    btn.textContent = "Add";
    btn.onclick = () => addPoi(p);
    row.appendChild(btn);
    poiListEl.appendChild(row);
  });
}

async function optimizeRoute() {
  if (stops.length < 2) {
    resultEl.textContent = "Add at least two stops first.";
    return;
  }
  resultEl.textContent = "Optimizing...";
  const res = await fetch("/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "optimize", locations: stops }),
  });
  const data = await res.json();
  if (data.error) {
    resultEl.textContent = data.error;
    return;
  }
  stops = data.ordered_locations;
  renderStops();
  drawRoute(stops);
  renderPois(data.suggested_pois || []);
  resultEl.textContent = `Optimized! Total distance: ${data.total_distance_km} km`;
}

async function addPoi(poi) {
  resultEl.textContent = "Adding detour...";
  const res = await fetch("/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "add_poi", locations: stops, poi }),
  });
  const data = await res.json();
  if (data.error) {
    resultEl.textContent = data.error;
    return;
  }
  stops = data.ordered_locations;
  renderStops();
  drawRoute(stops);
  resultEl.textContent = `Added ${poi.name} (+${data.added_detour_km} km). Total: ${data.total_distance_km} km`;
  poiListEl.innerHTML = "";
}

document.getElementById("add-stop-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const name = document.getElementById("stop-name").value.trim();
  const lat = parseFloat(document.getElementById("stop-lat").value);
  const lng = parseFloat(document.getElementById("stop-lng").value);
  stops.push({ name, lat, lng });
  renderStops();
  e.target.reset();
});

document.getElementById("optimize-btn").addEventListener("click", optimizeRoute);

stops = [
  { name: "Phoenix Sky Harbor", lat: 33.4352, lng: -112.0101 },
  { name: "Flagstaff", lat: 35.1983, lng: -111.6513 },
  { name: "Tucson", lat: 32.2226, lng: -110.9747 },
  { name: "Page", lat: 36.9147, lng: -111.4558 },
];
renderStops();
