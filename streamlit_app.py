"""
Minimalistic Streamlit Frontend for Google SERP API Testing
"""

import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import traceback

# Configuration
API_BASE_URL = "http://localhost:8000"
COMMON_COUNTRIES = {
    "US": "United States",
    "UK": "United Kingdom", 
    "DE": "Germany",
    "FR": "France",
    "JP": "Japan",
    "CA": "Canada",
    "AU": "Australia",
    "IN": "India"
}
COMMON_LANGUAGES = {
    "en": "English",
    "es": "Spanish", 
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "zh": "Chinese",
    "pt": "Portuguese",
    "ru": "Russian"
}

# Initialize session state
def init_session_state():
    """Initialize session state variables."""
    if 'api_url' not in st.session_state:
        st.session_state.api_url = API_BASE_URL
    if 'connection_status' not in st.session_state:
        st.session_state.connection_status = None
    if 'last_search_results' not in st.session_state:
        st.session_state.last_search_results = None
    if 'last_batch_results' not in st.session_state:
        st.session_state.last_batch_results = None

# API Client Functions
def test_api_connection(api_url: str) -> Dict[str, Any]:
    """Test API connection using health endpoint."""
    try:
        response = requests.get(f"{api_url}/api/v1/health", timeout=10)
        if response.status_code == 200:
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}", "data": response.text}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Connection failed - API server not reachable"}
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Connection timeout"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

def check_search_status(api_url: str) -> Dict[str, Any]:
    """Check search API status."""
    try:
        response = requests.get(f"{api_url}/api/v1/search/status", timeout=10)
        return {"status": "success", "data": response.json(), "status_code": response.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def make_single_search(api_url: str, query: str, country: str, language: str, page: int, results_per_page: int, instagram_filter: str = "all") -> Dict[str, Any]:
    """Make single search API call."""
    payload = {
        "query": query,
        "country": country,
        "language": language,
        "page": page,
        "results_per_page": results_per_page,
        "instagram_content_type": instagram_filter
    }
    
    try:
        response = requests.post(f"{api_url}/api/v1/search", json=payload, timeout=30)
        if response.status_code == 200:
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}", "data": response.json() if response.text else None}
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def make_batch_search(api_url: str, query: str, country: str, language: str, max_pages: int, results_per_page: int, start_page: int, instagram_filter: str = "all") -> Dict[str, Any]:
    """Make batch search API call."""
    payload = {
        "query": query,
        "country": country,
        "language": language,
        "max_pages": max_pages,
        "results_per_page": results_per_page,
        "start_page": start_page,
        "instagram_content_type": instagram_filter
    }
    
    try:
        response = requests.post(f"{api_url}/api/v1/search/pages", json=payload, timeout=60)
        if response.status_code == 200:
            return {"status": "success", "data": response.json()}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}", "data": response.json() if response.text else None}
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timeout"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Validation Functions
def validate_country_code(code: str) -> bool:
    """Validate country code format."""
    return len(code) == 2 and code.isupper()

def validate_language_code(code: str) -> bool:
    """Validate language code format.""" 
    return len(code) == 2 and code.islower()

