import json
import os
import azure.functions as func

from azure.core.paging import ItemPaged
from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from azure.cosmos import CosmosClient, ContainerProxy
from tool_property import ToolProperty
import requests
from embeddings import generate_embeddings

load_dotenv()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

DATABASE_TOOL_PROPERTY = ToolProperty("database", "string", "The name of the Cosmos DB database.")
CONTAINER_TOOL_PROPERTY = ToolProperty("container", "string", "The name of the container in a Cosmos DB database.")
FIELD_TOOL_PROPERTY = ToolProperty("field", "string", "The field to be used in the query.")
VALUE_TOOL_PROPERTY = ToolProperty("value", "string", "The value to be used in the query.")
FIELDS_TOOL_PROPERTY = ToolProperty("fields", "string", "The fields to be used in the query.")
SAMPLE_N_TOOL_PROPERTY = ToolProperty("n", "integer", "The number of sample documents to retrieve.")
QUERY_TOOL_PROPERTY = ToolProperty("query", "string", "The query provided by the user.")
TOP_K_TOOL_PROPERTY = ToolProperty("top_k", "integer", "The number of top K results to retrieve.")
SIMILARITY_THRESHOLD_TOOL_PROPERTY = ToolProperty("similarity_threshold", "string", "The similarity threshold for the vector query.")
DOCUMENTS_LIST_TOOL_PROPERTY = ToolProperty("documents", "string", "The List of strings of documents to be reranked which are returned from either vector search or hybrid search.")

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
    FIELDS_TOOL_PROPERTY
]

VECTOR_SEARCH_PROPERTIES = [
    DATABASE_TOOL_PROPERTY,
    CONTAINER_TOOL_PROPERTY,
    QUERY_TOOL_PROPERTY,
    TOP_K_TOOL_PROPERTY,
    SIMILARITY_THRESHOLD_TOOL_PROPERTY,
]

HYBRID_SEARCH_PROPERTIES = [
    DATABASE_TOOL_PROPERTY,
    CONTAINER_TOOL_PROPERTY,
    QUERY_TOOL_PROPERTY,
    TOP_K_TOOL_PROPERTY
]

SEMANTIC_RERANKING_PROPERTIES = [
    DOCUMENTS_LIST_TOOL_PROPERTY,
    QUERY_TOOL_PROPERTY
]

EMBEDDINGS_PROPERTIES = [
    QUERY_TOOL_PROPERTY,
]

GET_DATABASES_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_DATABASES_PROPERTIES])
GET_CONTAINER_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_CONTAINER_PROPERTIES])
GET_COLLECTION_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_COLLECTION_PROPERTIES])
GET_COUNT_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_COUNT_PROPERTIES])
GET_SCHEMA_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_SCHEMA_PROPERTIES])
GET_SAMPLE_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in GET_SAMPLE_PROPERTIES])
VECTOR_SEARCH_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in VECTOR_SEARCH_PROPERTIES])
HYBRID_SEARCH_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in HYBRID_SEARCH_PROPERTIES])
SEMANTIC_RERANKING_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in SEMANTIC_RERANKING_PROPERTIES])
EMBEDDINGS_PROPERTIES_JSON = json.dumps([prop.to_dict() for prop in EMBEDDINGS_PROPERTIES])

