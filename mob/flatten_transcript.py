#!/usr/bin/env python3
"""
Transcript Flattening Script
Reads transcript.json, flattens it using JSONFlattener, and saves the result
"""

import json
import sys
from pathlib import Path
from json_flattener import JSONFlattener

def main():
    """Main function to flatten transcript.json"""
    print("🔄 Transcript Flattening Script")
    print("=" * 40)
    
    # Initialize the JSON flattener
    flattener = JSONFlattener()
    
    # Define input and output files
    input_file = Path("transcript.json")
    output_file = Path("flattened_transcript.json")
    
    # Check if input file exists
    if not input_file.exists():
        print(f"❌ Error: Input file '{input_file}' not found")
        print("Please ensure transcript.json exists in the current directory")
        sys.exit(1)
    
    try:
        # Read the transcript JSON
        print(f"📖 Reading transcript from: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        print(f"✅ Loaded transcript with {len(transcript_data.get('transcript_chunks', []))} chunks")
        
        # Flatten the transcript
        print("🔄 Flattening transcript...")
        documents = flattener.flatten_for_ai_search(transcript_data)
        
        if not documents:
            print("❌ Error: Failed to flatten transcript")
            sys.exit(1)
        
        # Get statistics
        stats = flattener.get_document_statistics(documents)
        print(f"✅ Flattened successfully!")
        print(f"   📊 Statistics:")
        print(f"   - Total documents: {stats['total_documents']}")
        print(f"   - File documents: {stats['file_documents']}")
        print(f"   - Chunk documents: {stats['chunk_documents']}")
        print(f"   - Unique speakers: {stats['unique_speakers']}")
        print(f"   - Total text length: {stats['total_text_length']:,} characters")
        print(f"   - Average chunk duration: {stats['avg_chunk_duration']:.2f} seconds")
        print(f"   - Total duration: {stats['total_duration']:.2f} seconds")
        
        # Save the flattened documents
        print(f"💾 Saving flattened transcript to: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Flattened transcript saved successfully!")
        print(f"📁 Output file: {output_file}")
        
        # Show sample of the flattened structure
        print("\n📋 Sample flattened structure:")
        
        # Show file document
        file_doc = next((doc for doc in documents if 'flattened_transcript' in doc), None)
        if file_doc:
            print(f"   📄 File Document:")
            print(f"      ID: {file_doc['id']}")
            print(f"      Filename: {file_doc['Filename']}")
            print(f"      Duration: {file_doc['duration']}s")
            print(f"      Transcript length: {len(file_doc['flattened_transcript'])} characters")
        
        # Show chunk document
        chunk_doc = next((doc for doc in documents if 'parentDocId' in doc), None)
        if chunk_doc:
            print(f"   🎯 Chunk Document:")
            print(f"      ID: {chunk_doc['id']}")
            print(f"      Parent Doc ID: {chunk_doc['parentDocId']}")
            print(f"      Speaker: {chunk_doc['speaker']}")
            print(f"      Start: {chunk_doc['start_at']}")
            print(f"      End: {chunk_doc['end_at']}")
            print(f"      Text: {chunk_doc['text'][:100]}...")
            
            # Show unique speakers
            speakers = list(set(doc['speaker'] for doc in documents if 'speaker' in doc))
            print(f"   🎤 All speakers: {speakers}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {input_file}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 