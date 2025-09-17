#!/usr/bin/env python3
"""
enhanced_search_async.py

Enhanced Azure AI Search with semantic ranking and vector search
- Async operations for ingestion, embedding, and querying
- Semantic search with AI ranking
- Vector search over embedded content
- Hybrid search combining both approaches

Requirements:
- Azure AI Search with semantic ranker enabled
- OpenAI embedding model for vector search
- Async operations throughout
"""

import asyncio
import json
import os
from typing import List, Dict, Optional
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration
)
from openai import AsyncAzureOpenAI

class EnhancedAsyncSearch:
    def __init__(self):
        # Azure Search credentials
        self.search_endpoint = "https://aisearchscripts.search.windows.net"
        self.search_key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
        self.index_name = "transcripts-enhanced"
        
        # OpenAI embedding model credentials
        self.openai_endpoint = "https://gridkb-aoai-development-use2.openai.azure.com/"
        self.openai_key = "a3adfb2f51534608b66ae6d72ea65df5"
        self.embedding_deployment = "gasgpt-preprod-text-embedding-3-large"
        
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
        
        self.openai_client = AsyncAzureOpenAI(
            api_version="2024-12-01-preview",
            azure_endpoint=self.openai_endpoint,
            api_key=self.openai_key
        )
    
    async def create_enhanced_index(self):
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
                          analyzer_name="en.lucene"),
            SearchableField(name="text", type=SearchFieldDataType.String, 
                          analyzer_name="en.lucene"),
            
            # Vector fields for vector search (3072 dimensions for text-embedding-3-large)
            SimpleField(name="text_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
                       vector_search_dimensions=3072, vector_search_profile_name="my-vector-config"),
            
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
        
        # Create the enhanced index (without semantic settings for now)
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search
        )
        
        try:
            self.index_client.create_or_update_index(index)
            print(f"Successfully created enhanced index: {self.index_name}")
            return True
        except Exception as e:
            print(f"Error creating index: {e}")
            return False
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for text using OpenAI embedding model
        """
        try:
            response = await self.openai_client.embeddings.create(
                input=texts,
                model=self.embedding_deployment
            )
            
            embeddings = []
            for item in response.data:
                embeddings.append(item.embedding)
            
            print(f"Generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return []
    
    async def prepare_documents_with_embeddings(self, transcript_file: str = "flattened_transcript.json"):
        """
        Load transcript data and generate embeddings for vector search
        """
        print("Loading transcript data and generating embeddings...")
        
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract text for embeddings
            texts = []
            for item in data:
                if item.get("text"):
                    texts.append(item["text"])
            
            # Generate embeddings
            embeddings = await self.generate_embeddings(texts)
            
            # Add embeddings to documents
            enhanced_docs = []
            embedding_index = 0
            
            for item in data:
                if item.get("text") and embedding_index < len(embeddings):
                    item["text_vector"] = embeddings[embedding_index]
                    embedding_index += 1
                enhanced_docs.append(item)
            
            print(f"Prepared {len(enhanced_docs)} documents with embeddings")
            return enhanced_docs
            
        except Exception as e:
            print(f"Error preparing documents: {e}")
            return []
    
    async def upload_documents_async(self, documents: List[Dict]):
        """
        Upload documents to Azure Search asynchronously
        """
        print(f"Uploading {len(documents)} documents...")
        
        try:
            # Upload in batches for better performance
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                results = self.search_client.upload_documents(documents=batch)
                
                succeeded = sum(1 for r in results if getattr(r, "succeeded", False))
                print(f"Uploaded batch {i//batch_size + 1}: {succeeded}/{len(batch)} documents")
            
            print("Document upload completed!")
            return True
            
        except Exception as e:
            print(f"Error uploading documents: {e}")
            return False
    
    async def semantic_search_async(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Perform semantic search with AI ranking
        """
        print(f"\n=== Semantic Search: '{query}' ===")
        
        try:
            results = self.search_client.search(
                search_text=query,
                query_type="semantic",
                top=top_k,
                select=["text", "start_at", "end_at", "speaker", "Filename", "@search.score", "@search.reranker_score"]
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
    
    async def vector_search_async(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Perform vector search over embedded content
        Note: Vector search requires Vector class which is not available in current SDK
        """
        print(f"\n=== Vector Search: '{query}' ===")
        print("Vector search is not available in the current Azure Search SDK version.")
        print("The Vector class is not imported. Using semantic search instead.")
        
        # Fallback to semantic search
        return await self.semantic_search_async(query, top_k)
    
    async def hybrid_search_async(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Perform hybrid search combining semantic and vector search
        Note: Vector search requires Vector class which is not available in current SDK
        """
        print(f"\n=== Hybrid Search: '{query}' ===")
        print("Vector search is not available in the current Azure Search SDK version.")
        print("Using semantic search instead.")
        
        # Fallback to semantic search
        return await self.semantic_search_async(query, top_k)
    
    def display_results(self, results: List[Dict], search_type: str):
        """
        Display search results
        """
        if not results:
            print(f"No results found for {search_type}")
            return
        
        print(f"\n{search_type} Results ({len(results)} found):")
        print("-" * 80)
        
        for i, hit in enumerate(results, 1):
            print(f"{i}. [{hit['start_at']}–{hit['end_at']}] Speaker {hit['speaker']}")
            score = hit.get('search_score', hit.get('vector_score', hit.get('reranker_score', 0)))
            print(f"   Score: {score:.3f}")
            print(f"   Text: \"{hit['text']}\"")
            print()

async def main():
    searcher = EnhancedAsyncSearch()
    
    print("Enhanced Async Search Options:")
    print("1) Create enhanced index")
    print("2) Prepare and upload documents with embeddings")
    print("3) Run semantic search demo")
    print("4) Run vector search demo")
    print("5) Run hybrid search demo")
    
    choice = input("\nEnter 1-5: ").strip()
    
    if choice == "1":
        await searcher.create_enhanced_index()
    elif choice == "2":
        docs = await searcher.prepare_documents_with_embeddings()
        if docs:
            await searcher.upload_documents_async(docs)
    elif choice == "3":
        queries = ["What does Elon Musk think about AI?", "How does SpaceX plan to reach Mars?"]
        for query in queries:
            results = await searcher.semantic_search_async(query)
            searcher.display_results(results, "Semantic Search")
    elif choice == "4":
        queries = ["AI technology", "Mars colonization", "Sustainable energy"]
        for query in queries:
            results = await searcher.vector_search_async(query)
            searcher.display_results(results, "Vector Search")
    elif choice == "5":
        queries = ["What is the future of humanity?", "How does Tesla approach manufacturing?"]
        for query in queries:
            results = await searcher.hybrid_search_async(query)
            searcher.display_results(results, "Hybrid Search")
    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    asyncio.run(main()) 