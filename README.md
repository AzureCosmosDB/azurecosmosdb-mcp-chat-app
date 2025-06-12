# 🧠 Python MCP Server & Client Example with Azure Cosmos DB

## Overview

This repository contains a complete example of a chat application powered by a **Model Context Protocol (MCP)** server written in Python. It demonstrates how to:

- Build and run an **MCP Server** that interacts with **Azure Cosmos DB for NoSQL**
- Use **`chainlit`** and **`gradio`** as MCP clients to build interactive chat UIs
- Host both server and client **locally** or deploy them to **Azure**

The MCP server exposes tools that let LLM agents insert and query data from Azure Cosmos DB. It uses **Managed Identity** for authentication and assumes the use of **Azure OpenAI** for embeddings and LLM responses (you can modify it to use other providers as needed).

---

## 🛠️ Project Structure

```plaintext
azure_containers/cosmosdb/   # MCP Server using Azure Container Apps
azure_functions/cosmosdb/    # MCP Server using Azure Functions
mcp_client/                  # MCP Client using Chainlit or Gradio
```

---

## 🚀 Deploying the MCP Server

The MCP server exposes an SSE (Server-Sent Events) endpoint that the client connects to. You can run it locally with Docker or deploy it to Azure using Azure Container Apps or Functions.

### 1. Set up environment variables

Create a `.env` file in the root of your server folder with:

```env
ACCOUNT_KEY=<Your Azure Cosmos DB Account Key>
ACCOUNT_ENDPOINT=<Your Azure Cosmos DB Account Endpoint>
```

### 2. Local Deployment (with Docker)

Run the following commands:

```bash
docker-compose build
docker-compose up -d
```

Once running, the MCP Server is available at [http://localhost:5000/](http://localhost:5000/)

### 3. Azure Deployment (Container Apps)

You can deploy via [Azure Container Apps](https://marketplace.visualstudio.com/items/?itemName=ms-azuretools.vscode-azurecontainerapps) using the VS Code extension. Before that:

- Create an Azure Container App in your subscription.
- Then deploy via VS Code.

Update your `.env` with the following GPT model details:

```env
openai_key=<API key for Azure OpenAI model>
openai_endpoint=<Base URL of your Azure OpenAI deployment>
openai_api_version=2025-01-01-preview
openai_embeddings_deployment="text-embedding-3-large-2"
openai_embeddings_model="text-embedding-3-large"
```

---

## 💬 Deploying the MCP Client

The MCP client is located in the `mcp_client/` folder. It uses either `chainlit` or `gradio` to create a front-end chat UI connected to the MCP server.

### 1. Set up environment variables

Same `.env` as above:

```env
CHAT_MODEL_NAME=<Your GPT deployment name>
CHAT_MODEL_API_KEY=<API key for Azure OpenAI model>
CHAT_MODEL_BASE_URL=<Base URL of your Azure OpenAI deployment>
CHAT_MODEL_API_VERSION=2025-01-01-preview
```

### 2. Local Deployment

Install dependencies:

```bash
pip install -r requirements.txt
```

Then run either interface:

**Chainlit:**
```bash
python -m chainlit run chat_app.py
```

**Gradio:**
```bash
python app.py
```

The app runs locally at: [http://localhost:8000/](http://localhost:8000/)

> 💡 Once opened, use the UI plug-in button to set your MCP server SSE endpoint (e.g., `http://localhost:5000/sse` or your Azure-deployed server).

---

### 3. Azure Deployment (App Service)

To deploy to Azure App Service:

- Use the [Azure App Service](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azureappservice) VS Code extension.
- Create an App Service resource in your Azure subscription.
- Deploy the code from `mcp_client/`.

---

## 🔧 Notes & Customization

- This sample assumes usage of **Azure OpenAI** for embeddings and LLMs. To use other providers (e.g., OpenAI, HuggingFace), adjust the API calls accordingly.
- The MCP Server supports **Cosmos DB for NoSQL** only, but you can extend it to other APIs if needed.

---

## 📎 Related Technologies

- [Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/introduction)
- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [Azure App Service](https://learn.microsoft.com/azure/app-service/)
- [Chainlit](https://docs.chainlit.io)
- [Gradio](https://www.gradio.app/)

---

## 📬 Feedback

We welcome contributions and feedback! Please open issues or PRs if you'd like to improve the project or have suggestions.