# UI Components
def render_header():
    """Render app header with connection status."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("🔍 SERP API Tester")
        st.caption("Minimalistic frontend for Google SERP API testing")
    
    with col2:
        if st.session_state.connection_status:
            if st.session_state.connection_status["status"] == "success":
                st.success("🟢 Connected")
            else:
                st.error("🔴 Disconnected")
        else:
            st.info("⚪ Not tested")

def render_api_settings():
    """Render API settings panel."""
    with st.expander("⚙️ API Settings", expanded=False):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            api_url = st.text_input(
                "API Base URL", 
                value=st.session_state.api_url,
                help="Base URL for the FastAPI server"
            )
            if api_url != st.session_state.api_url:
                st.session_state.api_url = api_url
                st.session_state.connection_status = None
        
        with col2:
            st.write("")  # Spacing
            if st.button("Test Connection", type="secondary"):
                with st.spinner("Testing connection..."):
                    result = test_api_connection(st.session_state.api_url)
                    st.session_state.connection_status = result
                    if result["status"] == "success":
                        st.success("✅ Connection successful!")
                    else:
                        st.error(f"❌ {result['message']}")

def render_instagram_filter_section(section_key=""):
    """Render Instagram content type filter section."""
    st.subheader("📱 Instagram Content Filter")
    
    # Create toggle buttons for Instagram content types
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        all_selected = st.button("🌍 All Content", 
                                type="secondary" if st.session_state.get('ig_filter', 'all') != 'all' else "primary",
                                key=f"ig_all_{section_key}")
        if all_selected:
            st.session_state.ig_filter = 'all'
    
    with col2:
        reels_selected = st.button("🎬 Reels Only", 
                                  type="secondary" if st.session_state.get('ig_filter', 'all') != 'reels' else "primary",
                                  key=f"ig_reels_{section_key}")
        if reels_selected:
            st.session_state.ig_filter = 'reels'
    
    with col3:
        posts_selected = st.button("📷 Posts Only", 
                                  type="secondary" if st.session_state.get('ig_filter', 'all') != 'posts' else "primary",
                                  key=f"ig_posts_{section_key}")
        if posts_selected:
            st.session_state.ig_filter = 'posts'
    
    with col4:
        accounts_selected = st.button("👤 Accounts Only", 
                                     type="secondary" if st.session_state.get('ig_filter', 'all') != 'accounts' else "primary",
                                     key=f"ig_accounts_{section_key}")
        if accounts_selected:
            st.session_state.ig_filter = 'accounts'
    
    # Initialize default filter
    if 'ig_filter' not in st.session_state:
        st.session_state.ig_filter = 'all'
    
    # Display current filter status
    filter_labels = {
        'all': "🌍 All Content",
        'reels': "🎬 Reels Only", 
        'posts': "📷 Posts Only",
        'accounts': "👤 Accounts Only"
    }
    
    st.info(f"Active Filter: {filter_labels[st.session_state.ig_filter]}")
    return st.session_state.ig_filter

def render_single_search_form():
    """Render single search form."""
    st.subheader("🔍 Single Search")
    
    # Instagram filter section
    instagram_filter = render_instagram_filter_section("single")
    
    # Query input
    query = st.text_input("Search Query", value="", placeholder="Enter your search query...")
    
    # Location and language settings
    col1, col2 = st.columns(2)
    
    with col1:
        country_option = st.selectbox(
            "Country", 
            ["Custom"] + list(COMMON_COUNTRIES.keys()),
            format_func=lambda x: f"{x} - {COMMON_COUNTRIES[x]}" if x in COMMON_COUNTRIES else x
        )
        
        if country_option == "Custom":
            country = st.text_input("Country Code", value="US", max_chars=2, help="2-letter uppercase ISO code")
        else:
            country = country_option
        
        # Validate country code
        if not validate_country_code(country):
            st.error("❌ Country code must be 2-letter uppercase (e.g., 'US')")
    
    with col2:
        language_option = st.selectbox(
            "Language",
            ["Custom"] + list(COMMON_LANGUAGES.keys()),
            format_func=lambda x: f"{x} - {COMMON_LANGUAGES[x]}" if x in COMMON_LANGUAGES else x
        )
        
        if language_option == "Custom":
            language = st.text_input("Language Code", value="en", max_chars=2, help="2-letter lowercase ISO code")
        else:
            language = language_option
        
        # Validate language code
        if not validate_language_code(language):
            st.error("❌ Language code must be 2-letter lowercase (e.g., 'en')")
    
    # Pagination settings
    col3, col4 = st.columns(2)
    with col3:
        page = st.number_input("Page", min_value=1, max_value=100, value=1)
    with col4:
        results_per_page = st.number_input("Results per Page", min_value=1, max_value=100, value=10)
    
    # Search button
    if st.button("🚀 Search", type="primary", disabled=not query or not validate_country_code(country) or not validate_language_code(language)):
        with st.spinner("Searching..."):
            result = make_single_search(st.session_state.api_url, query, country, language, page, results_per_page, instagram_filter)
            st.session_state.last_search_results = result
    
    # Display results
    if st.session_state.last_search_results:
        render_search_results(st.session_state.last_search_results, "single")

def render_batch_search_form():
    """Render batch search form."""
    st.subheader("📄 Batch Search")
    
    # Instagram filter section (shared with single search)
    instagram_filter = render_instagram_filter_section("batch")
    
    # Query input
    query = st.text_input("Search Query", value="", placeholder="Enter your search query...", key="batch_query")
    
    # Location and language settings
    col1, col2 = st.columns(2)
    
    with col1:
        country_option = st.selectbox(
            "Country", 
            ["Custom"] + list(COMMON_COUNTRIES.keys()),
            format_func=lambda x: f"{x} - {COMMON_COUNTRIES[x]}" if x in COMMON_COUNTRIES else x,
            key="batch_country"
        )
        
        if country_option == "Custom":
            country = st.text_input("Country Code", value="US", max_chars=2, help="2-letter uppercase ISO code", key="batch_country_custom")
        else:
            country = country_option
        
        # Validate country code
        if not validate_country_code(country):
            st.error("❌ Country code must be 2-letter uppercase (e.g., 'US')")
    
    with col2:
        language_option = st.selectbox(
            "Language",
            ["Custom"] + list(COMMON_LANGUAGES.keys()),
            format_func=lambda x: f"{x} - {COMMON_LANGUAGES[x]}" if x in COMMON_LANGUAGES else x,
            key="batch_language"
        )
        
        if language_option == "Custom":
            language = st.text_input("Language Code", value="en", max_chars=2, help="2-letter lowercase ISO code", key="batch_language_custom")
        else:
            language = language_option
        
        # Validate language code
        if not validate_language_code(language):
            st.error("❌ Language code must be 2-letter lowercase (e.g., 'en')")
    
    # Batch settings
    col3, col4, col5 = st.columns(3)
    with col3:
        max_pages = st.number_input("Max Pages", min_value=1, max_value=10, value=3)
    with col4:
        start_page = st.number_input("Start Page", min_value=1, max_value=100, value=1)
    with col5:
        results_per_page = st.number_input("Results per Page", min_value=1, max_value=100, value=10, key="batch_results_per_page")
    
    # Search button
    if st.button("🚀 Batch Search", type="primary", disabled=not query or not validate_country_code(country) or not validate_language_code(language)):
        with st.spinner(f"Searching {max_pages} pages..."):
            result = make_batch_search(st.session_state.api_url, query, country, language, max_pages, results_per_page, start_page, instagram_filter)
            st.session_state.last_batch_results = result
    
    # Display results
    if st.session_state.last_batch_results:
        render_batch_results(st.session_state.last_batch_results)

def render_search_results(result: Dict[str, Any], search_type: str):
    """Render single search results."""
    st.subheader("📊 Search Results")
    
    if result["status"] == "error":
        st.error(f"❌ Search failed: {result['message']}")
        if "data" in result and result["data"]:
            with st.expander("Error Details"):
                st.json(result["data"])
        return
    
    data = result["data"]
    
    # Summary
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Query", data["query"])
    with col2:
        st.metric("Results Found", data["results_count"])
    with col3:
        st.metric("Timestamp", data["timestamp"][:19])
    with col4:
        # Show Instagram filter if available in metadata
        ig_filter = "N/A"
        if data.get("search_metadata") and "instagram_content_type" in data["search_metadata"]:
            ig_filter = data["search_metadata"]["instagram_content_type"].title()
        st.metric("Instagram Filter", ig_filter)
    
    # Pagination info
    if "pagination" in data and data["pagination"]:
        pagination = data["pagination"]
        st.info(f"📄 Page {pagination['current_page']} | Results {pagination['page_range_start']}-{pagination['page_range_end']} | Estimated total: {pagination.get('total_results_estimate', 'N/A')}")
    
    # Results table
    if data["organic_results"]:
        st.subheader("🔗 Organic Results")
        results_data = []
        for result in data["organic_results"]:
            results_data.append({
                "Rank": result["rank"],
                "Title": result["title"][:100] + "..." if len(result["title"]) > 100 else result["title"],
                "URL": result["url"],
                "Description": result.get("description", "")[:200] + "..." if result.get("description") and len(result.get("description", "")) > 200 else result.get("description", "")
            })
        
        st.dataframe(results_data, use_container_width=True)
    else:
        st.warning("No organic results found.")
    
    # Raw JSON
    with st.expander("📄 Raw JSON Response"):
        st.json(data)

def render_batch_results(result: Dict[str, Any]):
    """Render batch search results."""
    st.subheader("📊 Batch Search Results")
    
    if result["status"] == "error":
        st.error(f"❌ Batch search failed: {result['message']}")
        if "data" in result and result["data"]:
            with st.expander("Error Details"):
                st.json(result["data"])
        return
    
    data = result["data"]
    
    # Summary
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Query", data["query"])
    with col2:
        st.metric("Total Results", data["total_results"])
    with col3:
        st.metric("Pages Fetched", data["pages_fetched"])
    with col4:
        st.metric("Processing Time", f"{data['pagination_summary'].get('batch_processing_time', 0):.2f}s")
    with col5:
        # Show Instagram filter from first page's metadata if available
        ig_filter = "N/A"
        if data.get("pages") and len(data["pages"]) > 0:
            first_page = data["pages"][0]
            if first_page.get("search_metadata") and "instagram_content_type" in first_page["search_metadata"]:
                ig_filter = first_page["search_metadata"]["instagram_content_type"].title()
        st.metric("Instagram Filter", ig_filter)
    
    # Pages summary
    summary = data["pagination_summary"]
    st.info(f"📄 Pages {summary['start_page']}-{summary['end_page']} | {summary['results_per_page']} results per page | Total estimate: {summary.get('total_results_estimate', 'N/A')}")
    
    # View mode toggle
    view_mode = st.radio(
        "View Mode:", 
        ["Merged Results", "Page-by-Page"], 
        horizontal=True,
        help="Choose between merged continuous results or detailed page-by-page view"
    )
    
    if view_mode == "Merged Results":
        # Display merged results
        merged_results = data.get("merged_results", [])
        merged_metadata = data.get("merged_metadata")
        
        if merged_results:
            st.subheader(f"🔗 All Results ({len(merged_results)} total)")
            
            # Show merge metadata
            if merged_metadata:
                meta = merged_metadata
                pages_str = ", ".join(map(str, meta["pages_included"])) if meta["pages_included"] else "none"
                st.info(f"📊 Merged {meta['total_merged_results']} results from pages [{pages_str}] "
                       f"(processed in {meta['merge_processing_time']:.3f}s)")
            
            # Display merged results as single table
            results_data = []
            for result in merged_results:
                results_data.append({
                    "Rank": result["rank"],
                    "Title": result["title"][:100] + "..." if len(result["title"]) > 100 else result["title"],
                    "URL": result["url"],
                    "Description": result.get("description", "")[:200] + "..." if result.get("description") and len(result.get("description", "")) > 200 else result.get("description", "")
                })
            
            st.dataframe(results_data, use_container_width=True)
        else:
            st.warning("No merged results available.")
    
    else:
        # Display page-by-page results (original behavior)
        if data["pages"]:
            for page_result in data["pages"]:
                with st.expander(f"📄 Page {page_result['page_number']} ({page_result['results_count']} results)", expanded=False):
                    if page_result["organic_results"]:
                        results_data = []
                        for result in page_result["organic_results"]:
                            results_data.append({
                                "Rank": result["rank"],
                                "Title": result["title"][:80] + "..." if len(result["title"]) > 80 else result["title"],
                                "URL": result["url"],
                                "Description": result.get("description", "")[:150] + "..." if result.get("description") and len(result.get("description", "")) > 150 else result.get("description", "")
                            })
                        
                        st.dataframe(results_data, use_container_width=True)
                    else:
                        st.warning("No results for this page.")
        else:
            st.warning("No page results available.")
    
    # Raw JSON
    with st.expander("📄 Raw JSON Response"):
        st.json(data)

def render_health_checks():
    """Render health check section."""
    st.subheader("🏥 Health Checks")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 General Health Check"):
            with st.spinner("Checking general health..."):
                result = test_api_connection(st.session_state.api_url)
                if result["status"] == "success":
                    st.success("✅ API is healthy!")
                    st.json(result["data"])
                else:
                    st.error(f"❌ Health check failed: {result['message']}")
    
    with col2:
        if st.button("🔍 Search Status Check"):
            with st.spinner("Checking search status..."):
                result = check_search_status(st.session_state.api_url)
                if result["status"] == "success":
                    if result["status_code"] == 200:
                        st.success("✅ Search API is healthy!")
                    else:
                        st.warning(f"⚠️ Search API status: {result['status_code']}")
                    st.json(result["data"])
                else:
                    st.error(f"❌ Search status check failed: {result['message']}")

# Main App
def main():
    """Main application function."""
    st.set_page_config(
        page_title="SERP API Tester",
        page_icon="🔍",
        layout="wide"
    )
    
    init_session_state()
    render_header()
    render_api_settings()
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["🔍 Single Search", "📄 Batch Search", "🏥 Health Checks"])
    
    with tab1:
        render_single_search_form()
    
    with tab2:
        render_batch_search_form()
    
    with tab3:
        render_health_checks()
    
    # Footer
    st.divider()
    st.caption(f"🔗 Connected to: {st.session_state.api_url} | Built with Streamlit")

if __name__ == "__main__":
    main()