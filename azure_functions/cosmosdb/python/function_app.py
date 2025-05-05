import json
import azure.functions as func
from azure.core.paging import ItemPaged
from typing import Dict, Any, List
import os

from dotenv import load_dotenv

load_dotenv()

from azure.cosmos import CosmosClient

from tool_property import ToolProperty

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

DATABASE_TOOL_PROPERTY = ToolProperty("database", "string", "The name of the Cosmos DB database.")
CONTAINER_TOOL_PROPERTY = ToolProperty("container", "string", "The name of the container in a Cosmos DB database.")
FIELD_TOOL_PROPERTY = ToolProperty("field", "string", "The field to be used in the query.")
VALUE_TOOL_PROPERTY = ToolProperty("value", "string", "The value to be used in the query.")
FIELDS_TOOL_PROPERTY = ToolProperty("fields", "string", "The fields to be used in the query.")
SAMPLE_N_TOOL_PROPERTY = ToolProperty("n", "integer", "The number of sample documents to retrieve.")

GET_DATABASES_PROPERTIES = []

GET_CONTAINER_PROPERTIES = [
    DATABASE_TOOL_PROPERTY,
]

GET_COLLECTION_PROPERTIES = [
    DATABASE_TOOL_PROPERTY,
    CONTAINER_TOOL_PROPERTY,
    FIELD_TOOL_PROPERTY,
    VALUE_TOOL_PROPERTY,
    FIELDS_TOOL_PROPERTY,
]

GET_COUNT_PROPERTIES = [
    DATABASE_TOOL_PROPERTY,
    CONTAINER_TOOL_PROPERTY
]

GET_SCHEMA_PROPERTIES = [
    DATABASE_TOOL_PROPERTY,
    CONTAINER_TOOL_PROPERTY
]

GET_SAMPLE_PROPERTIES = [
    DATABASE_TOOL_PROPERTY,
    CONTAINER_TOOL_PROPERTY,
    SAMPLE_N_TOOL_PROPERTY,
]

GET_DATABASES_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_DATABASES_PROPERTIES])
GET_CONTAINER_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_CONTAINER_PROPERTIES])
GET_COLLECTION_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_COLLECTION_PROPERTIES])
GET_COUNT_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_COUNT_PROPERTIES])
GET_SCHEMA_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_SCHEMA_PROPERTIES])
GET_SAMPLE_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_SAMPLE_PROPERTIES])

cosmosClient = CosmosClient(
    url="https://msmarco-cdb.documents.azure.com:443/",
    credential=os.getenv("AZURE_COSMOSDB_KEY"),
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
    
@app.generic_trigger(
    arg_name="req",
    type="mcpToolTrigger",
    toolName="get_databases",
    description="Get all databases in the Cosmos DB account.",
    toolProperties=GET_DATABASES_PROPERTIES_JSON,
)
def get_databases(req: str) -> str:
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
    
@app.generic_trigger(
    arg_name="req",
    type="mcpToolTrigger",
    toolName="get_containers",
    description="Get all containers in the specified database.",
    toolProperties=GET_CONTAINER_PROPERTIES_JSON,
)
def get_collections_of_database(req: str) -> str:
    db_client = cosmosClient.get_database_client(json.loads(req)["arguments"]["database"])
    containers = db_client.list_containers()
    return [container['id'] for container in containers]

@app.generic_trigger(
    arg_name="req",
    type="mcpToolTrigger",
    toolName="get_document_by_field_filter",
    description="Get a document from the specified database and collection by field filter.",
    toolProperties=GET_COLLECTION_PROPERTIES_JSON,
)
def get_document_by_field_filter_tool(req: str) -> str:
    document = get_document_by_field_filter(json.loads(req)["arguments"]["database"],
                                               json.loads(req)["arguments"]["container"],
                                               json.loads(req)["arguments"]["field"],
                                               json.loads(req)["arguments"]["value"],
                                               json.loads(req)["arguments"]["fields"])
    if document:
        return document
    else:
        return "Document not found"
    
@app.generic_trigger(
    arg_name="req",
    type="mcpToolTrigger",
    toolName="get_count_of_documents",
    description="Get the count of documents in the specified database and collection.",
    toolProperties=GET_COUNT_PROPERTIES_JSON,
)
def get_count_of_documents_tool(req: str) -> str:
    count = get_count_of_documents(json.loads(req)["arguments"]["database"],
                                   json.loads(req)["arguments"]["container"])
    if count:
        return count
    else:
        return "Count not found"
    
@app.generic_trigger(
    arg_name="req",
    type="mcpToolTrigger",
    toolName="get_collection_schema",
    description="Get the schema of the specified database and collection.",
    toolProperties=GET_SCHEMA_PROPERTIES_JSON,
)
def get_collection_schema_tool(req: str) -> str:
    schema = get_collection_schema(json.loads(req)["arguments"]["database"],
                                   json.loads(req)["arguments"]["container"])
    if schema:
        return schema
    else:
        return "Schema not found"

@app.generic_trigger(
    arg_name="req",
    type="mcpToolTrigger",
    toolName="get_sample_documents",
    description="Get a sample document from the specified database and collection.",
    toolProperties=GET_SAMPLE_PROPERTIES_JSON,
)
def get_sample_documents(req):
    """
    Get a sample document from the specified database and collection.
    """
    try:
        database_proxy = cosmosClient.get_database_client(json.loads(req)["arguments"]["database"])
        container = database_proxy.get_container_client(json.loads(req)["arguments"]["container"])
        documentIterator: ItemPaged[Dict[str, Any]] = container.query_items(
            query=f"SELECT TOP {json.loads(req)['arguments']['n']} * FROM c",
            enable_cross_partition_query=True,
        )
        results = []
        for item in documentIterator:
            results.append(item)
        return {"result": results, "query": f"SELECT TOP {json.loads(req)['arguments']['n']} c.passage FROM c"}
    except Exception as e:
        print(f"Error retrieving sample document: {e}")
        return None