# .NET MCP Azure Functions

This is an equivalent implementation in .NET 8 for defining tools that
connect to a CosmosDB database to perform queries against it using a
chat tool like Chainlit.

# Local Execution

Follow the below steps to run the function app locally:

1. Make sure you have the .NET 8 SDK and the latest Azure Functions Core Tools installed
1. Clone the repo
1. Open this folder in VS Code
1. If not already, install the recommended extensions and wait for the solution to load
1. There are two options to run the app:
    1. If no debug is needed, run `func start` in the terminal
    1. To run with the debugger attached, press F5 or go to *Run and Debug*
    and run the `Attach to .NET Functions` configuration
1. Wait until the `MCP server SSE endpoint` log shows up
1. Copy and paste the URL into a frontend like Chainlit or MCP Inspector with the
`SSE` transport

**Note:** the CosmosDB endpoint can be changed in the `local.settings.json` file with
the `ACCOUNT_ENDPOINT` variable, which should be a URL pointing to a CosmosDB account.

**Note 2:** make sure you have RBAC access to the CosmosDB account you are trying to
get connected to. Another alternative is to specify the `ACCOUNT_KEY` environment
variable in `local.settings.json`.

# Azure deployments

Follow the below steps to deploy and run the function app in Azure:

1. Open this folder in VS Code
1. Make sure you have the Azure Functions extension installed
1. Go to the Azure menu in VS Code
1. Create a **.NET 8 Isolated** Function App in Azure
    1. Under the *Settings > Environment Variables* section, specify the `ACCOUNT_ENDPOINT`
    environment variable with the desired CosmosDB account endpoint
1. Right click the project in the Workspace section and click *Deploy to Azure*
1. Follow the steps to select the resource group and function app
1. Once the deployment completes you will need to copy the `mcp_extension` key,
located in [Function App] > Functions > App Keys > System Keys
1. Format the following template URL and use a frontend to connect to it:
    ```
    https://<Function App Name>.azurewebsites.net/runtime/webhooks/mcp/sse?code=<mcp_extension key>
    ```
