#!/usr/bin/env python3
"""
transcript_search.py

Enhanced retrieval script for your flattened "transcripts" index.
Supports four modes:
  1) Sample tests
  2) Interactive search
  3) Comprehensive Mars colony search
  4) Semantic search with AI ranking

Usage:
    python transcript_search.py
"""

import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

class SearchFilter:
    def __init__(self):
        # Either set these as environment vars or hard-code them here
        self.search_endpoint = "https://aisearchscripts.search.windows.net"
        self.search_key      = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
        self.index_name      = "transcripts-v2"
        self.client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(self.search_key)
        )

    def search_with_relevance_filter(self, query, min_relevance=50, top_k=10):
        """
        Perform a search, then post-filter by simple term-overlap relevance.
        """
        terms = query.lower().split()
        
        try:
            results = self.client.search(
                search_text=query,
                top=top_k,
                select=["text", "start_at", "end_at", "speaker", "videolink", "Filename"]
            )

            filtered = []
            for r in results:
                # Skip results with no text content
                if not r.get("text"):
                    continue
                    
                txt = r["text"].lower()
                found = [t for t in terms if t in txt]
                relevance = len(found) / len(terms) * 100 if terms else 0
                if relevance >= min_relevance:
                    filtered.append({
                        "relevance":  relevance,
                        "found_terms": found,
                        "text":        r["text"],
                        "start_at":    r["start_at"],
                        "end_at":      r["end_at"],
                        "speaker":     r["speaker"],
                        "video_link":  r["videolink"],
                        "filename":    r["Filename"]
                    })

            # sort descending by relevance
            filtered.sort(key=lambda x: x["relevance"], reverse=True)
            return filtered
            
        except Exception as e:
            print(f"Error in search: {e}")
            print("This might be due to network connectivity issues or index configuration.")
            return []

    def semantic_search(self, query, top_k=10):
        """
        Perform semantic search with AI ranking using Microsoft's semantic ranker
        Based on: https://learn.microsoft.com/en-us/azure/search/semantic-search-overview
        """
        print(f"\n=== Semantic Search: '{query}' ===")
        
        try:
            results = self.client.search(
                search_text=query,
                select=["text", "start_at", "end_at", "speaker", "Filename", "@search.score", "@search.reranker_score"],
                semantic_configuration_name="default",
                query_type="semantic",
                top=top_k
            )
            
            hits = []
            for result in results:
                hit = {
                    "text": result.get("text", ""),
                    "start_at": result.get("start_at"),
                    "end_at": result.get("end_at"),
                    "speaker": result.get("speaker"),
                    "filename": result.get("Filename"),
                    "search_score": result.get("@search.score", 0),
                    "reranker_score": result.get("@search.reranker_score", 0)
                }
                hits.append(hit)
            
            return hits
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            print("Note: Semantic search requires semantic configuration in the index")
            print("Falling back to regular search...")
            return self.search_with_relevance_filter(query, min_relevance=30, top_k=top_k)

    def display_semantic_results(self, results):
        """
        Display semantic search results with reranker scores
        """
        if not results:
            print("No semantic search results found.")
            return
        
        print(f"\nSemantic Search Results ({len(results)} found):")
        print("-" * 80)
        
        for i, hit in enumerate(results, 1):
            print(f"{i}. [{hit['start_at']}–{hit['end_at']}] Speaker {hit['speaker']}")
            print(f"   Reranker Score: {hit.get('reranker_score', 0):.1f}/4.0")
            print(f"   Search Score: {hit.get('search_score', 0):.3f}")
            print(f"   Text: \"{hit['text']}\"")
            print()

    def run_sample_tests(self):
        """
        Mode 1: Run a few preset queries and display their results.
        """
        print("\n=== Sample Test Queries ===")
        for query in ["AI and technology", "SpaceX Mars colony", "Tesla manufacturing"]:
            print(f"\nQuery: '{query}'")
            hits = self.search_with_relevance_filter(query, min_relevance=50, top_k=3)
            if not hits:
                print("  No results found above threshold.")
            else:
                for i, hit in enumerate(hits, 1):
                    print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] "
                          f"{hit['relevance']:.0f}% | Speaker {hit['speaker']}")
                    print(f"     \"{hit['text']}\"")

    def interactive_search(self):
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
            # Relax thresholds if no hits
            for thresh in (50, 30, 10):
                hits = self.search_with_relevance_filter(q, min_relevance=thresh, top_k=5)
                if hits:
                    for i, hit in enumerate(hits, 1):
                        print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] "
                              f"{hit['relevance']:.0f}% | Speaker {hit['speaker']}")
                        print(f"     \"{hit['text']}\"")
                    break
            else:
                print("No results found.")

    def get_mars_colony_content(self):
        """
        Mode 3: Comprehensive search for 'Mars colony' using multiple strategies.
        """
        print("\n=== Comprehensive Mars Colony Search ===")
        strategies = [
            ('Exact phrase',       '"Mars colony"'),
            ('Keyword: Mars',      'Mars'),
            ('Keyword: multiplanetary', 'multiplanetary'),
            ('Phrase: going to Mars',  '"going to Mars"'),
            ('Keyword: space',     'space'),
            ('Keyword: planet',    'planet'),
            ('Keyword: SpaceX',    'SpaceX'),
            ('Keyword: Tesla',     'Tesla'),
            ('Keyword: technology', 'technology'),
            ('Keyword: future',    'future')
        ]

        all_hits = []
        for name, query in strategies:
            print(f"\nStrategy: {name} → {query}")
            # Try with different relevance thresholds
            for threshold in [70, 50, 30]:
                hits = self.search_with_relevance_filter(query, min_relevance=threshold, top_k=5)
                if hits:
                    print(f"  Found {len(hits)} results (threshold: {threshold}%)")
                    for hit in hits:
                        all_hits.append(hit)
                    break
            else:
                print("  No results found.")

        # Dedupe by start_at, keep the best relevance
        unique = {}
        for hit in all_hits:
            key = hit["start_at"]
            if key not in unique or hit["relevance"] > unique[key]["relevance"]:
                unique[key] = hit

        print(f"\nSummary: {len(unique)} unique segments found.\nTop 5 by relevance:")
        for i, hit in enumerate(sorted(unique.values(), key=lambda x: x["relevance"], reverse=True)[:5], 1):
            print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] "
                  f"{hit['relevance']:.0f}% | Speaker {hit['speaker']}")
            print(f"     \"{hit['text']}\"")

    def run_semantic_search_demo(self):
        """
        Mode 4: Demonstrate semantic search with AI ranking
        """
        print("\n=== Semantic Search Demo ===")
        print("Testing semantic ranking with AI-powered reranking")
        print("Based on Microsoft's semantic ranker technology")
        
        queries = [
            "What does Elon Musk think about AI?",
            "How does SpaceX plan to reach Mars?",
            "What are the challenges of sustainable energy?",
            "What is the future of humanity?",
            "How does Tesla approach manufacturing?"
        ]
        
        for query in queries:
            print(f"\n{'='*60}")
            print(f"Testing semantic search: '{query}'")
            print('='*60)
            
            # Try semantic search (includes fallback to regular search)
            semantic_results = self.semantic_search(query)
            self.display_semantic_results(semantic_results)

def main():
    searcher = SearchFilter()
    print("Choose mode:")
    print("  1) Run sample tests")
    print("  2) Interactive search")
    print("  3) Mars colony comprehensive search")
    print("  4) Semantic search with AI ranking")
    choice = input("\nEnter 1-4: ").strip()

    if choice == "1":
        searcher.run_sample_tests()
    elif choice == "2":
        searcher.interactive_search()
    elif choice == "3":
        searcher.get_mars_colony_content()
    elif choice == "4":
        searcher.run_semantic_search_demo()
    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    main()
