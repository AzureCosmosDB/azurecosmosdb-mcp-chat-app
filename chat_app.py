import chainlit as cl
import logging
import uuid

from dotenv import load_dotenv
from chat_service import ChatService

load_dotenv()

logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)

chat_services = {}

@cl.on_chat_start
async def on_chat_start():
	# Create a thread for the agent
	if not cl.user_session.get("thread_id"):
		thread_id = str(uuid.uuid4())

		cl.user_session.set("thread_id", thread_id)
		chat_services[thread_id] = ChatService()
		
@cl.on_message
async def on_message(message: cl.Message):
	thread_id = cl.user_session.get("thread_id")

	try:
		# Show thinking message to user
		msg = await cl.Message("thinking...", author="agent").send()

		chat_service: ChatService = chat_services[thread_id]

		response = await chat_service.process_message(message.content)

		msg.content = response
		await msg.update()

	except Exception as e:
		await cl.Message(content=f"Error: {str(e)}").send()
    
if __name__ == "main":
    pass