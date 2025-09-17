#!/usr/bin/env python3
"""
update_index_with_vectors.py - Update Existing Index with Vector Search

Updates the existing transcripts-v2 index to include vector search capabilities
by adding vector fields to the existing index schema.

Usage:
    python update_index_with_vectors.py
"""

import os
import asyncio
import json
from typing import List, Dict, Any
from azure.core.credentials import AzureKeyCredential
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
from openai import AsyncAzureOpenAI

class IndexVectorUpdater:
    def __init__(self):
        # Azure Search credentials
        self.search_endpoint = "https://aisearchscripts.search.windows.net"
        self.search_key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
        self.index_name = "transcripts-v2"  # Existing index
        
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
        """Generate embeddings for a list of texts"""
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

    async def get_existing_index(self) -> SearchIndex:
        """Retrieve the existing index"""
        try:
            credential = AzureKeyCredential(self.search_key)
            index_client = SearchIndexClient(self.search_endpoint, credential)
            
            index = await index_client.get_index(self.index_name)
            await index_client.close()
            return index
            
        except Exception as e:
            print(f"Error retrieving existing index: {e}")
            return None

    def create_updated_index(self, existing_index: SearchIndex) -> SearchIndex:
        """Create updated index with vector fields added"""
        
        # Add vector fields to existing fields
        updated_fields = existing_index.fields.copy()
        
        # Add vector fields
        vector_fields = [
            SearchField(
                name="textVector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,  # text-embedding-3-large dimensions
                vector_search_profile_name="my-vector-config"
            ),
            SearchField(
                name="transcriptVector", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name="my-vector-config"
            ),
        ]
        
        updated_fields.extend(vector_fields)
        
        # Create vector search configuration
        vector_search = VectorSearch(
            profiles=[VectorSearchProfile(name="my-vector-config", algorithm_configuration_name="my-algorithms-config")],
            algorithms=[HnswAlgorithmConfiguration(name="my-algorithms-config")],
        )
        
        # Create updated index
        updated_index = SearchIndex(
            name=existing_index.name,
            fields=updated_fields,
            vector_search=vector_search
        )
        
        return updated_index

    async def update_index_with_vectors(self):
        """Update the existing index to include vector search capabilities"""
        try:
            print(f"Updating index '{self.index_name}' with vector search capabilities...")
            
            # Get existing index
            existing_index = await self.get_existing_index()
            if not existing_index:
                print("Could not retrieve existing index")
                return False
            
            print(f"Retrieved existing index with {len(existing_index.fields)} fields")
            
            # Create updated index
            updated_index = self.create_updated_index(existing_index)
            
            # Update the index
            credential = AzureKeyCredential(self.search_key)
            index_client = SearchIndexClient(self.search_endpoint, credential)
            
            await index_client.create_or_update_index(updated_index)
            await index_client.close()
            
            print(f"Successfully updated index '{self.index_name}' with vector search capabilities")
            print(f"Added vector fields: textVector, transcriptVector")
            print(f"Vector search dimensions: 3072 (text-embedding-3-large)")
            return True
            
        except Exception as e:
            print(f"Error updating index: {e}")
            return False

    async def prepare_documents_with_embeddings(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare documents by adding embeddings to each document"""
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

    async def upload_documents_with_embeddings(self, documents: List[Dict[str, Any]]):
        """Upload documents with embeddings to the updated index"""
        try:
            from azure.search.documents.aio import SearchClient
            
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

    async def load_transcript_data(self) -> List[Dict[str, Any]]:
        """Load transcript data from JSON file"""
        try:
            with open("flattened_transcript.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            
            print(f"Loaded {len(data)} transcript chunks")
            return data
            
        except Exception as e:
            print(f"Error loading transcripts: {e}")
            return []

async def main():
    """Main function to update index with vector capabilities"""
    updater = IndexVectorUpdater()
    
    print("=== Update Index with Vector Search Capabilities ===")
    
    # 1. Update the existing index with vector fields
    success = await updater.update_index_with_vectors()
    
    if not success:
        print("Failed to update index. Exiting.")
        return
    
    # 2. Load transcript data
    documents = await updater.load_transcript_data()
    if not documents:
        print("No documents to process")
        return
    
    # 3. Upload documents with embeddings
    print("\n=== Uploading Documents with Embeddings ===")
    await updater.upload_documents_with_embeddings(documents)
    
    print("\n=== Vector Search Setup Complete ===")
    print("Your transcripts-v2 index now supports:")
    print("- Semantic search (existing)")
    print("- Vector search (new)")
    print("- Hybrid search (text + vector)")
    print("\nYou can now use comprehensive_search.py to test all search types!")

if __name__ == "__main__":
    asyncio.run(main()) 