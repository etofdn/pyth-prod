# MD Search Script
# Handles searching markdown documents in AI Search
# Specialized search for MD content and structure

import time
from typing import Dict, List, Any, Optional
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

class MDSearch:
    """
    Markdown Search for AI Search
    Specialized search for MD content and structure
    """
    
    def __init__(self, search_endpoint: str, search_key: str, index_name: str):
        self.search_endpoint = search_endpoint
        self.search_key = search_key
        self.index_name = index_name
        self.credential = AzureKeyCredential(search_key)
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=self.credential
        )
    
    def search_md_content(self, query: str, top: int = 10) -> List[Dict[str, Any]]:
        """
        Search markdown content with full-text search
        """
        try:
            start_time = time.time()
            results = []
            
            # Search for markdown content
            search_results = self.search_client.search(
                search_text=query,
                filter="metadata_file_type eq 'md'",
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["@search.score desc"]
            )
            
            for result in search_results:
                doc = dict(result)
                doc['relevance_score'] = result.get('@search.score', 0.0)
                results.append(doc)
            
            search_time = time.time() - start_time
            print(f"✅ MD content search completed in {search_time:.3f}s")
            print(f"   Query: '{query}'")
            print(f"   Found: {len(results)} markdown documents")
            
            return results
            
        except Exception as e:
            print(f"❌ Error in MD content search: {e}")
            return []
    
    def search_md_headers(self, header_query: str, top: int = 10) -> List[Dict[str, Any]]:
        """
        Search for specific headers in markdown documents
        """
        try:
            start_time = time.time()
            results = []
            
            # Search for headers in markdown content
            search_results = self.search_client.search(
                search_text=f"#{header_query}",
                filter="metadata_file_type eq 'md'",
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["@search.score desc"]
            )
            
            for result in search_results:
                doc = dict(result)
                doc['relevance_score'] = result.get('@search.score', 0.0)
                results.append(doc)
            
            search_time = time.time() - start_time
            print(f"✅ MD header search completed in {search_time:.3f}s")
            print(f"   Header query: '{header_query}'")
            print(f"   Found: {len(results)} markdown documents")
            
            return results
            
        except Exception as e:
            print(f"❌ Error in MD header search: {e}")
            return []
    
    def search_md_sections(self, section_query: str, top: int = 10) -> List[Dict[str, Any]]:
        """
        Search for specific sections in markdown documents
        """
        try:
            start_time = time.time()
            results = []
            
            # Search for sections in markdown content
            search_results = self.search_client.search(
                search_text=f'"{section_query}"',
                filter="metadata_file_type eq 'md'",
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["@search.score desc"]
            )
            
            for result in search_results:
                doc = dict(result)
                doc['relevance_score'] = result.get('@search.score', 0.0)
                results.append(doc)
            
            search_time = time.time() - start_time
            print(f"✅ MD section search completed in {search_time:.3f}s")
            print(f"   Section query: '{section_query}'")
            print(f"   Found: {len(results)} markdown documents")
            
            return results
            
        except Exception as e:
            print(f"❌ Error in MD section search: {e}")
            return []
    
    def search_md_keywords(self, keywords: List[str], top: int = 10) -> List[Dict[str, Any]]:
        """
        Search markdown documents by keywords
        """
        try:
            start_time = time.time()
            all_results = []
            
            for keyword in keywords:
                search_results = self.search_client.search(
                    search_text=keyword,
                    filter="metadata_file_type eq 'md'",
                    top=top,
                    select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                    order_by=["@search.score desc"]
                )
                
                for result in search_results:
                    doc = dict(result)
                    doc['relevance_score'] = result.get('@search.score', 0.0)
                    doc['matched_keyword'] = keyword
                    all_results.append(doc)
            
            # Remove duplicates and sort by score
            unique_results = {}
            for result in all_results:
                doc_id = result['id']
                if doc_id not in unique_results or result['relevance_score'] > unique_results[doc_id]['relevance_score']:
                    unique_results[doc_id] = result
            
            final_results = sorted(unique_results.values(), key=lambda x: x['relevance_score'], reverse=True)
            
            search_time = time.time() - start_time
            print(f"✅ MD keyword search completed in {search_time:.3f}s")
            print(f"   Keywords: {keywords}")
            print(f"   Found: {len(final_results)} unique markdown documents")
            
            return final_results[:top]
            
        except Exception as e:
            print(f"❌ Error in MD keyword search: {e}")
            return []
    
    def search_md_by_structure(self, structure_filters: Dict[str, Any], top: int = 10) -> List[Dict[str, Any]]:
        """
        Search markdown documents by structure (headers, sections, etc.)
        """
        try:
            start_time = time.time()
            results = []
            
            # Build filter string
            filter_parts = ["metadata_file_type eq 'md'"]
            
            for key, value in structure_filters.items():
                if key == 'min_headers':
                    # This would require custom analysis, simplified for now
                    pass
                elif key == 'has_sections':
                    # This would require custom analysis, simplified for now
                    pass
                elif key == 'content_length_min':
                    # This would require custom analysis, simplified for now
                    pass
            
            filter_string = " and ".join(filter_parts)
            
            search_results = self.search_client.search(
                search_text="",
                filter=filter_string,
                top=top,
                select=["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                order_by=["timestamp_processed_date desc"]
            )
            
            for result in search_results:
                doc = dict(result)
                doc['relevance_score'] = result.get('@search.score', 0.0)
                results.append(doc)
            
            search_time = time.time() - start_time
            print(f"✅ MD structure search completed in {search_time:.3f}s")
            print(f"   Structure filters: {structure_filters}")
            print(f"   Found: {len(results)} markdown documents")
            
            return results
            
        except Exception as e:
            print(f"❌ Error in MD structure search: {e}")
            return []
    
    def search_md_advanced(self, query: str, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Advanced markdown search with multiple options
        """
        try:
            start_time = time.time()
            
            # Extract options
            top = options.get('top', 10)
            min_score = options.get('min_score', 0.0)
            include_headers = options.get('include_headers', False)
            include_sections = options.get('include_sections', False)
            highlight = options.get('highlight', False)
            
            # Build search parameters
            search_params = {
                'search_text': query,
                'filter': "metadata_file_type eq 'md'",
                'top': top,
                'select': ["id", "content", "metadata", "source", "timestamp", "summary", "keywords"],
                'order_by': ["@search.score desc"]
            }
            
            if highlight:
                search_params['highlight'] = "content"
            
            # Perform search
            search_results = self.search_client.search(**search_params)
            
            results = []
            
            for result in search_results:
                score = result.get('@search.score', 0.0)
                if score >= min_score:
                    doc = dict(result)
                    doc['relevance_score'] = score
                    
                    # Add header and section analysis if requested
                    if include_headers or include_sections:
                        content = doc.get('content', '')
                        analysis = self._analyze_md_content(content)
                        
                        if include_headers:
                            doc['headers'] = analysis.get('headers', [])
                        
                        if include_sections:
                            doc['sections'] = analysis.get('sections', [])
                    
                    results.append(doc)
            
            search_time = time.time() - start_time
            print(f"✅ Advanced MD search completed in {search_time:.3f}s")
            print(f"   Query: '{query}'")
            print(f"   Found: {len(results)} markdown documents")
            
            return results
            
        except Exception as e:
            print(f"❌ Error in advanced MD search: {e}")
            return []
    
    def _analyze_md_content(self, content: str) -> Dict[str, Any]:
        """
        Analyze markdown content for headers and sections
        """
        analysis = {
            'headers': [],
            'sections': []
        }
        
        lines = content.split('\n')
        current_section = ""
        
        for line in lines:
            if line.startswith('#'):
                # Extract header
                level = len(line) - len(line.lstrip('#'))
                header_text = line.lstrip('#').strip()
                analysis['headers'].append({
                    'level': level,
                    'text': header_text
                })
                
                # Save previous section
                if current_section.strip():
                    analysis['sections'].append(current_section.strip())
                current_section = ""
            else:
                current_section += line + "\n"
        
        # Add final section
        if current_section.strip():
            analysis['sections'].append(current_section.strip())
        
        return analysis
    
    def get_md_statistics(self) -> Dict[str, Any]:
        """
        Get markdown document statistics
        """
        try:
            stats = {
                'total_md_documents': 0,
                'avg_content_length': 0,
                'total_headers': 0,
                'total_sections': 0,
                'common_headers': {},
                'common_keywords': {}
            }
            
            # Get all markdown documents
            search_results = self.search_client.search(
                search_text="",
                filter="metadata_file_type eq 'md'",
                top=100,
                select=["content", "metadata"]
            )
            
            documents = []
            for result in search_results:
                documents.append(dict(result))
            
            if documents:
                stats['total_md_documents'] = len(documents)
                
                content_lengths = []
                all_headers = []
                all_keywords = []
                
                for doc in documents:
                    content = doc.get('content', '')
                    content_lengths.append(len(content))
                    
                    # Analyze content
                    analysis = self._analyze_md_content(content)
                    stats['total_headers'] += len(analysis['headers'])
                    stats['total_sections'] += len(analysis['sections'])
                    
                    # Collect headers
                    for header in analysis['headers']:
                        header_text = header['text'].lower()
                        stats['common_headers'][header_text] = stats['common_headers'].get(header_text, 0) + 1
                    
                    # Extract keywords from content
                    words = content.lower().split()
                    for word in words:
                        if len(word) > 3:  # Skip short words
                            all_keywords.append(word)
                
                # Calculate averages
                if content_lengths:
                    stats['avg_content_length'] = sum(content_lengths) / len(content_lengths)
                
                # Get top keywords
                keyword_freq = {}
                for word in all_keywords:
                    keyword_freq[word] = keyword_freq.get(word, 0) + 1
                
                sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
                stats['common_keywords'] = dict(sorted_keywords[:10])
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting MD statistics: {e}")
            return {}
    
    def search_md_by_source(self, source: str, top: int = 10) -> List[Dict[str, Any]]:
        """
        Search markdown documents by source
        """
        try:
            start_time = time.time()
            results = []
            
            # Filter by source and markdown type
            filter_string = f"metadata_file_type eq 'md' and source_data_source eq '{source}'"
            
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
            print(f"✅ MD source search completed in {search_time:.3f}s")
            print(f"   Source: {source}")
            print(f"   Found: {len(results)} markdown documents")
            
            return results
            
        except Exception as e:
            print(f"❌ Error in MD source search: {e}")
            return []

def main():
    """Test MD search functionality"""
    print("🔍 MD Search for AI Search")
    print("=" * 35)
    
    # Load configuration
    from config import Config
    config = Config.get_search_config()
    search_endpoint = config['search_endpoint']
    search_key = config['search_key']
    index_name = config['index_name']
    
    md_search = MDSearch(search_endpoint, search_key, index_name)
    
    # Test basic MD content search
    print("\n🔍 MD content search:")
    content_results = md_search.search_md_content("AI search", top=5)
    for i, result in enumerate(content_results, 1):
        print(f"   {i}. {result['id']} (Score: {result['relevance_score']:.3f})")
        print(f"      Content: {result['content'][:100]}...")
    
    # Test MD header search
    print("\n🔍 MD header search:")
    header_results = md_search.search_md_headers("Sample", top=3)
    for i, result in enumerate(header_results, 1):
        print(f"   {i}. {result['id']} (Score: {result['relevance_score']:.3f})")
    
    # Test MD section search
    print("\n🔍 MD section search:")
    section_results = md_search.search_md_sections("markdown", top=3)
    for i, result in enumerate(section_results, 1):
        print(f"   {i}. {result['id']} (Score: {result['relevance_score']:.3f})")
    
    # Test MD keyword search
    print("\n🔍 MD keyword search:")
    keywords = ["document", "processing", "search"]
    keyword_results = md_search.search_md_keywords(keywords, top=3)
    for i, result in enumerate(keyword_results, 1):
        print(f"   {i}. {result['id']} - Matched: {result['matched_keyword']}")
    
    # Test advanced MD search
    print("\n🔍 Advanced MD search:")
    options = {
        'top': 5,
        'min_score': 0.5,
        'include_headers': True,
        'include_sections': True,
        'highlight': True
    }
    advanced_results = md_search.search_md_advanced("markdown functionality", options)
    print(f"   Found {len(advanced_results)} high-relevance markdown documents")
    
    # Test MD source search
    print("\n🔍 MD source search:")
    source_results = md_search.search_md_by_source("markdown_files", top=3)
    for i, result in enumerate(source_results, 1):
        print(f"   {i}. {result['id']} - {result['source']['data_source']}")
    
    # Get MD statistics
    print("\n📊 MD statistics:")
    stats = md_search.get_md_statistics()
    print(f"   Total MD documents: {stats['total_md_documents']}")
    print(f"   Average content length: {stats['avg_content_length']:.0f} characters")
    print(f"   Total headers: {stats['total_headers']}")
    print(f"   Total sections: {stats['total_sections']}")
    print(f"   Common headers: {list(stats['common_headers'].keys())[:5]}")
    print(f"   Common keywords: {list(stats['common_keywords'].keys())[:5]}")

if __name__ == "__main__":
    main() 