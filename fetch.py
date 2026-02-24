import json
import re
import time
import urllib.request
import urllib.parse

QUERY = """

"""

OUTPUT = "places.json"

SERVERS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

RANK = {
    "region": 1, "province": 1, "state": 1,
    "district": 2, "county": 2,
    "municipality": 3, "city": 3,
    "town": 4,
    "village": 5, "hamlet": 5, "isolated_dwelling": 5,
    "suburb": 6, "quarter": 6,
    "neighbourhood": 7, "allotments": 7,
}


def load_queries(text):
    lines = [l for l in text.splitlines() if not l.strip().startswith("//")]
    blocks = re.split(r'(?=\[out:json\])', "\n".join(lines))
    return [b.strip() for b in blocks if b.strip()]


def fetch(query):
    timeout = int((re.search(r'\[timeout:(\d+)\]', query) or type('',(),{'group':lambda s,x:'600'})()).group(1)) + 30
    data = urllib.parse.urlencode({"data": query}).encode()
    for server in SERVERS:
        wait = 15
        for attempt in range(4):
            try:
                print(f"  -> {server}", flush=True)
                req = urllib.request.Request(server, data=data, headers={"User-Agent": "BORDMET/1.5"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print(f"  ! 429 — waiting {wait}s", flush=True)
                    time.sleep(wait)
                    wait = min(wait * 2, 120)
                else:
                    print(f"  ! HTTP {e.code}", flush=True)
                    break
            except Exception as e:
                print(f"  ! {e}", flush=True)
                break
    raise RuntimeError("all servers failed")


all_places = []
seen = set()

for idx, query in enumerate(load_queries(QUERY)):
    types = (re.search(r'\["place"~"\^\(([^)]+)\)\$"\]', query) or type('',(),{'group':lambda s,x:''})()).group(1)
    print(f"\n[BAND {idx+1} — {types}]", flush=True)
    if idx > 0:
        print("  ~ 5s pause", flush=True)
        time.sleep(5)
    t0 = time.time()
    try:
        result = fetch(query)
    except RuntimeError as e:
        print(f"  SKIPPED: {e}", flush=True)
        continue
    new = 0
    for el in result.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:en")
        place = tags.get("place", "")
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if not name or lat is None or lon is None:
            continue
        key = (name.lower(), place)
        if key in seen:
            continue
        seen.add(key)
        all_places.append({"name": name, "place": place, "rank": RANK.get(place, 9), "coordinates": [round(float(lat), 7), round(float(lon), 7)]})
        new += 1
        print(f"    [{RANK.get(place,9)}] {place:20s} {name}", flush=True)
    print(f"  {new} new  ({time.time()-t0:.1f}s)", flush=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(sorted(all_places, key=lambda x: x["rank"]), f, ensure_ascii=False, indent=2)
    print(f"  -> {len(all_places)} total in {OUTPUT}", flush=True)

print(f"\nDone. {len(all_places)} places in {OUTPUT}")