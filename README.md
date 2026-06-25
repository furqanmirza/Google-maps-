# SmartRoute

## Origin Story

In May, my parents flew in for my graduation. Between the ceremony, family
dinners, and showing them around, we ended up with a list of stops scattered
across Arizona — Phoenix, Sedona, the Grand Canyon, Tucson — and no good way
to figure out the order that wouldn't waste half the day driving back and
forth. I sat there manually reordering pins on a map app, eyeballing
distances. SmartRoute is the tool I wished I'd had: drop in your stops, get
the optimal route, and get nudged toward worthwhile detours along the way.

## What It Does

1. **Dynamic Stop Reordering** — enter an unordered list of stops; a Python
   serverless function computes the optimal visiting order (nearest-neighbor
   + 2-opt heuristic TSP solver).
2. **Smart POI Suggestions** — once the route is optimized, nearby points of
   interest within a small detour radius of the route polyline are surfaced.
3. **Low-Impact Detour Addition** — add a suggested POI and the backend
   reinserts it at the position that adds the least extra distance, then
   re-optimizes.

## Tech Stack

- Frontend: static HTML/CSS/Vanilla JS + Leaflet.js (`public/`)
- Backend: Python serverless function, standard library only (`api/`)
- Hosting: Vercel free tier

## Project Structure

```
.
├── api/
│   └── index.py        # TSP solver + POI suggestion endpoint
├── public/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── requirements.txt
├── vercel.json
└── README.md
```

## Deploying to Vercel (Free Tier)

1. **Push to GitHub**
   ```bash
   git init                      # if not already a repo
   git add .
   git commit -m "Initial SmartRoute MVP"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```

2. **Connect to Vercel**
   - Go to https://vercel.com/new
   - Import your GitHub repository
   - Framework preset: **Other** (no build step needed)
   - Leave build/output settings at defaults — `public/` is served as
     static assets and `api/index.py` is auto-detected as a Python
     serverless function
   - Click **Deploy**

3. **Verify**
   - Visit the deployed URL
   - Add a few stops, click "Optimize Route"
   - Confirm the map redraws with the optimized polyline and suggested
     detours appear in the sidebar

No environment variables, API keys, or paid services required — everything
runs on Vercel's free tier using open-source mapping (OpenStreetMap tiles
via Leaflet) and a self-contained Python heuristic solver.
