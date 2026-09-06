import json
import re

import streamlit as st

from auth import require_login
from cluster_data import get_disk_usage_all, get_pihole_stats, get_pool_status, get_tailscale_status, get_thinq_status
from fleet import FLEET

st.set_page_config(page_title="Cluster Dashboard", layout="wide")
require_login()

st.title("Cluster Dashboard")

if st.button("Refresh"):
    st.cache_data.clear()


@st.cache_data(ttl=15)
def load_all():
    return {
        "tailscale": get_tailscale_status(),
        "disk": get_disk_usage_all(),
        "pool": get_pool_status(),
        "pihole": get_pihole_stats(),
        "appliances": get_thinq_status(),
    }


with st.spinner("Querying fleet..."):
    data = load_all()

# --- Storage pool summary ---
st.subheader("Storage Pool")
pool = data["pool"]
if pool:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", pool["size"])
    c2.metric("Used", pool["used"])
    c3.metric("Free", pool["avail"])
    c4.metric("Usage", pool["pct"])
else:
    st.warning("Could not reach the storage pool.")

st.divider()

# --- Fleet status ---
st.subheader("Fleet Status")
ts = data["tailscale"]
disk = data["disk"]

cols = st.columns(3)
for i, (name, machine) in enumerate(FLEET.items()):
    ts_name = name if name != "turion" else "turion"
    info = ts.get(ts_name) or next((v for k, v in ts.items() if name in k), None)
    online = info["online"] if info else None

    with cols[i % 3]:
        with st.container(border=True):
            status_dot = "🟢" if online else ("🔴" if online is False else "⚪")
            st.markdown(f"### {status_dot} {name}")
            st.caption(machine["os"])

            raw = disk.get(name)
            if raw:
                if machine["os"] == "windows":
                    try:
                        j = json.loads(raw)
                        st.write(f"Disk: {j['FreeGB']} GB free / {j['SizeGB']} GB")
                    except Exception:
                        st.write(raw)
                else:
                    m = re.match(r"(\d+)G\s+(\d+)G", raw) or re.match(r"(\d+)\s+(\d+)", raw)
                    if m:
                        st.write(f"Disk: {m.group(1)}GB free / {m.group(2)}GB total")
                    else:
                        st.write(raw)
            else:
                st.caption("no data")

st.divider()

# --- Home appliances (LG ThinQ) ---
st.subheader("Home Appliances")
appliances = data["appliances"]
if appliances:
    cols = st.columns(len(appliances))
    for i, dev in enumerate(appliances):
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"### {dev['alias']}")
                st.write(f"Status: **{dev['state']}**")
    st.caption("Full controls under Home tab.")
else:
    st.warning("Could not reach LG ThinQ.")

st.divider()

# --- Pi-hole ---
st.subheader("Pi-hole")
pihole_raw = data["pihole"]
if pihole_raw:
    try:
        stats = json.loads(pihole_raw)
        c1, c2, c3 = st.columns(3)
        c1.metric("Queries today", stats.get("dns_queries_today", "?"))
        c2.metric("Blocked today", stats.get("ads_blocked_today", "?"))
        c3.metric("Percent blocked", f"{stats.get('ads_percentage_today', '?')}%")
    except Exception:
        st.code(pihole_raw)
else:
    st.warning("Could not reach Pi-hole.")
