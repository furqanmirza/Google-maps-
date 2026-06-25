# SmartRoute

## Origin Story

In May, my parents flew in for my graduation. Between the ceremony, family
dinners, and showing them around, we ended up with a list of stops scattered
across Arizona — Phoenix, Sedona, the Grand Canyon, Tucson — and no good way
to figure out the order that wouldn't waste half the day driving back and
forth, especially with traffic changing throughout the day. I sat there
manually reordering pins on a map app, eyeballing distances. SmartRoute is
the tool I wished I'd had: search for your stops, get the optimal order, add
a detour without breaking your itinerary, and route around traffic
automatically.

## V4 — The Live Traffic TSP Rerouting Engine

SmartRoute's core is no longer a static optimizer — it's a **live traffic
TSP rerouting engine**. Every time the stop list changes (you add a stop,
or you add a suggested detour), the *entire* trip sequence is recalculated
from scratch by TomTom's cloud routing engine using current traffic
conditions (`traffic=true`, `depart=now`). The route isn't just re-drawn —
it's re-solved: TomTom's TSP engine decides whether the new stop belongs at
the start, middle, or end of the trip, and the whole sequence is re-ordered
to minimize total live-traffic-aware travel time. This means a bottleneck
detected on the original route can cause stops to be visited in a
completely different order, not just a patched-in detour.

### What's new in V4

1. **Context-Aware Location Search (Viewport Biasing)**
   The main search bar now sends the current map center (`map.getCenter()`)
   to the backend as `lat`/`lon`. The backend passes these to TomTom Search
   with `radius=50000` (50 km), so a generic query like "Sam's Club" returns
   the location nearest to what you're currently looking at on the map,
   instead of a essentially random nationwide match.

2. **Dynamic "Search Along Route" (Smart Detours)**
   There is no more hardcoded list of points of interest. Once a route is
   optimized, a "Find Along Route" search box appears. It calls a new
   `/api/route?action=search_along_route` endpoint, which forwards your
   route's polyline and query to **TomTom's Search Along Route API**. This
   returns real businesses/POIs that are physically near your *actual driving
   path*, ranked by detour time. Clicking "Add to Route" appends the stop and
   immediately triggers a full re-optimization — the live traffic rerouting
   engine described above — not just an insertion.

3. **Explicit Traffic Rerouting UI**
   The sidebar now surfaces a dedicated traffic banner whenever TomTom
   reports a non-zero `trafficDelayInSeconds`, e.g. *"Live Traffic
   Rerouting: this trip currently includes +12 min of traffic delay, already
   factored into the optimized sequence."* The main result line still shows
   total distance, total time, and the traffic delay component.

## Tech Stack

- Frontend: static HTML/CSS/Vanilla JS + TomTom Maps SDK for Web (`public/`)
- Backend: Python serverless function using `requests` (`api/`)
- External APIs: TomTom Search API (viewport-biased), TomTom Search Along
  Route API, TomTom Routing API (`computeBestOrder` + `traffic` + `depart=now`)
- Hosting: Vercel free tier

## Project Structure

```
.
├── api/
│   └── index.py        # GET ?action=search (viewport-biased)
│                         # POST ?action=optimize (live-traffic TSP)
│                         # POST ?action=search_along_route (smart detours)
├── public/
│   ├── index.html       # TomTom Maps SDK tags, search bar, along-route box
│   ├── style.css         # dropdowns, traffic banner, detour suggestion cards
│   └── app.js             # map init, viewport-biased search, along-route search,
│                           # traffic banner rendering, full re-optimization
├── requirements.txt      # requests only
├── vercel.json
└── README.md
```

## Getting a Free TomTom API Key (No Credit Card)

1. Go to https://developer.tomtom.com/ and click **Get a free API key**.
2. Sign up with just an email address — no credit card required for the
   free tier (2,500 free daily requests across Search/Routing/Maps).
3. In the Developer Portal, go to **My Apps** → create a new app, then
   copy the generated key.

## Configuring Keys

- **Frontend map key (public by design):** open `public/index.html` and
  replace:
  ```html
  <script>
    window.TOMTOM_API_KEY = "[YOUR_TOMTOM_FRONTEND_PUBLIC_KEY]";
  </script>
  ```
  This key only initializes map tiles in the browser.
- **Backend key (secret, used by the proxy):** all Search, Search Along
  Route, and Routing API calls happen server-side in `api/index.py`,
  reading from the `TOMTOM_API_KEY` environment variable. It is never
  embedded in any frontend file.

### Adding `TOMTOM_API_KEY` to Vercel

1. Open your project in the Vercel dashboard.
2. Go to **Settings → Environment Variables**.
3. Add a new variable: Name `TOMTOM_API_KEY`, Value `<your TomTom key>`,
   scope it to Production / Preview / Development as needed.
4. Redeploy so the function picks it up.

## Deploying to Vercel (Free Tier)

1. **Push to GitHub**
   ```bash
   git init                      # if not already a repo
   git add .
   git commit -m "SmartRoute V4: live traffic rerouting + smart detours"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```

2. **Connect to Vercel**
   - Go to https://vercel.com/new
   - Import your GitHub repository
   - Framework preset: **Other** (no build step needed)
   - `public/` is served as static assets; `api/index.py` is auto-detected
     as a Python serverless function

3. **Add the environment variable** (see above), then deploy.

4. **Verify**
   - Visit the deployed URL
   - Pan/zoom the map, then search for a generic place name — results
     should be biased toward your current viewport
   - Add at least two stops, click **Optimize Route (Live Traffic)**
   - Use **Find Along Route** to search for something like "Gas Station"
     and click **Add to Route** — confirm the trip re-optimizes and the
     traffic banner updates

No paid services required — TomTom's free tier and Vercel's free tier
cover this app end to end.
