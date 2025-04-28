using Azure.Identity;
using Microsoft.Azure.Cosmos;
using Microsoft.Azure.Functions.Worker.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var builder = FunctionsApplication.CreateBuilder(args);

builder.ConfigureFunctionsWebApplication();
builder.EnableMcpToolMetadata();

builder.Services.AddTransient((_) =>
{
    string? endpoint = Environment.GetEnvironmentVariable("ACCOUNT_ENDPOINT");
    if (string.IsNullOrEmpty(endpoint))
    {
        throw new InvalidOperationException("Environment variable ACCOUNT_ENDPOINT is not set.");
    }

    string? accountKey = Environment.GetEnvironmentVariable("ACCOUNT_KEY");
    if (!string.IsNullOrEmpty(accountKey))
    {
        return new CosmosClient(endpoint, accountKey);
    }

    return new CosmosClient(endpoint, new DefaultAzureCredential());
});

builder.Build().Run();
