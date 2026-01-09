#!/usr/bin/env python3
"""
Update airports.json (lat/lon/name/iata) + snowtam_status.json by scraping a public SNOWTAM page.

IMPORTANT
- This is NOT an official AIS/NOTAM service.
- Ensure your use complies with the source website's terms/disclaimer and your organisation's policies.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from bs4 import BeautifulSoup

OURAIRPORTS_CSV = "https://davidmegginson.github.io/ourairports-data/airports.csv"
SNOWTAM_URL = "https://flightplan.romatsa.ro/init/notam/getsnowtam?ad={icao}"

USER_AGENT = "Mozilla/5.0 (compatible; WIZZ-SNOWTAM-Watch/1.0; +https://github.com/)"

@dataclass
class Airport:
    icao: str
    iata: str
    name: str
    lat: float
    lon: float
    iso_country: str

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_airports_txt(path: str) -> List[str]:
    icaos: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            code = line.strip().upper()
            if not code:
                continue
            if not re.fullmatch(r"[A-Z0-9]{4}", code):
                print(f"Skipping invalid ICAO in airports.txt: {code}", file=sys.stderr)
                continue
            icaos.append(code)
    return sorted(set(icaos))

def fetch_url(url: str, timeout: int = 35, retries: int = 3, backoff_s: float = 2.0) -> bytes:
    """Fetch URL with small retry/backoff to reduce flaky Action failures."""
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=timeout) as r:
                return r.read()
        except (HTTPError, URLError, TimeoutError, OSError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff_s * attempt)
            else:
                raise
    # unreachable, but keeps type-checkers happy
    raise last_err  # type: ignore[misc]


def load_cached_airports(out_airports_path: str) -> Dict[str, Airport]:
    """Load a previously generated data/airports.json as a fallback."""
    try:
        with open(out_airports_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        out: Dict[str, Airport] = {}
        for a in payload.get("airports", []) or []:
            icao = (a.get("icao") or "").strip().upper()
            lat = a.get("lat")
            lon = a.get("lon")
            if len(icao) == 4 and isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                out[icao] = Airport(
                    icao=icao,
                    iata=(a.get("iata") or "").strip().upper(),
                    name=(a.get("name") or "").strip(),
                    lat=float(lat),
                    lon=float(lon),
                    iso_country=(a.get("country") or "").strip().upper(),
                )
        return out
    except Exception:
        return {}

def load_ourairports_index() -> Dict[str, Airport]:
    """
    Return mapping: ident(ICAO) -> Airport.
    """
    raw = fetch_url(OURAIRPORTS_CSV, timeout=60).decode("utf-8", errors="replace")
    reader = csv.DictReader(raw.splitlines())
    out: Dict[str, Airport] = {}
    for row in reader:
        ident = (row.get("ident") or "").strip().upper()
        if len(ident) != 4:
            continue
        lat = row.get("latitude_deg") or ""
        lon = row.get("longitude_deg") or ""
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except Exception:
            continue
        out[ident] = Airport(
            icao=ident,
            iata=(row.get("iata_code") or "").strip().upper(),
            name=(row.get("name") or "").strip(),
            lat=lat_f,
            lon=lon_f,
            iso_country=(row.get("iso_country") or "").strip().upper(),
        )
    return out

def extract_text_blocks(html: str) -> Tuple[str, str, str, str]:
    """
    Return: received_utc_text, raw_block, decode_block, decode_opposite_block
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")

    # Received on:YYYY-MM-DD HH:MM UTC
    received = ""
    m = re.search(r"Received on:\s*([0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}\s+UTC)", text)
    if m:
        received = m.group(1)

    # RAW block: start at line containing '(SNOWTAM' and include until ')'
    raw = ""
    # The page typically contains an initial line like "SWXXXXnnnn ICAO yymmddhhmm"
    # We'll capture from the first line starting with 'SW' until a line containing ').)'
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip() != ""]
    # find index of first line that starts with SW and contains ICAO
    start_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("SW") and "SNOWTAM" in " ".join(lines[i:i+5]):
            start_idx = i
            break
        if ln.startswith("SW") and re.search(r"\bSNOWTAM\b", ln):
            start_idx = i
            break
        # common format: "SWLH0012 LHBP 01090622"
        if ln.startswith("SW") and len(ln.split()) >= 3 and re.fullmatch(r"[A-Z0-9]{4}", ln.split()[1]):
            start_idx = i
            break
    if start_idx is not None:
        collected = []
        for ln in lines[start_idx:]:
            collected.append(ln)
            if ln.strip().endswith(").") or ln.strip().endswith(")"):
                # heuristic stop: raw usually ends at ')'
                # but keep collecting until we hit 'UNOFFICIAL PLAIN LANGUAGE DECODE'
                if "UNOFFICIAL PLAIN LANGUAGE DECODE" in "\n".join(lines[start_idx: start_idx+120]):
                    break
        raw = "\n".join(collected).strip()

    # Decode blocks:
    decode = ""
    decode2 = ""
    # We'll locate headings and take until next heading
    def slice_between(head: str, next_head: str) -> str:
        try:
            a = text.index(head)
        except ValueError:
            return ""
        b = text.find(next_head, a + len(head))
        if b == -1:
            b = len(text)
        return text[a+len(head):b].strip()

    decode = slice_between("UNOFFICIAL PLAIN LANGUAGE DECODE", "UNOFFICIAL PLAIN LANGUAGE DECODE OPPOSITE DIRECTION")
    decode2 = slice_between("UNOFFICIAL PLAIN LANGUAGE DECODE OPPOSITE DIRECTION", "Select voice:")

    return received, raw, decode, decode2

