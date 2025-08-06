"""
Company Analysis page for the multi-page Streamlit application.
"""

import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Company Analysis",
    page_icon="🏢",
    layout="wide"
)

# Import shared utilities
from utils.streamlit_shared import make_api_request, init_session_state, render_sidebar_config

# Initialize session state
init_session_state()

st.title("🏢 Company Analysis")
st.markdown("Comprehensive company analysis including website discovery and employee extraction.")

# Render sidebar configuration
render_sidebar_config()

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
if st.session_state.get('company_results'):
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

# Navigation hint is now handled by render_sidebar_config()