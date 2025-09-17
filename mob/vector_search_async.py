#!/usr/bin/env python3
"""
vector_search_async.py - Async Vector Search with Embeddings

Implements vector search over embedded transcript content using Azure OpenAI embeddings.
Features:
- Async embedding generation
- Vector field creation and indexing
- Vector search queries
- Hybrid search (vector + semantic)
- Batch processing for large datasets

Usage:
    python vector_search_async.py
"""

import os
import asyncio
import json
from typing import List, Dict, Any
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)
from azure.search.documents.models import VectorizedQuery
from openai import AsyncAzureOpenAI

class AsyncVectorSearch:
    def __init__(self):
        # Azure Search credentials
        self.search_endpoint = "https://aisearchscripts.search.windows.net"
        self.search_key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
        self.index_name = "transcripts-vector"
        
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

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using Azure OpenAI
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

    def create_vector_index(self) -> SearchIndex:
        """
        Create search index with vector search capabilities
        """
        fields = [
            # Core identification fields
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True, retrievable=True),
            SimpleField(name="parentDocId", type=SearchFieldDataType.String, filterable=True, retrievable=True),
            
            # Metadata fields
            SimpleField(name="transaction_key", type=SearchFieldDataType.String, filterable=True, retrievable=True),
            SimpleField(name="request_id", type=SearchFieldDataType.String, filterable=True, retrievable=True),
            SimpleField(name="sha256", type=SearchFieldDataType.String, filterable=True, retrievable=True),
            SimpleField(name="created", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True, retrievable=True),
            SimpleField(name="duration", type=SearchFieldDataType.Double, filterable=True, sortable=True, retrievable=True),
            SimpleField(name="channels", type=SearchFieldDataType.Int32, filterable=True, sortable=True, retrievable=True),
            
            # File information
            SimpleField(name="Filename", type=SearchFieldDataType.String, filterable=True, retrievable=True),
            SimpleField(name="videolink", type=SearchFieldDataType.String, filterable=True, retrievable=True),
            
            # Searchable content fields
            SearchableField(name="flattened_transcript", type=SearchFieldDataType.String, 
                          analyzer_name="en.lucene", retrievable=True),
            SearchableField(name="text", type=SearchFieldDataType.String, 
                          analyzer_name="en.lucene", retrievable=True),
            
            # Vector fields for embeddings
            SearchField(
                name="textVector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,  # text-embedding-3-large dimensions
                vector_search_profile_name="my-vector-config",
                retrievable=True
            ),
            SearchField(
                name="transcriptVector", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name="my-vector-config",
                retrievable=True
            ),
            
            # Speaker and timing information
            SimpleField(name="speaker", type=SearchFieldDataType.Int32, filterable=True, sortable=True, retrievable=True),
            SimpleField(name="start_offset", type=SearchFieldDataType.Double, filterable=True, sortable=True, retrievable=True),
            SimpleField(name="end_offset", type=SearchFieldDataType.Double, filterable=True, sortable=True, retrievable=True),
            SimpleField(name="start_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True, retrievable=True),
            SimpleField(name="end_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True, retrievable=True),
        ]

        # Vector search configuration
        vector_search = VectorSearch(
            profiles=[VectorSearchProfile(name="my-vector-config", algorithm_configuration_name="my-algorithms-config")],
            algorithms=[HnswAlgorithmConfiguration(name="my-algorithms-config")],
        )

        return SearchIndex(name=self.index_name, fields=fields, vector_search=vector_search)

    async def create_or_update_index(self):
        """
        Create or update the search index with vector capabilities
        """
        try:
            credential = AzureKeyCredential(self.search_key)
            index_client = SearchIndexClient(self.search_endpoint, credential)
            
            index = self.create_vector_index()
            await index_client.create_or_update_index(index)
            print(f"Created/updated index '{self.index_name}' with vector search capabilities")
            
        except Exception as e:
            print(f"Error creating index: {e}")

    async def prepare_documents_with_embeddings(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prepare documents by adding embeddings to each document
        """
        print(f"Preparing {len(documents)} documents with embeddings...")
        
        # Extract texts for embedding generation
        texts_for_embedding = []
        for doc in documents:
            # Use text field for embedding, fallback to flattened_transcript
            text_content = doc.get("text", "") or doc.get("flattened_transcript", "")
            if text_content:
                texts_for_embedding.append(text_content)
            else:
                texts_for_embedding.append("")  # Empty string for documents without text
        
        # Generate embeddings
        embeddings = await self.generate_embeddings(texts_for_embedding)
        
        # Add embeddings to documents
        prepared_docs = []
        for i, doc in enumerate(documents):
            if i < len(embeddings) and embeddings[i]:
                doc["textVector"] = embeddings[i]
                doc["transcriptVector"] = embeddings[i]  # Use same embedding for both fields
            else:
                doc["textVector"] = [0.0] * 3072  # Zero vector as fallback
                doc["transcriptVector"] = [0.0] * 3072
            prepared_docs.append(doc)
        
        print(f"Prepared {len(prepared_docs)} documents with embeddings")
        return prepared_docs

    async def upload_documents(self, documents: List[Dict[str, Any]]):
        """
        Upload documents with embeddings to the search index
        """
        try:
            credential = AzureKeyCredential(self.search_key)
            client = SearchClient(self.search_endpoint, self.index_name, credential)
            
            # Prepare documents with embeddings
            prepared_docs = await self.prepare_documents_with_embeddings(documents)
            
            # Upload in batches
            batch_size = 100
            for i in range(0, len(prepared_docs), batch_size):
                batch = prepared_docs[i:i + batch_size]
                await client.upload_documents(documents=batch)
                print(f"Uploaded batch {i//batch_size + 1}/{(len(prepared_docs) + batch_size - 1)//batch_size}")
            
            await client.close()
            print(f"Successfully uploaded {len(prepared_docs)} documents with embeddings")
            
        except Exception as e:
            print(f"Error uploading documents: {e}")

    async def vector_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform vector search using embeddings
        """
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
            credential = AzureKeyCredential(self.search_key)
            client = SearchClient(self.search_endpoint, self.index_name, credential)
            
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
            
            await client.close()
            return hits
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []

    async def hybrid_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and semantic search
        """
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
            credential = AzureKeyCredential(self.search_key)
            client = SearchClient(self.search_endpoint, self.index_name, credential)
            
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
            
            await client.close()
            return hits
            
        except Exception as e:
            print(f"Error in hybrid search: {e}")
            return []

    async def load_and_process_transcripts(self) -> List[Dict[str, Any]]:
        """
        Load transcript data and prepare for vector indexing
        """
        try:
            with open("flattened_transcript.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            
            print(f"Loaded {len(data)} transcript chunks")
            return data
            
        except Exception as e:
            print(f"Error loading transcripts: {e}")
            return []

async def main():
    """
    Main function to demonstrate vector search capabilities
    """
    vector_search = AsyncVectorSearch()
    
    print("=== Vector Search Setup ===")
    
    # 1. Create/update index with vector capabilities
    await vector_search.create_or_update_index()
    
    # 2. Load and process transcript data
    documents = await vector_search.load_and_process_transcripts()
    if not documents:
        print("No documents to process")
        return
    
    # 3. Upload documents with embeddings
    await vector_search.upload_documents(documents)
    
    # 4. Test vector search
    print("\n=== Testing Vector Search ===")
    test_queries = [
        "AI technology and its impact",
        "SpaceX Mars colonization plans", 
        "Tesla manufacturing approach",
        "sustainable energy challenges",
        "future of humanity"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Vector search
        vector_results = await vector_search.vector_search(query, top_k=3)
        print(f"Vector Search Results ({len(vector_results)} found):")
        for i, hit in enumerate(vector_results, 1):
            print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] | Speaker {hit['speaker']}")
            print(f"     \"{hit['text']}\"")
        
        # Hybrid search
        hybrid_results = await vector_search.hybrid_search(query, top_k=3)
        print(f"Hybrid Search Results ({len(hybrid_results)} found):")
        for i, hit in enumerate(hybrid_results, 1):
            print(f"  {i}. [{hit['start_at']}–{hit['end_at']}] | Speaker {hit['speaker']}")
            print(f"     \"{hit['text']}\"")

if __name__ == "__main__":
    asyncio.run(main()) 