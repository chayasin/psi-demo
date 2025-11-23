import streamlit as st
from bob import BobServer
import time
import pandas as pd

st.set_page_config(page_title="Bob (Server)", layout="wide")

st.title("Bob: PSI Server")

# Initialize Session State
if 'server' not in st.session_state:
    st.session_state.server = BobServer()
if 'server_running' not in st.session_state:
    st.session_state.server_running = False

# Sidebar Controls
st.sidebar.header("Server Control")
host = st.sidebar.text_input("Host", "0.0.0.0")
port = st.sidebar.number_input("Port", value=5000)

col1, col2 = st.sidebar.columns(2)

if col1.button("Start Server"):
    if not st.session_state.server_running:
        st.session_state.server.host = host
        st.session_state.server.port = port
        st.session_state.server.start()
        st.session_state.server_running = True
        st.success("Server Started")

if col2.button("Stop Server"):
    if st.session_state.server_running:
        st.session_state.server.stop()
        st.session_state.server_running = False
        st.warning("Server Stopped")

# Main Area
if st.session_state.server.df_bob is not None:
    st.subheader(f"Bob's Data ({len(st.session_state.server.df_bob)} rows)")
    st.dataframe(st.session_state.server.df_bob.head(10))
else:
    st.info("Data will be generated when server starts.")

# Logs
st.subheader("Server Logs")
log_placeholder = st.empty()

# Auto-refresh logs
while st.session_state.server_running:
    logs = st.session_state.server.logs
    log_placeholder.text_area("Logs", value="\n".join(logs[::-1]), height=300)
    time.sleep(1)
    st.rerun()

# If not running, show static logs
logs = st.session_state.server.logs
log_placeholder.text_area("Logs", value="\n".join(logs[::-1]), height=300)