def received_to_iso(received_text: str) -> Optional[str]:
    # "2026-01-09 06:32 UTC"
    if not received_text:
        return None
    try:
        dt = datetime.strptime(received_text, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except Exception:
        return None

def snowtam_severity(raw: str, decode: str) -> Tuple[str, str]:
    """
    Return (severity, summary)
    severity in: ok, yellow, orange, red
    """
    if not raw.strip():
        return "ok", "No valid SNOWTAM"
    # hard red indicators
    upper = (raw + "\n" + decode).upper()
    if any(k in upper for k in ["CLOSED", "CLSD", "RWY CLSD", "RUNWAY CLSD"]):
        return "red", "Runway closed indicator found"
    if "BRAKING ACTION" in upper and "POOR" in upper:
        return "red", "Braking action POOR"

    # parse surface condition codes (GRF) from decode: "SURFACE CONDITION CODE 5 5 5"
    codes: List[int] = []
    for m in re.finditer(r"SURFACE CONDITION CODE\s+([0-9])\s+([0-9])\s+([0-9])", decode.upper()):
        try:
            codes.extend([int(m.group(1)), int(m.group(2)), int(m.group(3))])
        except Exception:
            pass

    min_code = min(codes) if codes else None

    # movement areas POOR pushes to at least orange
    has_poor = " POOR" in upper

    if min_code is not None:
        if min_code <= 2:
            sev = "red"
        elif 3 <= min_code <= 4:
            sev = "orange"
        else:
            sev = "yellow"
        if has_poor and sev == "yellow":
            sev = "orange"
        summary = f"minRWYCC={min_code}; poorAreas={has_poor}"
        return sev, summary

    # fallback if we cannot parse codes
    if has_poor:
        return "orange", "Could not parse RWYCC; POOR movement area noted"
    return "yellow", "Could not parse RWYCC; SNOWTAM present"

def stable_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8", errors="ignore"))
        h.update(b"\n---\n")
    return h.hexdigest()[:16]

def main() -> int:
    repo_root = "."
    airports_txt = f"{repo_root}/airports.txt"
    out_airports = f"{repo_root}/data/airports.json"
    out_status = f"{repo_root}/data/snowtam_status.json"

    icaos = read_airports_txt(airports_txt)
    if not icaos:
        print("No ICAO codes found in airports.txt", file=sys.stderr)
        return 2

    print(f"Loading OurAirports index ({len(icaos)} ICAOs)…")
    idx: Dict[str, Airport] = {}
    ourairports_error: Optional[str] = None
    try:
        idx = load_ourairports_index()
    except Exception as e:
        ourairports_error = f"{type(e).__name__}: {e}"
        print(
            "WARNING: Could not download OurAirports airports.csv. "
            "Falling back to cached data/airports.json if available. "
            f"Details: {ourairports_error}",
            file=sys.stderr,
        )
        idx = load_cached_airports(out_airports)

    airports_payload = {
        "generatedUtc": utc_now_iso(),
        "source": {"name": "OurAirports (public domain)", "url": "https://ourairports.com/data/"},
        "warnings": ([f"OurAirports download failed; using cached airports.json. {ourairports_error}"] if ourairports_error else []),
        "airports": []
    }
    for icao in icaos:
        ap = idx.get(icao)
        if not ap:
            # still include, but without coords
            airports_payload["airports"].append({
                "icao": icao, "iata": "", "name": "(not found in OurAirports)", "lat": None, "lon": None, "country": ""
            })
        else:
            airports_payload["airports"].append({
                "icao": ap.icao,
                "iata": ap.iata,
                "name": ap.name,
                "lat": ap.lat,
                "lon": ap.lon,
                "country": ap.iso_country
            })

    # Fetch SNOWTAM pages
    print("Fetching SNOWTAMs…")
    status_airports: Dict[str, dict] = {}

    for n, icao in enumerate(icaos, start=1):
        url = SNOWTAM_URL.format(icao=icao)
        try:
            html = fetch_url(url, timeout=35).decode("utf-8", errors="replace")
            received_text, raw, dec, dec2 = extract_text_blocks(html)
            received_iso = received_to_iso(received_text)

            has_snowtam = bool(raw.strip())
            sev, summary = snowtam_severity(raw, dec)

            # try to extract snowtam number
            snowtam_no = ""
            m = re.search(r"\(SNOWTAM\s+([0-9]{4})", raw, re.IGNORECASE)
            if m:
                snowtam_no = m.group(1)

            h = stable_hash(raw.strip(), dec.strip(), dec2.strip())

            status_airports[icao] = {
                "icao": icao,
                "hasSnowtam": has_snowtam,
                "severity": ("ok" if not has_snowtam else sev),
                "receivedUtc": received_iso,
                "receivedText": received_text,
                "snowtamNumber": snowtam_no,
                "raw": raw.strip(),
                "decode": dec.strip(),
                "decodeOpposite": dec2.strip(),
                "summary": summary,
                "hash": h,
                "source": {"name": "ROMATSA Aeronautical Information Portal (unofficial page)", "url": url},
            }
        except Exception as e:
            status_airports[icao] = {
                "icao": icao,
                "hasSnowtam": False,
                "severity": "unknown",
                "receivedUtc": None,
                "error": str(e),
                "hash": stable_hash("error", str(e)),
                "source": {"name": "ROMATSA Aeronautical Information Portal (unofficial page)", "url": url},
            }

        # gentle pacing to reduce load on the external site
        if n % 10 == 0:
            time.sleep(1.0)

        print(f"{n:>3}/{len(icaos)} {icao} done")

    status_payload = {
        "generatedUtc": utc_now_iso(),
        "source": {"name": "ROMATSA Aeronautical Information Portal (unofficial)", "url": "https://flightplan.romatsa.ro/init/notam/snowtam"},
        "airports": status_airports
    }

    with open(out_airports, "w", encoding="utf-8") as f:
        json.dump(airports_payload, f, ensure_ascii=False, indent=2)

    with open(out_status, "w", encoding="utf-8") as f:
        json.dump(status_payload, f, ensure_ascii=False, indent=2)

    print("Wrote:", out_airports, out_status)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
