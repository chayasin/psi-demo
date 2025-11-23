import streamlit as st
from alice import AliceClient
import pandas as pd
import time

st.set_page_config(page_title="Alice (Client)", layout="wide")

st.title("Alice: PSI Client")

# Initialize Session State
if 'client' not in st.session_state:
    st.session_state.client = AliceClient()
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'data_generated' not in st.session_state:
    st.session_state.data_generated = False

# Sidebar
st.sidebar.header("Connection")
host = st.sidebar.text_input("Bob's Host", "127.0.0.1")
port = st.sidebar.number_input("Bob's Port", value=5000)

# 1. Generate Data
st.header("1. Data Generation")
if st.button("Generate Alice's Data"):
    with st.spinner("Generating data..."):
        st.session_state.client.generate_data()
        st.session_state.data_generated = True
    st.success(f"Generated {len(st.session_state.client.df_alice)} rows.")

if st.session_state.data_generated:
    st.dataframe(st.session_state.client.df_alice.head())

# 2. Connect
st.header("2. Connection")
if st.button("Connect to Bob"):
    st.session_state.client.host = host
    st.session_state.client.port = port
    if st.session_state.client.connect():
        st.session_state.connected = True
        st.success("Connected!")
    else:
        st.error("Connection Failed. Make sure Bob is running.")

# 3. Scenarios
if st.session_state.connected:
    st.header("3. Scenarios")
    
    # Scenario 1
    st.subheader("Scenario 1: Basic Intersection")
    if st.button("Run PSI Protocol"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(p):
            progress_bar.progress(p)
            status_text.text(f"Progress: {int(p*100)}%")
            
        intersection = st.session_state.client.run_psi(progress_callback=update_progress)
        if intersection:
            st.success(f"Intersection found: {len(intersection)} items.")
            st.write("Sample Intersection IDs:", intersection[:10])
        else:
            st.error("PSI Failed.")

    # Scenario 2
    st.subheader("Scenario 2: Join Data")
    if st.button("Fetch Joined Data"):
        with st.spinner("Fetching data..."):
            joined = st.session_state.client.run_join()
        if joined is not None:
            st.success("Data Joined!")
            st.dataframe(joined.head(10))
        else:
            st.error("Join Failed. Run PSI first.")

    # Scenario 3
    st.subheader("Scenario 3: Aggregation")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Run Aggregation (Insecure)"):
            agg = st.session_state.client.run_aggregation()
            if agg is not None:
                st.success("Aggregation Complete!")
                st.dataframe(agg)
            else:
                st.error("Aggregation Failed. Run Join first.")

    with col2:
        if st.button("Run Secure Aggregation (HE)"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(p):
                progress_bar.progress(p)
                status_text.text(f"Progress: {int(p*100)}%")
                
            with st.spinner("Running Secure Aggregation..."):
                agg = st.session_state.client.run_secure_aggregation(progress_callback=update_progress)
            
            if agg is not None:
                st.success("Secure Aggregation Complete!")
                st.dataframe(agg)
            else:
                st.error("Secure Aggregation Failed. Run PSI first.")

# Logs
st.header("Logs")
logs = st.session_state.client.logs
st.text_area("Client Logs", value="\n".join(logs[::-1]), height=200)
