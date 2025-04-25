
using System.Text.Json;
using Azure.Identity;
using Microsoft.Azure.Cosmos;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Extensions.Mcp;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json.Linq;

namespace CosmosDbMcpDotnet;

public class MsMarcoFunctions(CosmosClient client, ILogger<MsMarcoFunctions> logger)
{
    private readonly ILogger<MsMarcoFunctions> Logger = logger;

    private readonly CosmosClient CosmosClient = client;

    private readonly List<string> SchemaInternalFields =
    [
        "_rid",
        "_self",
        "_etag",
        "_attachments",
        "_ts"
    ];

    private const string DatabaseParamDescription = "The name of the Cosmos DB database.";
    
    private const string ContainerParamDescription = "The name of the Cosmos DB container.";

    [Function(nameof(GetDatabasesAsync))]
    public async Task<string> GetDatabasesAsync(
        [McpToolTrigger("get_databases", "Gets all databases in the Cosmos DB account.")]
        ToolInvocationContext context
    )
    {
        try
        {
            FeedIterator<DatabaseProperties> databases = CosmosClient.GetDatabaseQueryIterator<DatabaseProperties>();
            List<string> dbs = [];

            while (databases.HasMoreResults)
            {
                FeedResponse<DatabaseProperties> response = await databases.ReadNextAsync();
                foreach (var db in response)
                {
                    dbs.Add(db.Id);
                }
            }

            return string.Join(", ", dbs);
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Error retrieving databases: {error}", ex.Message);
            return ex.Message;
        }
    }

    [Function(nameof(GetContainersAsync))]
    public async Task<string> GetContainersAsync(
        [McpToolTrigger("get_containers", "Gets all containers in the specified database.")]
        ToolInvocationContext context,
        [McpToolProperty("database", "string", DatabaseParamDescription)]
        string database
    )
    {
        try
        {
            Database db = CosmosClient.GetDatabase(database);
            FeedIterator<ContainerProperties> containers = db.GetContainerQueryIterator<ContainerProperties>();
            List<string> containerIds = [];

            while (containers.HasMoreResults)
            {
                FeedResponse<ContainerProperties> response = await containers.ReadNextAsync();
                foreach (var cont in response)
                {
                    containerIds.Add(cont.Id);
                }
            }

            return string.Join(", ", containerIds);
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Error retrieving containers: {error}", ex.Message);
            return ex.Message;
        }
    }

    [Function(nameof(GetDocumentByFieldAsync))]
    public async Task<string> GetDocumentByFieldAsync(
        [McpToolTrigger("get_document_by_field", "Gets a document from the specified database and collection by field filter.")]
        ToolInvocationContext context,
        [McpToolProperty("database", "string", DatabaseParamDescription)]
        string database,
        [McpToolProperty("container", "string", ContainerParamDescription)]
        string container,
        [McpToolProperty("field", "string", "The field to be used in the query.")]
        string field,
        [McpToolProperty("value", "string", "The value to be used in the query.")]
        string value,
        [McpToolProperty("fields", "string", "Comma-separated fields to be used in the query.")]
        string fields = "*"
    )
    {
        try
        {
            Database db = CosmosClient.GetDatabase(database);
            Container cont = db.GetContainer(container);

            string containerFields = fields != "*"
                ? string.Join(",", fields.Split(',').Select(field => $"c.{field}"))
                : "*";

            string query = $"SELECT {containerFields} FROM c WHERE c.{field} = '{value}'";
            FeedIterator<object> items = cont.GetItemQueryIterator<object>(queryText: query);
            List<string> results = [];

            while (items.HasMoreResults)
            {
                FeedResponse<object> response = await items.ReadNextAsync();
                foreach (var item in response)
                {
                    results.Add(item.ToString() ?? "(null)");
                }
            }

            return JsonSerializer.Serialize(new { result = results, query });
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Error retrieving documents: {error}", ex.Message);
            return ex.Message;
        }
    }

    [Function(nameof(GetCountOfDocumentsAsync))]
    public async Task<string> GetCountOfDocumentsAsync(
        [McpToolTrigger("get_count_of_documents", "Gets the count of documents in the specified database and collection.")]
        ToolInvocationContext context,
        [McpToolProperty("database", "string", DatabaseParamDescription)]
        string database,
        [McpToolProperty("container", "string", ContainerParamDescription)]
        string container
    )
    {
        try
        {
            Database db = CosmosClient.GetDatabase(database);
            Container cont = db.GetContainer(container);

            string query = $"SELECT VALUE COUNT(1) FROM c";
            FeedIterator<int> items = cont.GetItemQueryIterator<int>(queryText: query);
            int result = 0;

            if (items.HasMoreResults)
            {
                FeedResponse<int> response = await items.ReadNextAsync();
                result = response.First();
            }

            return JsonSerializer.Serialize(new { result, query });
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Error retrieving document count: {error}", ex.Message);
            return ex.Message;
        }
    }

    [Function(nameof(GetCollectionSchemaAsync))]
    public async Task<string> GetCollectionSchemaAsync(
        [McpToolTrigger("get_collection_schema", "Gets the schema of the specified collection.")]
        ToolInvocationContext context,
        [McpToolProperty("database", "string", DatabaseParamDescription)]
        string database,
        [McpToolProperty("container", "string", ContainerParamDescription)]
        string container
    )
    {
        try
        {
            Database db = CosmosClient.GetDatabase(database);
            Container cont = db.GetContainer(container);

            string query = $"SELECT TOP 1 * FROM c";
            FeedIterator<object> items = cont.GetItemQueryIterator<object>(queryText: query);
            Dictionary<string, string> schema = [];

            if (items.HasMoreResults)
            {
                FeedResponse<object> response = await items.ReadNextAsync();
                var fields = (IDictionary<string, JToken>)response.Resource.First();
                foreach ((string key, JToken value) in fields)
                {
                    if (SchemaInternalFields.Contains(key))
                    {
                        continue;
                    }

                    schema[key] = value.Type.ToString();
                }
            }

            return JsonSerializer.Serialize(new { schema });
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Error retrieving collection schema: {error}", ex.Message);
            return ex.Message;
        }
    }

    [Function(nameof(GetSampleDocumentsAsync))]
    public async Task<string> GetSampleDocumentsAsync(
        [McpToolTrigger("get_sample_documents", "Gets sample documents from the specified database and collection.")]
        ToolInvocationContext context,
        [McpToolProperty("database", "string", DatabaseParamDescription)]
        string database,
        [McpToolProperty("container", "string", ContainerParamDescription)]
        string container,
        [McpToolProperty("count", "integer", "The number of sample documents to retrieve.")]
        int count = 5
    )
    {
        try
        {
            Database db = CosmosClient.GetDatabase(database);
            Container cont = db.GetContainer(container);

            string query = $"SELECT TOP {count} * FROM c";
            FeedIterator<object> items = cont.GetItemQueryIterator<object>(queryText: query);
            List<string> results = [];

            while (items.HasMoreResults)
            {
                FeedResponse<object> response = await items.ReadNextAsync();
                foreach (var item in response)
                {
                    results.Add(item.ToString() ?? "(null)");
                }
            }

            return JsonSerializer.Serialize(new { result = results, query });
        }
        catch (Exception ex)
        {
            Logger.LogError(ex, "Error retrieving sample documents: {error}", ex.Message);
            return ex.Message;
        }
    }
}
