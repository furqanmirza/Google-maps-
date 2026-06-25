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

## What It Does

1. **Seamless Location Search** — type into the search bar to get live
   address/place suggestions via the TomTom Search API (Fuzzy Search);
   clicking a result adds it as a stop with saved coordinates.
2. **Native TSP Solver + Live Traffic** — stops are sent to a Python
   serverless function, which calls the TomTom Calculate Route API with
   `computeBestOrder=true` (TomTom's native waypoint-order optimizer) and
   `traffic=true` (live traffic-aware routing).
3. **Map Display** — the optimized route polyline is rendered on a TomTom
   Maps Web SDK map.
4. **Locked Start** — the first stop you add is always treated as your
   fixed starting origin; the UI calls this out explicitly.

## Tech Stack

- Frontend: static HTML/CSS/Vanilla JS + TomTom Maps SDK for Web (`public/`)
- Backend: Python serverless function, standard library only (`api/`)
- External APIs: TomTom Search API, TomTom Routing API
- Hosting: Vercel free tier

## Project Structure

```
.
├── api/
│   └── index.py        # Calls TomTom Calculate Route (computeBestOrder + traffic)
├── public/
│   ├── index.html       # TomTom SDK script/css tags + API key placeholder
│   ├── style.css
│   └── app.js            # Map init, fuzzy search dropdown, route drawing
├── requirements.txt      # empty — stdlib urllib only
├── vercel.json
└── README.md
```

## Getting a Free TomTom API Key (No Credit Card)

1. Go to https://developer.tomtom.com/ and click **Get a free API key**.
2. Sign up with just an email address — no credit card is required for the
   free tier (2,500 free daily requests across Search/Routing/Maps).
3. In the TomTom Developer Portal, go to **My Apps** → create a new app.
4. Copy the generated API key.
5. Optionally restrict the key to your deployed domain under app settings
   for production use.

## Configuring the Key

This app uses the **same TomTom key in two places**:

- **Frontend (client-side, public by design):** open `public/index.html`
  and replace the placeholder:
  ```html
  <script>
    window.TOMTOM_API_KEY = "YOUR_TOMTOM_API_KEY";
  </script>
  ```
- **Backend (server-side, kept secret):** set an environment variable named
  `TOMTOM_API_KEY` in your Vercel project (see below) — never hardcode it
  in `api/index.py`.

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

3. **Add the environment variable**
   - In the Vercel project → **Settings → Environment Variables**
   - Add `TOMTOM_API_KEY` = `<your TomTom key>` for Production/Preview/Dev
   - Click **Deploy** (or redeploy if you already deployed)

4. **Verify**
   - Visit the deployed URL
   - Search for and add at least two stops
   - Click **Optimize Route (Live Traffic)**
   - Confirm the map redraws with the optimized, traffic-aware route

No paid services required — TomTom's free tier and Vercel's free tier
cover this MVP end to end.
