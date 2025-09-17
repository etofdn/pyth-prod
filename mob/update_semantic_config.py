#!/usr/bin/env python3
"""
update_semantic_config.py

Update the existing transcripts-v2 index to include semantic configuration
Following the Microsoft documentation pattern for semantic search
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch
)

def main():
    # Azure Search credentials
    search_endpoint = "https://aisearchscripts.search.windows.net"
    admin_key = "xdht5cEFq32FJyVl9PZkE8lYv0s7Ylxo16c1dhIJg6AzSeAu6GKO"
    index_name = "transcripts-v2"
    
    # Create the SearchIndexClient
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=AzureKeyCredential(admin_key))
    
    try:
        # Get the existing index schema
        print(f"Retrieving existing index: {index_name}")
        existing_index = index_client.get_index(index_name)
        
        print(f"Index name: {existing_index.name}")
        print(f"Number of fields: {len(existing_index.fields)}")
        
        # Print field details
        for field in existing_index.fields:
            print(f"Field: {field.name}, Type: {field.type}, Searchable: {getattr(field, 'searchable', False)}")
        
        # Check if semantic configuration already exists
        if existing_index.semantic_search and existing_index.semantic_search.configurations:
            print("\nExisting semantic configurations:")
            for config in existing_index.semantic_search.configurations:
                print(f"  Configuration: {config.name}")
                if config.prioritized_fields.title_field:
                    print(f"    Title field: {config.prioritized_fields.title_field.field_name}")
        else:
            print("\nNo semantic configuration exists for this index")
        
        # Create a new semantic configuration for transcript data
        print("\nCreating semantic configuration...")
        new_semantic_config = SemanticConfiguration(
            name="transcript-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="text"),  # Main content field
                keywords_fields=[
                    SemanticField(field_name="flattened_transcript"),  # Full transcript
                    SemanticField(field_name="Filename")  # File name as keyword
                ],
                content_fields=[
                    SemanticField(field_name="text"),  # Individual text segments
                    SemanticField(field_name="flattened_transcript")  # Full transcript
                ]
            )
        )
        
        # Add semantic configuration to the index
        if existing_index.semantic_search is None:
            existing_index.semantic_search = SemanticSearch(configurations=[new_semantic_config])
            print("Created new semantic search configuration")
        else:
            # Check if configuration already exists
            config_exists = any(config.name == "transcript-semantic-config" 
                              for config in existing_index.semantic_search.configurations)
            if not config_exists:
                existing_index.semantic_search.configurations.append(new_semantic_config)
                print("Added semantic configuration to existing semantic search")
            else:
                print("Semantic configuration already exists")
        
        # Update the index
        print("Updating index with semantic configuration...")
        result = index_client.create_or_update_index(existing_index)
        
        # Get the updated index and display detailed information
        updated_index = index_client.get_index(index_name)
        
        print("\n✅ Semantic configuration successfully added!")
        print("\nUpdated semantic configurations:")
        print("-" * 40)
        if updated_index.semantic_search and updated_index.semantic_search.configurations:
            for config in updated_index.semantic_search.configurations:
                print(f"  Configuration: {config.name}")
                if config.prioritized_fields.title_field:
                    print(f"    Title field: {config.prioritized_fields.title_field.field_name}")
                if config.prioritized_fields.keywords_fields:
                    keywords = [kf.field_name for kf in config.prioritized_fields.keywords_fields]
                    print(f"    Keywords fields: {', '.join(keywords)}")
                if config.prioritized_fields.content_fields:
                    content = [cf.field_name for cf in config.prioritized_fields.content_fields]
                    print(f"    Content fields: {', '.join(content)}")
                print()
        else:
            print("  No semantic configurations found")
        
        print("Index is now ready for semantic search!")
        print("You can now run semantic queries using:")
        print("- query_type='semantic'")
        print("- semantic_configuration_name='transcript-semantic-config'")
        
    except Exception as ex:
        print(f"❌ Error updating semantic configuration: {ex}")
        print("This might be due to network connectivity issues.")

if __name__ == "__main__":
    main() 