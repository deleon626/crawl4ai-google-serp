"""
Web Crawling page for the SERP Parser & Business Intelligence multi-page Streamlit application.
Provides comprehensive web content extraction using Crawl4ai integration.
"""

import streamlit as st
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import re

# Page Configuration
st.set_page_config(
    page_title="Web Crawling - SERP Parser & BI",
    page_icon="🕷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import shared utilities
from utils.streamlit_shared import make_api_request, init_session_state, render_sidebar_config

def init_crawl_session_state():
    """Initialize crawl-specific session state variables."""
    crawl_defaults = {
        'crawl_results': None,
        'crawl_history': [],
        'crawl_settings': {
            'word_count_threshold': 10,
            'extraction_strategy': 'NoExtractionStrategy',
            'chunking_strategy': 'RegexChunking',
            'include_raw_html': False,
            'css_selector': '',
            'user_agent': '',
            'custom_headers': {}
        },
        'crawl_status': 'ready'
    }
    
    for key, value in crawl_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def validate_url(url: str) -> bool:
    """Validate URL format."""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def build_crawl_request(url: str, advanced_settings: Dict[str, Any]) -> Dict[str, Any]:
    """Build crawl request payload."""
    request_data = {
        "url": url,
        "word_count_threshold": advanced_settings.get('word_count_threshold', 10),
        "extraction_strategy": advanced_settings.get('extraction_strategy', 'NoExtractionStrategy'),
        "chunking_strategy": advanced_settings.get('chunking_strategy', 'RegexChunking'),
        "include_raw_html": advanced_settings.get('include_raw_html', False)
    }
    
    # Add optional fields only if they have values
    if advanced_settings.get('css_selector'):
        request_data["css_selector"] = advanced_settings['css_selector']
    
    if advanced_settings.get('user_agent'):
        request_data["user_agent"] = advanced_settings['user_agent']
    
    if advanced_settings.get('custom_headers'):
        request_data["headers"] = advanced_settings['custom_headers']
    
    return request_data

def add_to_crawl_history(url: str, result: Dict[str, Any], execution_time: float):
    """Add crawl result to history."""
    history_item = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "execution_time": execution_time,
        "success": result.get("success", False),
        "title": result.get("result", {}).get("title", "N/A") if result.get("success") else "Failed",
        "error": result.get("error") if not result.get("success") else None
    }
    
    # Keep only last 10 items
    st.session_state.crawl_history.insert(0, history_item)
    if len(st.session_state.crawl_history) > 10:
        st.session_state.crawl_history = st.session_state.crawl_history[:10]

