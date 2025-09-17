#!/usr/bin/env python3
"""
comprehensive_index_creation.py - Create Comprehensive Index with All Features

Creates a comprehensive Azure AI Search index with:
- Semantic search capabilities
- Vector search with embeddings
- Enhanced text search
- All fields optimized for retrieval

Usage:
    python comprehensive_index_creation.py
"""

import asyncio
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
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch
)

class ComprehensiveIndexCreator:
    def __init__(self):
        # Azure Search credentials
        self.search_endpoint = "https://aisearchscripts.search.windows.net"
        self.search_key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
        self.index_name = "transcripts-v2"
        self.semantic_config_name = "transcript-semantic-config"

    def create_comprehensive_index(self) -> SearchIndex:
        """Create the comprehensive index with all features"""
        
        # Define all fields including vector fields
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
            
            # Searchable content fields for semantic search
            SearchableField(name="flattened_transcript", type=SearchFieldDataType.String, 
                           analyzer_name="en.lucene", retrievable=True),
            SearchableField(name="text", type=SearchFieldDataType.String, 
                           analyzer_name="en.lucene", retrievable=True),
            
            # Speaker and timing information
            SimpleField(name="speaker", type=SearchFieldDataType.Int32, filterable=True, sortable=True, retrievable=True),
            SimpleField(name="start_offset", type=SearchFieldDataType.Double, filterable=True, sortable=True, retrievable=True),
            SimpleField(name="end_offset", type=SearchFieldDataType.Double, filterable=True, sortable=True, retrievable=True),
            SimpleField(name="start_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True, retrievable=True),
            SimpleField(name="end_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True, retrievable=True),
            
            # Vector fields for vector search
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
                vector_search_dimensions=3072,  # text-embedding-3-large dimensions
                vector_search_profile_name="my-vector-config"
            ),
        ]
        
        # Vector search configuration
        vector_search = VectorSearch(
            profiles=[VectorSearchProfile(name="my-vector-config", algorithm_configuration_name="my-algorithms-config")],
            algorithms=[HnswAlgorithmConfiguration(name="my-algorithms-config")],
        )
        
        # Semantic search configuration
        semantic_config = SemanticConfiguration(
            name=self.semantic_config_name,
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="text"),
                keywords_fields=[
                    SemanticField(field_name="flattened_transcript"),
                    SemanticField(field_name="Filename")
                ],
                content_fields=[
                    SemanticField(field_name="text"),
                    SemanticField(field_name="flattened_transcript")
                ]
            )
        )
        
        semantic_search = SemanticSearch(configurations=[semantic_config])
        
        # Create comprehensive index
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        return index

    async def create_or_update_index(self):
        """Create or update the comprehensive index"""
        try:
            credential = AzureKeyCredential(self.search_key)
            index_client = SearchIndexClient(self.search_endpoint, credential)
            
            # Check if index exists
            try:
                existing_index = await index_client.get_index(self.index_name)
                print(f"Index '{self.index_name}' exists. Updating with comprehensive features...")
            except:
                print(f"Creating new comprehensive index '{self.index_name}'...")
            
            # Create comprehensive index
            comprehensive_index = self.create_comprehensive_index()
            
            # Create or update the index
            result = await index_client.create_or_update_index(comprehensive_index)
            await index_client.close()
            
            print("Comprehensive index created/updated successfully!")
            print(f"   - Semantic search: Enabled with config '{self.semantic_config_name}'")
            print(f"   - Vector search: Enabled with 3072-dimension embeddings")
            print(f"   - All fields: Retrievable and optimized")
            print(f"   - Index name: {self.index_name}")
            
            return True
            
        except Exception as e:
            print(f"Error creating/updating index: {e}")
            return False

    async def run_index_creation(self):
        """Run the index creation process"""
        print("Starting Comprehensive Index Creation")
        print("=" * 60)
        
        print("\nStep 1: Creating/Updating Comprehensive Index")
        print("-" * 50)
        success = await self.create_or_update_index()
        
        if success:
            print("\n" + "=" * 60)
            print("COMPREHENSIVE INDEX CREATION COMPLETE")
            print("=" * 60)
            print(f"Index '{self.index_name}' is now ready with:")
            print(f"   - Semantic search capabilities")
            print(f"   - Vector search with embeddings")
            print(f"   - Enhanced text search")
            print(f"   - All fields optimized for retrieval")
            print("\nYou can now use upload_transcripts.py for data ingestion!")
        else:
            print("\nIndex creation failed. Please check the error messages above.")

async def main():
    """Main function"""
    creator = ComprehensiveIndexCreator()
    await creator.run_index_creation()

if __name__ == "__main__":
    asyncio.run(main())
