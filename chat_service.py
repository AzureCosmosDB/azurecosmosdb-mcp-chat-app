import os
import logging

from ai_plugins.cosmosdb_plugin import CosmosDB_AIPlugin
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.utils.logging import setup_logging

class ChatService:
    def __init__(self):
        self.kernel = Kernel()

        self.chat_completion = AzureChatCompletion(
            deployment_name=os.getenv("CHAT_MODEL_NAME"),
            api_key=os.getenv("CHAT_MODEL_API_KEY"),
            base_url=os.getenv("CHAT_MODEL_BASE_URL")
        )

        self.kernel.add_service(self.chat_completion)

        setup_logging()
        logging.getLogger("kernel").setLevel(logging.DEBUG)

        self.kernel.add_plugin(
            CosmosDB_AIPlugin("msmarco-cdb"),
            plugin_name="cosmosdb"
        )

        self.execution_settings = AzureChatPromptExecutionSettings()
        self.execution_settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
        self.chat_history = ChatHistory()

    async def process_message(self, message: str) -> str:
        self.chat_history.add_user_message(message)
        
        result = await self.chat_completion.get_chat_message_content(
            chat_history=self.chat_history,
            settings=self.execution_settings,
            kernel=self.kernel
        )

        self.chat_history.add_message(result)

        return str(result)
