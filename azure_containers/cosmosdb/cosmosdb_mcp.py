from azure.cosmos import CosmosClient, ContainerProxy
from azure.core.paging import ItemPaged
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP
from azure.identity import DefaultAzureCredential
from embeddings import generate_embeddings
import requests
import os

mcp = FastMCP("cosmosdb")

cosmosClient = None
ACCOUNT_KEY = os.getenv("ACCOUNT_KEY")
ACCOUNT_ENDPOINT = os.getenv("ACCOUNT_ENDPOINT")
EMBEDDING_DIMENSIONS = os.getenv("openai_embeddings_dimensions")

if ACCOUNT_KEY is not None:
    cosmosClient = CosmosClient(
        url=ACCOUNT_ENDPOINT,
        credential=ACCOUNT_KEY,
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
    
# Function to perform vector search in container
def cdb_vector_search(container_passage: ContainerProxy, query_vector, top_k=5):
    # Perform vector search
    return container_passage.query_items( 
            query='SELECT TOP @top_k c.pid, c.passage, VectorDistance(c.embedding,@embedding) AS SimilarityScore FROM c ORDER BY VectorDistance(c.embedding,@embedding)', 
            parameters=[ 
                {"name": "@embedding", "value": query_vector},
                {"name": "@top_k", "value": top_k},
            ], enable_cross_partition_query=True)

#Function to perform hybrid search in container
def cdb_hybrid_search(container_passage: ContainerProxy, query_text, query_vector, top_k=5):
    query = f'SELECT TOP {top_k} c.pid, c.passage FROM c ORDER BY RANK RRF(FullTextScore(c.passage, {query_text.split()}), VectorDistance(c.embedding, {query_vector}))'
    return container_passage.query_items(
            query = query, 
            enable_cross_partition_query=True)

def perform_reranking(documents: List[str], query: str) -> Dict[str, Any]:
    """
    Perform semantic reranking on the given documents based on the query.
    """
    try:
        response = requests.post("https://reranker-api-h2b5czhkfkcphnf4.westus3-01.azurewebsites.net/rerank", 
                            json={"documents": documents, "query": query, "return_documents": True})
                            #headers=headers)
        response.raise_for_status()
        reranked_documents = response.json()
        return reranked_documents
    except Exception as e:
        print(f"Error performing semantic reranking: {e}")
        return {"result": [], "error": str(e)}

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
    
@mcp.tool(
    name="do_vector_search",
    description="Get the matching documents using vector search."
)
def do_vector_search(database: str, container: str, query: str, top_k: int = 5, similarity_threshold: float = 0.5):
    """
    Get the matching documents using vector search.
    """
    try:
        database_proxy = cosmosClient.get_database_client(database)
        container_proxy = database_proxy.get_container_client(container)
        query_vector = generate_embeddings(query)

        results = cdb_vector_search(container_proxy, query_vector, top_k)
        result = []
        for item in results:
            if item['SimilarityScore'] >= similarity_threshold:
                result.append(item['passage'])

        return {"result": result, "query": f'SELECT TOP {top_k} c.pid, c.passage, VectorDistance(c.embedding,{query_vector}) AS SimilarityScore FROM c ORDER BY VectorDistance(c.embedding, {query_vector})'}
    except Exception as e:
        print(f"Error retrieving matching documents: {e}")
        return None
    
@mcp.tool(
    name="do_hybrid_search",
    description="Get the matching documents using hybrid search."
)
def do_hybrid_search(database: str, container: str, query: str, top_k: int):
    """
    Get the matching documents using hybrid search.
    """
    try:
        database_proxy = cosmosClient.get_database_client(database)
        container_proxy = database_proxy.get_container_client(container)
        query_vector = generate_embeddings(query)

        results = cdb_hybrid_search(container_proxy, query, query_vector, top_k)
        result = []
        for item in results:
            result.append(item['passage'])

        return {"result": result, "query": f'SELECT TOP {top_k} c.pid, c.passage FROM c ORDER BY RANK RRF(FullTextScore(c.passage, {query.split()}), VectorDistance(c.embedding, {query_vector}))'}
    except Exception as e:
        print(f"Error retrieving matching documents: {e}")
        return None

@mcp.tool(
    name="get_embedding",
    description="Get the embedding of the specified text."
)
def get_embedding(text: str) -> str:
    """
    Get the embedding of the specified text.
    """
    try:
        embedding = generate_embeddings(text)
        if len(embedding) == EMBEDDING_DIMENSIONS:
            return {"result": embedding, "embedding_model": os.getenv("openai_embeddings_model")}
        else:
            return {"error": "Embedding generation using openai large model failed."}
    except Exception as e:
        print(f"Error retrieving embedding: {e}")
        return None
    
@mcp.tool(
    name="get_semantic_reranking",
    description="Get the semantic reranking for set of documents and specified query."
)
def get_semantic_reranking(documents: List[str], query: str) -> str:
    """
    Get the semantic reranking for set of documents and specified query.
    """
    try:
        # Assuming documents is a list of strings
        reranked_documents = perform_reranking(documents, query)
        return {"result": reranked_documents}
    except Exception as e:
        print(f"Error retrieving semantic reranking: {e}")
        return None