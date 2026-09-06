import streamlit as st

from auth import require_login

st.set_page_config(page_title="Home", layout="wide")
require_login()

st.components.v1.iframe("https://mikel-z390-aorus-master.tailf8336a.ts.net:8123", height=900, scrolling=True)
