/* global L */
const POLL_SECONDS = 60;

const state = {
  map: null,
  airports: [], // {icao,iata,name,lat,lon,country}
  markers: new Map(), // icao -> {marker, airport}
  status: {}, // icao -> status object
  lastFetchUtc: null,
};

function fmtUtc(iso){
  if(!iso) return "—";
  try{
    const d = new Date(iso);
    return d.toISOString().replace('T',' ').replace('.000Z','Z');
  }catch{ return iso; }
}

function colorFor(sev){
  switch(sev){
    case "ok": return "#2ecc71";
    case "yellow": return "#f1c40f";
    case "orange": return "#f39c12";
    case "red": return "#e74c3c";
    default: return "#7f8c8d";
  }
}

function badgeClass(sev){
  switch(sev){
    case "ok": return "ok";
    case "yellow": return "y";
    case "orange": return "o";
    case "red": return "r";
    default: return "g";
  }
}

function labelFor(sev){
  switch(sev){
    case "ok": return "OK";
    case "yellow": return "MINOR";
    case "orange": return "MOD";
    case "red": return "SEV";
    default: return "…";
  }
}

function getPrevMap(){
  try{
    return JSON.parse(localStorage.getItem("snowtamPrev") || "{}");
  }catch{
    return {};
  }
}
function setPrevMap(obj){
  localStorage.setItem("snowtamPrev", JSON.stringify(obj));
}

function ensureMap(){
  state.map = L.map('map', { preferCanvas: true }).setView([48.0, 12.0], 4);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 10,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(state.map);
}

function markerPopupContent(airport){
  const s = state.status[airport.icao];
  const has = s && s.hasSnowtam;
  const sev = s ? s.severity : "unknown";
  const received = has ? fmtUtc(s.receivedUtc) : "—";
  const raw = has ? s.raw : "No valid SNOWTAM found for this aerodrome.";
  const decode = has ? (s.decode || "Decode not available.") : "—";
  return { sev, received, raw, decode, meta: s };
}

function openPopup(airport){
  const {sev, received, raw, decode, meta} = markerPopupContent(airport);
  document.getElementById("popupTitle").textContent =
    `${airport.icao}${airport.iata ? " / " + airport.iata : ""} — ${airport.name || ""}`.trim();

  const sevLabel = labelFor(sev);
  const sourceName = (meta && meta.source && meta.source.name) ? meta.source.name : "Repository JSON";
  document.getElementById("popupMeta").textContent =
    `Severity: ${sevLabel} | Received: ${received} | Source: ${sourceName}`;

  document.getElementById("popupRaw").textContent = raw || "";
  document.getElementById("popupDecode").textContent = decode || "";

  document.getElementById("popup").classList.remove("hidden");
  setActiveTab("raw");
}

function closePopup(){
  document.getElementById("popup").classList.add("hidden");
}

function setActiveTab(tab){
  for(const btn of document.querySelectorAll(".tab")){
    const is = btn.dataset.tab === tab;
    btn.classList.toggle("active", is);
  }
  document.getElementById("popupRaw").classList.toggle("hidden", tab !== "raw");
  document.getElementById("popupDecode").classList.toggle("hidden", tab !== "decode");
}

function addMarkers(){
  const bounds = [];
  for(const ap of state.airports){
    if(typeof ap.lat !== "number" || typeof ap.lon !== "number") continue;
    const marker = L.circleMarker([ap.lat, ap.lon], {
      radius: 6,
      color: "#111",
      weight: 1,
      fillColor: "#7f8c8d",
      fillOpacity: 0.95
    }).addTo(state.map);

    marker.on("click", () => openPopup(ap));
    state.markers.set(ap.icao, { marker, airport: ap });
    bounds.push([ap.lat, ap.lon]);
  }
  if(bounds.length){
    state.map.fitBounds(bounds, { padding: [20,20] });
  }
}

function applyStatusToMarker(icao, status, changed){
  const entry = state.markers.get(icao);
  if(!entry) return;
  const marker = entry.marker;

  const sev = status ? status.severity : "unknown";
  marker.setStyle({ fillColor: colorFor(sev) });

  const el = marker.getElement && marker.getElement();
  if(el){
    el.classList.toggle("blinking", !!changed);
    if(changed){
      // Stop blinking automatically after 3 minutes
      setTimeout(() => {
        const e2 = marker.getElement && marker.getElement();
        if(e2) e2.classList.remove("blinking");
      }, 180000);
    }
  }
}