def render_crawl_results(result: Dict[str, Any]):
    """Render crawl results in tabbed interface."""
    if not result:
        return
        
    if result.get("success") and result.get("result"):
        crawl_data = result["result"]
        
        # Results tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📄 Content", "📊 Metadata", "🔗 Links", "🖼️ Media", "🔧 Raw Data"])
        
        with tab1:
            st.subheader("Extracted Content")
            if crawl_data.get("title"):
                st.markdown(f"**Title:** {crawl_data['title']}")
                st.markdown("---")
            
            if crawl_data.get("markdown"):
                st.markdown("**Content:**")
                st.markdown(crawl_data["markdown"])
            else:
                st.info("No content extracted. Try adjusting the extraction settings.")
        
        with tab2:
            st.subheader("Page Metadata")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Execution Time", f"{result.get('execution_time', 0):.2f}s")
                if crawl_data.get("title"):
                    st.metric("Title Length", f"{len(crawl_data['title'])} chars")
                
            with col2:
                st.metric("Content Length", f"{len(crawl_data.get('markdown', ''))} chars")
                timestamp = result.get('timestamp', datetime.now().isoformat())
                st.write(f"**Crawled:** {timestamp}")
            
            if crawl_data.get("metadata"):
                st.subheader("Additional Metadata")
                st.json(crawl_data["metadata"])
        
        with tab3:
            st.subheader("Extracted Links")
            if crawl_data.get("links"):
                links = crawl_data["links"]
                
                col1, col2 = st.columns(2)
                with col1:
                    if "internal" in links:
                        st.write(f"**Internal Links ({len(links['internal'])})**")
                        for link in links["internal"][:10]:  # Show first 10
                            st.write(f"• {link}")
                        if len(links["internal"]) > 10:
                            st.write(f"... and {len(links['internal']) - 10} more")
                
                with col2:
                    if "external" in links:
                        st.write(f"**External Links ({len(links['external'])})**")
                        for link in links["external"][:10]:  # Show first 10
                            st.write(f"• {link}")
                        if len(links["external"]) > 10:
                            st.write(f"... and {len(links['external']) - 10} more")
            else:
                st.info("No links extracted from the page.")
        
        with tab4:
            st.subheader("Media Content")
            if crawl_data.get("media"):
                media = crawl_data["media"]
                
                if "images" in media and media["images"]:
                    st.write(f"**Images ({len(media['images'])})**")
                    for i, img_url in enumerate(media["images"][:5]):  # Show first 5
                        try:
                            st.image(img_url, caption=f"Image {i+1}", width=200)
                        except:
                            st.write(f"• {img_url}")
                    
                    if len(media["images"]) > 5:
                        st.write(f"... and {len(media['images']) - 5} more images")
                
                if "videos" in media and media["videos"]:
                    st.write(f"**Videos ({len(media['videos'])})**")
                    for video_url in media["videos"]:
                        st.write(f"• {video_url}")
            else:
                st.info("No media content extracted from the page.")
        
        with tab5:
            st.subheader("Raw Data")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📥 Download as JSON"):
                    json_str = json.dumps(result, indent=2, default=str)
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name=f"crawl_result_{int(time.time())}.json",
                        mime="application/json"
                    )
            
            with col2:
                if crawl_data.get("markdown") and st.button("📝 Download as Markdown"):
                    st.download_button(
                        label="Download Markdown",
                        data=crawl_data["markdown"],
                        file_name=f"crawl_content_{int(time.time())}.md",
                        mime="text/markdown"
                    )
            
            st.subheader("Complete Response")
            st.json(result)
            
            if crawl_data.get("cleaned_html") and result["request"].get("include_raw_html"):
                st.subheader("Cleaned HTML")
                st.code(crawl_data["cleaned_html"], language="html")
    
    else:
        # Error state
        st.error(f"❌ **Crawl Failed**: {result.get('error', 'Unknown error')}")
        
        # Troubleshooting suggestions
        st.subheader("🔧 Troubleshooting")
        st.markdown("""
        **Common solutions:**
        1. **Check URL**: Ensure the URL is valid and accessible
        2. **Network Issues**: Try again in a few moments
        3. **JavaScript Required**: Some sites need JavaScript rendering (not supported in basic mode)
        4. **Rate Limiting**: The target site may be blocking automated requests
        5. **Server Error**: Check the backend API connection in the sidebar
        """)

# Initialize session state
init_session_state()
init_crawl_session_state()

# Render sidebar configuration
render_sidebar_config()

# Header
st.title("🕷️ Web Content Crawler")
st.markdown("**Extract and analyze content from any web page using advanced crawling technology.**")

# Quick stats
col1, col2, col3 = st.columns(3)
with col1:
    crawl_count = len(st.session_state.crawl_history)
    st.metric("Pages Crawled", crawl_count, help="Total pages crawled in this session")
with col2:
    successful_crawls = sum(1 for item in st.session_state.crawl_history if item.get("success", False))
    success_rate = (successful_crawls / max(crawl_count, 1)) * 100
    st.metric("Success Rate", f"{success_rate:.0f}%", help="Percentage of successful crawls")
