#!/usr/bin/env python3
import os
import json
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

def main():
    # 1) Grab your endpoint, key, and index name from env
    endpoint   = "https://aisearchscripts.search.windows.net"
    api_key    = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
    index_name = "transcripts-v2"

    # 2) Create the SearchClient
    client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(api_key)
    )

    # 3) Load your flattened payload
    payload_path = "flattened_transcript.json"
    
    if not os.path.exists(payload_path):
        print(f"Error: File '{payload_path}' not found!")
        print("   Make sure to run 'python flatten_transcript.py' first to generate the flattened transcript.")
        return
    
    try:
        with open(payload_path, "r", encoding="utf-8") as f:
            docs = json.load(f)
        
        # The JSON file contains a direct array, not an object with "value" key
        if not isinstance(docs, list):
            print(f"Error: Expected array of documents, got {type(docs)}")
            return
            
        print(f"Loaded {len(docs)} documents from {payload_path}")
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file: {e}")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # 4) Upload documents
    print(f"Uploading {len(docs)} documents to '{index_name}'...")
    results = client.upload_documents(documents=docs)

    # 5) Report success/failures
    succeeded = sum(1 for r in results if getattr(r, "succeeded", False))
    failed = len(docs) - succeeded
    
    print(f"Uploaded {succeeded}/{len(docs)} documents to '{index_name}'")
    
    if failed > 0:
        print(f"{failed} documents failed to upload:")
        for r in results:
            if not getattr(r, "succeeded", False):
                print(f"  - Failed doc key={r.key}: {r.error_message}")
    else:
        print("All documents uploaded successfully!")

if __name__ == "__main__":
    main()
