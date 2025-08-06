"""
Instagram Analysis page for the multi-page Streamlit application.
"""

import streamlit as st
import requests
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Instagram Analysis",
    page_icon="📱",
    layout="wide"
)

# Import shared utilities
from utils.streamlit_shared import make_api_request, init_session_state, render_sidebar_config

# Initialize session state
init_session_state()

st.title("📱 Instagram Analysis")
st.markdown("Analyze Instagram profiles for business indicators and extract valuable insights.")

# Render sidebar configuration
render_sidebar_config()

tab1, tab2 = st.tabs(["Profile Analysis", "Search Query Generator"])

with tab1:
    st.subheader("Instagram Profile Analysis")
    
    with st.form("instagram_analysis_form"):
        url = st.text_input("Instagram Profile URL", placeholder="https://instagram.com/username")
        
        col1, col2 = st.columns(2)
        with col1:
            extract_links = st.checkbox("Extract Links", value=True)
        with col2:
            extract_keywords = st.checkbox("Extract Keywords", value=True)
        
        submitted = st.form_submit_button("🔍 Analyze Profile", type="primary")
        
        if submitted and url:
            with st.spinner("Analyzing Instagram profile..."):
                data = {
                    "url": url,
                    "extract_links": extract_links,
                    "extract_keywords": extract_keywords
                }
                
                result = make_api_request("/api/v1/analyze/instagram", "POST", data, timeout=45)
                st.session_state.instagram_results = result
                st.rerun()

with tab2:
    st.subheader("Instagram Search Query Generator")
    
    with st.form("instagram_search_form"):
        col1, col2 = st.columns(2)
        with col1:
            business_type = st.text_input("Business Type", placeholder="restaurant, cafe, fitness")
        with col2:
            location = st.text_input("Location", placeholder="San Francisco, CA")
        
        keywords = st.text_area("Additional Keywords", placeholder="organic, healthy, premium (one per line)").split('\n')
        keywords = [k.strip() for k in keywords if k.strip()]
        
        submitted = st.form_submit_button("Generate Queries")
        
        if submitted and business_type:
            with st.spinner("Generating search queries..."):
                data = {
                    "business_type": business_type,
                    "location": location,
                    "keywords": keywords
                }
                
                result = make_api_request("/api/v1/search/instagram", "POST", data)
                
                if result["success"]:
                    queries = result["data"]["search_queries"]
                    st.success(f"Generated {len(queries)} search queries:")
                    
                    for i, query in enumerate(queries, 1):
                        st.code(f"{i}. {query}")
                else:
                    st.error(f"Failed to generate queries: {result['error']}")

# Display Instagram Analysis Results
if st.session_state.get('instagram_results'):
    result = st.session_state.instagram_results
    
    if result["success"]:
        data = result["data"]
        st.success("✅ Instagram analysis completed!")
        
        # Business Indicators
        if data.get("business_analysis"):
            business = data["business_analysis"]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Business Confidence", f"{business.get('confidence_score', 0):.2f}")
            with col2:
                st.metric("Is Business", "✅" if business.get('is_business') else "❌")
            with col3:
                st.metric("Contact Methods", len(business.get('contact_methods', [])))
            
            if business.get('indicators'):
                st.subheader("Business Indicators")
                indicators_df = pd.DataFrame(business['indicators'])
                st.dataframe(indicators_df)
        
        # Link Analysis
        if data.get("link_analysis"):
            links = data["link_analysis"]
            st.subheader("Link Analysis")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Links", links.get('total_links', 0))
            with col2:
                st.metric("Business Links", links.get('business_relevant_count', 0))
            
            if links.get('categorized_links'):
                for category, category_links in links['categorized_links'].items():
                    if category_links:
                        st.write(f"**{category.title()}:**")
                        for link in category_links:
                            st.write(f"- [{link.get('text', 'Link')}]({link.get('url', '#')})")
        
        # Keywords
        if data.get("keywords"):
            st.subheader("Extracted Keywords")
            keywords_df = pd.DataFrame(data["keywords"])
            st.dataframe(keywords_df)
    else:
        st.error(f"❌ Analysis failed: {result['error']}")

# Navigation hint is now handled by render_sidebar_config()