function renderList(filterText=""){
  const list = document.getElementById("list");
  list.innerHTML = "";
  const q = filterText.trim().toLowerCase();

  const airports = state.airports
    .filter(ap => {
      if(!q) return true;
      return (ap.icao || "").toLowerCase().includes(q)
        || (ap.iata || "").toLowerCase().includes(q)
        || (ap.name || "").toLowerCase().includes(q);
    })
    .slice(0, 300);

  for(const ap of airports){
    const s = state.status[ap.icao];
    const sev = s ? s.severity : "unknown";
    const item = document.createElement("div");
    item.className = "item";
    item.addEventListener("click", () => {
      const entry = state.markers.get(ap.icao);
      if(entry){
        state.map.setView(entry.marker.getLatLng(), Math.max(state.map.getZoom(), 7), { animate: true });
      }
      openPopup(ap);
    });

    const left = document.createElement("div");
    left.className = "left";
    const code = document.createElement("div");
    code.className = "code";
    code.textContent = `${ap.icao}${ap.iata ? " / " + ap.iata : ""}`;
    const name = document.createElement("div");
    name.className = "name";
    name.textContent = ap.name || "";
    left.appendChild(code);
    left.appendChild(name);

    const badge = document.createElement("div");
    badge.className = `badge ${badgeClass(sev)}`;
    badge.textContent = labelFor(sev);

    item.appendChild(left);
    item.appendChild(badge);
    list.appendChild(item);
  }
}

async function loadAirports(){
  const res = await fetch("./data/airports.json?t=" + Date.now(), { cache: "no-store" });
  if(!res.ok) throw new Error("Failed to load data/airports.json");
  const json = await res.json();
  state.airports = json.airports || [];
}

async function loadStatus(){
  const res = await fetch("./data/snowtam_status.json?t=" + Date.now(), { cache: "no-store" });
  if(!res.ok) throw new Error("Failed to load data/snowtam_status.json");
  const json = await res.json();

  state.lastFetchUtc = json.generatedUtc || null;

  // UI header
  document.getElementById("dataStamp").textContent = fmtUtc(state.lastFetchUtc);
  const src = json.source || {};
  document.getElementById("srcLink").textContent = src.name || "—";
  document.getElementById("srcLink").href = src.url || "#";

  const prev = getPrevMap();
  const nextPrev = { ...prev };

  state.status = json.airports || {};

  for(const [icao, s] of Object.entries(state.status)){
    const h = s && s.hash ? s.hash : "";
    const prevH = prev[icao] || "";
    const changed = (prevH !== h);
    applyStatusToMarker(icao, s, changed);
    nextPrev[icao] = h;
  }

  // also: if an airport disappears from JSON, keep its previous hash, but marker will remain
  setPrevMap(nextPrev);
}

async function boot(){
  ensureMap();

  document.getElementById("pollEvery").textContent = `${POLL_SECONDS}s`;

  document.getElementById("popupClose").addEventListener("click", closePopup);
  document.getElementById("popup").addEventListener("click", (e) => {
    if(e.target && e.target.id === "popup") closePopup();
  });
  for(const btn of document.querySelectorAll(".tab")){
    btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
  }
  document.addEventListener("keydown", (e) => {
    if(e.key === "Escape") closePopup();
  });

  document.getElementById("search").addEventListener("input", (e) => {
    renderList(e.target.value || "");
  });

  // Load airports first to draw markers
  await loadAirports();
  addMarkers();
  renderList("");

  // Load status and then poll
  await loadStatus();
  renderList(document.getElementById("search").value || "");

  setInterval(async () => {
    try{
      await loadStatus();
      renderList(document.getElementById("search").value || "");
    }catch(err){
      console.error(err);
      document.getElementById("dataStamp").textContent = "ERROR";
    }
  }, POLL_SECONDS * 1000);
}

boot().catch(err => {
  console.error(err);
  document.getElementById("dataStamp").textContent = "BOOT ERROR";
});
