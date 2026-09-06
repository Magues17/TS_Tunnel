import streamlit as st

OWNER_EMAIL = "mikel.d.campbell@gmail.com"

pages = [
    st.Page("page_dashboard.py", title="Dashboard", icon=":material/dashboard:", url_path="dashboard", default=True),
    st.Page("page_home.py", title="Home", icon=":material/home:", url_path="home"),
]

if st.user.is_logged_in and st.user.email == OWNER_EMAIL:
    pages.append(st.Page("page_control.py", title="Control", icon=":material/terminal:", url_path="control"))

pg = st.navigation(pages)
pg.run()
