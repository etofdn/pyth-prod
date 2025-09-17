# MD Ingestion Script
# Handles preprocessed Markdown files for AI Search
# Converts MD to standardized JSON structure

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import required modules
from document_ingestion import DocumentIngestionPipeline
from json_flattener import JSONFlattener

class MDIngestion:
    """
    Markdown Ingestion for AI Search
    Processes preprocessed MD files into standardized JSON
    """
    
    def __init__(self, search_endpoint: str, search_key: str, index_name: str):
        self.search_endpoint = search_endpoint
        self.search_key = search_key
        self.index_name = index_name
        self.document_pipeline = DocumentIngestionPipeline()
        self.json_flattener = JSONFlattener()
        
    def ingest_md_file(self, file_path: str, source_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Ingest a single MD file
        """
        try:
            print(f"📄 Processing MD file: {file_path}")
            
            # Validate file exists
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                return None
            
            # Validate file extension
            if not file_path.lower().endswith('.md'):
                print(f"❌ Not a markdown file: {file_path}")
                return None
            
            # Process the MD file
            document = self.document_pipeline.ingest_preprocessed_document(file_path, source_info)
            
            if document:
                print(f"✅ MD file ingested successfully: {os.path.basename(file_path)}")
                return document
            else:
                print(f"❌ Failed to ingest MD file: {file_path}")
                return None
                
        except Exception as e:
            print(f"❌ Error ingesting MD file {file_path}: {e}")
            return None
    
    def batch_ingest_md_files(self, file_paths: List[str], source_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Batch ingest multiple MD files
        """
        documents = []
        
        print(f"📄 Batch ingesting {len(file_paths)} MD files...")
        
        for file_path in file_paths:
            document = self.ingest_md_file(file_path, source_info)
            if document:
                documents.append(document)
        
        print(f"✅ Batch MD ingestion completed: {len(documents)} files processed")
        return documents
    
    def ingest_md_directory(self, directory_path: str, source_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Ingest all MD files in a directory
        """
        documents = []
        
        if not os.path.exists(directory_path):
            print(f"❌ Directory not found: {directory_path}")
            return documents
        
        # Find all MD files
        md_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.join(root, file))
        
        print(f"📄 Found {len(md_files)} MD files in directory: {directory_path}")
        
        # Process all MD files
        for file_path in md_files:
            document = self.ingest_md_file(file_path, source_info)
            if document:
                documents.append(document)
        
        print(f"✅ Directory MD ingestion completed: {len(documents)} files processed")
        return documents
    
    def create_sample_md_files(self, output_dir: str = "sample_md_files") -> List[str]:
        """
        Create sample MD files for testing
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        sample_files = [
            {
                "filename": "sample_document.md",
                "content": """# Sample Document

This is a sample markdown document for testing AI search functionality.

## Features

- **Markdown formatting**: Supports headers, lists, and emphasis
- **Structured content**: Organized sections and subsections
- **Easy to read**: Clean and readable format

## Content Sections

### Introduction
This document demonstrates the capabilities of markdown processing in the AI search system.

### Main Content
The main content includes various topics and keywords for testing search capabilities.

### Conclusion
This document shows how markdown files can be processed and indexed for search.

## Keywords
- AI search
- Document processing
- Markdown
- Testing
- Sample content
"""
            },
            {
                "filename": "technical_guide.md",
                "content": """# Technical Guide

A comprehensive guide for technical documentation.

## Overview

This guide covers various technical topics and implementation details.

### Architecture
The system architecture includes multiple components:
- Data ingestion pipeline
- Search engine
- Document processing
- Analytics layer

### Implementation
Implementation details and code examples.

## Best Practices
1. Follow coding standards
2. Document your code
3. Test thoroughly
4. Optimize performance

## References
- Official documentation
- API references
- Code examples
"""
            },
            {
                "filename": "user_manual.md",
                "content": """# User Manual

Complete user guide for the AI search system.

## Getting Started

Welcome to the AI search system. This manual will help you get started.

### Installation
Follow these steps to install the system:
1. Download the software
2. Run the installer
3. Configure settings
4. Start the service

### Usage
Learn how to use the search functionality:
- Basic search
- Advanced filters
- Result analysis
- Export options

## Troubleshooting
Common issues and solutions.

## Support
Contact information and support resources.
"""
            }
        ]
        
        file_paths = []
        
        for sample in sample_files:
            file_path = os.path.join(output_dir, sample["filename"])
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(sample["content"])
            
            file_paths.append(file_path)
            print(f"✅ Created sample MD file: {file_path}")
        
        print(f"✅ Created {len(file_paths)} sample MD files in {output_dir}")
        return file_paths
    
    def analyze_md_content(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze MD file content for metadata extraction
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            analysis = {
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'content_length': len(content),
                'line_count': len(content.split('\n')),
                'word_count': len(content.split()),
                'headers': [],
                'sections': [],
                'keywords': []
            }
            
            # Extract headers
            lines = content.split('\n')
            for line in lines:
                if line.startswith('#'):
                    level = len(line) - len(line.lstrip('#'))
                    header_text = line.lstrip('#').strip()
                    analysis['headers'].append({
                        'level': level,
                        'text': header_text
                    })
            
            # Extract sections (content between headers)
            current_section = ""
            for line in lines:
                if line.startswith('#'):
                    if current_section.strip():
                        analysis['sections'].append(current_section.strip())
                    current_section = ""
                else:
                    current_section += line + "\n"
            
            if current_section.strip():
                analysis['sections'].append(current_section.strip())
            
            # Extract potential keywords (words that appear multiple times)
            words = content.lower().split()
            word_freq = {}
            for word in words:
                if len(word) > 3:  # Skip short words
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top keywords
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            analysis['keywords'] = [word for word, freq in sorted_words[:10] if freq > 1]
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error analyzing MD content: {e}")
            return {}
    
    def validate_md_structure(self, file_path: str) -> Dict[str, Any]:
        """
        Validate MD file structure and content
        """
        try:
            analysis = self.analyze_md_content(file_path)
            
            validation = {
                'file_path': file_path,
                'is_valid': True,
                'warnings': [],
                'errors': []
            }
            
            # Check file size
            if analysis['file_size'] < 100:
                validation['warnings'].append("File is very small (< 100 bytes)")
            
            if analysis['file_size'] > 1024 * 1024:  # 1MB
                validation['warnings'].append("File is very large (> 1MB)")
            
            # Check content length
            if analysis['content_length'] < 50:
                validation['errors'].append("Content is too short (< 50 characters)")
                validation['is_valid'] = False
            
            # Check for headers
            if not analysis['headers']:
                validation['warnings'].append("No headers found in document")
            
            # Check for sections
            if not analysis['sections']:
                validation['warnings'].append("No content sections found")
            
            # Check for keywords
            if not analysis['keywords']:
                validation['warnings'].append("No keywords extracted")
            
            return validation
            
        except Exception as e:
            return {
                'file_path': file_path,
                'is_valid': False,
                'warnings': [],
                'errors': [f"Error analyzing file: {e}"]
            }
    
    def get_ingestion_statistics(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about ingested MD documents
        """
        stats = {
            'total_documents': len(documents),
            'total_content_length': 0,
            'avg_content_length': 0,
            'file_types': {},
            'sources': {},
            'languages': {},
            'processing_times': []
        }
        
        if documents:
            content_lengths = []
            
            for doc in documents:
                # Content length
                content = doc.get('content', '')
                content_length = len(content)
                content_lengths.append(content_length)
                stats['total_content_length'] += content_length
                
                # File types
                file_type = doc.get('metadata', {}).get('file_type', 'unknown')
                stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
                
                # Sources
                source = doc.get('source', {}).get('data_source', 'unknown')
                stats['sources'][source] = stats['sources'].get(source, 0) + 1
                
                # Languages
                language = doc.get('metadata', {}).get('language', 'unknown')
                stats['languages'][language] = stats['languages'].get(language, 0) + 1
            
            # Calculate averages
            stats['avg_content_length'] = sum(content_lengths) / len(content_lengths)
        
        return stats

def main():
    """Test MD ingestion functionality"""
    print("📄 MD Ingestion for AI Search")
    print("=" * 40)
    
    # Load configuration
    from config import Config
    config = Config.get_search_config()
    search_endpoint = config['search_endpoint']
    search_key = config['search_key']
    index_name = config['index_name']
    
    md_ingestion = MDIngestion(search_endpoint, search_key, index_name)
    
    # Create sample MD files
    print("\n📝 Creating sample MD files...")
    sample_files = md_ingestion.create_sample_md_files()
    
    # Source info for ingestion
    source_info = {
        "data_source": "markdown_files",
        "container": "documents",
        "author": "MD Processor",
        "category": "markdown",
        "priority": 1
    }
    
    # Test single file ingestion
    if sample_files:
        print(f"\n📄 Testing single file ingestion: {sample_files[0]}")
        document = md_ingestion.ingest_md_file(sample_files[0], source_info)
        if document:
            print(f"   ✅ Ingested: {document['id']}")
            print(f"   Content preview: {document['content'][:100]}...")
    
    # Test batch ingestion
    print(f"\n📄 Testing batch ingestion of {len(sample_files)} files...")
    documents = md_ingestion.batch_ingest_md_files(sample_files, source_info)
    print(f"   ✅ Batch ingested: {len(documents)} documents")
    
    # Test content analysis
    if sample_files:
        print(f"\n📊 Analyzing MD content: {sample_files[0]}")
        analysis = md_ingestion.analyze_md_content(sample_files[0])
        print(f"   File size: {analysis['file_size']} bytes")
        print(f"   Content length: {analysis['content_length']} characters")
        print(f"   Headers: {len(analysis['headers'])}")
        print(f"   Sections: {len(analysis['sections'])}")
        print(f"   Keywords: {analysis['keywords'][:5]}")
    
    # Test validation
    if sample_files:
        print(f"\n✅ Validating MD structure: {sample_files[0]}")
        validation = md_ingestion.validate_md_structure(sample_files[0])
        print(f"   Valid: {validation['is_valid']}")
        if validation['warnings']:
            print(f"   Warnings: {validation['warnings']}")
        if validation['errors']:
            print(f"   Errors: {validation['errors']}")
    
    # Get ingestion statistics
    if documents:
        print(f"\n📊 Ingestion statistics:")
        stats = md_ingestion.get_ingestion_statistics(documents)
        print(f"   Total documents: {stats['total_documents']}")
        print(f"   Total content length: {stats['total_content_length']} characters")
        print(f"   Average content length: {stats['avg_content_length']:.0f} characters")
        print(f"   File types: {stats['file_types']}")
        print(f"   Sources: {stats['sources']}")

if __name__ == "__main__":
    main() 