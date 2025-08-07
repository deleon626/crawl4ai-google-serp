"""
Analytics Dashboard page for the multi-page Streamlit application.
"""

import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Import shared utilities
from utils.streamlit_shared import make_api_request, init_session_state, render_sidebar_config

# Initialize session state
init_session_state()

st.title("📊 Analytics Dashboard")
st.markdown("Overview of recent analyses and insights.")

# Render sidebar configuration
render_sidebar_config()

# Summary Cards
col1, col2, col3 = st.columns(3)

with col1:
    instagram_count = 1 if st.session_state.get('instagram_results') else 0
    st.metric("Instagram Analyses", instagram_count)

with col2:
    company_count = 1 if st.session_state.get('company_results') else 0
    st.metric("Company Analyses", company_count)

with col3:
    total_analyses = instagram_count + company_count
    st.metric("Total Analyses", total_analyses)

# Recent Results Summary
if total_analyses > 0:
    st.subheader("Recent Analysis Summary")
    
    # Create summary data
    summary_data = []
    
    if st.session_state.get('instagram_results') and st.session_state.instagram_results["success"]:
        data = st.session_state.instagram_results["data"]
        business_confidence = data.get('business_analysis', {}).get('confidence_score', 0)
        summary_data.append({
            'Type': 'Instagram Analysis',
            'Status': '✅ Success', 
            'Results': f"Confidence: {business_confidence:.2f}",
            'Processing Time': f"{data.get('processing_time_seconds', 0):.2f}s"
        })
    
    if st.session_state.get('company_results') and st.session_state.company_results["success"]:
        data = st.session_state.company_results["data"]
        employees_found = len(data.get('company', {}).get('employees', []))
        summary_data.append({
            'Type': 'Company Analysis',
            'Status': '✅ Success',
            'Results': f"Employees: {employees_found}",
            'Processing Time': f"{data.get('processing_time_seconds', 0):.2f}s"
        })
    
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
else:
    st.info("No analyses performed yet. Use the other pages to run some analyses!")

# API Health Status
st.subheader("API Health Status")
test_result = make_api_request("/api/v1/health")

if test_result["success"]:
    health_data = test_result["data"]
    st.success("✅ API is healthy")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Status:** {health_data.get('status', 'unknown')}")
        st.write(f"**Timestamp:** {health_data.get('timestamp', 'N/A')}")
    with col2:
        st.write(f"**Version:** {health_data.get('version', 'N/A')}")
        st.write(f"**Environment:** {health_data.get('environment', 'N/A')}")
else:
    st.error(f"❌ API health check failed: {test_result['error']}")

# Available Endpoints
st.subheader("Available API Endpoints")

endpoint_data = [
    {"Endpoint": "GET /api/v1/health", "Description": "Application health check"},
    {"Endpoint": "POST /api/v1/search", "Description": "Basic Google SERP search"},
    {"Endpoint": "POST /api/v1/search/batch", "Description": "Batch pagination search"},
    {"Endpoint": "POST /api/v1/crawl", "Description": "Web crawling with Crawl4ai"},
    {"Endpoint": "POST /api/v1/analyze/instagram", "Description": "Instagram profile analysis"},
    {"Endpoint": "POST /api/v1/search/instagram", "Description": "Instagram search queries"},
    {"Endpoint": "POST /api/v1/company/analyze", "Description": "Company analysis & employee discovery"},
    {"Endpoint": "POST /api/v1/company/search-queries", "Description": "Company search queries"},
]

endpoints_df = pd.DataFrame(endpoint_data)
st.dataframe(endpoints_df, use_container_width=True, hide_index=True)

# Navigation hint is now handled by render_sidebar_config()

# Instructions
with st.expander("📖 How to Use This Dashboard"):
    st.markdown("""
    **Multi-Page Navigation:**
    1. Use the **sidebar menu** to navigate between pages
    2. Each page has its own functionality:
       - **📱 Instagram Analysis**: Business profile analysis
       - **🏢 Company Analysis**: Company research & employee discovery
       - **📊 Analytics Dashboard**: Overview and insights
    
    **Getting Started:**
    1. Configure the API URL in the sidebar (default: http://localhost:8000)
    2. Test the connection to ensure the backend is running
    3. Use any of the analysis pages to start gathering data
    4. Return to this dashboard to see summaries and insights
    
    **Pro Tips:**
    - Results are shared across all pages
    - The API connection status is shown in the sidebar
    - Processing times and success rates are tracked automatically
    """)