cosmosClient = CosmosClient(
    url=os.getenv("AZURE_COSMOSDB_ENDPOINT"),
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

def get_document_by_field_filter(database: str, collection: str, field: str, value: str, fields: str =""):
    """
    Get a document from the specified database and collection.
    """
    try:
        database_proxy = cosmosClient.get_database_client(database)
        container = database_proxy.get_container_client(collection)
        fields = list(map(lambda x: f"c.{x}", fields.split(","))) if fields != "" else ["*"]
        result: ItemPaged[Dict[str, Any]] = container.query_items(
            query=f'SELECT {",".join(fields)} FROM c WHERE c.{field} = "{value}"',
            enable_cross_partition_query=True,
        )
        data = result.next()
        return {"result": data, "query": f'SELECT {",".join(fields)} FROM c WHERE c.{field} = "{value}"'}
    except Exception as e:
        print(f"Error retrieving document: {e}")
        return None

def get_sample_documents(database: str, collection: str, n_sample = 5, fields: str = ""):
    """
    Get a document from the specified database and collection.
    """
    try:
        database_proxy = cosmosClient.get_database_client(database)
        container = database_proxy.get_container_client(collection)
        fields = list(map(lambda x: f"c.{x}", fields.split(","))) if fields != "" else ["*"]
        result: ItemPaged[Dict[str, Any]] = container.query_items(
            query=f'SELECT TOP {n_sample} {",".join(fields)} FROM c',
            enable_cross_partition_query=True,
        )
        results = []
        for item in result:
            results.append(item)
        return {"result": results, "query": f'SELECT TOP {n_sample} {",".join(fields)} FROM c'}
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
    
# Function to perform vector search in container
def cdb_vector_search(container_passage: ContainerProxy, query_vector, top_k=5):
    # Perform vector search
    return container_passage.query_items( 
            query='SELECT TOP @top_k c.pid, c.passage, VectorDistance(c.embedding,@embedding) AS SimilarityScore FROM c ORDER BY VectorDistance(c.embedding,@embedding)', 
            parameters=[ 
                {"name": "@embedding", "value": query_vector},
                {"name": "@top_k", "value": top_k},
            ], enable_cross_partition_query=True)

# Function to perform hybrid search in container
def cdb_hybrid_search(container_passage: ContainerProxy, query_text, query_vector, top_k=5):
    query = f'SELECT TOP {top_k} c.pid, c.passage FROM c ORDER BY RANK RRF(FullTextScore(c.passage, {query_text.split()}), VectorDistance(c.embedding, {query_vector}))'
    return container_passage.query_items(
            query = query, 
            enable_cross_partition_query=True)

# Function to perform semantic reranking
def perform_reranking(documents: List[str], query: str) -> Dict[str, Any]:
    """
    Perform semantic reranking on the given documents based on the query.
    """
    try:
        response = requests.post("https://reranker-api-h2b5czhkfkcphnf4.westus3-01.azurewebsites.net/rerank", 
                            json={"documents": documents, "query": query, "return_documents": True})
        
        response.raise_for_status()
        reranked_documents = response.json()
        return reranked_documents
    except Exception as e:
        print(f"Error performing semantic reranking: {e}")
        return {"result": [], "error": str(e)}
    
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
def get_sample_documents_tool(req):
    """
    Get a sample document from the specified database and collection.
    """
    try:
        database = json.loads(req)["arguments"]["database"]
        container = json.loads(req)["arguments"]["container"]
        n_sample = json.loads(req)["arguments"]["n"]
        fields = json.loads(req)["arguments"]["fields"] if "fields" in json.loads(req)["arguments"] else ""

        return get_sample_documents(database, container, n_sample, fields)
    except Exception as e:
        print(f"Error retrieving sample document: {e}")
        return None
    
@app.generic_trigger(
    arg_name="req",
    type="mcpToolTrigger",
    toolName="vector_search",
    description="Perform vector search in the specified database and collection.",
    toolProperties=VECTOR_SEARCH_PROPERTIES_JSON,
)
def vector_search_tool(req: str) -> str:
    """
    Perform vector search in the specified database and collection.
    """
    try:
        database = json.loads(req)["arguments"]["database"]
        container = json.loads(req)["arguments"]["container"]
        query = json.loads(req)["arguments"]["query"]
        top_k = json.loads(req)["arguments"]["top_k"] if "top_k" in json.loads(req)["arguments"] else 5
        similarity_threshold = json.loads(req)["arguments"]["similarity_threshold"] if "similarity_threshold" in json.loads(req)["arguments"] else 0.3

        database_proxy = cosmosClient.get_database_client(database)
        container_passage = database_proxy.get_container_client(container)
        query_vector = generate_embeddings(query)

        results = cdb_vector_search(container_passage, query_vector, top_k)
        result = []
        for item in results:
            if float(item['SimilarityScore']) >= similarity_threshold:
                result.append(item['passage'])

        return {"result": result, "query": f"SELECT TOP @top_k c.pid, c.passage FROM c ORDER BY VectorDistance(c.embedding,@embedding)"}
    except Exception as e:
        print(f"Error performing vector search: {e}")
        return None
    
@app.generic_trigger(
    arg_name="req",
    type="mcpToolTrigger",
    toolName="hybrid_search",
    description="Perform hybrid search in the specified database and collection.",
    toolProperties=HYBRID_SEARCH_PROPERTIES_JSON,
)
def hybrid_search_tool(req: str) -> str:
    """
    Perform hybrid search in the specified database and collection.
    """
    try:
        database = json.loads(req)["arguments"]["database"]
        container = json.loads(req)["arguments"]["container"]
        query = json.loads(req)["arguments"]["query"]
        top_k = json.loads(req)["arguments"]["top_k"] if "top_k" in json.loads(req)["arguments"] else 5

        database_proxy = cosmosClient.get_database_client(database)
        container_passage = database_proxy.get_container_client(container)
        query_vector = generate_embeddings(query)

        results = cdb_hybrid_search(container_passage, query, query_vector, top_k)
        result = []
        for item in results:
            result.append(item['passage'])

        return {"result": result, "query": f"SELECT TOP @top_k c.pid, c.passage FROM c ORDER BY RANK RRF(FullTextScore(c.passage, ['your','query', 'here']), VectorDistance(c.embedding, @embedding))"}
    except Exception as e:
        print(f"Error performing hybrid search: {e}")
        return None
    
@app.generic_trigger(
    arg_name="req",
    type="mcpToolTrigger",
    toolName="semantic_reranking",
    description="Get the semantic reranking for set of documents and specified query.",
    toolProperties=SEMANTIC_RERANKING_PROPERTIES_JSON,
)
def semantic_reranking_tool(req: str) -> str:
    """
    Get the semantic reranking for set of documents and specified query.
    """
    try:
        documents = json.loads(req)["arguments"]["documents"]
        query = json.loads(req)["arguments"]["query"]

        reranked_documents = perform_reranking(documents, query)
        return {"result": reranked_documents}
    except Exception as e:
        print(f"Error performing semantic reranking: {e}")
        return None
    
@app.generic_trigger(
    arg_name="req",
    type="mcpToolTrigger",
    toolName="get_embeddings",
    description="Get the embeddings for the specified input.",
    toolProperties=EMBEDDINGS_PROPERTIES_JSON,
)
def get_embeddings_tool(req: str) -> str:
    """
    Get the embeddings for the specified input.
    """
    try:
        query = json.loads(req)["arguments"]["query"]
        embeddings = generate_embeddings(query)
        return {"result": embeddings, "embedding_model": os.getenv("openai_embeddings_model")}
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return None