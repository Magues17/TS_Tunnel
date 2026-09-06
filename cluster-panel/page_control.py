import streamlit as st

from auth import require_login
from cluster_data import get_resource_stats_all, get_tailscale_status
from fleet import FLEET, PRESETS
from ssh_exec import run

st.set_page_config(page_title="Cluster Control", layout="wide")
require_login()

OWNER_EMAIL = "mikel.d.campbell@gmail.com"
if st.user.email != OWNER_EMAIL:
    st.error("This page is restricted.")
    st.stop()

st.title("Cluster Control")

st.link_button("Connect to Mikel via SSH", "clusterssh://mikel-linux/")
st.caption("Opens a real PowerShell window on your own machine, already connected to Mikel.")

st.divider()

if st.button("Refresh"):
    st.cache_data.clear()


@st.cache_data(ttl=15)
def load_stats():
    return {"tailscale": get_tailscale_status(), "stats": get_resource_stats_all()}


with st.spinner("Querying fleet..."):
    data = load_stats()

ts = data["tailscale"]
stats = data["stats"]

cols = st.columns(3)
for i, (name, machine) in enumerate(FLEET.items()):
    info = ts.get(name) or next((v for k, v in ts.items() if name in k), None)
    online = info["online"] if info else None
    machine_stats = stats.get(name)

    with cols[i % 3]:
        with st.container(border=True):
            status_dot = "🟢" if online else ("🔴" if online is False else "⚪")
            st.markdown(f"### {status_dot} {name}")
            st.caption(machine["os"])

            if machine_stats:
                if "raw" in machine_stats:
                    st.code(machine_stats["raw"], language="text")
                else:
                    if "cpu" in machine_stats:
                        st.write(f"CPU: {machine_stats['cpu']}")
                    if "ram" in machine_stats:
                        st.write(f"RAM: {machine_stats['ram']}")
                    if "disk" in machine_stats:
                        st.write(f"Disk: {machine_stats['disk']}")
            else:
                st.caption("no data")

            with st.expander("Run a command"):
                presets = PRESETS[machine["os"]]
                for label, cmd in presets.items():
                    if st.button(label, key=f"preset-{name}-{label}"):
                        st.session_state[f"cmd-{name}"] = cmd

                custom_cmd = st.text_area(
                    "Command",
                    value=st.session_state.get(f"cmd-{name}", ""),
                    height=80,
                    key=f"text-{name}",
                )
                if st.button("Run", key=f"run-{name}", type="primary"):
                    with st.spinner(f"Running on {name}..."):
                        result = run(machine["host"], machine["user"], custom_cmd)
                    if result["ok"]:
                        st.success(f"Exit code {result['exit_code']}")
                    else:
                        st.error(f"Exit code {result['exit_code']}")
                    if result["stdout"]:
                        st.code(result["stdout"], language="text")
                    if result["stderr"]:
                        st.code(result["stderr"], language="text")

