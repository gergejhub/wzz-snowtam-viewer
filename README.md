# WIZZ SNOWTAM Watch (Unofficial)

Static GitHub Pages UI + GitHub Actions data updater.

## What it does

- Reads `airports.txt` (159 ICAO codes).
- Every ~10 minutes, GitHub Actions:
  - Builds `data/airports.json` from the public-domain OurAirports dataset.
  - Scrapes the public SNOWTAM page (per ICAO) and writes `data/snowtam_status.json`.
- The web UI (Leaflet map):
  - Shows airports as points.
  - Colors by severity:
    - Green: no valid SNOWTAM
    - Yellow: minor (RWYCC ≥ 5)
    - Orange: moderate (RWYCC 3–4 or “POOR” movement areas)
    - Red: severe (RWYCC ≤ 2 / CLOSED / critical)
  - Blinks when the SNOWTAM hash changes (new / updated / removed).

## Important disclaimer

This tool is **NOT** an official AIS/NOTAM service.
It relies on an external public web page and produces derived JSON. Use for situational awareness only, and always
cross-check with official briefing sources. Ensure usage complies with the source website disclaimer/terms and your internal policies.

## Deploy on GitHub Pages

1. Create a new GitHub repo and push the contents of this ZIP.
2. In GitHub:
   - **Settings → Pages**
   - Source: **Deploy from a branch**
   - Branch: `main` (or `master`), folder: `/ (root)`
3. Go to **Actions** tab and run **“Update SNOWTAM JSON”** once (workflow_dispatch).
4. Refresh the Pages site after the workflow finishes. Markers will appear once `data/airports.json` is generated.

## Change polling / severity rules

- UI polling interval: `assets/app.js` → `POLL_SECONDS`
- SNOWTAM parsing + severity logic: `scripts/update_snowtams.py`

## Data sources

- Airport coordinates/names: OurAirports open data dump.
- SNOWTAM page: ROMATSA Aeronautical Information Portal SNOWTAM pages (unofficial).
