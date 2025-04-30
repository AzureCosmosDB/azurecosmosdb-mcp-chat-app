# Building a chat application serving as a MCP client in Azure using Azure App Services and Azure Container Applications to host the MCP server

## Context

As part of this repository, we are building a chat application totally hosted in Azure that will work as a chat application supporting Model Context Protocol (MCP) Servers hosted in Azure using Python. With this, you can get an idea about how to deploy a chat application integrated with MCP using Azure resources. For the MCP client application we will be using `chainlit` which is a Python library used to build chat applications, this application will be hosted as an Azure App Service. On the other side, we will use an Azure Container Application to deploy our MCP Server that will help us to get information from Azure Cosmos DB authenticating via Managed Identities.

## Deploying the MCP Server

All code needed for the MCP server is in folder `azure_containers/cosmosdb` where we define a MCP server that will be exposing an SSE endpoint for us to connect to it and use it in our LLMs. You can deploy it locally during testing or in Azure itself.

Before going to the deployment, you need to create a `.env` file in the root of the folder and add the following variables:

```powershell
ACCOUNT_KEY=<Your Azure Cosmos DB Account Key>
ACCOUNT_ENDPOINT=<You Azure Cosmos DB Account endpoint>
```

### Local deployment

For the local deployment we will be using Docker. For this, you can bring up the MCP server with the following commands which will build the container and then bring it up locally.

```powershell
docker-compose build
docker-compose up -d
```

After this, your MCP server will be running in endpoint [http://localhost:5000/](http://localhost:5000/). You will be able to connect to it from our MCP client application.

### Deployment in Azure

To deploy this container to Azure, you can use VSCode to connect to your Azure subscription and deploy the container using the extension ["Azure Container Apps"](https://marketplace.visualstudio.com/items/?itemName=ms-azuretools.vscode-azurecontainerapps). Before that, you will need to create a Azure Container Application in your Azure subscription so that you can see it from VSCode.

Before going to the deployment, you need to create a `.env` file in the root of the folder and add the following variables:

```powershell
CHAT_MODEL_NAME=<The name of your GPT model in Azure AI Foundry>
CHAT_MODEL_API_KEY=<The key to use the deployment of the GPT model in Azure AI Foundry>
CHAT_MODEL_BASE_URL=<The base URL of the GPT chat model in Azure AI Foundry>
CHAT_MODEL_API_VERSION="2025-01-01-preview"
```

## Deploying the MCP Client 

All code needed for the MCP client is in folder `mcp_client/` where you can find the usage of the library `chainlit` to build the chat application and then connect to the MCP server hosted in Azure. To deploy it, you can do it locally or in Azure.

### Local deployment

To deploy it locally, you might need to install all the required packages in your devbox first by running `pip install -r requirements.txt` and then you should be able to run the client running:

```powershell

python -m chainlit run .\chat_app.py
```

After this, the MCP client will be available in [http://localhost:8000/](http://localhost:8000/). There you can click the plug-in button and set the SSE endpoint of your MCP server; could be the one of the Azure Container App or the local endpoint, in any of them you need to add the suffix /sse.

### Deployment to Azure

To deploy this App Service in Azure you can use VSCode and the extension called ["Azure App Service"](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azureappservice) to deploy your app service with this code. However, before deploying it you need to create an Azure App Service in your subscription.