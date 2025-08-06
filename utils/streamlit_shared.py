"""
Shared utilities for Streamlit multi-page application.
"""

import streamlit as st
import requests
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"

def init_session_state():
    """Initialize session state variables."""
    defaults = {
        'api_url': API_BASE_URL,
        'connection_status': None,
        'search_results': None,
        'instagram_results': None,
        'company_results': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

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

def render_sidebar_config():
    """Render the API configuration sidebar."""
    with st.sidebar:
        st.header("⚙️ Configuration")
        new_api_url = st.text_input("API Base URL", value=st.session_state.api_url)
        
        if new_api_url != st.session_state.api_url:
            st.session_state.api_url = new_api_url
            st.session_state.connection_status = None
            st.rerun()
        
        if st.button("Test Connection"):
            result = make_api_request("/api/v1/health")
            st.session_state.connection_status = result
            st.rerun()
        
        if st.session_state.connection_status:
            if st.session_state.connection_status["success"]:
                st.success("✅ API Connected")
            else:
                st.error(f"❌ API Error: {st.session_state.connection_status['error']}")
        
        st.markdown("---")
        st.info("💡 Navigate between pages using the sidebar menu")