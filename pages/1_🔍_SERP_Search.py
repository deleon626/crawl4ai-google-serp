"""
SERP Search page for the multi-page Streamlit application.
"""

import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any

# Page Configuration
st.set_page_config(
    page_title="SERP Search",
    page_icon="🔍",
    layout="wide"
)

# Import shared utilities
from utils.streamlit_shared import make_api_request, init_session_state, render_sidebar_config

# Initialize session state
init_session_state()

st.title("🔍 SERP Search")
st.markdown("Search Google with advanced filtering and pagination options.")

# Render sidebar configuration
render_sidebar_config()

# Main search form
with st.form("serp_search_form"):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        query = st.text_input("Search Query", placeholder="Enter your search query...")
        
    with col2:
        search_mode = st.selectbox("Search Mode", ["Single Page", "Batch Pagination"])
    
    col3, col4, col5 = st.columns(3)
    with col3:
        country = st.selectbox("Country", ["US", "ID", "UK", "DE", "FR", "JP", "CA", "AU"])
    with col4:
        language = st.selectbox("Language", ["en", "es", "fr", "de", "ja", "zh"])
    with col5:
        num_results = st.selectbox("Results per Page", [10, 20, 30, 50])
    
    if search_mode == "Batch Pagination":
        col6, col7 = st.columns(2)
        with col6:
            max_pages = st.slider("Max Pages", 1, 10, 3)
        with col7:
            delay_seconds = st.slider("Delay Between Requests (seconds)", 1, 10, 2)
    
    submitted = st.form_submit_button("🔍 Search", type="primary")
    
    if submitted and query:
        with st.spinner("Searching..."):
            if search_mode == "Single Page":
                endpoint = "/api/v1/search"
                data = {
                    "query": query,
                    "country": country,
                    "language": language, 
                    "num_results": num_results
                }
            else:
                endpoint = "/api/v1/search/batch-pagination"
                data = {
                    "query": query,
                    "country": country,
                    "language": language,
                    "num_results": num_results,
                    "max_pages": max_pages,
                    "delay_seconds": delay_seconds
                }
            
            result = make_api_request(endpoint, "POST", data, timeout=60)
            st.session_state.search_results = result
            st.rerun()

# Display Results
if st.session_state.get('search_results'):
    result = st.session_state.search_results
    
    if result["success"]:
        data = result["data"]
        st.success(f"✅ Search completed successfully!")
        
        # Display metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Results", data.get("total_results", "N/A"))
        with col2:
            st.metric("Processing Time", f"{data.get('processing_time_seconds', 0):.2f}s")
        with col3:
            st.metric("Results Returned", len(data.get("results", [])))
        
        # Display results
        if data.get("results"):
            st.subheader("Search Results")
            for i, result in enumerate(data["results"], 1):
                with st.expander(f"{i}. {result.get('title', 'No Title')}"):
                    st.write(f"**URL:** {result.get('link', 'N/A')}")
                    st.write(f"**Snippet:** {result.get('snippet', 'No snippet available')}")
                    if result.get('displayed_link'):
                        st.write(f"**Displayed Link:** {result['displayed_link']}")
    else:
        st.error(f"❌ Search failed: {result['error']}")

# Navigation hint is now handled by render_sidebar_config()