from openai import AzureOpenAI
import os
import tiktoken

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=".env")

OPENAI_API_KEY = os.getenv('openai_key')
OPENAI_API_ENDPOINT = os.getenv('openai_endpoint')
OPENAI_API_VERSION = os.getenv('openai_api_version') # at the time of authoring, the api version is 2024-02-01
EMBEDDING_MODEL_DEPLOYMENT_NAME = os.getenv('openai_embeddings_deployment')
EMBEDDING_MODEL_NAME = os.getenv('openai_embeddings_model')

# Load tokenizer for text-embedding-3-large
tokenizer = tiktoken.get_encoding("cl100k_base")
AOAI_client = AzureOpenAI(
    api_key=OPENAI_API_KEY,
    azure_endpoint=OPENAI_API_ENDPOINT,  # type: ignore
    azure_deployment=EMBEDDING_MODEL_DEPLOYMENT_NAME,
    api_version=OPENAI_API_VERSION)

def truncate_text(text, max_tokens=8192):
    tokens = tokenizer.encode(text)
    if len(tokens) > max_tokens:
        truncated_tokens = tokens[:max_tokens]
        text = tokenizer.decode(truncated_tokens)
    return text

def generate_embeddings(text: str):
    if EMBEDDING_MODEL_NAME is None:
        raise ValueError("Embedding model deployment name is not set.")
    
    text = truncate_text(text)
    response = AOAI_client.embeddings.create(input=text, model=EMBEDDING_MODEL_NAME)
    embeddings = response.model_dump()
    return embeddings['data'][0]['embedding']