ECAC Airports METAR/TAF + SNOWTAM Viewer — v13
Overview
This web-based HTML application (version 13) provides flight dispatchers with a real-time, map-based interface to monitor airports across the ECAC region. The tool integrates METAR, TAF, and SNOWTAM data, highlights active runway condition reports, and allows visual inspection of runways divided into thirds. Version 13 introduces enhanced robustness with an embedded fallback airport list to guarantee that airports are always visible, even if the OurAirports data feed is unavailable.
Main Features
•	Interactive map view (Leaflet + OpenStreetMap) tailored for 16:9 displays.
•	Displays large and medium airports in ECAC as grey markers.
•	Markers change color when SNOWTAMs are detected: YELLOW, ORANGE, or RED, with blinking for severity.
•	Automatic retrieval of METAR, TAF, and SNOWTAM data on airport click.
•	Automatic background refresh every 15 minutes (toggleable ON/OFF).
•	Manual 'Refresh now' button to update METAR/TAF for all airports at once.
•	Reload Airports button to re-fetch the airport list dynamically.
•	Built-in fallback list of major European airports (ensures markers are always visible).
•	Runway visualization: runways drawn and divided into three segments, each colored according to RWYCC from SNOWTAM.
•	Detailed SNOWTAM decoder translating ICAO fields (A, B, C, D, E, F, G, H, N, T) into plain English.
•	Diagnostics bar to display status messages.
•	Toast notifications for real-time feedback (e.g., METAR updated, SNOWTAM found).
•	Support for multiple CORS proxies to bypass restrictive network environments.
System Architecture
The application is fully client-side, implemented in HTML, CSS, and JavaScript. It requires no server-side logic. The map rendering is handled by Leaflet, with tiles from OpenStreetMap. Data retrieval is done via public aviation data sources, with multiple proxy layers to mitigate CORS or firewall restrictions. The application can run locally in a browser or be hosted on any static web server (e.g., GitHub Pages, Netlify, Vercel).
Data Sources
•	OurAirports CSV datasets (airports.csv, runways.csv) with GitHub mirror fallback.
•	Built-in embedded fallback list of major airports (ensures resilience if CSV feeds fail).
•	Aviation Weather Center (aviationweather.gov) METAR and TAF API.
•	FAA NOTAM services (notams.aim.faa.gov, notams.faa.gov) for SNOWTAM retrieval.
•	Multiple CORS proxies: direct, corsproxy.io, thingproxy.freeboard.io, and jina.ai cache.
Usage Instructions
1.	Open the HTML file (index.html) in any modern web browser (Chrome, Edge, Firefox).
2.	The map initializes centered over Europe with airports shown as grey dots.
3.	If the online data source is unavailable, a fallback set of major European airports is loaded automatically.
4.	Click on any airport marker to automatically fetch and display its latest METAR, TAF, and SNOWTAM data.
5.	Markers will change color based on SNOWTAM severity (YELLOW/ORANGE/RED).
6.	Runways appear when zoomed in to level ≥ 10, divided into three colored thirds based on RWYCC values.
7.	Use the 'Reload airports' button to refresh the airport dataset.
8.	Use 'Refresh now' to immediately update METAR/TAF for all airports.
9.	Toggle 'Auto 15m' to enable or disable automatic 15-minute refresh cycles.
10.	Check or uncheck 'Show Runways' to enable or disable runway overlays.
11.	Status messages are displayed in the Diagnostics bar at the bottom-left, while pop-up toasts appear in the top-right corner.
SNOWTAM Decoding
The decoder translates ICAO SNOWTAM fields into plain English:
- A) Aerodrome location indicator
- B) Observation time (UTC)
- C) Runway designator(s)
- D) Runway Condition Codes (RWYCC) for thirds
- E) Percent coverage
- F) Depth of deposit (mm)
- G) Condition description (e.g., slush, ice)
- H) Width of cleared runway (m)
- N) Remarks
- T) Measured friction or braking action method

Categories:
- RED: RWYCC 0–1 (very poor / closed)
- ORANGE: RWYCC 2–3 (medium to poor)
- YELLOW: RWYCC 4–5 (good to medium)
- GREY: No active SNOWTAM
Deployment
To deploy the tool publicly, upload the HTML file to any static web host.

GitHub Pages deployment:
1. Create a new repository on GitHub.
2. Upload the HTML file and rename it to 'index.html'.
3. Enable GitHub Pages in repository settings → Pages (branch: main, folder: root).
4. Access the live site at: https://<username>.github.io/<repository>/
Limitations
• METAR/TAF/SNOWTAM availability depends on external sources and may be subject to temporary outages.
• Some AIS/NOTAM sources may require login or block cross-origin requests; FAA fallback ensures minimal coverage.
• In restrictive networks, proxies may also be blocked; the 'Reload airports' fallback list ensures visibility of major airports regardless.
• The application shows only large and medium airports to avoid clutter and maintain performance.
Conclusion
The ECAC Airports Viewer v13 is a robust, self-contained monitoring tool for dispatchers and flight operations. With embedded fallbacks, proxy support, and detailed SNOWTAM decoding, it ensures continuous situational awareness across the European region even in constrained network environments.

