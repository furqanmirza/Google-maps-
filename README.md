# SmartRoute

## Origin Story

In May, my parents flew in for my graduation. Between the ceremony, family
dinners, and showing them around, we ended up with a list of stops scattered
across Arizona — Phoenix, Sedona, the Grand Canyon, Tucson — and no good way
to figure out the order that wouldn't waste half the day driving back and
forth, especially with traffic changing throughout the day. I sat there
manually reordering pins on a map app, eyeballing distances. SmartRoute is
the tool I wished I'd had: search for your stops, get the optimal order,
and account for live traffic conditions automatically.

## V2 — Live Traffic Upgrade

V1 used a homegrown Haversine distance matrix and a local 2-opt heuristic.
V2 retires all of that custom math in favor of TomTom's cloud routing
engine:

- **Seamless search** — manual lat/lng inputs are gone. A single search box
  queries a backend proxy (`/api/route?action=search`), which calls
  TomTom's Fuzzy Search API and returns a clean autocomplete dropdown.
- **Native TSP + live traffic** — optimizing a route now calls
  `/api/route?action=optimize`, which proxies to TomTom's Calculate Route
  API with `computeBestOrder=true`, `traffic=true`, and `depart=now`,
  so TomTom's own waypoint-ordering engine reorders stops using real-time
  traffic conditions.
- **Road-snapped polylines** — the optimized route geometry returned by
  TomTom is drawn directly on a TomTom Maps Web SDK map, with the view
  auto-fit to the full trip.
- **Locked start banner** — a stylized note in the sidebar makes clear the
  first stop added is the fixed origin; everything else is reordered.

## Tech Stack

- Frontend: static HTML/CSS/Vanilla JS + TomTom Maps SDK for Web (`public/`)
- Backend: Python serverless function using `requests` (`api/`)
- External APIs: TomTom Search API, TomTom Routing API (both proxied
  server-side so the secret API key never reaches the browser)
- Hosting: Vercel free tier

## Project Structure

```
.
├── api/
│   └── index.py        # GET ?action=search, POST ?action=optimize — proxies TomTom
├── public/
│   ├── index.html       # TomTom Maps SDK tags + frontend key placeholder
│   ├── style.css         # autocomplete dropdown + locked-start banner styling
│   └── app.js             # map init, search box, polyline plotting
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

Two distinct roles for the same TomTom key:

- **Frontend map key (public by design):** open `public/index.html` and
  replace:
  ```html
  <script>
    window.TOMTOM_API_KEY = "[YOUR_TOMTOM_FRONTEND_PUBLIC_KEY]";
  </script>
  ```
  This key only initializes map tiles in the browser — it never makes
  Search or Routing calls directly.
- **Backend key (secret, used by the proxy):** all Search and Routing API
  calls happen server-side in `api/index.py`, reading from the
  `TOMTOM_API_KEY` environment variable. It is never embedded in any
  frontend file.

### Adding `TOMTOM_API_KEY` to Vercel

1. Open your project in the Vercel dashboard.
2. Go to **Settings → Environment Variables**.
3. Add a new variable: Name `TOMTOM_API_KEY`, Value `<your TomTom key>`,
   scope it to Production / Preview / Development as needed.
4. Redeploy (or trigger a new deployment) so the function picks it up.

## Deploying to Vercel (Free Tier)

1. **Push to GitHub**
   ```bash
   git init                      # if not already a repo
   git add .
   git commit -m "SmartRoute V2: live traffic + TomTom"
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
   - Search for and add at least two stops via the search box
   - Click **Optimize Route (Live Traffic)**
   - Confirm the map redraws with the optimized, traffic-aware,
     road-snapped route

No paid services required — TomTom's free tier and Vercel's free tier
cover this app end to end.
