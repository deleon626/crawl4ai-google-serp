"""
Main page for the SERP Parser & Business Intelligence multi-page Streamlit application.
"""

import streamlit as st
import requests

# Page Configuration
st.set_page_config(
    page_title="SERP Parser & Business Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import shared utilities
from utils.streamlit_shared import make_api_request, init_session_state, render_sidebar_config

# Initialize session state
init_session_state()

# Header
st.title("🔍 SERP Parser & Web Crawler")
st.markdown("**Comprehensive web research platform with Google SERP search and intelligent content analysis.**")

# Render sidebar configuration
render_sidebar_config()

# Quick Stats Dashboard
st.subheader("📊 Platform Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    search_count = len(st.session_state.get('search_history', []))
    st.metric("SERP Searches", search_count, help="Google SERP searches performed")

with col2:
    crawl_count = 1 if st.session_state.get('crawl_results') else 0
    st.metric("Pages Crawled", crawl_count, help="Web pages crawled and analyzed")

with col3:
    total_operations = search_count + crawl_count
    st.metric("Total Operations", total_operations, help="All searches and crawls performed")

with col4:
    connection_status = st.session_state.get('connection_status', {})
    is_active = connection_status.get('success', False) if connection_status else False
    st.metric("API Status", "🟢 Active" if is_active else "🔴 Unknown", help="Backend API connection status")

# Platform Capabilities
st.subheader("🚀 Platform Capabilities")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 🔍 **Google SERP Search**
    - Multi-page batch search capabilities
    - Real-time search result parsing
    - Advanced pagination support
    - Rich metadata extraction
    - Organic result filtering
    - Continuation token management
    """)

with col2:
    st.markdown("""
    ### 🕷️ **Web Content Crawling**
    - Intelligent content extraction
    - JavaScript rendering support
    - Structured data parsing
    - Content cleaning and formatting
    
    ### 📊 **Analytics & Insights**
    - Search performance dashboard
    - Crawling success metrics
    - Processing time optimization
    - Export capabilities for analysis
    """)

# Getting Started Guide
st.subheader("📖 Getting Started")

with st.expander("🔧 **Step 1: Setup & Configuration**"):
    st.markdown("""
    1. **API Connection**: Ensure your backend API is running at `http://localhost:8000`
    2. **Test Connection**: Use the "Test Connection" button in the sidebar
    3. **Environment Setup**: Make sure you have your `.env` file configured with `BRIGHT_DATA_TOKEN`
    4. **Dependencies**: All dependencies should be installed via `uv pip install -r requirements.txt`
    """)

with st.expander("🔍 **Step 2: SERP Search**"):
    st.markdown("""
    1. Go to **🔍 SERP Search** page
    2. **Single Search**: Enter search query for immediate results
    3. **Batch Search**: Configure multi-page searches with pagination
    4. Review organic results with titles, URLs, and snippets
    5. Export search results for further analysis
    """)

with st.expander("🕷️ **Step 3: Web Crawling**"):
    st.markdown("""
    1. Access **🕷️ Crawling** page
    2. Provide target URL for content extraction
    3. Configure crawling options:
       - **JavaScript Rendering**: For dynamic content
       - **Content Filtering**: Focus on specific content types
       - **Timeout Settings**: Balance speed vs. completeness
    4. Review extracted content and metadata
    """)

with st.expander("📊 **Step 4: Analytics Dashboard**"):
    st.markdown("""
    1. Visit **📊 Analytics Dashboard** for overview
    2. Monitor search and crawl performance
    3. Review API health status and available endpoints
    4. Track processing times and success rates
    5. Access operation history and metrics
    """)

# API Health Check
st.subheader("🔧 System Status")

# Test API connection automatically on page load
if not st.session_state.get('connection_status'):
    with st.spinner("Checking API connection..."):
        result = make_api_request("/api/v1/health")
        st.session_state.connection_status = result

if st.session_state.connection_status:
    if st.session_state.connection_status["success"]:
        health_data = st.session_state.connection_status["data"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("✅ **API Status**: Healthy")
        with col2:
            st.info(f"🔗 **Base URL**: {st.session_state.api_url}")
        with col3:
            st.info(f"📅 **Version**: {health_data.get('version', 'N/A')}")
            
    else:
        st.error(f"❌ **API Connection Failed**: {st.session_state.connection_status['error']}")
        st.markdown("""
        **Troubleshooting Steps:**
        1. Ensure your FastAPI backend is running: `uv run python main.py`
        2. Check if port 8000 is available
        3. Verify your `.env` file has the required API tokens
        4. Try refreshing the page or updating the API URL in the sidebar
        """)

# Navigation Instructions
st.markdown("---")
st.markdown("### 🧭 **Navigation**")
st.info("👈 **Use the sidebar menu** to navigate between different analysis modules. Each page offers specialized functionality for different types of business intelligence gathering.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
<p><strong>SERP Parser & Web Crawler Platform</strong></p>
<p>Powered by FastAPI + Streamlit | Crawl4ai + Bright Data | Phase 1 Core</p>
</div>
""", unsafe_allow_html=True)