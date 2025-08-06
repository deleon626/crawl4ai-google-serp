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
st.title("🔍 SERP Parser & Business Intelligence")
st.markdown("**Comprehensive business research platform with Google SERP, Instagram analysis, and company intelligence.**")

# Render sidebar configuration
render_sidebar_config()

# Quick Stats Dashboard
st.subheader("📊 Platform Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    search_count = 1 if st.session_state.get('search_results') else 0
    st.metric("SERP Searches", search_count, help="Google search analyses completed")

with col2:
    instagram_count = 1 if st.session_state.get('instagram_results') else 0  
    st.metric("Instagram Analyses", instagram_count, help="Instagram business profiles analyzed")

with col3:
    company_count = 1 if st.session_state.get('company_results') else 0
    st.metric("Company Research", company_count, help="Company analyses with employee discovery")

with col4:
    total_analyses = search_count + instagram_count + company_count
    st.metric("Total Analyses", total_analyses, help="All analyses across platforms")

# Platform Capabilities
st.subheader("🚀 Platform Capabilities")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 🔍 **SERP Search Engine**
    - Advanced Google search with country/language targeting
    - Batch pagination for comprehensive results
    - Real-time search result processing
    - Bright Data API integration for reliable access
    
    ### 📱 **Instagram Business Intelligence**
    - Automated business profile detection
    - Contact information extraction
    - Link analysis and validation
    - Keyword extraction with confidence scoring
    """)

with col2:
    st.markdown("""
    ### 🏢 **Company Analysis & Discovery**
    - Intelligent company website discovery
    - Employee extraction with role categorization
    - Technology stack identification
    - Social media profile mapping
    
    ### 📊 **Analytics & Insights**
    - Cross-platform analysis dashboard
    - Performance metrics and processing times
    - Confidence scoring for all extracted data
    - Export capabilities for further analysis
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
    1. Navigate to **🔍 SERP Search** in the sidebar
    2. Enter your search query and configure options:
       - **Country**: Target specific geographic regions
       - **Language**: Set language preferences
       - **Results**: Control number of results per page
    3. Choose between single page or batch pagination
    4. Review results and metrics
    """)

with st.expander("📱 **Step 3: Instagram Analysis**"):
    st.markdown("""
    1. Go to **📱 Instagram Analysis** page
    2. **Profile Analysis**: Enter Instagram profile URL for business intelligence
    3. **Search Queries**: Generate targeted Instagram business search queries
    4. Review confidence scores and extracted business indicators
    5. Export contact information and business insights
    """)

with st.expander("🏢 **Step 4: Company Research**"):
    st.markdown("""
    1. Access **🏢 Company Analysis** page
    2. Provide company information:
       - **Company Name**: For automatic website discovery
       - **Website URL**: For direct analysis
       - **LinkedIn URL**: For enhanced company context
    3. Configure analysis options:
       - **Deep Analysis**: Comprehensive website crawling
       - **Employee Extraction**: Discover key personnel
       - **Max Employees**: Limit results for faster processing
    4. Review comprehensive company intelligence report
    """)

with st.expander("📊 **Step 5: Analytics Dashboard**"):
    st.markdown("""
    1. Visit **📊 Analytics Dashboard** for overview
    2. Monitor analysis performance and success rates
    3. Review API health status and available endpoints
    4. Track processing times and result quality metrics
    5. Access historical analysis summaries
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
<p><strong>SERP Parser & Business Intelligence Platform</strong></p>
<p>Powered by FastAPI + Streamlit | Crawl4ai + Bright Data | Phase 2.5 Complete</p>
</div>
""", unsafe_allow_html=True)