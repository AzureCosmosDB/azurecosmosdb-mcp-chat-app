from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from semantic_kernel.functions import kernel_function
from typing import Dict, Any, List
from azure.core.paging import ItemPaged

class CosmosDB_AIPlugin:
    def __init__(self, account_name):
        self.cosmos_client = CosmosClient(
            url=f"https://{account_name}.documents.azure.com:443/",
            credential=DefaultAzureCredential()
        )

    
    def get_count_of_documents(self, database: str, collection: str):
        """
        Get the count of documents in the specified database and collection.
        """
        try:
            database_proxy = self.cosmos_client.get_database_client(database)
            container = database_proxy.get_container_client(collection)
            documentIterator: ItemPaged[Dict[str, Any]] = container.query_items(
                query="SELECT VALUE COUNT(1) FROM c",
                enable_cross_partition_query=True,
            )
            count = documentIterator.next()
            return {"result": str(count), "query": "SELECT VALUE COUNT(1) FROM c"}
        except Exception as e:
            print(f"Error retrieving document count: {e}")
            return None

    def get_document_by_field_filter(self, database: str, collection: str, field: str, value: str, fields: List[str] = ["*"]):
        """
        Get a document from the specified database and collection.
        """
        try:
            database_proxy = self.cosmos_client.get_database_client(database)
            container = database_proxy.get_container_client(collection)
            fields = list(map(lambda x: f"c.{x}", fields)) if fields != ["*"] else ["*"]
            result: ItemPaged[Dict[str, Any]] = container.query_items(
                query=f'SELECT {",".join(fields)} FROM c WHERE c.{field} = "{value}"',
                enable_cross_partition_query=True,
            )
            data = result.next()
            return {"result": data, "query": f'SELECT {",".join(fields)} FROM c WHERE c.{field} = "{value}"'}
        except Exception as e:
            print(f"Error retrieving document: {e}")
            return None

    def get_collection_schema(self, database: str, collection: str):
        """
        Get the schema of the specified database and collection.
        """
        try:
            database_proxy = self.cosmos_client.get_database_client(database)
            container = database_proxy.get_container_client(collection)
            documentIterator: ItemPaged[Dict[str, Any]] = container.query_items(
                query="SELECT TOP 1 * FROM c",
                enable_cross_partition_query=True,
            )
            data = documentIterator.next()
            schema = {}
            for key in data.keys():
                if key not in ["_rid", "_self", "_etag", "_attachments", "_ts"]:
                    schema[key] = type(data[key]).__name__
            return {"result": schema, "query": "SELECT TOP 1 * FROM c"}
        except Exception as e:
            print(f"Error retrieving collection schema: {e}")
            return None


    @kernel_function(
        name="get_databases",
        description="Get a list of all databases in the Cosmos DB account"
    )
    def get_databases(self):
        databases = self.cosmos_client.list_databases()
        result = [database['id'] for database in list(databases)]
        return result
    
    @kernel_function(
        name="get_collections",
        description="Get the collections of a database"
    )
    def get_collections_of_database(self, database: str):
        db_client = self.cosmos_client.get_database_client(database)
        containers = db_client.list_containers()
        return [container['id'] for container in containers]

    @kernel_function(
        name="get_document_by_field_filter_tool",
        description="Tool to get a document from a specified database and collection."
    )
    def get_document_by_field_filter_tool(
        self, 
        database: str, 
        collection: str, 
        field: str, 
        value: str, 
        fields: List[str] = ["*"]
    ):
        document = self.get_document_by_field_filter(database, collection, field, value, fields)
        if document:
            return document
        else:
            return "Document not found"
        
    @kernel_function(
        name="get_count_of_documents_tool",
        description="Tool to get the count of documents in the specified database and collection."
    )
    def get_count_of_documents_tool(self, database: str, collection: str):
        count = self.get_count_of_documents(database, collection)
        if count:
            return count
        else:
            return "Count not found"
        
    @kernel_function(
        name="get_collection_schema_tool",
        description="Tool to get the schema of the specified database and collection."
    )
    def get_collection_schema_tool(self, database: str, collection: str):
        schema = self.get_collection_schema(database, collection)
        if schema:
            return schema
        else:
            return "Schema not found"