import asyncio
import gradio as gr
import os
import json
import pytz
import uuid

from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client
from typing import List, Dict, Any, Union
from gradio.components.chatbot import ChatMessage
from openai import AsyncAzureOpenAI
from azure.cosmos import CosmosClient, ContainerProxy, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from embeddings import generate_embeddings
from datetime import datetime

class MCPClientWrapper:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        asyncio.set_event_loop(self.loop)
        self.session = None
        self.exit_stack: AsyncExitStack = None
        self.tools = []
        self.deployment_name = os.environ["CHAT_MODEL_NAME"]
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=os.environ["CHAT_MODEL_BASE_URL"],
            api_key=os.environ["CHAT_MODEL_API_KEY"],
            api_version=os.environ["CHAT_MODEL_API_VERSION"]
        )
        self.chat_history_account = CosmosClient(
            url=os.getenv("COSMOSDB_ACCOUNT_ENDPOINT"),
            credential=os.getenv("COSMOSDB_ACCOUNT_KEY")
        )

    def connect(self, server_sse_url, mcp_tools, key):
        # None and "" are falsy values so we just do this oneliner
        headers = { "x-functions-key": key } if key else None

        response = self.loop.run_until_complete(
            self._connect_mcp_server(server_sse_url, mcp_tools, headers)
        )
        return response

    def process_message(self, message: str,  history: List[Union[Dict[str, Any], ChatMessage]], user: str):
        history.append({"role": "user", "content": message})
        self.loop.run_until_complete(self._process_query(message, history, user))
        return history, gr.Textbox(value="")
    
    def load_user_messages(self, user: str) -> List[Union[Dict[str, Any], ChatMessage]]:
        try: 
            db = self.chat_history_account.get_database_client("agent_threads")
            container: ContainerProxy = db.get_container_client("chat_history")
            items = container.query_items(
                query="SELECT * FROM c WHERE c.user = @user ORDER BY c.timestamp ASC",
                parameters=[
                    {"name": "@user", "value": user}
                ],
                enable_cross_partition_query=True
            )
            messages = []
            for item in items:
                messages.append({
                    "role": "user",
                    "content": item["user_message"]
                })
                messages.append({
                    "role": "assistant",
                    "content": item["assistant_message"]
                })
            return messages
        except CosmosResourceNotFoundError:
            print(f"Container for user {user} not found.")
            return []
    
    async def _connect_mcp_server(self, server_sse_url: str, mcp_tools: str, headers: dict[str, Any] | None = None):
        try:
            if self.exit_stack:
                await self.exit_stack.aclose()

            self.exit_stack = AsyncExitStack()

            streams = await self.exit_stack.enter_async_context(
                sse_client(url = server_sse_url, headers = headers)
            )

            self.session = await self.exit_stack.enter_async_context(ClientSession(*streams))

            await self.session.initialize()

            response = await self.session.list_tools()

            self.tools = [{ 
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                }
            } for tool in response.tools]

            print(f"Connected to MCP server at URL {server_sse_url} with tools: {','.join([tool['function']['name'] for tool in self.tools])}")
            mcp_tools += f"MCP URL: {server_sse_url.strip('https://').split('/sse')[0]}/sse\nTools: {', '.join([tool['function']['name'] for tool in self.tools])}\n"
            return mcp_tools
        except Exception as e:
            print(f"Error connecting to MCP server: {e}")
            mcp_tools += f"Error connecting to MCP server: {server_sse_url.strip('https://').split('/')[0]}\n"
            return mcp_tools

    async def _process_query(self, message: str, history: List[Union[Dict[str, Any], ChatMessage]], user: str):
        similar_message = self._check_similar_message(message, user)
        if similar_message is not None:
            print(f"Similar message found: {similar_message}")
            history.append({"role": "assistant", "content": similar_message})
            self._store_chat_message(user, message, similar_message)
            return

        while True:
            messages = []

            for msg in history:
                if isinstance(msg, ChatMessage):
                    role, content = msg.role, msg.content
                else:
                    role, content = msg["role"], msg["content"]

                if role in ["user", "assistant", "system"]:
                    messages.append({"role": role, "content": content})

            response_stream = await self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                tools=self.tools,
                parallel_tool_calls=False,
                stream=True,
                temperature=0
            )

            done = await self.process_response_stream(response_stream, history, message, user)

            if done:
                break

    def _check_similar_message(self, message: str, user: str) -> str:
        try: 
            db = self.chat_history_account.get_database_client("agent_threads")
            container: ContainerProxy = db.get_container_client("chat_history")
            message_embeddings = generate_embeddings(message)
            items = container.query_items(
                query="SELECT TOP 1 c.assistant_message, c.timestamp, VectorDistance(c.user_message_embeddings, @embeddings) AS SimilarityScore FROM c WHERE c.user = @user ORDER BY c.timestamp DESC",
                parameters=[
                    {"name": "@embeddings", "value": message_embeddings},
                    {"name": "@user", "value": user}
                ],
                enable_cross_partition_query=True
            )
            message = next(items, None)
            print(f"Message: {message}")
            if message is not None and message["SimilarityScore"] > 0.95:
                return message["assistant_message"]
            return None
        except CosmosResourceNotFoundError:
            print(f"Container for user {user} not found.")
            return None

    async def process_response_stream(self, response_stream, history: List[Union[Dict[str, Any], ChatMessage]], message: str, user: str):
        function_arguments = ""
        function_name = ""
        is_collecting_function_args = False
        collected_messages = []
        
        async for part in response_stream:
            if part.choices == []:
                continue
            delta = part.choices[0].delta
            finish_reason = part.choices[0].finish_reason

            # Process assistant content
            if delta.content:
                collected_messages.append(delta.content)
            
            # Handle tool calls
            if delta.tool_calls:
                if len(delta.tool_calls) > 0:
                    tool_call = delta.tool_calls[0]
                    
                    # Get function name
                    if tool_call.function.name:
                        function_name = tool_call.function.name
                    
                    # Process function arguments delta
                    if tool_call.function.arguments:
                        function_arguments += tool_call.function.arguments
                        is_collecting_function_args = True
            
            # Check if we've reached the end of a tool call
            if finish_reason == "tool_calls" and is_collecting_function_args:
                # Process the current tool call
                print(f"function_name: {function_name} function_arguments: {function_arguments}")
                function_args = json.loads(function_arguments)

                # Call the tool and add response to messages
                func_response = await self.session.call_tool(function_name, function_args)

                print(f"Function Response: {json.loads(func_response.model_dump_json())}")
                
                if not func_response.isError:
                    # Add the assistant message with tool call
                    history.append({
                        "role":"assistant",
                        "metadata":{"title": f"🛠️ Used tool {function_name}"},
                        "content":f"Arguments: {function_args}"
                    })
                else:
                    print(f"Error calling the tool {function_name}: {func_response.content}")
                    # Add the assistant message with error
                    history.append({
                        "role": "system",
                        "content": f"Error calling the tool {function_name}: {func_response.content}",
                    })
                
                history.append({
                    "role": "system",
                    "content": f"The response from the tool {function_name} with arguments {function_arguments} is {func_response}",
                })
            
            # Check if we've reached the end of assistant's response
            if finish_reason == "stop":
                # Add final assistant message if there's content
                print("Final assistant message:", ''.join(collected_messages))
                if collected_messages:
                    final_content = ''.join([msg for msg in collected_messages if msg is not None])
                    if final_content.strip():
                        history.append({"role": "assistant", "content": final_content})
                        self._store_chat_message(user, message, final_content)
                        return True

        return False  # In case the loop ends without a return, we can handle it here if needed

    def _store_chat_message(self, user: str, user_message: str, assistant_message: str):
        user_message_embeddings = generate_embeddings(user_message)
        message = {
            "id": str(uuid.uuid4()),
            "user": user,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "user_message_embeddings": user_message_embeddings,
            "timestamp": datetime.now(tz=pytz.UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
        db = self.chat_history_account.create_database_if_not_exists("agent_threads")
        vector_embedding_policy = { 
            "vectorEmbeddings": 
            [ 
                { 
                    "path": "/embedding", 
                    "dataType": "float32", 
                    "distanceFunction": "cosine", 
                    "dimensions": 3072 
                }, 
            ]    
        }
        indexing_policy = {
            "includedPaths": 
            [ 
                { 
                    "path": "/*" 
                } 
            ], 
            "excludedPaths": 
            [ 
                { 
                    "path": "/\"_etag\"/?",
                    "path": "/embedding/*",   
                } 
            ], 
            "vectorIndexes": 
            [ 
                {
                    "path": "/embedding", 
                    "type": "diskANN",
                    "vectorIndexShardKey": ["/user"]
                } 
            ]
        }

        container: ContainerProxy = db.create_container_if_not_exists(
            id = "chat_history",
            partition_key=PartitionKey(path="/user", kind="Hash"),
            vector_embedding_policy=vector_embedding_policy,
            indexing_policy=indexing_policy)
        container.create_item(message)