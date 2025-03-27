# Web Application for a Chat Application using Model Context Protocol (MCP)

## Context

This is a web application that will be using as a Chat Application to serve as a Model Context Protocol (MCP) host and therefore allow the LLM to get real time data.

## Prerequisites

In order to deploy this you will need to have Python install and the following packages

- chainlit
- logging
- dotenv
- azure-ai-projects
- azure-identity
- semantic-kernel

## Deploy locally

To deploy your application locally you can run

```powershell
python -m chainlit run .\chat_app.py
```

From your terminal.

## References

- [Deploy Your First Azure AI Agent Service on Azure App Service](https://techcommunity.microsoft.com/blog/azure-ai-services-blog/deploy-your-first-azure-ai-agent-service-on-azure-app-service/4396173)