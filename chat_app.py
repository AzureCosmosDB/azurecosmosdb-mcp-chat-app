import chainlit as cl
import logging
import uuid
from typing import Dict

from dotenv import load_dotenv
from chat_service import ChatService
from mcp import ClientSession

load_dotenv(override=True)

logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)

chat_services = {}
chat_messages = {}

def flatten(xss):
    return [x for xs in xss for x in xs]

@cl.on_mcp_connect
async def on_mcp(connection, session: ClientSession):
    print(f"Connected to {connection.name}")
    result = await session.list_tools()
    tools = [{
        "name": t.name,
        "description": t.description,
        "parameters": t.inputSchema,
        } for t in result.tools]
    
    mcp_tools = cl.user_session.get("mcp_tools", {})
    mcp_tools[connection.name] = tools
    cl.user_session.set("mcp_tools", mcp_tools)

@cl.on_chat_start
async def on_chat_start():
	# Create a thread for the agent
	if not cl.user_session.get("thread_id"):
		thread_id = str(uuid.uuid4())

		cl.user_session.set("thread_id", thread_id)
		chat_services[thread_id] = ChatService()
		chat_messages[thread_id] = []
		
@cl.on_message
async def on_message(message: cl.Message):
	mcp_tools = cl.user_session.get("mcp_tools", {})
	tools = flatten([tools for _, tools in mcp_tools.items()])
	tools = [{"type": "function", "function": tool} for tool in tools]
    
	# Get the thread ID from the user session
	thread_id = cl.user_session.get("thread_id")
	chat_service: ChatService = chat_services.get(thread_id)
    
	if not chat_service:
		raise ValueError("Chat service not found for the given thread ID.")
    
    # Restore conversation history
	chat_service.messages = cl.user_session.get(f"messages-{thread_id}", [])
    
	msg = cl.Message(content="thinking...")

	await msg.send()

	msg = cl.Message(content="thinking...")

	async for text in chat_service.generate_response(human_input=message.content, tools=tools):
		msg.content = ""
		await msg.stream_token(text)
    
    # Update the stored messages after processing
	cl.user_session.set(f"messages-{thread_id}", chat_service.messages)
    
if __name__ == "main":
    pass