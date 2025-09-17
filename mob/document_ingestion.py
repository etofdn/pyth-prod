# Document Ingestion Pipeline for AI Search
# Handles preprocessed MD/JSON files from SharePoint and Blob Storage
# Converts to standardized JSON structure with 4-5 keys
# Supports: PDF, Word, Excel, PowerPoint, Text files (preprocessed)

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Import JSON flattener
from json_flattener import JSONFlattener

class DocumentIngestionPipeline:
    """
    Ingestion Pipeline for Preprocessed MD/JSON Files
    DS1: JSON processing pipeline
    DS2: Word document pipeline  
    Excel: Datafile preprocessing pipeline
    """
    
    def __init__(self):
        self.supported_file_types = {
            'json': self._process_json,
            'md': self._process_markdown,
            'txt': self._process_text
        }
        self.json_flattener = JSONFlattener()
        
    def ingest_preprocessed_document(self, file_path: str, source_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingest preprocessed MD/JSON document
        Expected: Already processed MD/JSON files, not raw files
        """
        try:
            # Get file info
            file_name = os.path.basename(file_path)
            file_extension = file_name.split('.')[-1].lower()
            
            # Validate file type
            if file_extension not in self.supported_file_types:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            # Process preprocessed file
            document_data = self.supported_file_types[file_extension](file_path)
            
            if not document_data:
                raise ValueError(f"Failed to process file: {file_path}")
            
            # Flatten JSON if needed
            if file_extension == 'json':
                document_data = self.json_flattener.flatten_for_ai_search(document_data)
            
            # Create standardized JSON structure
            document = self._create_standardized_document(
                file_path=file_path,
                file_name=file_name,
                file_extension=file_extension,
                document_data=document_data,
                source_info=source_info
            )
            
            print(f"✅ Preprocessed document ingested: {file_name}")
            return document
            
        except Exception as e:
            print(f"❌ Error ingesting preprocessed document {file_path}: {e}")
            return None
    
    def _process_json(self, file_path: str) -> Dict[str, Any]:
        """Process preprocessed JSON files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            print(f"Error reading JSON file {file_path}: {e}")
            return None
    
    def _process_markdown(self, file_path: str) -> Dict[str, Any]:
        """Process preprocessed Markdown files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Convert Markdown to JSON structure
            return {
                "id": f"md-{int(time.time())}",
                "content": content,
                "metadata": {
                    "file_type": "markdown",
                    "file_name": os.path.basename(file_path),
                    "language": "en"
                },
                "source": {
                    "data_source": "markdown_processing",
                    "path": file_path
                },
                "timestamp": {
                    "processed_date": datetime.now().isoformat()
                }
            }
        except Exception as e:
            print(f"Error reading Markdown file {file_path}: {e}")
            return None
    
    def _process_text(self, file_path: str) -> Dict[str, Any]:
        """Process preprocessed text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Convert text to JSON structure
            return {
                "id": f"txt-{int(time.time())}",
                "content": content,
                "metadata": {
                    "file_type": "text",
                    "file_name": os.path.basename(file_path),
                    "language": "en"
                },
                "source": {
                    "data_source": "text_processing",
                    "path": file_path
                },
                "timestamp": {
                    "processed_date": datetime.now().isoformat()
                }
            }
        except Exception as e:
            print(f"Error reading text file {file_path}: {e}")
            return None
    
    def _create_standardized_document(self, file_path: str, file_name: str, 
                                    file_extension: str, document_data: Dict[str, Any],
                                    source_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create standardized JSON structure with 4-5 keys from preprocessed data
        """
        # Generate unique ID if not present
        doc_id = document_data.get('id', f"{file_extension}-{int(time.time())}")
        
        return {
            # Standardized Key 1: ID (unique identifier)
            "id": doc_id,
            
            # Standardized Key 2: Content (main searchable content)
            "content": document_data.get('content', ''),
            
            # Standardized Key 3: Metadata (file info, structure)
            "metadata": {
                "file_type": file_extension,
                "file_name": file_name,
                "original_file_type": document_data.get('metadata', {}).get('file_type', file_extension),
                "file_size": os.path.getsize(file_path),
                "page_count": document_data.get('metadata', {}).get('page_count', 1),
                "language": document_data.get('metadata', {}).get('language', 'en'),
                "author": document_data.get('metadata', {}).get('author', source_info.get('author', 'Unknown')),
                "title": document_data.get('metadata', {}).get('title', file_name),
                "category": document_data.get('metadata', {}).get('category', source_info.get('category', 'general'))
            },
            
            # Standardized Key 4: Source (data source info)
            "source": {
                "data_source": source_info.get('data_source', 'preprocessed_files'),
                "container": source_info.get('container', 'documents'),
                "path": file_path,
                "url": source_info.get('url', ''),
                "sharepoint_site": source_info.get('sharepoint_site', ''),
                "blob_container": source_info.get('blob_container', ''),
                "original_format": document_data.get('source', {}).get('original_format', file_extension)
            },
            
            # Standardized Key 5: Timestamp (processing and creation times)
            "timestamp": {
                "created_date": document_data.get('timestamp', {}).get('created_date', source_info.get('created_date', datetime.now().isoformat())),
                "modified_date": document_data.get('timestamp', {}).get('modified_date', datetime.now().isoformat()),
                "processed_date": datetime.now().isoformat()
            },
            
            # Additional fields for enhanced search
            "summary": document_data.get('summary', ''),
            "keywords": document_data.get('keywords', ''),
            "is_active": document_data.get('is_active', True),
            "priority": document_data.get('priority', source_info.get('priority', 1))
        }
    
    def batch_ingest_preprocessed(self, file_paths: List[str], source_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Batch ingest preprocessed MD/JSON documents
        """
        documents = []
        
        for file_path in file_paths:
            print(f"Processing preprocessed file: {file_path}")
            document = self.ingest_preprocessed_document(file_path, source_info)
            if document:
                documents.append(document)
        
        print(f"✅ Batch ingestion completed: {len(documents)} preprocessed documents processed")
        return documents
    
    def create_sample_preprocessed_files(self) -> List[Dict[str, Any]]:
        """
        Create sample preprocessed documents for testing
        """
        sample_files = [
            {"path": "/samples/document1.json", "type": "json"},
            {"path": "/samples/report.md", "type": "md"},
            {"path": "/samples/data.txt", "type": "txt"}
        ]
        
        source_info = {
            "data_source": "preprocessed_files",
            "container": "documents",
            "author": "Test User",
            "category": "sample",
            "priority": 1
        }
        
        documents = []
        for file_info in sample_files:
            # Create sample document data
            sample_data = self._create_sample_preprocessed_content(file_info["type"])
            document = self._create_standardized_document(
                file_path=file_info["path"],
                file_name=f"sample.{file_info['type']}",
                file_extension=file_info["type"],
                document_data=sample_data,
                source_info=source_info
            )
            if document:
                documents.append(document)
        
        return documents
    
    def _create_sample_preprocessed_content(self, file_type: str) -> Dict[str, Any]:
        """Create sample preprocessed content based on file type"""
        if file_type == "json":
            return {
                "id": "sample-json-001",
                "content": "This is sample JSON content for testing AI search functionality.",
                "metadata": {
                    "file_type": "pdf",
                    "file_name": "sample.pdf",
                    "page_count": 3,
                    "language": "en",
                    "author": "Test Author",
                    "title": "Sample Document",
                    "category": "test"
                },
                "source": {
                    "data_source": "sharepoint",
                    "container": "documents",
                    "path": "/samples/sample.pdf",
                    "original_format": "pdf"
                },
                "timestamp": {
                    "created_date": "2025-01-15T10:30:00Z",
                    "modified_date": "2025-01-16T14:45:00Z"
                },
                "summary": "Sample JSON document for testing",
                "keywords": "sample, test, json, document",
                "is_active": True,
                "priority": 1
            }
        elif file_type == "md":
            return {
                "id": "sample-md-001",
                "content": "# Sample Markdown Document\n\nThis is a sample markdown document for testing AI search functionality.\n\n## Features\n- Markdown formatting\n- Structured content\n- Easy to read\n\n## Conclusion\nThis document demonstrates markdown processing capabilities.",
                "metadata": {
                    "file_type": "markdown",
                    "language": "en"
                },
                "source": {
                    "data_source": "markdown_processing"
                },
                "timestamp": {
                    "created_date": "2025-01-15T10:30:00Z"
                }
            }
        else:  # txt
            return {
                "id": "sample-txt-001",
                "content": "This is a sample text document for testing AI search functionality. The content includes various topics and keywords for testing search capabilities.",
                "metadata": {
                    "file_type": "text",
                    "language": "en"
                },
                "source": {
                    "data_source": "text_processing"
                },
                "timestamp": {
                    "created_date": "2025-01-15T10:30:00Z"
                }
            }

def main():
    """Test the preprocessed document ingestion pipeline"""
    print("📄 Preprocessed Document Ingestion Pipeline")
    print("=" * 50)
    
    pipeline = DocumentIngestionPipeline()
    
    # Test with sample preprocessed documents
    print("\n🔄 Creating sample preprocessed documents...")
    documents = pipeline.create_sample_preprocessed_files()
    
    print(f"\n✅ Created {len(documents)} sample preprocessed documents")
    print("\n📋 Sample document structure:")
    if documents:
        print(json.dumps(documents[0], indent=2))

if __name__ == "__main__":
    main() 