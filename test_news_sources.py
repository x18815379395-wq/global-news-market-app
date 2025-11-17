"""
Test script for the enhanced news source management module
"""
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news import get_news, Market
from news.legacy import NewsSourceManagerV2

def test_news_source_manager():
    print("=== Testing News Source Manager ===")
    
    # Initialize the manager
    manager = NewsSourceManagerV2(markets=[Market.GLOBAL, Market.US])
    
    health_snapshot = manager.get_health_snapshot()
    print("Adapter health summary:")
    for name, info in health_snapshot.items():
        if name == "last_fetch":
            continue
        print(f" - {name}: healthy={info.get('healthy')} last_error={info.get('last_error')}")
    print(f"Last fetch timestamp: {health_snapshot.get('last_fetch')}")
    
    # Test enhanced news data retrieval
    print("\n--- Retrieving enhanced news data ---")
    try:
        results = manager.get_enhanced_news_data()
        print(f"Retrieved {len(results)} articles")
        
        # Show first 5 articles with detailed info
        for i, article in enumerate(results[:5]):
            print(f"\n{i+1}. {article['title'][:100]}{'...' if len(article['title']) > 100 else ''}")
            print(f"   Source: {article['source']}")
            print(f"   Type: {article['contentType']}")
            print(f"   Relevance: {article['relevance_score']:.2f}")
            print(f"   Published: {article.get('publishedAt', 'N/A')}")
            print(f"   URL: {article['url']}")
            print(f"   Description: {article['description'][:100]}...")
        
        # Show source breakdown
        source_counts = {}
        type_counts = {}
        for article in results:
            source = article['source']
            content_type = article['contentType']
            
            source_counts[source] = source_counts.get(source, 0) + 1
            type_counts[content_type] = type_counts.get(content_type, 0) + 1
        
        print(f"\n--- Source Breakdown ---")
        for source, count in source_counts.items():
            print(f"{source}: {count} articles")
        
        print(f"\n--- Content Type Breakdown ---")
        for content_type, count in type_counts.items():
            print(f"{content_type}: {count} articles")
        
    except Exception as e:
        print(f"Error testing news source manager: {e}")
        import traceback
        traceback.print_exc()

def test_original_vs_enhanced():
    print("\n=== Comparing Original vs Enhanced Implementation ===")
    
    # Import the main application to test both methods
    from ears_of_fortune_v2 import get_news_safe_original
    
    print("Testing original implementation...")
    try:
        original_results = get_news_safe_original()
        print(f"Original implementation returned {len(original_results)} articles")
    except Exception as e:
        print(f"Error in original implementation: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTesting enhanced implementation...")
    try:
        pipeline_result = get_news([Market.GLOBAL, Market.US])
        enhanced_results = [
            {
                "title": item.title,
                "description": item.description,
                "source": item.source,
                "contentType": item.content_type.value,
                "publishedAt": item.published_at.isoformat() if item.published_at else None,
                "relevance_score": item.relevance_score or 0.0,
                "url": item.url,
            }
            for item in pipeline_result.items
        ]
        print(f"Enhanced implementation returned {len(enhanced_results)} articles")
    except Exception as e:
        print(f"Error in enhanced implementation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_news_source_manager()
    test_original_vs_enhanced()