with col3:
    if st.session_state.crawl_history:
        avg_time = sum(item.get("execution_time", 0) for item in st.session_state.crawl_history) / len(st.session_state.crawl_history)
        st.metric("Avg Time", f"{avg_time:.1f}s", help="Average crawling time")
    else:
        st.metric("Avg Time", "0.0s", help="Average crawling time")

st.markdown("---")

# Main Interface
st.subheader("🎯 URL Input & Quick Actions")

# URL input
url_col, test_col = st.columns([3, 1])

with url_col:
    url_input = st.text_input(
        "Enter URL to crawl:",
        value="",
        placeholder="https://example.com",
        help="Enter a complete URL starting with http:// or https://"
    )

with test_col:
    st.write("")  # Spacing
    st.write("")  # More spacing
    if st.button("🧪 Quick Test", help="Test crawl with default settings"):
        if url_input:
            if validate_url(url_input):
                st.session_state.crawl_status = 'testing'
                st.rerun()
            else:
                st.error("Please enter a valid URL")
        else:
            # Use default test URL
            url_input = "https://httpbin.org/html"
            st.session_state.crawl_status = 'testing'
            st.rerun()

# Example URLs for quick testing
with st.expander("📋 **Example URLs for Testing**"):
    example_urls = [
        "https://httpbin.org/html",
        "https://example.com",
        "https://www.wikipedia.org",
        "https://news.ycombinator.com",
        "https://github.com"
    ]
    
    cols = st.columns(len(example_urls))
    for i, example_url in enumerate(example_urls):
        with cols[i]:
            if st.button(f"📄 {example_url.split('//')[1].split('/')[0]}", key=f"example_{i}"):
                url_input = example_url
                st.rerun()

