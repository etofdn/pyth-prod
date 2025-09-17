#!/usr/bin/env python3
"""
ai_search_enhanced.py

Enhanced Azure AI Search implementation with:
1) Semantic search with AI ranking
2) Vector search over embedded content
3) Hybrid search combining both approaches

Requirements:
- Azure AI Search service with semantic search enabled
- Vector search capabilities
- OpenAI embeddings for vector search

Usage:
    python ai_search_enhanced.py
"""

import os
import json
from typing import List, Dict, Optional
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import Vector
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    SemanticConfiguration,
    SemanticField,
    SemanticSettings
)

class EnhancedAISearch:
    def __init__(self):
        # Azure Search credentials
        self.search_endpoint = "https://aisearchscripts.search.windows.net"
        self.search_key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
        self.index_name = "transcripts-enhanced"
        
        # Initialize clients
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(self.search_key)
        )
        
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=AzureKeyCredential(self.search_key)
        )
    
    def create_enhanced_index(self):
        """
        Create an enhanced index with semantic search and vector search capabilities
        """
        print("Creating enhanced index with semantic and vector search...")
        
        # Define fields with vector search support
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SimpleField(name="parentDocId", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="transaction_key", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="request_id", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="sha256", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="created", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SimpleField(name="duration", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SimpleField(name="channels", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
            SimpleField(name="Filename", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="videolink", type=SearchFieldDataType.String, filterable=True),
            
            # Searchable fields for semantic search
            SearchableField(name="flattened_transcript", type=SearchFieldDataType.String, 
                          analyzer_name="en.lucene", semantic_configuration_name="default"),
            SearchableField(name="text", type=SearchFieldDataType.String, 
                          analyzer_name="en.lucene", semantic_configuration_name="default"),
            
            # Vector fields for vector search
            SimpleField(name="text_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
                       vector_search_dimensions=1536, vector_search_profile_name="my-vector-config"),
            
            SimpleField(name="speaker", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
            SimpleField(name="start_offset", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SimpleField(name="end_offset", type=SearchFieldDataType.Double, filterable=True, sortable=True),
            SimpleField(name="start_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
            SimpleField(name="end_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        ]
        
        # Vector search configuration
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="my-vector-config",
                    algorithm_configuration_name="my-algorithms-config"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="my-algorithms-config"
                )
            ]
        )
        
        # Semantic search configuration
        semantic_settings = SemanticSettings(
            configurations=[
                SemanticConfiguration(
                    name="default",
                    prioritized_fields=SemanticField(
                        title_field=SemanticField(name="text"),
                        content_fields=[
                            SemanticField(name="text"),
                            SemanticField(name="flattened_transcript")
                        ],
                        keywords_fields=[
                            SemanticField(name="Filename"),
                            SemanticField(name="speaker")
                        ]
                    )
                )
            ]
        )
        
        # Create the enhanced index
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_settings=semantic_settings
        )
        
        try:
            self.index_client.create_or_update_index(index)
            print(f"Successfully created enhanced index: {self.index_name}")
            return True
        except Exception as e:
            print(f"Error creating index: {e}")
            return False
    
    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Perform semantic search with AI ranking
        """
        print(f"\n=== Semantic Search: '{query}' ===")
        
        try:
            results = self.search_client.search(
                search_text=query,
                select=["text", "start_at", "end_at", "speaker", "Filename", "@search.score", "@search.reranker_score"],
                semantic_configuration_name="default",
                query_type="semantic",
                query_language="en-us",
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
            return []
    
    def vector_search(self, query_vector: List[float], top_k: int = 5) -> List[Dict]:
        """
        Perform vector search over embedded content
        Note: This requires pre-computed embeddings in the index
        """
        print(f"\n=== Vector Search ===")
        
        try:
            vector = Vector(value=query_vector, k=top_k, fields="text_vector")
            
            results = self.search_client.search(
                search_text="",
                vectors=[vector],
                select=["text", "start_at", "end_at", "speaker", "Filename", "@search.score"],
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
                    "vector_score": result.get("@search.score", 0)
                }
                hits.append(hit)
            
            return hits
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []
    
    def hybrid_search(self, query: str, query_vector: Optional[List[float]] = None, top_k: int = 5) -> List[Dict]:
        """
        Perform hybrid search combining semantic and vector search
        """
        print(f"\n=== Hybrid Search: '{query}' ===")
        
        try:
            search_params = {
                "search_text": query,
                "select": ["text", "start_at", "end_at", "speaker", "Filename", "@search.score", "@search.reranker_score"],
                "semantic_configuration_name": "default",
                "query_type": "semantic",
                "query_language": "en-us",
                "top": top_k
            }
            
            # Add vector search if vector is provided
            if query_vector:
                vector = Vector(value=query_vector, k=top_k, fields="text_vector")
                search_params["vectors"] = [vector]
            
            results = self.search_client.search(**search_params)
            
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
            print(f"Error in hybrid search: {e}")
            return []
    
    def display_results(self, results: List[Dict], search_type: str):
        """
        Display search results in a formatted way
        """
        if not results:
            print(f"No results found for {search_type}")
            return
        
        print(f"\n{search_type} Results ({len(results)} found):")
        print("-" * 80)
        
        for i, hit in enumerate(results, 1):
            print(f"{i}. [{hit['start_at']}–{hit['end_at']}] Speaker {hit['speaker']}")
            print(f"   Score: {hit.get('search_score', hit.get('vector_score', 0)):.3f}")
            print(f"   Text: \"{hit['text']}\"")
            print()
    
    def run_demo(self):
        """
        Run a demonstration of all search capabilities
        """
        print("=== Enhanced AI Search Demo ===")
        
        # Test queries
        queries = [
            "AI and technology",
            "SpaceX Mars colony", 
            "Tesla manufacturing",
            "future of humanity",
            "sustainable energy"
        ]
        
        for query in queries:
            print(f"\n{'='*60}")
            print(f"Testing query: '{query}'")
            print('='*60)
            
            # Semantic search
            semantic_results = self.semantic_search(query)
            self.display_results(semantic_results, "Semantic Search")
            
            # Note: Vector search requires pre-computed embeddings
            # For demo purposes, we'll skip vector search unless embeddings are available
            print("Vector search requires pre-computed embeddings in the index.")
            print("To enable vector search, you need to:")
            print("1. Generate embeddings for your text content")
            print("2. Upload documents with vector fields populated")
            print("3. Use OpenAI or other embedding service")

def main():
    searcher = EnhancedAISearch()
    
    print("Enhanced AI Search Options:")
    print("1) Create enhanced index (semantic + vector)")
    print("2) Run semantic search demo")
    print("3) Run hybrid search demo")
    
    choice = input("\nEnter 1-3: ").strip()
    
    if choice == "1":
        searcher.create_enhanced_index()
    elif choice == "2":
        searcher.run_demo()
    elif choice == "3":
        print("Hybrid search demo - requires both semantic and vector capabilities")
        searcher.run_demo()
    else:
        print("Invalid choice. Running demo...")
        searcher.run_demo()

if __name__ == "__main__":
    main() 