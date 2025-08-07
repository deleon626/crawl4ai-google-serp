"""
Multi-page Streamlit application for Google SERP Parser with Company Analysis.
Features: SERP Search, Instagram Analysis, Company Analysis, and Employee Discovery.
"""

import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List
import traceback
from urllib.parse import urlparse

# Page Configuration
st.set_page_config(
    page_title="SERP Parser & Business Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
API_BASE_URL = "http://localhost:8000"

# Initialize session state
def init_session_state():
    """Initialize session state variables."""
    defaults = {
        'api_url': API_BASE_URL,
        'connection_status': None,
        'current_page': 'Instagram Analysis',
        'search_results': None,
        'instagram_results': None,
        'company_results': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# API Helper Functions
def make_api_request(endpoint: str, method: str = "GET", data: Dict = None, timeout: int = 30) -> Dict[str, Any]:
    """Make API request with error handling."""
    url = f"{st.session_state.api_url}{endpoint}"
    
    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        else:
            response = requests.get(url, timeout=timeout)
            
        response.raise_for_status()
        return {"success": True, "data": response.json()}
        
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Could not connect to API"}
    except requests.exceptions.HTTPError as e:
        try:
            error_detail = response.json()
            return {"success": False, "error": f"HTTP {response.status_code}: {error_detail.get('message', str(e))}"}
        except:
            return {"success": False, "error": f"HTTP {response.status_code}: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}

# Page Navigation
def render_sidebar():
    """Render sidebar navigation."""
    st.sidebar.title("🔍 SERP Parser & BI")
    
    # API Configuration
    st.sidebar.header("⚙️ Configuration")
    new_api_url = st.sidebar.text_input("API Base URL", value=st.session_state.api_url)
    
    if new_api_url != st.session_state.api_url:
        st.session_state.api_url = new_api_url
        st.session_state.connection_status = None
        st.rerun()
    
    # Connection Test
    if st.sidebar.button("Test Connection"):
        result = make_api_request("/api/v1/health")
        st.session_state.connection_status = result
        st.rerun()
    
    # Display connection status
    if st.session_state.connection_status:
        if st.session_state.connection_status["success"]:
            st.sidebar.success("✅ API Connected")
        else:
            st.sidebar.error(f"❌ API Error: {st.session_state.connection_status['error']}")
    
    st.sidebar.markdown("---")
    
    # Page Navigation
    st.sidebar.header("📄 Pages")
    pages = [
        "📱 Instagram Analysis", 
        "🏢 Company Analysis",
        "📊 Analytics Dashboard"
    ]
    
    selected_page = st.sidebar.radio("Select Page", pages, key="page_selector")
    st.session_state.current_page = selected_page.split(" ", 1)[1]  # Remove emoji
    
    return selected_page

# Page Components

def render_instagram_analysis_page():
    """Render Instagram analysis functionality page.""" 
    st.title("📱 Instagram Analysis")
    st.markdown("Analyze Instagram profiles for business indicators and extract valuable insights.")
    
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
    if st.session_state.instagram_results:
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

def render_company_analysis_page():
    """Render company analysis functionality page."""
    st.title("🏢 Company Analysis")
    st.markdown("Comprehensive company analysis including website discovery and employee extraction.")
    
    tab1, tab2 = st.tabs(["Company Analysis", "Search Queries"])
    
    with tab1:
        st.subheader("Company Analysis")
        
        with st.form("company_analysis_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                company_name = st.text_input("Company Name", placeholder="Acme Corporation")
                company_url = st.text_input("Company Website (optional)", placeholder="https://company.com")
                
            with col2:
                linkedin_url = st.text_input("LinkedIn URL (optional)", placeholder="https://linkedin.com/company/acme")
                additional_context = st.text_input("Additional Context", placeholder="technology, software, AI")
            
            col3, col4, col5 = st.columns(3)
            with col3:
                deep_analysis = st.checkbox("Deep Website Analysis", value=True)
            with col4:
                extract_employees = st.checkbox("Extract Employees", value=True)
            with col5:
                max_employees = st.slider("Max Employees", 5, 100, 20)
            
            submitted = st.form_submit_button("🔍 Analyze Company", type="primary")
            
            if submitted and (company_name or company_url or linkedin_url):
                with st.spinner("Analyzing company... This may take a while."):
                    data = {
                        "company_name": company_name if company_name else None,
                        "company_url": company_url if company_url else None,
                        "linkedin_url": linkedin_url if linkedin_url else None,
                        "additional_context": additional_context if additional_context else None,
                        "deep_analysis": deep_analysis,
                        "extract_employees": extract_employees,
                        "max_employees": max_employees
                    }
                    
                    result = make_api_request("/api/v1/company/analyze", "POST", data, timeout=120)
                    st.session_state.company_results = result
                    st.rerun()
    
    with tab2:
        st.subheader("Company Search Query Generator")
        
        with st.form("company_search_form"):
            col1, col2 = st.columns(2)
            with col1:
                search_company = st.text_input("Company Name", placeholder="Tesla Inc")
                search_industry = st.text_input("Industry (optional)", placeholder="automotive, technology")
            with col2:
                search_location = st.text_input("Location (optional)", placeholder="Palo Alto, CA")
                search_type = st.selectbox("Search Type", ["comprehensive", "website", "employees", "contact"])
            
            search_keywords = st.text_area("Additional Keywords", placeholder="founder, CEO, headquarters").split('\n')
            search_keywords = [k.strip() for k in search_keywords if k.strip()]
            
            submitted = st.form_submit_button("Generate Search Queries")
            
            if submitted and search_company:
                data = {
                    "company_name": search_company,
                    "industry": search_industry if search_industry else None,
                    "location": search_location if search_location else None,
                    "search_type": search_type,
                    "additional_keywords": search_keywords
                }
                
                result = make_api_request("/api/v1/company/search-queries", "POST", data)
                
                if result["success"]:
                    data = result["data"]
                    st.success(f"Generated {len(data['search_queries'])} search queries:")
                    
                    for query in data["search_queries"]:
                        explanation = data["query_explanations"].get(query, "General search")
                        st.code(query)
                        st.caption(explanation)
                else:
                    st.error(f"Failed to generate queries: {result['error']}")
    
    # Display Company Analysis Results
    if st.session_state.company_results:
        result = st.session_state.company_results
        
        if result["success"]:
            data = result["data"]
            st.success("✅ Company analysis completed!")
            
            # Company Information
            if data.get("company"):
                company = data["company"]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Confidence Score", f"{company.get('confidence_score', 0):.2f}")
                with col2:
                    st.metric("Employees Found", len(company.get('employees', [])))
                with col3:
                    st.metric("Social Profiles", len(company.get('social_profiles', {})))
                
                # Company Details
                st.subheader("Company Information")
                info_col1, info_col2 = st.columns(2)
                
                with info_col1:
                    st.write(f"**Name:** {company.get('name', 'N/A')}")
                    st.write(f"**Domain:** {company.get('domain', 'N/A')}")
                    st.write(f"**Industry:** {company.get('industry', 'N/A')}")
                    
                with info_col2:
                    st.write(f"**Size Category:** {company.get('size_category', 'N/A')}")
                    st.write(f"**Founded:** {company.get('founded_year', 'N/A')}")
                    st.write(f"**Headquarters:** {company.get('headquarters', 'N/A')}")
                
                if company.get('description'):
                    st.write(f"**Description:** {company['description']}")
                
                # Website Analysis
                if company.get('website'):
                    website = company['website']
                    st.subheader("Website Analysis")
                    
                    st.write(f"**URL:** [{website.get('url', 'N/A')}]({website.get('url', '#')})")
                    if website.get('title'):
                        st.write(f"**Title:** {website['title']}")
                    if website.get('technologies'):
                        st.write(f"**Technologies:** {', '.join(website['technologies'])}")
                    if website.get('keywords'):
                        st.write(f"**Keywords:** {', '.join(website['keywords'])}")
                
                # Employee Information
                if company.get('employees'):
                    st.subheader("Discovered Employees")
                    
                    employees_data = []
                    for employee in company['employees']:
                        employees_data.append({
                            'Name': employee.get('name', 'N/A'),
                            'Title': employee.get('title', 'N/A'),
                            'Role Category': employee.get('role_category', 'N/A'),
                            'Department': employee.get('department', 'N/A'),
                            'Confidence': f"{employee.get('confidence_score', 0):.2f}",
                            'Source': employee.get('source_url', 'N/A')
                        })
                    
                    employees_df = pd.DataFrame(employees_data)
                    st.dataframe(employees_df, use_container_width=True)
                
                # Social Profiles
                if company.get('social_profiles'):
                    st.subheader("Social Profiles")
                    for platform, url in company['social_profiles'].items():
                        st.write(f"**{platform.title()}:** [{url}]({url})")
            
            # Statistics
            if data.get("employee_stats"):
                stats = data["employee_stats"]
                st.subheader("Discovery Statistics")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Pages Crawled", stats.get('total_pages_crawled', 0))
                with col2:
                    st.metric("Employees Found", stats.get('employees_found', 0))
                with col3:
                    st.metric("High Confidence", stats.get('high_confidence_employees', 0))
                with col4:
                    st.metric("Processing Time", f"{stats.get('extraction_time_seconds', 0):.1f}s")
                
                if stats.get('roles_distribution'):
                    st.write("**Role Distribution:**")
                    roles_df = pd.DataFrame(list(stats['roles_distribution'].items()), columns=['Role', 'Count'])
                    st.bar_chart(roles_df.set_index('Role'))
        else:
            st.error(f"❌ Company analysis failed: {result['error']}")

def render_analytics_dashboard():
    """Render analytics dashboard page."""
    st.title("📊 Analytics Dashboard")
    st.markdown("Overview of recent analyses and insights.")
    
    # Summary Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        instagram_count = 1 if st.session_state.instagram_results else 0
        st.metric("Instagram Analyses", instagram_count)
    
    with col2:
        company_count = 1 if st.session_state.company_results else 0
        st.metric("Company Analyses", company_count)
    
    with col3:
        total_analyses = instagram_count + company_count
        st.metric("Total Analyses", total_analyses)
    
    # Recent Results Summary
    if total_analyses > 0:
        st.subheader("Recent Analysis Summary")
        
        # Create summary data
        summary_data = []
        
        if st.session_state.instagram_results and st.session_state.instagram_results["success"]:
            result = st.session_state.instagram_results
            # Fix data structure access - API returns 'result' not 'data'
            analysis_result = result.get("data", {}).get("result", {}) if "data" in result else result.get("result", {})
            business_confidence = analysis_result.get('business_analysis', {}).get('confidence', 0)
            processing_time = result.get('execution_time', 0)
            summary_data.append({
                'Type': 'Instagram Analysis',
                'Status': '✅ Success', 
                'Results': f"Confidence: {business_confidence:.2f}",
                'Processing Time': f"{processing_time:.2f}s"
            })
        
        if st.session_state.company_results and st.session_state.company_results["success"]:
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

# Main Application
def main():
    """Main application logic."""
    init_session_state()
    
    # Render sidebar navigation
    selected_page = render_sidebar()
    
    # Render selected page
    if "Instagram Analysis" in selected_page:
        render_instagram_analysis_page()
    elif "Company Analysis" in selected_page:
        render_company_analysis_page()
    elif "Analytics Dashboard" in selected_page:
        render_analytics_dashboard()

if __name__ == "__main__":
    main()