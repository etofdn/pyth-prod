#!/usr/bin/env python3
"""
transcript_searchv2.py - Async Semantic Search for Transcripts

Retrieval script for your flattened "transcripts-v2" index with semantic search capabilities.
Supports four modes:
  1) Sample tests
  2) Interactive search  
  3) Comprehensive Mars colony search
  4) Semantic search demo

Usage:
    python transcript_searchv2.py
"""

import os
import asyncio
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential

class AsyncSearchFilter:
    def __init__(self):
        # Hard-coded credentials
        self.search_endpoint = "https://aisearchscripts.search.windows.net"
        self.search_key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
        self.index_name = "transcripts-v2"
        self.semantic_config_name = "transcript-semantic-config"
        
    async def get_client(self):
        """Get async search client"""
        credential = AzureKeyCredential(self.search_key)
        return SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=credential
        )

    async def basic_search(self, query, top_k=10):
        """
        Basic search without semantic ranking
        """
        client = await self.get_client()
        try:
            results = await client.search(
                search_text=query,
                top=top_k,
                select=[
                    "text",
                    "start_at", 
                    "end_at",
                    "speaker",
                    "videolink",
                    "Filename",
                    "transaction_key",
                    "request_id",
                    "parentDocId",
                    "start_offset",
                    "end_offset",
                    "channels",
                    "flattened_transcript"
                ]
            )
            
            hits = []
            async for result in results:
                if result.get("text"):
                    hits.append({
                        "text": result["text"],
                        "start_at": result.get("start_at"),
                        "end_at": result.get("end_at"),
                        "speaker": result.get("speaker"),
                        "video_link": result.get("videolink"),
                        "filename": result.get("Filename"),
                        "transaction_key": result.get("transaction_key"),
                        "parent_doc_id": result.get("parentDocId"),
                        "start_offset": result.get("start_offset"),
                        "end_offset": result.get("end_offset"),
                        "channels": result.get("channels"),
                        "flattened_transcript": result.get("flattened_transcript")
                    })
            
            await client.close()
            return hits
            
        except Exception as e:
            print(f"Error in basic search: {e}")
            await client.close()
            return []

    async def semantic_search(self, query, top_k=10):
        """
        Semantic search with AI ranking - enhanced to be more flexible
        """
        client = await self.get_client()
        try:
            # Try semantic search first
            results = await client.search(
                search_text=query,
                query_type="semantic",
                semantic_configuration_name=self.semantic_config_name,
                top=top_k,
                select=[
                    "text",
                    "start_at",
                    "end_at", 
                    "speaker",
                    "videolink",
                    "Filename",
                    "transaction_key",
                    "request_id",
                    "parentDocId",
                    "start_offset",
                    "end_offset",
                    "channels",
                    "flattened_transcript"
                ]
            )
            
            semantic_hits = []
            async for result in results:
                if result.get("text"):
                    semantic_hits.append({
                        "text": result["text"],
                        "start_at": result.get("start_at"),
                        "filename": result.get("Filename"),
                        "speaker": result.get("speaker"),
                        "video_link": result.get("videolink"),
                        "end_at": result.get("end_at"),
                        "transaction_key": result.get("transaction_key"),
                        "parent_doc_id": result.get("parentDocId"),
                        "start_offset": result.get("start_offset"),
                        "end_offset": result.get("end_offset"),
                        "channels": result.get("channels"),
                        "flattened_transcript": result.get("flattened_transcript"),
                        "search_type": "semantic"
                    })
            
            # If semantic search found results, return them
            if semantic_hits:
                await client.close()
                return semantic_hits
            
            # If no semantic results, try basic search as fallback
            print(f"Semantic search returned {len(semantic_hits)} results, trying basic search...")
            basic_results = await client.search(
                search_text=query,
                top=top_k,
                select=[
                    "text",
                    "start_at",
                    "end_at", 
                    "speaker",
                    "videolink",
                    "Filename",
                    "transaction_key",
                    "request_id",
                    "parentDocId",
                    "start_offset",
                    "end_offset",
                    "channels",
                    "flattened_transcript"
                ]
            )
            
            basic_hits = []
            async for result in basic_results:
                if result.get("text"):
                    basic_hits.append({
                        "text": result["text"],
                        "start_at": result.get("start_at"),
                        "filename": result.get("Filename"),
                        "speaker": result.get("speaker"),
                        "video_link": result.get("videolink"),
                        "end_at": result.get("end_at"),
                        "transaction_key": result.get("transaction_key"),
                        "parent_doc_id": result.get("parentDocId"),
                        "start_offset": result.get("start_offset"),
                        "end_offset": result.get("end_offset"),
                        "channels": result.get("channels"),
                        "flattened_transcript": result.get("flattened_transcript"),
                        "search_type": "basic"
                    })
            
            await client.close()
            return basic_hits
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            await client.close()
            return []

    async def search_with_relevance_filter(self, query, min_relevance=50, top_k=10):
        """
        Perform a search, then post-filter by simple term-overlap relevance.
        """
        hits = await self.basic_search(query, top_k)
        
        terms = query.lower().split()
        filtered = []
        
        for hit in hits:
            txt = hit["text"].lower()
            found = [t for t in terms if t in txt]
            relevance = len(found) / len(terms) * 100 if terms else 0
            if relevance >= min_relevance:
                filtered.append({
                    "relevance": relevance,
                    "found_terms": found,
                    **hit
                })
        
        # Sort descending by relevance
        filtered.sort(key=lambda x: x["relevance"], reverse=True)
        return filtered

    async def run_sample_tests(self):
        """
        Mode 1: Run a few preset queries and display their results.
        """
        print("\n=== Sample Test Queries ===")
        queries = ["AI and technology", "SpaceX Mars colony", "Tesla manufacturing"]
        
        for query in queries:
            print(f"\nQuery: '{query}'")
            hits = await self.search_with_relevance_filter(query, min_relevance=50, top_k=3)
            if not hits:
                print("  No results found above threshold.")
            else:
                for i, hit in enumerate(hits, 1):
                    print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] "
                          f"{hit['relevance']:.0f}% | Speaker {hit['speaker']}")
                    print(f"     \"{hit['text']}\"")

    async def interactive_search(self):
        """
        Mode 2: Prompt the user for queries until they type 'quit'.
        """
        print("\n=== Interactive Transcript Search ===")
        print("Type your query, or 'quit' to exit.")
        
        while True:
            q = input("\n> ").strip()
            if not q or q.lower() in {"quit", "exit", "q"}:
                print("Goodbye.")
                break
                
            print("Searching...")
            
            # Try semantic search (now includes fallback to basic search)
            hits = await self.semantic_search(q, top_k=5)
            
            if hits:
                search_type = hits[0].get("search_type", "unknown") if hits else "unknown"
                print(f"Found {len(hits)} results using {search_type} search:")
                for i, hit in enumerate(hits, 1):
                    relevance = hit.get("relevance", 0)
                    if relevance > 0:
                        print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] {relevance:.0f}% | Speaker {hit['speaker']}")
                    else:
                        print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] | Speaker {hit['speaker']}")
                    print(f"     \"{hit['text']}\"")
            else:
                print("No results found.")

    async def get_mars_colony_content(self):
        """
        Mode 3: Comprehensive search for 'Mars colony' using multiple strategies.
        """
        print("\n=== Comprehensive Mars Colony Search ===")
        strategies = [
            ('Exact phrase', '"Mars colony"'),
            ('Keyword: Mars', 'Mars'),
            ('Keyword: multiplanetary', 'multiplanetary'),
            ('Phrase: going to Mars', '"going to Mars"'),
            ('Keyword: space', 'space'),
            ('Keyword: planet', 'planet'),
            ('Keyword: SpaceX', 'SpaceX'),
            ('Keyword: Tesla', 'Tesla'),
            ('Keyword: technology', 'technology'),
            ('Keyword: future', 'future')
        ]

        all_hits = []
        for name, query in strategies:
            print(f"\nStrategy: {name} → {query}")
            # Try semantic search first
            hits = await self.semantic_search(query, top_k=5)
            if not hits:
                # Fallback to basic search with relevance filter
                for threshold in [70, 50, 30]:
                    hits = await self.search_with_relevance_filter(query, min_relevance=threshold, top_k=5)
                    if hits:
                        print(f"  Found {len(hits)} results (threshold: {threshold}%)")
                        all_hits.extend(hits)
                        break
                else:
                    print("  No results found.")
            else:
                print(f"  Found {len(hits)} semantic results")
                all_hits.extend(hits)

        # Dedupe by start_at, keep the best relevance
        unique = {}
        for hit in all_hits:
            key = hit["start_at"]
            relevance = hit.get("relevance", 0)
            if key not in unique or relevance > unique[key].get("relevance", 0):
                unique[key] = hit

        print(f"\nSummary: {len(unique)} unique segments found.\nTop 5 by relevance:")
        sorted_hits = sorted(unique.values(), key=lambda x: x.get("relevance", 0), reverse=True)[:5]
        for i, hit in enumerate(sorted_hits, 1):
            relevance = hit.get("relevance", 0)
            print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] "
                  f"{relevance:.0f}% | Speaker {hit['speaker']}")
            print(f"     \"{hit['text']}\"")

    async def run_semantic_search_demo(self):
        """
        Mode 4: Demo semantic search capabilities
        """
        print("\n=== Semantic Search Demo ===")
        print("Testing various types of semantic queries")
        
        test_queries = [
            ("Basic Search", "AI technology"),
            ("Question Search", "What does Elon Musk think about AI?"),
            ("Semantic Search", "SpaceX Mars colonization plans"),
            ("Question Search", "How does Tesla approach manufacturing?"),
            ("Semantic Search", "future of humanity and sustainability"),
            ("Question Search", "What are the challenges of sustainable energy?")
        ]
        
        for test_name, query in test_queries:
            print(f"\n{'='*60}")
            print(f"Testing: {test_name}")
            print(f"Query: '{query}'")
            print(f"{'='*60}")
            
            try:
                hits = await self.semantic_search(query, top_k=3)
                
                if hits:
                    print(f"\n=== {test_name}: '{query}' ===")
                    for i, hit in enumerate(hits, 1):
                        print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] | Speaker {hit['speaker']}")
                        print(f"     \"{hit['text']}\"")
                else:
                    print(f"\n=== {test_name}: '{query}' ===")
                    print("  No semantic results found.")
                    
            except Exception as e:
                print(f"\n=== {test_name}: '{query}' ===")
                print(f"Error in {test_name.lower()}: {e}")

async def main():
    searcher = AsyncSearchFilter()
    print("Choose mode:")
    print("  1) Run sample tests")
    print("  2) Interactive search")
    print("  3) Comprehensive search demo")
    print("  4) Semantic search demo")
    
    choice = input("\nEnter 1-4: ").strip()

    if choice == "1":
        await searcher.run_sample_tests()
    elif choice == "2":
        await searcher.interactive_search()
    elif choice == "3":
        await searcher.get_mars_colony_content()
    elif choice == "4":
        await searcher.run_semantic_search_demo()
    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    asyncio.run(main())
 