# Advanced Configuration
st.subheader("⚙️ Advanced Configuration")
with st.expander("🔧 **Advanced Crawling Options**", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Content Extraction")
        word_threshold = st.slider(
            "Word Count Threshold",
            min_value=1,
            max_value=100,
            value=st.session_state.crawl_settings['word_count_threshold'],
            help="Minimum words required for content blocks"
        )
        
        extraction_strategy = st.selectbox(
            "Extraction Strategy",
            ["NoExtractionStrategy", "LLMExtractionStrategy", "CosineStrategy"],
            index=0,
            help="Method used to extract content from the page"
        )
        
        chunking_strategy = st.selectbox(
            "Chunking Strategy",
            ["RegexChunking", "NlpSentenceChunking", "TopicSegmentationChunking"],
            index=0,
            help="How to divide content into chunks"
        )
    
    with col2:
        st.subheader("Advanced Options")
        css_selector = st.text_input(
            "CSS Selector (Optional)",
            value=st.session_state.crawl_settings.get('css_selector', ''),
            placeholder="e.g., .article-content, #main",
            help="Target specific elements using CSS selectors"
        )
        
        user_agent = st.text_input(
            "Custom User Agent (Optional)",
            value=st.session_state.crawl_settings.get('user_agent', ''),
            placeholder="e.g., Mozilla/5.0...",
            help="Override the default user agent string"
        )
        
        include_raw_html = st.checkbox(
            "Include Raw HTML",
            value=st.session_state.crawl_settings['include_raw_html'],
            help="Include cleaned HTML in the response (increases response size)"
        )
    
    # Custom Headers
    st.subheader("Custom Headers")
    headers_input = st.text_area(
        "Custom Headers (JSON format)",
        value=json.dumps(st.session_state.crawl_settings.get('custom_headers', {}), indent=2),
        placeholder='{"Authorization": "Bearer token", "X-Custom": "value"}',
        help="Add custom HTTP headers as JSON"
    )
    
    # Update settings in session state
    st.session_state.crawl_settings.update({
        'word_count_threshold': word_threshold,
        'extraction_strategy': extraction_strategy,
        'chunking_strategy': chunking_strategy,
        'css_selector': css_selector,
        'user_agent': user_agent,
        'include_raw_html': include_raw_html
    })
    
    # Parse custom headers
    try:
        if headers_input.strip():
            custom_headers = json.loads(headers_input)
            st.session_state.crawl_settings['custom_headers'] = custom_headers
        else:
            st.session_state.crawl_settings['custom_headers'] = {}
    except json.JSONDecodeError:
        st.error("Invalid JSON format for custom headers")

# Action Buttons
st.subheader("🚀 Actions")
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    crawl_button = st.button(
        "🕷️ **Start Crawl**",
        type="primary",
        disabled=not url_input or not validate_url(url_input) if url_input else True,
        help="Start crawling with current settings"
    )

with col2:
    if st.button("🔄 Reset Settings", help="Reset all settings to defaults"):
        st.session_state.crawl_settings = {
            'word_count_threshold': 10,
            'extraction_strategy': 'NoExtractionStrategy',
            'chunking_strategy': 'RegexChunking',
            'include_raw_html': False,
            'css_selector': '',
            'user_agent': '',
            'custom_headers': {}
        }
        st.rerun()

# Handle crawl execution
if crawl_button or st.session_state.crawl_status == 'testing':
    if url_input and validate_url(url_input):
        st.session_state.crawl_status = 'crawling'
        
        with st.spinner("🕷️ Crawling webpage... This may take a few moments."):
            progress_bar = st.progress(0)
            progress_text = st.empty()
            
            progress_text.text("Preparing request...")
            progress_bar.progress(20)
            
            # Build request
            request_data = build_crawl_request(url_input, st.session_state.crawl_settings)
            
            progress_text.text("Sending request to crawler...")
            progress_bar.progress(40)
            
            # Make API call
            start_time = time.time()
            if st.session_state.crawl_status == 'testing':
                result = make_api_request("/api/v1/crawl/test", method="GET", timeout=60)
            else:
                result = make_api_request("/api/v1/crawl", method="POST", data=request_data, timeout=60)
            
            progress_text.text("Processing response...")
            progress_bar.progress(80)
            
            execution_time = time.time() - start_time
            
            progress_text.text("Complete!")
            progress_bar.progress(100)
            
            # Store result
            st.session_state.crawl_results = result
            
            # Add to history
            add_to_crawl_history(url_input, result, execution_time)
            
            # Clear status
            st.session_state.crawl_status = 'ready'
            
            # Clear progress indicators
            progress_bar.empty()
            progress_text.empty()
    
    elif url_input:
        st.error("Please enter a valid URL starting with http:// or https://")

# Display Results
if st.session_state.crawl_results:
    st.markdown("---")
    st.subheader("📊 Crawl Results")
    render_crawl_results(st.session_state.crawl_results)

# Crawl History
if st.session_state.crawl_history:
    st.markdown("---")
    st.subheader("📚 Crawl History")
    
    with st.expander(f"**Recent Crawls ({len(st.session_state.crawl_history)})**", expanded=False):
        for i, item in enumerate(st.session_state.crawl_history):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                status_icon = "✅" if item.get("success") else "❌"
                st.write(f"{status_icon} **{item.get('title', 'No Title')}**")
                st.write(f"🔗 {item['url']}")
            
            with col2:
                st.write(f"⏱️ {item.get('execution_time', 0):.2f}s")
                timestamp = datetime.fromisoformat(item['timestamp']).strftime("%H:%M:%S")
                st.write(f"🕒 {timestamp}")
            
            with col3:
                if item.get("error"):
                    st.write(f"❌ {item['error'][:50]}...")
                else:
                    st.write("✅ Success")
            
            with col4:
                if st.button(f"🔄", key=f"recrawl_{i}", help="Recrawl this URL"):
                    url_input = item['url']
                    st.rerun()
            
            if i < len(st.session_state.crawl_history) - 1:
                st.markdown("---")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
<p><strong>Web Content Crawler</strong> | Powered by Crawl4ai & FastAPI</p>
<p>💡 <em>Tip: Use CSS selectors to target specific content areas for more precise extraction</em></p>
</div>
""", unsafe_allow_html=True)