#!/usr/bin/env python3
"""
comprehensive_search.py - Comprehensive Search System

Combines semantic search, vector search, and hybrid search capabilities.
Features:
- Semantic search with AI ranking
- Vector search with embeddings
- Hybrid search (text + vector)
- Interactive search interface
- Async operations throughout

Usage:
    python comprehensive_search.py
"""

import os
import asyncio
import json
from typing import List, Dict, Any
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AsyncAzureOpenAI

class ComprehensiveSearch:
    def __init__(self):
        # Azure Search credentials
        self.search_endpoint = "https://aisearchscripts.search.windows.net"
        self.search_key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
        
        # Index names - both use the same updated index
        self.semantic_index = "transcripts-v2"
        self.vector_index = "transcripts-v2"  # Use the same index that has vector capabilities
        
        # Semantic configuration
        self.semantic_config_name = "transcript-semantic-config"
        
        # Azure OpenAI credentials for embeddings
        self.openai_endpoint = "https://gridkb-aoai-development-use2.openai.azure.com/"
        self.openai_key = "a3adfb2f51534608b66ae6d72ea65df5"
        self.embedding_deployment = "gasgpt-preprod-text-embedding-3-large"
        
        # Initialize OpenAI client
        self.openai_client = AsyncAzureOpenAI(
            api_version="2024-12-01-preview",
            azure_endpoint=self.openai_endpoint,
            api_key=self.openai_key
        )

    async def get_client(self, index_name: str):
        """Get async search client for specified index"""
        credential = AzureKeyCredential(self.search_key)
        return SearchClient(
            endpoint=self.search_endpoint,
            index_name=index_name,
            credential=credential
        )

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            response = await self.openai_client.embeddings.create(
                input=texts,
                model=self.embedding_deployment
            )
            
            embeddings = []
            for item in response.data:
                embeddings.append(item.embedding)
            
            return embeddings
            
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return []

    async def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Semantic search with AI ranking - enhanced with flattened transcript context"""
        client = await self.get_client(self.semantic_index)
        try:
            results = await client.search(
                search_text=query,
                query_type="semantic",
                semantic_configuration_name=self.semantic_config_name,
                top=top_k,
                select=[
                    "text", "start_at", "end_at", "speaker", "videolink",
                    "Filename", "transaction_key", "parentDocId", "start_offset",
                    "end_offset", "channels", "flattened_transcript"
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
                        "flattened_transcript": result.get("flattened_transcript"),
                        "search_type": "semantic"
                    })
            
            return hits
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []
        finally:
            await client.close()

    async def enhanced_context_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Enhanced search that leverages both text and flattened_transcript for better context"""
        client = await self.get_client(self.semantic_index)
        try:
            # First, try semantic search on the main text
            results = await client.search(
                search_text=query,
                query_type="semantic",
                semantic_configuration_name=self.semantic_config_name,
                top=top_k,
                select=[
                    "text", "start_at", "end_at", "speaker", "videolink",
                    "Filename", "transaction_key", "parentDocId", "start_offset",
                    "end_offset", "channels", "flattened_transcript"
                ]
            )
            
            hits = []
            async for result in results:
                if result.get("text"):
                    # Calculate context relevance using flattened_transcript
                    context_relevance = self._calculate_context_relevance(query, result.get("flattened_transcript", ""))
                    
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
                        "flattened_transcript": result.get("flattened_transcript"),
                        "context_relevance": context_relevance,
                        "search_type": "enhanced_context"
                    })
            
            # Sort by context relevance if available
            hits.sort(key=lambda x: x.get("context_relevance", 0), reverse=True)
            return hits
            
        except Exception as e:
            print(f"Error in enhanced context search: {e}")
            return []
        finally:
            await client.close()

    def _calculate_context_relevance(self, query: str, context: str) -> float:
        """Calculate relevance score based on context from flattened_transcript"""
        if not context:
            return 0.0
        
        query_terms = set(query.lower().split())
        context_terms = set(context.lower().split())
        
        # Calculate term overlap
        overlap = len(query_terms.intersection(context_terms))
        total_terms = len(query_terms)
        
        if total_terms == 0:
            return 0.0
        
        # Base relevance score
        relevance = overlap / total_terms
        
        # Bonus for longer context (more comprehensive)
        context_length_bonus = min(len(context.split()) / 100, 0.2)  # Max 20% bonus
        
        return min(relevance + context_length_bonus, 1.0)

    async def vector_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Vector search using embeddings"""
        client = None
        try:
            # Generate embedding for the query
            query_embeddings = await self.generate_embeddings([query])
            if not query_embeddings:
                return []
            
            query_vector = query_embeddings[0]
            
            # Create vector query
            vector_query = VectorizedQuery(
                vector=query_vector, 
                k_nearest_neighbors=top_k, 
                fields="textVector,transcriptVector"
            )
            
            # Perform search
            client = await self.get_client(self.vector_index)
            
            results = await client.search(
                search_text="",  # Pure vector search
                vector_queries=[vector_query],
                select=[
                    "text", "start_at", "end_at", "speaker", "videolink", 
                    "Filename", "transaction_key", "parentDocId", "start_offset", 
                    "end_offset", "channels", "flattened_transcript"
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
                        "flattened_transcript": result.get("flattened_transcript"),
                        "search_type": "vector"
                    })
            
            return hits
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []
        finally:
            if client:
                await client.close()

    async def semantic_vector_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Combined semantic and vector search with AI ranking"""
        client = None
        try:
            # Generate embedding for the query
            query_embeddings = await self.generate_embeddings([query])
            if not query_embeddings:
                return []
            
            query_vector = query_embeddings[0]
            
            # Create vector query
            vector_query = VectorizedQuery(
                vector=query_vector, 
                k_nearest_neighbors=top_k, 
                fields="textVector,transcriptVector"
            )
            
            # Perform semantic + vector search
            client = await self.get_client(self.vector_index)
            
            results = await client.search(
                search_text=query,  # Text search
                query_type="semantic",  # Enable semantic ranking
                semantic_configuration_name=self.semantic_config_name,
                vector_queries=[vector_query],  # Vector search
                select=[
                    "text", "start_at", "end_at", "speaker", "videolink", 
                    "Filename", "transaction_key", "parentDocId", "start_offset", 
                    "end_offset", "channels", "flattened_transcript"
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
                        "flattened_transcript": result.get("flattened_transcript"),
                        "search_type": "semantic_vector"
                    })
            
            return hits
            
        except Exception as e:
            print(f"Error in semantic-vector search: {e}")
            return []
        finally:
            if client:
                await client.close()

    async def hybrid_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Hybrid search combining text and vector search"""
        client = None
        try:
            # Generate embedding for the query
            query_embeddings = await self.generate_embeddings([query])
            if not query_embeddings:
                return []
            
            query_vector = query_embeddings[0]
            
            # Create vector query
            vector_query = VectorizedQuery(
                vector=query_vector, 
                k_nearest_neighbors=top_k, 
                fields="textVector,transcriptVector"
            )
            
            # Perform hybrid search
            client = await self.get_client(self.vector_index)
            
            results = await client.search(
                search_text=query,  # Text search
                vector_queries=[vector_query],  # Vector search
                select=[
                    "text", "start_at", "end_at", "speaker", "videolink", 
                    "Filename", "transaction_key", "parentDocId", "start_offset", 
                    "end_offset", "channels", "flattened_transcript"
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
                        "flattened_transcript": result.get("flattened_transcript"),
                        "search_type": "hybrid"
                    })
            
            return hits
            
        except Exception as e:
            print(f"Error in hybrid search: {e}")
            return []
        finally:
            if client:
                await client.close()

    async def basic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Basic text search without semantic ranking"""
        client = await self.get_client(self.semantic_index)
        try:
            results = await client.search(
                search_text=query,
                top=top_k,
                select=[
                    "text", "start_at", "end_at", "speaker", "videolink",
                    "Filename", "transaction_key", "parentDocId", "start_offset",
                    "end_offset", "channels", "flattened_transcript"
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
                        "flattened_transcript": result.get("flattened_transcript"),
                        "search_type": "basic"
                    })
            
            return hits
            
        except Exception as e:
            print(f"Error in basic search: {e}")
            return []
        finally:
            await client.close()

    def display_results(self, results: List[Dict[str, Any]], search_type: str):
        """Display search results in a formatted way with enhanced context"""
        if not results:
            print(f"No {search_type} results found.")
            return
        
        print(f"\n=== {search_type.title()} Search Results ({len(results)} found) ===")
        for i, hit in enumerate(results, 1):
            # Show context relevance if available
            relevance_info = ""
            if hit.get('context_relevance') is not None:
                relevance_info = f" | Context Relevance: {hit['context_relevance']:.2f}"
            
            print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] | Speaker {hit['speaker']}{relevance_info}")
            print(f"     Text: \"{hit['text']}\"")
            
            # Show flattened transcript if available and different from text
            if hit.get('flattened_transcript') and hit['flattened_transcript'] != hit['text']:
                # Truncate if too long
                transcript = hit['flattened_transcript']
                if len(transcript) > 200:
                    transcript = transcript[:200] + "..."
                print(f"     Context: \"{transcript}\"")
            
            # Show additional metadata if available
            if hit.get('Filename'):
                print(f"     File: {hit['Filename']}")
            if hit.get('transaction_key'):
                print(f"     Transaction: {hit['transaction_key']}")
            print()

    async def run_comprehensive_search(self, query: str):
        """Run all search types and compare results"""
        print(f"\n{'='*60}")
        print(f"Comprehensive Search for: '{query}'")
        print(f"{'='*60}")
        
        # Run all search types
        semantic_results = await self.semantic_search(query, top_k=3)
        vector_results = await self.vector_search(query, top_k=3)
        semantic_vector_results = await self.semantic_vector_search(query, top_k=3)
        hybrid_results = await self.hybrid_search(query, top_k=3)
        basic_results = await self.basic_search(query, top_k=3)
        enhanced_context_results = await self.enhanced_context_search(query, top_k=3)
        
        # Display results
        self.display_results(semantic_results, "Semantic")
        self.display_results(vector_results, "Vector")
        self.display_results(semantic_vector_results, "Semantic+Vector")
        self.display_results(hybrid_results, "Hybrid")
        self.display_results(basic_results, "Basic")
        self.display_results(enhanced_context_results, "Enhanced Context")

    async def interactive_search(self):
        """Interactive search interface"""
        print("\n=== Comprehensive Search Interface ===")
        print("Search Types Available:")
        print("  1) Semantic Search (AI-powered ranking)")
        print("  2) Vector Search (embedding-based)")
        print("  3) Semantic+Vector Search (AI ranking + embeddings)")
        print("  4) Hybrid Search (text + vector)")
        print("  5) Basic Search (text only)")
        print("  6) Enhanced Context Search (text + flattened_transcript)")
        print("  7) Comprehensive Search (all types)")
        print("  8) Exit")
        
        while True:
            # Use asyncio.to_thread for non-blocking input
            choice = await asyncio.to_thread(input, "\nEnter search type (1-7): ")
            choice = choice.strip()
            
            if choice == "8":
                print("Goodbye!")
                break
            
            query = await asyncio.to_thread(input, "Enter your search query: ")
            query = query.strip()
            if not query:
                print("Please enter a query.")
                continue
            
            print("Searching...")
            
            if choice == "1":
                results = await self.semantic_search(query, top_k=5)
                self.display_results(results, "Semantic")
            elif choice == "2":
                results = await self.vector_search(query, top_k=5)
                self.display_results(results, "Vector")
            elif choice == "3":
                results = await self.semantic_vector_search(query, top_k=5)
                self.display_results(results, "Semantic+Vector")
            elif choice == "4":
                results = await self.hybrid_search(query, top_k=5)
                self.display_results(results, "Hybrid")
            elif choice == "5":
                results = await self.basic_search(query, top_k=5)
                self.display_results(results, "Basic")
            elif choice == "6":
                results = await self.enhanced_context_search(query, top_k=5)
                self.display_results(results, "Enhanced Context")
            elif choice == "7":
                await self.run_comprehensive_search(query)
            else:
                print("Invalid choice. Please enter 1-8.")

    async def run_demo_searches(self):
        """Run demo searches to showcase all capabilities"""
        demo_queries = [
            "AI technology and its impact on society",
            "SpaceX Mars colonization plans and challenges",
            "Tesla manufacturing approach and innovation",
            "sustainable energy challenges and solutions",
            "future of humanity and technology"
        ]
        
        print("\n=== Demo: Comprehensive Search Capabilities ===")
        
        for query in demo_queries:
            await self.run_comprehensive_search(query)
            await asyncio.to_thread(input, "\nPress Enter to continue to next query...")

async def main():
    """Main function"""
    search = ComprehensiveSearch()
    
    print("=== Comprehensive Search System ===")
    print("Choose mode:")
    print("  1) Interactive search")
    print("  2) Demo searches")
    
    choice = await asyncio.to_thread(input, "\nEnter 1-2: ")
    choice = choice.strip()
    
    if choice == "1":
        await search.interactive_search()
    elif choice == "2":
        await search.run_demo_searches()
    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    asyncio.run(main()) 