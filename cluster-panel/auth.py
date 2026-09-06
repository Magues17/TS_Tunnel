import streamlit as st


def require_login():
    if not st.user.is_logged_in:
        st.title("Cluster Control Panel")
        if st.button("Log in with Google"):
            st.login()
        st.stop()

    allowed = st.secrets.get("allowed_emails", [])
    if st.user.email not in allowed:
        st.error("Your account is not authorized to view this panel.")
        st.stop()

    with st.sidebar:
        st.write("Logged in as")
        st.write(st.user.email)
        if st.button("Log out"):
            st.logout()
