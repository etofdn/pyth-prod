# AI Search Engine
# Unified search engine combining all 5 search key functionalities
# ID, Content, Metadata, Source, and Timestamp search capabilities

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# Import configuration
from config import Config

class AISearchEngine:
    """
    Unified AI Search Engine
    Combines all 5 search key functionalities:
    - ID Search (Key 1)
    - Content Search (Key 2) 
    - Metadata Search (Key 3)
    - Source Search (Key 4)
    - Timestamp Search (Key 5)
    """
    
    def __init__(self):
        """Initialize the search engine with Azure Search configuration"""
        config = Config.get_search_config()
        self.search_endpoint = config['search_endpoint']
        self.search_key = config['search_key']
        self.index_name = config['index_name']
        self.credential = AzureKeyCredential(self.search_key)
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
    
    # ============================================================================
    # SEARCH KEY 1: ID SEARCH
    # ============================================================================
    
    def search_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Search for document by exact ID match"""
        try:
            start_time = time.time()
            
            results = self.search_client.search(
                search_text="",
                filter=f"id eq '{document_id}'",
                top=1,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"]
            )
            
            for result in results:
                search_time = time.time() - start_time
                print(f" ID search completed in {search_time:.3f}s")
                print(f"   Found document: {result['id']}")
                return dict(result)
            
            print(f" Document with ID '{document_id}' not found")
            return None
            
        except Exception as e:
            print(f" Error in ID search: {e}")
            return None
    
    def search_by_id_list(self, document_ids: List[str]) -> List[Dict[str, Any]]:
        """Search for multiple documents by ID list"""
        try:
            start_time = time.time()
            documents = []
            
            id_filters = [f"id eq '{doc_id}'" for doc_id in document_ids]
            combined_filter = " or ".join(id_filters)
            
            results = self.search_client.search(
                search_text="",
                filter=combined_filter,
                top=len(document_ids),
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"]
            )
            
            for result in results:
                documents.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Multi-ID search completed in {search_time:.3f}s")
            print(f"   Requested: {len(document_ids)} documents")
            print(f"   Found: {len(documents)} documents")
            
            return documents
            
        except Exception as e:
            print(f" Error in multi-ID search: {e}")
            return []
    
    def search_by_id_pattern(self, id_pattern: str) -> List[Dict[str, Any]]:
        """Search for documents by ID pattern (wildcard)"""
        try:
            start_time = time.time()
            documents = []
            
            results = self.search_client.search(
                search_text=f"id:{id_pattern}",
                top=50,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"]
            )
            
            for result in results:
                documents.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" ID pattern search completed in {search_time:.3f}s")
            print(f"   Pattern: {id_pattern}")
            print(f"   Found: {len(documents)} documents")
            
            return documents
            
        except Exception as e:
            print(f" Error in ID pattern search: {e}")
            return []
    
    # ============================================================================
    # SEARCH KEY 2: CONTENT SEARCH
    # ============================================================================
    
    def search_by_content(self, query: str, top: int = 10, min_relevance: float = 0.0) -> List[Dict[str, Any]]:
        """Search document content with full-text search"""
        try:
            start_time = time.time()
            results = []
            
            search_results = self.search_client.search(
                search_text=query,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["@search.score desc"]
            )
            
            for result in search_results:
                score = result.get('@search.score', 0.0)
                if score >= min_relevance:
                    doc = dict(result)
                    doc['relevance_score'] = score
                    results.append(doc)
            
            search_time = time.time() - start_time
            print(f" Content search completed in {search_time:.3f}s")
            print(f"   Query: '{query}'")
            print(f"   Found: {len(results)} documents")
            print(f"   Min relevance: {min_relevance}")
            
            return results
            
        except Exception as e:
            print(f" Error in content search: {e}")
            return []
    
    def search_by_content_with_filters(self, query: str, filters: Dict[str, Any], top: int = 10) -> List[Dict[str, Any]]:
        """Search content with additional filters"""
        try:
            start_time = time.time()
            results = []
            
            filter_parts = []
            for key, value in filters.items():
                if isinstance(value, str):
                    filter_parts.append(f"{key} eq '{value}'")
                elif isinstance(value, bool):
                    filter_parts.append(f"{key} eq {str(value).lower()}")
                else:
                    filter_parts.append(f"{key} eq {value}")
            
            filter_string = " and ".join(filter_parts) if filter_parts else None
            
            search_results = self.search_client.search(
                search_text=query,
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["@search.score desc"]
            )
            
            for result in search_results:
                doc = dict(result)
                doc['relevance_score'] = result.get('@search.score', 0.0)
                results.append(doc)
            
            search_time = time.time() - start_time
            print(f" Filtered content search completed in {search_time:.3f}s")
            print(f"   Query: '{query}'")
            print(f"   Filters: {filters}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in filtered content search: {e}")
            return []
    
    def search_by_phrases(self, phrases: List[str], top: int = 10) -> List[Dict[str, Any]]:
        """Search for specific phrases in content"""
        try:
            start_time = time.time()
            all_results = []
            
            for phrase in phrases:
                results = self.search_client.search(
                    search_text=f'"{phrase}"',
                    top=top,
                    select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                    order_by=["@search.score desc"]
                )
                
                for result in results:
                    doc = dict(result)
                    doc['relevance_score'] = result.get('@search.score', 0.0)
                    doc['matched_phrase'] = phrase
                    all_results.append(doc)
            
            unique_results = {}
            for result in all_results:
                doc_id = result['id']
                if doc_id not in unique_results or result['relevance_score'] > unique_results[doc_id]['relevance_score']:
                    unique_results[doc_id] = result
            
            final_results = sorted(unique_results.values(), key=lambda x: x['relevance_score'], reverse=True)
            
            search_time = time.time() - start_time
            print(f" Phrase search completed in {search_time:.3f}s")
            print(f"   Phrases: {phrases}")
            print(f"   Found: {len(final_results)} unique documents")
            
            return final_results[:top]
            
        except Exception as e:
            print(f" Error in phrase search: {e}")
            return []
    
    # ============================================================================
    # SEARCH KEY 3: METADATA SEARCH
    # ============================================================================
    
    def search_by_file_type(self, file_type: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by file type"""
        try:
            start_time = time.time()
            results = []
            
            filter_string = f"metadata_file_type eq '{file_type}'"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" File type search completed in {search_time:.3f}s")
            print(f"   File type: {file_type}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in file type search: {e}")
            return []
    
    def search_by_author(self, author: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by author"""
        try:
            start_time = time.time()
            results = []
            
            filter_string = f"metadata_author eq '{author}'"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Author search completed in {search_time:.3f}s")
            print(f"   Author: {author}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in author search: {e}")
            return []
    
    def search_by_language(self, language: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by language"""
        try:
            start_time = time.time()
            results = []
            
            filter_string = f"metadata_language eq '{language}'"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Language search completed in {search_time:.3f}s")
            print(f"   Language: {language}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in language search: {e}")
            return []
    
    def search_by_category(self, category: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by category"""
        try:
            start_time = time.time()
            results = []
            
            filter_string = f"metadata_category eq '{category}'"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Category search completed in {search_time:.3f}s")
            print(f"   Category: {category}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in category search: {e}")
            return []
    
    def search_by_metadata_filters(self, filters: Dict[str, Any], top: int = 10) -> List[Dict[str, Any]]:
        """Search documents with multiple metadata filters"""
        try:
            start_time = time.time()
            results = []
            
            filter_parts = []
            for key, value in filters.items():
                if isinstance(value, str):
                    filter_parts.append(f"metadata_{key} eq '{value}'")
                elif isinstance(value, (int, float)):
                    filter_parts.append(f"metadata_{key} eq {value}")
                elif isinstance(value, bool):
                    filter_parts.append(f"metadata_{key} eq {str(value).lower()}")
            
            filter_string = " and ".join(filter_parts) if filter_parts else None
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Metadata filters search completed in {search_time:.3f}s")
            print(f"   Filters: {filters}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in metadata filters search: {e}")
            return []
    
    # ============================================================================
    # SEARCH KEY 4: SOURCE SEARCH
    # ============================================================================
    
    def search_by_data_source(self, data_source: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by data source (SharePoint, Blob Storage, etc.)"""
        try:
            start_time = time.time()
            results = []
            
            filter_string = f"source_data_source eq '{data_source}'"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Data source search completed in {search_time:.3f}s")
            print(f"   Data source: {data_source}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in data source search: {e}")
            return []
    
    def search_by_container(self, container: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by container name"""
        try:
            start_time = time.time()
            results = []
            
            filter_string = f"source_container eq '{container}'"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Container search completed in {search_time:.3f}s")
            print(f"   Container: {container}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in container search: {e}")
            return []
    
    def search_by_path_pattern(self, path_pattern: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by path pattern"""
        try:
            start_time = time.time()
            results = []
            
            search_results = self.search_client.search(
                search_text=f"source_path:{path_pattern}",
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Path pattern search completed in {search_time:.3f}s")
            print(f"   Path pattern: {path_pattern}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in path pattern search: {e}")
            return []
    
    def search_by_sharepoint_site(self, site: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by SharePoint site"""
        try:
            start_time = time.time()
            results = []
            
            filter_string = f"source_sharepoint_site eq '{site}'"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" SharePoint site search completed in {search_time:.3f}s")
            print(f"   Site: {site}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in SharePoint site search: {e}")
            return []
    
    def search_by_blob_container(self, blob_container: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by Blob Storage container"""
        try:
            start_time = time.time()
            results = []
            
            filter_string = f"source_blob_container eq '{blob_container}'"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Blob container search completed in {search_time:.3f}s")
            print(f"   Blob container: {blob_container}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in blob container search: {e}")
            return []
    
    # ============================================================================
    # SEARCH KEY 5: TIMESTAMP SEARCH
    # ============================================================================
    
    def search_by_date_range(self, start_date: str, end_date: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by date range"""
        try:
            start_time = time.time()
            results = []
            
            filter_string = f"timestamp_processed_date ge {start_date} and timestamp_processed_date le {end_date}"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Date range search completed in {search_time:.3f}s")
            print(f"   Date range: {start_date} to {end_date}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in date range search: {e}")
            return []
    
    def search_by_created_date(self, start_date: str, end_date: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by creation date range"""
        try:
            start_time = time.time()
            results = []
            
            filter_string = f"timestamp_created_date ge {start_date} and timestamp_created_date le {end_date}"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_created_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Creation date search completed in {search_time:.3f}s")
            print(f"   Date range: {start_date} to {end_date}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in creation date search: {e}")
            return []
    
    def search_by_modified_date(self, start_date: str, end_date: str, top: int = 10) -> List[Dict[str, Any]]:
        """Search documents by modification date range"""
        try:
            start_time = time.time()
            results = []
            
            filter_string = f"timestamp_modified_date ge {start_date} and timestamp_modified_date le {end_date}"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_modified_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Modification date search completed in {search_time:.3f}s")
            print(f"   Date range: {start_date} to {end_date}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in modification date search: {e}")
            return []
    
    def search_recent_documents(self, days: int = 7, top: int = 10) -> List[Dict[str, Any]]:
        """Search for documents processed in the last N days"""
        try:
            start_time = time.time()
            results = []
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            start_date_str = start_date.isoformat()
            end_date_str = end_date.isoformat()
            
            filter_string = f"timestamp_processed_date ge {start_date_str} and timestamp_processed_date le {end_date_str}"
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                results.append(dict(result))
            
            search_time = time.time() - start_time
            print(f" Recent documents search completed in {search_time:.3f}s")
            print(f"   Last {days} days")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in recent documents search: {e}")
            return []
    
    # ============================================================================
    # COMBINED SEARCH METHODS
    # ============================================================================
    
    def combined_search(self, 
                       content_query: str = None,
                       metadata_filters: Dict[str, Any] = None,
                       source_filters: Dict[str, Any] = None,
                       date_range: Dict[str, str] = None,
                       top: int = 10) -> List[Dict[str, Any]]:
        """
        Combined search using multiple criteria
        """
        try:
            start_time = time.time()
            
            # Build combined filter
            filter_parts = []
            
            if metadata_filters:
                for key, value in metadata_filters.items():
                    if isinstance(value, str):
                        filter_parts.append(f"metadata_{key} eq '{value}'")
                    elif isinstance(value, (int, float)):
                        filter_parts.append(f"metadata_{key} eq {value}")
                    elif isinstance(value, bool):
                        filter_parts.append(f"metadata_{key} eq {str(value).lower()}")
            
            if source_filters:
                for key, value in source_filters.items():
                    if isinstance(value, str):
                        filter_parts.append(f"source_{key} eq '{value}'")
                    elif isinstance(value, (int, float)):
                        filter_parts.append(f"source_{key} eq {value}")
                    elif isinstance(value, bool):
                        filter_parts.append(f"source_{key} eq {str(value).lower()}")
            
            if date_range:
                start_date = date_range.get('start')
                end_date = date_range.get('end')
                if start_date and end_date:
                    filter_parts.append(f"timestamp_processed_date ge {start_date} and timestamp_processed_date le {end_date}")
            
            filter_string = " and ".join(filter_parts) if filter_parts else None
            
            # Perform search
            search_results = self.search_client.search(
                search_text=content_query or "",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["@search.score desc"]
            )
            
            results = []
            for result in search_results:
                doc = dict(result)
                doc['relevance_score'] = result.get('@search.score', 0.0)
                results.append(doc)
            
            search_time = time.time() - start_time
            print(f" Combined search completed in {search_time:.3f}s")
            print(f"   Content query: {content_query}")
            print(f"   Metadata filters: {metadata_filters}")
            print(f"   Source filters: {source_filters}")
            print(f"   Date range: {date_range}")
            print(f"   Found: {len(results)} documents")
            
            return results
            
        except Exception as e:
            print(f" Error in combined search: {e}")
            return []
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def get_document_count(self) -> int:
        """Get total number of documents in index"""
        try:
            results = self.search_client.search(
                search_text="",
                top=1,
                include_total_count=True
            )
            
            for result in results:
                return result.get('@odata.count', 0)
            
            return 0
            
        except Exception as e:
            print(f" Error getting document count: {e}")
            return 0
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get comprehensive search statistics"""
        try:
            stats = {
                'total_documents': 0,
                'file_types': {},
                'data_sources': {},
                'languages': {},
                'authors': {},
                'categories': {}
            }
            
            # Get basic stats
            stats['total_documents'] = self.get_document_count()
            
            # Get facets for detailed statistics
            facets = [
                "metadata_file_type,count:20",
                "source_data_source,count:20", 
                "metadata_language,count:10",
                "metadata_author,count:20",
                "metadata_category,count:20"
            ]
            
            for facet in facets:
                facet_name = facet.split(',')[0]
                results = self.search_client.search(
                    search_text="",
                    top=0,
                    facets=[facet]
                )
                
                for result in results:
                    if facet_name in result:
                        stats[facet_name.replace('metadata_', '').replace('source_', '') + 's'] = result[facet_name]
                    break
            
            return stats
            
        except Exception as e:
            print(f" Error getting search statistics: {e}")
            return {}

def main():
    """Test the unified AI search engine"""
    print("🔍 Unified AI Search Engine")
    print("=" * 40)
    
    # Initialize search engine
    search_engine = AISearchEngine()
    
    # Test ID search
    print("\n🔍 Testing ID search:")
    document = search_engine.search_by_id("sample-json-001")
    if document:
        print(f"   Found: {document['id']}")
    
    # Test content search
    print("\n🔍 Testing content search:")
    results = search_engine.search_by_content("AI search", top=3)
    print(f"   Found {len(results)} documents")
    
    # Test metadata search
    print("\n🔍 Testing metadata search:")
    metadata_results = search_engine.search_by_file_type("json", top=3)
    print(f"   Found {len(metadata_results)} JSON documents")
    
    # Test source search
    print("\n🔍 Testing source search:")
    source_results = search_engine.search_by_data_source("sharepoint", top=3)
    print(f"   Found {len(source_results)} SharePoint documents")
    
    # Test timestamp search
    print("\n🔍 Testing timestamp search:")
    recent_results = search_engine.search_recent_documents(days=30, top=3)
    print(f"   Found {len(recent_results)} recent documents")
    
    # Test combined search
    print("\n🔍 Testing combined search:")
    combined_results = search_engine.combined_search(
        content_query="search",
        metadata_filters={"file_type": "json"},
        source_filters={"data_source": "sharepoint"},
        top=3
    )
    print(f"   Found {len(combined_results)} documents with combined criteria")
    
    # Get statistics
    print("\n📊 Search statistics:")
    stats = search_engine.get_search_statistics()
    print(f"   Total documents: {stats['total_documents']}")
    print(f"   File types: {len(stats.get('file_types', []))}")
    print(f"   Data sources: {len(stats.get('data_sources', []))}")

if __name__ == "__main__":
    main() 