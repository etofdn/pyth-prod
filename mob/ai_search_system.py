# AI Search System for Document Retrieval and Analysis
# Handles: PDF, Word, Excel, PowerPoint, Text files
# Standardized JSON structure with 4-5 keys for consistent ingestion
# Performance target: ~3 seconds per query

import os
import json
import time
from datetime import datetime
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    ComplexField,
    CorsOptions
)

class AISearchSystem:
    """
    Complete AI Search System for Document Retrieval and Analysis
    Supports: SharePoint + Blob Storage → MD/JSON → Vector Database → AI Search → Retrieval & Analysis
    """
    
    def __init__(self):
        # Azure Search Configuration
        self.endpoint = "https://aisearchscripts.search.windows.net"
        self.key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
        self.index_name = "ai-document-search-v1"
        
        # Initialize clients
        self.credential = AzureKeyCredential(self.key)
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
        self.index_client = SearchIndexClient(self.endpoint, self.credential)
        
        # Performance tracking
        self.query_times = []
        
    def create_schema(self):
        """Create custom schema with standardized 4-5 JSON keys"""
        print("Creating AI Search Schema...")
        
        fields = [
            # Required: Document key
            SimpleField(
                name="id", 
                type=SearchFieldDataType.String, 
                key=True,
                filterable=True,
                sortable=True
            ),
            
            # Standardized Key 1: Content (Main searchable content)
            SearchableField(
                name="content", 
                type=SearchFieldDataType.String,
                analyzer_name="standard",
                filterable=True,
                sortable=True
            ),
            
            # Standardized Key 2: Metadata (File info, structure)
            ComplexField(
                name="metadata",
                fields=[
                    SimpleField(name="file_type", type=SearchFieldDataType.String, filterable=True, sortable=True, facetable=True),
                    SimpleField(name="file_name", type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name="file_size", type=SearchFieldDataType.Int64, filterable=True, sortable=True, facetable=True),
                    SimpleField(name="page_count", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
                    SimpleField(name="language", type=SearchFieldDataType.String, filterable=True, sortable=True, facetable=True),
                    SimpleField(name="author", type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name="title", type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, sortable=True, facetable=True),
                ]
            ),
            
            # Standardized Key 3: Source (Data source info)
            ComplexField(
                name="source",
                fields=[
                    SimpleField(name="data_source", type=SearchFieldDataType.String, filterable=True, sortable=True, facetable=True),  # SharePoint/Blob
                    SimpleField(name="container", type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name="path", type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name="url", type=SearchFieldDataType.String, filterable=True, sortable=True),
                ]
            ),
            
            # Standardized Key 4: Timestamp (Processing and creation times)
            ComplexField(
                name="timestamp",
                fields=[
                    SimpleField(name="created_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True, facetable=True),
                    SimpleField(name="modified_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                    SimpleField(name="processed_date", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                ]
            ),
            
            # Standardized Key 5: Transcript (For audio/video content with timestamps)
            ComplexField(
                name="transcript",
                fields=[
                    SearchableField(name="text", type=SearchFieldDataType.String, filterable=True, sortable=True),
                    SimpleField(name="start_time", type=SearchFieldDataType.Double, filterable=True, sortable=True),
                    SimpleField(name="end_time", type=SearchFieldDataType.Double, filterable=True, sortable=True),
                    SimpleField(name="speaker", type=SearchFieldDataType.String, filterable=True, sortable=True),
                ]
            ),
            
            # Additional searchable fields
            SearchableField(name="summary", type=SearchFieldDataType.String, analyzer_name="standard", filterable=True, sortable=True),
            SearchableField(name="keywords", type=SearchFieldDataType.String, analyzer_name="standard", filterable=True, sortable=True),
            
            # Performance and status fields
            SimpleField(name="is_active", type=SearchFieldDataType.Boolean, filterable=True, sortable=True, facetable=True),
            SimpleField(name="priority", type=SearchFieldDataType.Int32, filterable=True, sortable=True, facetable=True),
        ]
        
        cors_options = CorsOptions(allowed_origins=["*"], max_age_in_seconds=300)
        
        search_index = SearchIndex(
            name=self.index_name,
            fields=fields,
            cors_options=cors_options
        )
        
        try:
            result = self.index_client.create_index(search_index)
            print(f" AI Search Schema created successfully")
            print(f"Standardized Keys: id, content, metadata, source, timestamp, transcript")
            print(f"Supported File Types: PDF, Word, Excel, PowerPoint, Text")
            return True
        except Exception as e:
            print(f" Error creating schema: {e}")
            return False
    
    def ingest_document(self, document_data):
        """
        Ingest MD/JSON document into AI Search
        Expected JSON structure with standardized keys
        """
        try:
            # Validate document structure
            required_keys = ["id", "content", "metadata", "source", "timestamp"]
            for key in required_keys:
                if key not in document_data:
                    raise ValueError(f"Missing required key: {key}")
            
            # Upload document
            result = self.search_client.upload_documents([document_data])
            print(f" Document ingested: {document_data['id']}")
            return True
            
        except Exception as e:
            print(f" Error ingesting document: {e}")
            return False
    
    def search_documents(self, query, filters=None, top_k=10, min_relevance=50):
        """
        Search documents with performance tracking
        Target: ~3 seconds per query
        """
        start_time = time.time()
        
        try:
            # Build search parameters
            search_params = {
                "search_text": query,
                "top": top_k,
                "include_total_count": True
            }
            
            # Add filters if provided
            if filters:
                search_params["filter"] = filters
            
            # Execute search
            results = self.search_client.search(**search_params)
            
            # Process results
            processed_results = []
            for result in results:
                # Calculate relevance score
                content_lower = result.get("content", "").lower()
                query_terms = query.lower().split()
                found_terms = [term for term in query_terms if term in content_lower]
                relevance = len(found_terms) / len(query_terms) * 100 if query_terms else 0
                
                if relevance >= min_relevance:
                    processed_results.append({
                        "relevance": relevance,
                        "found_terms": found_terms,
                        "id": result.get("id"),
                        "content": result.get("content"),
                        "metadata": result.get("metadata"),
                        "source": result.get("source"),
                        "timestamp": result.get("timestamp"),
                        "transcript": result.get("transcript"),
                        "summary": result.get("summary"),
                        "keywords": result.get("keywords")
                    })
            
            # Sort by relevance
            processed_results.sort(key=lambda x: x["relevance"], reverse=True)
            
            # Track performance
            query_time = time.time() - start_time
            self.query_times.append(query_time)
            
            print(f"🔍 Search completed in {query_time:.2f}s")
            print(f"📊 Found {len(processed_results)} results (min relevance: {min_relevance}%)")
            
            return processed_results
            
        except Exception as e:
            print(f" Error searching documents: {e}")
            return []
    
    def search_with_transcript_timestamps(self, query, speaker_filter=None):
        """
        Search with transcript timestamps for audio/video content
        """
        start_time = time.time()
        
        try:
            # Build filter for transcript search
            filters = []
            if speaker_filter:
                filters.append(f"transcript/speaker eq '{speaker_filter}'")
            
            filter_string = " and ".join(filters) if filters else None
            
            results = self.search_documents(query, filters=filter_string, top_k=20)
            
            # Process transcript results
            transcript_results = []
            for result in results:
                transcript = result.get("transcript")
                if transcript and isinstance(transcript, dict):
                    transcript_results.append({
                        "relevance": result["relevance"],
                        "text": transcript.get("text"),
                        "start_time": transcript.get("start_time"),
                        "end_time": transcript.get("end_time"),
                        "speaker": transcript.get("speaker"),
                        "source": result.get("source"),
                        "metadata": result.get("metadata")
                    })
            
            query_time = time.time() - start_time
            print(f"🎤 Transcript search completed in {query_time:.2f}s")
            print(f"📝 Found {len(transcript_results)} transcript segments")
            
            return transcript_results
            
        except Exception as e:
            print(f" Error searching transcripts: {e}")
            return []
    
    def get_performance_stats(self):
        """Get performance statistics"""
        if not self.query_times:
            return "No queries executed yet"
        
        avg_time = sum(self.query_times) / len(self.query_times)
        max_time = max(self.query_times)
        min_time = min(self.query_times)
        
        return {
            "total_queries": len(self.query_times),
            "average_time": f"{avg_time:.2f}s",
            "max_time": f"{max_time:.2f}s",
            "min_time": f"{min_time:.2f}s",
            "target_met": avg_time <= 3.0
        }
    
    def create_sample_document(self, file_type="pdf"):
        """Create a sample document for testing"""
        return {
            "id": f"doc-{int(time.time())}",
            "content": "This is a sample document content for testing AI search functionality.",
            "metadata": {
                "file_type": file_type,
                "file_name": f"sample.{file_type}",
                "file_size": 1024,
                "page_count": 1,
                "language": "en",
                "author": "Test Author",
                "title": "Sample Document",
                "category": "test"
            },
            "source": {
                "data_source": "blob_storage",
                "container": "documents",
                "path": f"/samples/sample.{file_type}",
                "url": f"https://example.com/sample.{file_type}"
            },
            "timestamp": {
                "created_date": datetime.now().isoformat(),
                "modified_date": datetime.now().isoformat(),
                "processed_date": datetime.now().isoformat()
            },
            "transcript": {
                "text": "Sample transcript text with timestamps",
                "start_time": 0.0,
                "end_time": 10.0,
                "speaker": "Speaker 1"
            },
            "summary": "This is a sample document for testing purposes.",
            "keywords": "sample, test, document, ai, search",
            "is_active": True,
            "priority": 1
        }

def main():
    """Main function to test the AI Search System"""
    print("🚀 AI Search System - Document Retrieval and Analysis")
    print("=" * 60)
    
    # Initialize system
    ai_search = AISearchSystem()
    
    # Create schema
    if ai_search.create_schema():
        print("\n Schema created successfully")
    else:
        print("\n⚠️ Schema may already exist, continuing...")
    
    # Test with sample document
    print("\n📄 Testing with sample document...")
    sample_doc = ai_search.create_sample_document("pdf")
    ai_search.ingest_document(sample_doc)
    
    # Test search functionality
    print("\n🔍 Testing search functionality...")
    results = ai_search.search_documents("sample document", top_k=5)
    
    # Test transcript search
    print("\n🎤 Testing transcript search...")
    transcript_results = ai_search.search_with_transcript_timestamps("sample transcript")
    
    # Performance stats
    print("\n📊 Performance Statistics:")
    stats = ai_search.get_performance_stats()
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    main() 