# create_transcript_index.py
import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
)

# 1) Pull in your service endpoint + key
endpoint = "https://aisearchscripts.search.windows.net"
admin_key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"

# 2) Define your enhanced index schema for semantic search
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
]

# Create the enhanced index
index = SearchIndex(
    name="transcript-semantic",
    fields=fields,
    # Enable semantic search capabilities
    # Note: Semantic configuration is handled at the service level
)

# 3) Create or overwrite the index
client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))
client.create_or_update_index(index)
print("Created enhanced index 'transcript-semantic' with semantic search capabilities")
print("All fields are retrievable and optimized for semantic queries")
