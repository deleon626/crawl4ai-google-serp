#!/usr/bin/env python3
"""
Demo script showing the Query Modifier Preview functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from frontend.streamlit_app import generate_query_preview

def demo_query_preview():
    """Demonstrate query preview functionality with various examples."""
    
    print("🔍 Query Modifier Preview Demonstration")
    print("=" * 60)
    
    # Test cases
    test_queries = [
        "software engineer",
        "marketing tips",
        "python programming",
        "data science jobs"
    ]
    
    # Platform and filter combinations
    test_combinations = [
        ("none", "all", "all", "🌍 All Platforms"),
        ("instagram", "all", "all", "📱 Instagram All Content"),
        ("instagram", "reels", "all", "📱 Instagram Reels"),
        ("instagram", "posts", "all", "📱 Instagram Posts"),
        ("instagram", "accounts", "all", "📱 Instagram Accounts"),
        ("instagram", "tv", "all", "📱 Instagram TV"),
        ("instagram", "locations", "all", "📱 Instagram Locations"),
        ("linkedin", "all", "all", "💼 LinkedIn All Content"),
        ("linkedin", "all", "profiles", "💼 LinkedIn Profiles"),
        ("linkedin", "all", "companies", "💼 LinkedIn Companies"),
        ("linkedin", "all", "posts", "💼 LinkedIn Posts"),
        ("linkedin", "all", "jobs", "💼 LinkedIn Jobs"),
        ("linkedin", "all", "articles", "💼 LinkedIn Articles"),
    ]
    
    for query in test_queries:
        print(f"\n📝 Original Query: '{query}'")
        print("-" * 50)
        
        for platform, ig_filter, li_filter, description in test_combinations:
            modified_query, modifier_desc = generate_query_preview(query, platform, ig_filter, li_filter)
            
            if modified_query != query:  # Only show when query is actually modified
                print(f"\n{description}:")
                print(f"   Modified Query: {modified_query}")
                print(f"   Description: {modifier_desc}")
                google_url = f"https://www.google.com/search?q={modified_query.replace(' ', '+')}"
                print(f"   Google URL: {google_url}")
    
    print(f"\n✅ Query Preview Demo Complete!")
    print("\n💡 Usage Tips:")
    print("   • Enter a search query in the Streamlit app")
    print("   • Select platform (All/Instagram/LinkedIn)")
    print("   • Choose content type filters")
    print("   • See real-time preview of modified query")
    print("   • Copy the generated Google Search URL for direct testing")

def demo_specific_examples():
    """Show specific real-world examples."""
    
    print("\n\n🎯 Real-World Example Scenarios")
    print("=" * 60)
    
    examples = [
        {
            "scenario": "Finding LinkedIn profiles of software engineers",
            "query": "software engineer python",
            "platform": "linkedin",
            "ig_filter": "all",
            "li_filter": "profiles"
        },
        {
            "scenario": "Discovering Instagram reels about cooking",
            "query": "healthy recipes",
            "platform": "instagram",
            "ig_filter": "reels",
            "li_filter": "all"
        },
        {
            "scenario": "Finding LinkedIn job postings for data scientists",
            "query": "data scientist remote",
            "platform": "linkedin",
            "ig_filter": "all",
            "li_filter": "jobs"
        },
        {
            "scenario": "Looking for Instagram posts about travel",
            "query": "bali travel guide",
            "platform": "instagram",
            "ig_filter": "posts",
            "li_filter": "all"
        },
        {
            "scenario": "Finding LinkedIn articles about AI trends",
            "query": "artificial intelligence 2024",
            "platform": "linkedin",
            "ig_filter": "all",
            "li_filter": "articles"
        }
    ]
    
    for example in examples:
        print(f"\n🔍 Scenario: {example['scenario']}")
        print(f"   Original Query: '{example['query']}'")
        
        modified_query, description = generate_query_preview(
            example['query'], 
            example['platform'], 
            example['ig_filter'], 
            example['li_filter']
        )
        
        print(f"   Modified Query: {modified_query}")
        print(f"   What it does: {description}")
        
        google_url = f"https://www.google.com/search?q={modified_query.replace(' ', '+')}"
        print(f"   Test URL: {google_url}")

if __name__ == "__main__":
    demo_query_preview()
    demo_specific_examples()