#!/usr/bin/env python3
"""
test_semantic.py

Simple test for semantic search with existing index
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

def test_semantic_search():
    # Use existing index
    search_endpoint = "https://aisearchscripts.search.windows.net"
    search_key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
    index_name = "transcripts-v2"
    
    client = SearchClient(
        endpoint=search_endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(search_key)
    )
    
    print("Testing semantic search with existing index...")
    
    try:
        # Test basic search first
        print("\n1. Testing basic search...")
        results = list(client.search(
            search_text="AI",
            top=3,
            select=["text", "speaker", "@search.score"]
        ))
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. Speaker {result.get('speaker')} - Score: {result.get('@search.score', 0):.3f}")
            print(f"     Text: \"{result.get('text', '')}\"")
        
        # Test semantic search
        print("\n2. Testing semantic search...")
        semantic_results = list(client.search(
            search_text="What does Elon Musk think about AI?",
            query_type="semantic",
            top=3,
            select=["text", "speaker", "@search.score", "@search.reranker_score"]
        ))
        
        print(f"Found {len(semantic_results)} semantic results:")
        for i, result in enumerate(semantic_results, 1):
            print(f"  {i}. Speaker {result.get('speaker')} - Score: {result.get('@search.score', 0):.3f}")
            if result.get('@search.reranker_score'):
                print(f"     Reranker Score: {result.get('@search.reranker_score', 0):.3f}")
            print(f"     Text: \"{result.get('text', '')}\"")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_semantic_search() 