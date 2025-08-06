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
        # Fix data structure access - API returns 'result' not 'data'
        analysis_result = result.get("data", {}).get("result", {}) if "data" in result else result.get("result", {})
        st.success("✅ Instagram analysis completed!")
        
        # Business Indicators
        if analysis_result.get("business_analysis"):
            business = analysis_result["business_analysis"]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Business Confidence", f"{business.get('confidence', 0):.2f}")
            with col2:
                st.metric("Is Business", "✅" if business.get('is_business') else "❌")
            with col3:
                # Count contact info items from extracted_data
                contact_count = 0
                if business.get('extracted_data'):
                    extracted = business['extracted_data']
                    contact_count = (len(extracted.get('emails', [])) + 
                                   len(extracted.get('phones', [])) + 
                                   len(extracted.get('websites', [])))
                st.metric("Contact Methods", contact_count)
            
            # Business Indicators
            if business.get('indicators'):
                st.subheader("Business Indicators")
                indicators = business['indicators']
                
                # Display indicators in structured format
                if indicators.get('contact_info'):
                    st.write("**Contact Information Found:**")
                    for item in indicators['contact_info']:
                        st.write(f"- {item}")
                
                if indicators.get('business_signals'):
                    st.write("**Business Signals:**")
                    for signal in indicators['business_signals']:
                        st.write(f"- {signal}")
                
                if indicators.get('professional_markers'):
                    st.write("**Professional Markers:**")
                    for marker in indicators['professional_markers']:
                        st.write(f"- {marker}")
                
                if indicators.get('location_info'):
                    st.write("**Location Information:**")
                    for location in indicators['location_info']:
                        st.write(f"- {location}")
            
            # Extracted Contact Data
            if business.get('extracted_data'):
                extracted = business['extracted_data']
                st.subheader("Extracted Contact Information")
                
                contact_col1, contact_col2 = st.columns(2)
                with contact_col1:
                    if extracted.get('emails'):
                        st.write("**Email Addresses:**")
                        for email in extracted['emails']:
                            st.write(f"- {email}")
                    
                    if extracted.get('phones'):
                        st.write("**Phone Numbers:**")
                        for phone in extracted['phones']:
                            st.write(f"- {phone}")
                
                with contact_col2:
                    if extracted.get('websites'):
                        st.write("**Websites:**")
                        for website in extracted['websites']:
                            st.write(f"- [{website}]({website})")
                    
                    if extracted.get('social_handles'):
                        st.write("**Social Media Handles:**")
                        for handle in extracted['social_handles']:
                            st.write(f"- {handle}")
        
        # Link Analysis
        if analysis_result.get("link_analysis"):
            links = analysis_result["link_analysis"]
            st.subheader("Link Analysis")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Links", links.get('total_links', 0))
            with col2:
                st.metric("Business Links", len(links.get('business_links', [])))
            with col3:
                st.metric("Website Links", len(links.get('website_links', [])))
            
            # Display different types of links
            link_types = [
                ('business_links', 'Business Links'),
                ('website_links', 'Website Links'),
                ('social_links', 'Social Media Links'),
                ('contact_links', 'Contact Links')
            ]
            
            for link_key, link_title in link_types:
                if links.get(link_key):
                    st.write(f"**{link_title}:**")
                    for link in links[link_key]:
                        confidence_text = f" (Confidence: {link.get('confidence', 0):.2f})" if link.get('confidence') else ""
                        st.write(f"- [{link.get('original_text', 'Link')}]({link.get('url', '#')}){confidence_text}")
        
        # Keywords
        if analysis_result.get("keyword_analysis"):
            keyword_analysis = analysis_result["keyword_analysis"]
            st.subheader("Keyword Analysis")
            
            # Display top business keywords
            if keyword_analysis.get("top_business_keywords"):
                st.write("**Top Business Keywords:**")
                for keyword_info in keyword_analysis["top_business_keywords"]:
                    relevance = keyword_info.get('relevance_score', 0)
                    frequency = keyword_info.get('frequency', 0)
                    st.write(f"- **{keyword_info.get('keyword', 'N/A')}** (Relevance: {relevance:.2f}, Frequency: {frequency})")
            
            # Display all keywords in a table
            if keyword_analysis.get("keywords"):
                st.write("**All Keywords:**")
                keywords_data = []
                for keyword_info in keyword_analysis["keywords"]:
                    keywords_data.append({
                        'Keyword': keyword_info.get('keyword', 'N/A'),
                        'Category': keyword_info.get('category', 'N/A'),
                        'Frequency': keyword_info.get('frequency', 0),
                        'Relevance': f"{keyword_info.get('relevance_score', 0):.2f}"
                    })
                
                if keywords_data:
                    keywords_df = pd.DataFrame(keywords_data)
                    st.dataframe(keywords_df, use_container_width=True)
    else:
        st.error(f"❌ Analysis failed: {result['error']}")

# Navigation hint is now handled by render_sidebar_config()