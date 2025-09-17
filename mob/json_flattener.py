
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Union, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JSONFlattener:
    """
    """
    
    def __init__(self, separator: str = "_", max_depth: int = 10):
        self.separator = separator
        self.max_depth = max_depth
        self.required_keys = ['id', 'metadata']
        self.transcript_schema = True  # Handle transcript-specific schema
        
    def validate_document_structure(self, document: Dict[str, Any]) -> bool:
        """
        Validate document has required structure for AI Search
        Supports both standard and transcript schemas
        """
        try:
            # Check for required keys
            missing_keys = [key for key in self.required_keys if key not in document]
            if missing_keys:
                logger.warning(f"Missing required keys: {missing_keys}")
                return False
            
            # Validate ID
            if not document.get('id'):
                logger.error("Document ID is required")
                return False
            
            # Validate metadata structure
            metadata = document.get('metadata', {})
            if not isinstance(metadata, dict):
                logger.error("Metadata must be a dictionary")
                return False
            
            # Check for transcript schema
            if 'transcript_chunks' in document:
                logger.info("Detected transcript schema")
                if not isinstance(document['transcript_chunks'], list):
                    logger.error("transcript_chunks must be a list")
                    return False
                
                # Validate transcript chunks
                for i, chunk in enumerate(document['transcript_chunks']):
                    if not isinstance(chunk, dict):
                        logger.error(f"Transcript chunk {i} must be a dictionary")
                        return False
                    
                    required_chunk_fields = ['speaker', 'start', 'end', 'text']
                    missing_chunk_fields = [field for field in required_chunk_fields if field not in chunk]
                    if missing_chunk_fields:
                        logger.error(f"Transcript chunk {i} missing required fields: {missing_chunk_fields}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating document structure: {e}")
            return False
    
    def extract_transcript_content(self, document: Dict[str, Any]) -> str:
        """
        Extract and combine transcript content from chunks
        """
        try:
            content_parts = []
            
            # Extract flattened transcript if available
            if 'metadata' in document and 'flattened_transcript' in document['metadata']:
                flattened = document['metadata']['flattened_transcript']
                if isinstance(flattened, str) and flattened.strip():
                    content_parts.append(flattened)
            
            # Extract from transcript chunks
            if 'transcript_chunks' in document:
                chunks = document['transcript_chunks']
                if isinstance(chunks, list):
                    for chunk in chunks:
                        if isinstance(chunk, dict) and 'text' in chunk:
                            text = chunk['text'].strip()
                            if text:
                                content_parts.append(text)
            
            # Combine all content
            full_content = ' '.join(content_parts)
            
            if not full_content.strip():
                logger.warning("No transcript content found")
                return ""
            
            logger.info(f"Extracted {len(content_parts)} content parts, total length: {len(full_content)}")
            return full_content
            
        except Exception as e:
            logger.error(f"Error extracting transcript content: {e}")
            return ""
    
    def flatten_json(self, nested_json: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        Flatten nested JSON structure with production optimizations
        Returns flat dictionary with standardized key format
        """
        flattened = {}
        
        def _flatten(obj: Any, current_prefix: str, depth: int = 0):
            if depth > self.max_depth:
                logger.warning(f"Max depth {self.max_depth} reached, truncating")
                return
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Sanitize key name for Azure Search
                    sanitized_key = self._sanitize_key(key)
                    new_key = f"{current_prefix}{sanitized_key}" if current_prefix else sanitized_key
                    _flatten(value, new_key, depth + 1)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_key = f"{current_prefix}[{i}]" if current_prefix else f"[{i}]"
                    _flatten(item, new_key, depth + 1)
            else:
                # Convert value to searchable format
                if obj is None:
                    flattened[current_prefix] = ""
                elif isinstance(obj, (int, float, bool)):
                    flattened[current_prefix] = str(obj)
                else:
                    flattened[current_prefix] = str(obj)
        
        _flatten(nested_json, prefix)
        return flattened
    
    def _sanitize_key(self, key: str) -> str:
        """
        Sanitize key names for Azure Search compatibility
        """
        # Remove special characters that might cause issues
        sanitized = key.replace(' ', '_').replace('-', '_').replace('.', '_')
        # Ensure it starts with a letter or underscore
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
            sanitized = f"field_{sanitized}"
        return sanitized
    
    def flatten_for_ai_search(self, raw: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Produce one file-level doc with full transcript plus individual chunk docs.
        File doc contains all metadata + flattened_transcript.
        Chunk docs contain metadata (minus flattened_transcript) + chunk-specific fields.
        """
        try:
            # Validate document structure
            if not self.validate_document_structure(raw):
                return None
            
            meta = raw["metadata"]
            base = datetime.fromisoformat(meta["created"].rstrip("Z"))

            docs: List[Dict[str, Any]] = []

            # ——— 1) Document-level record ———
            file_doc = {
                "@search.action":       "upload",
                "id":                   raw["id"],
                "transaction_key":      meta["transaction_key"],
                "request_id":           meta["request_id"],
                "sha256":               meta["sha256"],
                "created":              meta["created"],
                "duration":             meta["duration"],
                "channels":             meta["channels"],
                "Filename":             meta["Filename"],
                "videolink":            meta["videolink"],
                "flattened_transcript": meta["flattened_transcript"],
            }
            docs.append(file_doc)

            # ——— 2) Chunk-level records ———
            for i, chunk in enumerate(raw["transcript_chunks"]):
                start, end = chunk["start"], chunk["end"]
                docs.append({
                    "@search.action":  "upload",
                    "id":              f"{raw['id']}_{i}",
                    "parentDocId":     raw["id"],

                    # metadata (minus flattened_transcript)
                    "transaction_key": meta["transaction_key"],
                    "request_id":      meta["request_id"],
                    "sha256":          meta["sha256"],
                    "created":         meta["created"],
                    "duration":        meta["duration"],
                    "channels":        meta["channels"],
                    "Filename":        meta["Filename"],
                    "videolink":       meta["videolink"],

                    # chunk-specific fields
                    "speaker":         chunk["speaker"],
                    "start_offset":    start,
                    "end_offset":      end,
                    "start_at":        (base + timedelta(seconds=start)).isoformat() + "Z",
                    "end_at":          (base + timedelta(seconds=end)).isoformat() + "Z",
                    "text":            chunk["text"].strip(),
                })

            logger.info(f"Flattened {len(docs)} documents from: {raw['id']} (1 file + {len(docs)-1} chunks)")
            return docs
            
        except Exception as e:
            logger.error(f"Error flattening JSON: {e}")
            return None
    
    def batch_flatten_json(self, json_files: List[str], validate_only: bool = False) -> List[Dict[str, Any]]:
        """
        Batch flatten multiple JSON files with production error handling
        """
        flattened_documents = []
        processed_count = 0
        error_count = 0
        
        logger.info(f"Starting batch flattening of {len(json_files)} files")
        
        for file_path in json_files:
            try:
                file_path = Path(file_path)
                if not file_path.exists():
                    logger.error(f"File not found: {file_path}")
                    error_count += 1
                    continue
                
                logger.info(f"Processing: {file_path.name}")
                
                # Load JSON file with encoding handling
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        document_json = json.load(file)
                except UnicodeDecodeError:
                    # Try with different encoding
                    with open(file_path, 'r', encoding='latin-1') as file:
                        document_json = json.load(file)
                
                # Validate document structure
                if not self.validate_document_structure(document_json):
                    logger.error(f"Document validation failed for: {file_path.name}")
                    error_count += 1
                    continue
                
                if validate_only:
                    logger.info(f"Validated: {file_path.name}")
                    processed_count += 1
                    continue
                
                # Flatten document
                chunk_docs = self.flatten_for_ai_search(document_json)
                if chunk_docs:
                    flattened_documents.extend(chunk_docs)
                    processed_count += 1
                else:
                    error_count += 1
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in {file_path}: {e}")
                error_count += 1
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                error_count += 1
        
        logger.info(f"Batch flattening completed:")
        logger.info(f"Processed: {processed_count}")
        logger.info(f"Errors: {error_count}")
        logger.info(f"Total chunk documents: {len(flattened_documents)}")
        logger.info(f"Success rate: {processed_count/(processed_count + error_count)*100:.1f}%")
        
        return flattened_documents
    
    def flatten_from_string(self, json_string: str) -> Optional[List[Dict[str, Any]]]:
        """
        Flatten JSON from string input
        """
        try:
            document_json = json.loads(json_string)
            return self.flatten_for_ai_search(document_json)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON string: {e}")
            return None
        except Exception as e:
            logger.error(f"Error flattening JSON string: {e}")
            return None
    
    def get_flattened_key_mapping(self, original_json: Dict[str, Any]) -> Dict[str, str]:
        """
        Get mapping of original keys to flattened keys for documentation
        """
        try:
            flattened = self.flatten_for_ai_search(original_json)
            if not flattened:
                return {}
            
            mapping = {}
            # Check both file-level and chunk-level documents
            for doc in flattened:
                for flat_key in doc.keys():
                    if flat_key not in ['@search.action', 'id', 'parentDocId', 'transaction_key', 'request_id', 'sha256', 'created', 'duration', 'channels', 'Filename', 'videolink', 'flattened_transcript', 'speaker', 'start_offset', 'end_offset', 'start_at', 'end_at', 'text']:
                        # Map back to original structure
                        if flat_key.startswith('metadata_'):
                            original_key = flat_key.replace('metadata_', 'metadata.')
                        elif flat_key.startswith('source_'):
                            original_key = flat_key.replace('source_', 'source.')
                        elif flat_key.startswith('timestamp_'):
                            original_key = flat_key.replace('timestamp_', 'timestamp.')
                        else:
                            original_key = flat_key
                        
                        mapping[flat_key] = original_key
            
            return mapping
            
        except Exception as e:
            logger.error(f"Error creating key mapping: {e}")
            return {}
    
    def validate_flattened_document(self, flat_document: Dict[str, Any]) -> bool:
        """
        Validate flattened document meets AI Search requirements
        """
        try:
            # Check if this is a file-level or chunk-level document
            is_file_doc = 'flattened_transcript' in flat_document
            is_chunk_doc = 'parentDocId' in flat_document
            
            # Common required fields
            common_fields = ['@search.action', 'id', 'transaction_key', 'request_id', 'sha256', 'created', 'duration', 'channels', 'Filename', 'videolink']
            
            for field in common_fields:
                if field not in flat_document:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Check ID format
            if not isinstance(flat_document['id'], str) or not flat_document['id']:
                logger.error("ID must be a non-empty string")
                return False
            
            # File-level document validation
            if is_file_doc:
                if 'flattened_transcript' not in flat_document:
                    logger.error("File document missing flattened_transcript")
                    return False
                
                if not isinstance(flat_document['flattened_transcript'], str):
                    logger.error("flattened_transcript must be a string")
                    return False
            
            # Chunk-level document validation
            if is_chunk_doc:
                chunk_fields = ['parentDocId', 'speaker', 'start_offset', 'end_offset', 'start_at', 'end_at', 'text']
                for field in chunk_fields:
                    if field not in flat_document:
                        logger.error(f"Chunk document missing required field: {field}")
                        return False
                
                # Check text format
                if not isinstance(flat_document['text'], str):
                    logger.error("Text must be a string")
                    return False
                
                # Check numeric fields
                if not isinstance(flat_document['start_offset'], (int, float)):
                    logger.error("start_offset must be numeric")
                    return False
                
                if not isinstance(flat_document['end_offset'], (int, float)):
                    logger.error("end_offset must be numeric")
                    return False
                
                # Check speaker field
                if not isinstance(flat_document['speaker'], (int, float)):
                    logger.error("speaker must be numeric")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating flattened document: {e}")
            return False
    
    def get_document_statistics(self, flat_documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about flattened documents
        """
        try:
            if not flat_documents:
                return {'total_documents': 0}
            
            # Separate file and chunk documents
            file_docs = [doc for doc in flat_documents if 'flattened_transcript' in doc]
            chunk_docs = [doc for doc in flat_documents if 'parentDocId' in doc]
            
            # Get unique parent documents
            parent_docs = set(doc.get('parentDocId', '') for doc in chunk_docs)
            
            # Calculate statistics
            total_text_length = sum(len(doc.get('text', '')) for doc in chunk_docs)
            unique_speakers = len(set(doc.get('speaker', '') for doc in chunk_docs))
            
            # Calculate average chunk duration
            total_duration = 0
            for doc in chunk_docs:
                start = doc.get('start_offset', 0)
                end = doc.get('end_offset', 0)
                total_duration += (end - start)
            
            avg_duration = total_duration / len(chunk_docs) if chunk_docs else 0
            
            stats = {
                'total_documents': len(flat_documents),
                'file_documents': len(file_docs),
                'chunk_documents': len(chunk_docs),
                'unique_parent_docs': len(parent_docs),
                'total_text_length': total_text_length,
                'unique_speakers': unique_speakers,
                'avg_chunk_duration': avg_duration,
                'total_duration': total_duration
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting document statistics: {e}")
            return {}

