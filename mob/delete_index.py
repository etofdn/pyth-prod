#!/usr/bin/env python3
"""
Delete the existing transcripts-test index to allow recreation with SearchableField
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient

def main():
    # Azure Search credentials
    endpoint = "https://aisearchscripts.search.windows.net"
    admin_key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
    
    # Create client
    client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))
    
    try:
        # Delete the existing index
        client.delete_index("transcripts-test")
        print("Deleted existing index 'transcripts-test'")
    except Exception as e:
        print(f"Error deleting index: {e}")
        print("Index may not exist, continuing...")

if __name__ == "__main__":
    main() 