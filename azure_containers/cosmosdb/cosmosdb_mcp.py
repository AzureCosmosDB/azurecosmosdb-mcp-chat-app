from azure.cosmos import CosmosClient
from azure.core.paging import ItemPaged
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP
from azure.identity import DefaultAzureCredential

import os

mcp = FastMCP("cosmosdb")

cosmosClient = None
account_key = os.getenv("ACCOUNT_KEY")

if account_key is not None:
    account_key = account_key.lower()
    cosmosClient = CosmosClient(
        url=os.getenv("ACCOUNT_ENDPOINT"),
        credential=account_key,
    )
else:
    cosmosClient = CosmosClient(
        url=os.getenv("ACCOUNT_ENDPOINT"),
        credential=DefaultAzureCredential(),
    )

def get_count_of_documents(database: str, collection: str):
    """
    Get the count of documents in the specified database and collection.
    """
    try:
        database_proxy = cosmosClient.get_database_client(database)
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

def get_document_by_field_filter(database: str, collection: str, field: str, value: str, fields: List[str] = ["*"]):
    """
    Get a document from the specified database and collection.
    """
    try:
        database_proxy = cosmosClient.get_database_client(database)
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

def get_collection_schema(database: str, collection: str):
    """
    Get the schema of the specified database and collection.
    """
    try:
        database_proxy = cosmosClient.get_database_client(database)
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
    
@mcp.tool(
    name="get_databases",
    description="Get all databases in the Cosmos DB account."
)
def get_databases():
    """
    Get all databases in the Cosmos DB account.
    """
    try:
        databases = cosmosClient.list_databases()
        database_list = [db['id'] for db in databases]
        return ",".join(database_list)
    except Exception as e:
        print(f"Error retrieving databases: {e}")
        return str(e)
    
@mcp.tool(
    name="get_collections_of_database",
    description="Get all collections in the specified database."
)
def get_collections_of_database(database: str) -> str:
    """
    Get all collections in the specified database.
    """
    db_client = cosmosClient.get_database_client(database)
    containers = db_client.list_containers()
    return [container['id'] for container in containers]

@mcp.tool(
    name="get_document_by_field_filter",
    description="Get a document from the specified database and collection by field filter."
)
def get_document_by_field_filter_tool(database: str, container: str, field: str, value: str, fields: str = "*") -> str:
    """
    Get a document from the specified database and collection by field filter.
    """
    document = get_document_by_field_filter(database, container, field, value, fields.split(","))
    if document:
        return document
    else:
        return "Document not found"
    
@mcp.tool(
    name="get_count_of_documents",
    description="Get the count of documents in the specified database and collection."
)
def get_count_of_documents_tool(database: str, container: str) -> str:
    """
    Get the count of documents in the specified database and collection.
    """
    count = get_count_of_documents(database, container)
    if count:
        return count
    else:
        return "Count not found"
    
@mcp.tool(
    name="get_collection_schema",
    description="Get the schema of the specified database and collection."
)
def get_collection_schema_tool(database: str, container: str) -> str:
    """
    Get the schema of the specified database and collection.
    """
    schema = get_collection_schema(database, container)
    if schema:
        return schema
    else:
        return "Schema not found"

@mcp.tool(
    name="get_sample_documents",
    description="Get a sample document from the specified database and collection."
)
def get_sample_documents(database: str, container: str, n: int = 1, fields: List = ["*"]) -> str:
    """
    Get a sample document from the specified database and collection.
    """
    try:
        database_proxy = cosmosClient.get_database_client(database)
        container = database_proxy.get_container_client(container)
        fields = list(map(lambda x: f"c.{x}", fields)) if fields != ["*"] else ["*"]
        documentIterator: ItemPaged[Dict[str, Any]] = container.query_items(
            query=f"SELECT TOP {n} {','.join(fields)} FROM c",
            enable_cross_partition_query=True,
        )
        results = []
        for item in documentIterator:
            results.append(item)
        return {"result": results, "query": f"SELECT TOP {n} c.passage FROM c"}
    except Exception as e:
        print(f"Error retrieving sample document: {e}")
        return None