import asyncio
import gradio as gr
import os
import json

from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client
from typing import List, Dict, Any, Union
from gradio.components.chatbot import ChatMessage
from openai import AsyncAzureOpenAI

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

    def connect(self, server_sse_url):
        return self.loop.run_until_complete(self._connect_mcp_server(server_sse_url))
    
    def process_message(self, message: str,  history: List[Union[Dict[str, Any], ChatMessage]]):
        history.append({"role": "user", "content": message})
        self.loop.run_until_complete(self._process_query(message, history))
        return history, gr.Textbox(value="")
    
    async def _connect_mcp_server(self, server_sse_url):
        if self.exit_stack:
            await self.exit_stack.aclose()

        self.exit_stack = AsyncExitStack()

        streams = await self.exit_stack.enter_async_context(sse_client(server_sse_url))

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

        return f"Connected to MCP server at URL {server_sse_url} with tools: {','.join([tool['function']['name'] for tool in self.tools])}"

    async def _process_query(self, message: str, history: List[Union[Dict[str, Any], ChatMessage]]):
        while True:
            messages = []

            for msg in history:
                if isinstance(msg, ChatMessage):
                    role, content = msg.role, msg.content
                else:
                    role, content = msg["role"], msg["content"]

                if role in ["user", "assistant", "system"]:
                    messages.append({"role": role, "content": content})
            
            messages.append({"role": "user", "content": message})
            response_stream = await self.openai_client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                tools=self.tools,
                parallel_tool_calls=False,
                stream=True,
                temperature=0
            )

            done = await self.process_response_stream(response_stream, history)

            if done:
                break

    async def process_response_stream(self, response_stream, history):
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
                        "role": "assistant",
                        "content": f"I will use the tool {function_name} with arguments {function_args}",
                    })
                else:
                    print(f"Error calling the tool {function_name}: {func_response.content}")
                    # Add the assistant message with error
                    history.append({
                        "role": "systen",
                        "content": f"Error calling the tool {function_name}: {func_response.content}",
                    })
                
                history.append({
                    "role": "system",
                    "content": f"Here is the response from the tool: {func_response}",
                })
            
            # Check if we've reached the end of assistant's response
            if finish_reason == "stop":
                # Add final assistant message if there's content
                print("Final assistant message:", ''.join(collected_messages))
                if collected_messages:
                    final_content = ''.join([msg for msg in collected_messages if msg is not None])
                    if final_content.strip():
                        history.append({"role": "assistant", "content": final_content})
                        return True

        return False  # In case the loop ends without a return, we can handle it here if needed
