import os
import requests
import pytz
from datetime import datetime, timedelta
from collections import defaultdict

# =========================
# CONFIG (ENV VARIABLES)
# =========================

API_URL = "https://api.cloudflare.com/client/v4/graphql"

API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
ACCOUNT_TAG = os.getenv("CLOUDFLARE_ACCOUNT_TAG")

if not API_TOKEN or not ACCOUNT_TAG:
    raise RuntimeError(
        "Missing environment variables. "
        "Please set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_TAG"
    )

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

QUERY = """
query ($accountTag: String!, $start: Time!, $end: Time!) {
  viewer {
    accounts(filter: { accountTag: $accountTag }) {
      rumPageloadEventsAdaptiveGroups(
        limit: 10000
        filter: {
          datetime_geq: $start
          datetime_lt: $end
        }
      ) {
        dimensions {
          requestPath
        }
        sum {
          visits
        }
      }
    }
  }
}
"""

# ===============================
# TIMEZONE HANDLING (GMT+2 DASHBOARD)
# ===============================

LOCAL_TZ = pytz.timezone("Europe/Athens")
UTC_TZ = pytz.utc

now_local = datetime.now(LOCAL_TZ)
yesterday_local = (now_local - timedelta(days=1)).date()

def local_to_utc_iso(hour, minute=0, second=0):
    local_dt = LOCAL_TZ.localize(
        datetime(
            yesterday_local.year,
            yesterday_local.month,
            yesterday_local.day,
            hour,
            minute,
            second
        )
    )
    return local_dt.astimezone(UTC_TZ).strftime("%Y-%m-%dT%H:%M:%SZ")

TIME_CHUNKS = [
    (local_to_utc_iso(0, 0, 0),  local_to_utc_iso(6, 0, 0)),
    (local_to_utc_iso(6, 0, 0),  local_to_utc_iso(12, 0, 0)),
    (local_to_utc_iso(12, 0, 0), local_to_utc_iso(18, 0, 0)),
    (local_to_utc_iso(18, 0, 0), local_to_utc_iso(23, 59, 59)),
]

# ===============================
# AGGREGATION OBJECTS
# ===============================

visits_by_path_country = defaultdict(int)
total_path_visits = 0

# ===============================
# FETCH & PROCESS (1:1 POSTMAN)
# ===============================

for start_ts, end_ts in TIME_CHUNKS:
    print(f"\nFetching data from {start_ts} → {end_ts}")

    payload = {
        "query": QUERY,
        "variables": {
            "accountTag": ACCOUNT_TAG,
            "start": start_ts,
            "end": end_ts
        }
    }

    response = requests.post(API_URL, headers=HEADERS, json=payload)
    data = response.json()

    rows = (
        data.get("data", {})
            .get("viewer", {})
            .get("accounts", [{}])[0]
            .get("rumPageloadEventsAdaptiveGroups", [])
    )

    for r in rows:
        path = r.get("dimensions", {}).get("requestPath")
        visits = r.get("sum", {}).get("visits", 0)

        if not path or visits == 0:
            continue

        segments = [s for s in path.split("/") if s]
        if not segments:
            continue

        path_country = "/" + segments[0].lower()

        visits_by_path_country[path_country] += visits
        total_path_visits += visits

# ===============================
# RESULTS
# ===============================

print("\n==============================")
print("Visits by path country:")
print("==============================")

for k in sorted(visits_by_path_country):
    print(f"{k}: {visits_by_path_country[k]}")

print("\n==============================")
print("TOTAL path visits:")
print("==============================")
print(total_path_visits)
