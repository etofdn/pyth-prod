#!/usr/bin/env python3
"""
setup_vector_search.py - Vector Search Setup

Sets up the vector search system by:
1. Creating the vector-enabled index
2. Loading transcript data
3. Generating embeddings for all documents
4. Uploading documents with embeddings

Usage:
    python setup_vector_search.py
"""

import asyncio
import json
from vector_search_async import AsyncVectorSearch

async def setup_vector_search():
    """Setup vector search system"""
    print("=== Vector Search Setup ===")
    
    vector_search = AsyncVectorSearch()
    
    # Step 1: Create/update index with vector capabilities
    print("\n1. Creating vector-enabled index...")
    await vector_search.create_or_update_index()
    
    # Step 2: Load transcript data
    print("\n2. Loading transcript data...")
    documents = await vector_search.load_and_process_transcripts()
    if not documents:
        print("No documents found. Please ensure flattened_transcript.json exists.")
        return
    
    print(f"Loaded {len(documents)} transcript chunks")
    
    # Step 3: Upload documents with embeddings
    print("\n3. Generating embeddings and uploading documents...")
    print("This may take a while depending on the number of documents...")
    await vector_search.upload_documents(documents)
    
    print("\n✅ Vector search setup complete!")
    print("You can now use:")
    print("  - vector_search_async.py for vector search operations")
    print("  - comprehensive_search.py for all search types")
    print("  - transcript_searchv2.py for semantic search")

async def test_vector_search():
    """Test the vector search functionality"""
    print("\n=== Testing Vector Search ===")
    
    vector_search = AsyncVectorSearch()
    
    test_queries = [
        "AI technology impact",
        "SpaceX Mars plans",
        "Tesla manufacturing",
        "sustainable energy",
        "future of humanity"
    ]
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        results = await vector_search.vector_search(query, top_k=2)
        
        if results:
            print(f"Found {len(results)} results:")
            for i, hit in enumerate(results, 1):
                print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] | Speaker {hit['speaker']}")
                print(f"     \"{hit['text']}\"")
        else:
            print("No results found")

async def main():
    """Main setup function"""
    print("Vector Search Setup")
    print("==================")
    print("This will:")
    print("1. Create a vector-enabled search index")
    print("2. Load your transcript data")
    print("3. Generate embeddings for all documents")
    print("4. Upload documents with embeddings")
    print()
    
    choice = input("Do you want to proceed? (y/n): ").strip().lower()
    
    if choice == 'y':
        await setup_vector_search()
        
        # Test the setup
        test_choice = input("\nDo you want to test the vector search? (y/n): ").strip().lower()
        if test_choice == 'y':
            await test_vector_search()
    else:
        print("Setup cancelled.")

if __name__ == "__main__":
    asyncio.run(main()) 