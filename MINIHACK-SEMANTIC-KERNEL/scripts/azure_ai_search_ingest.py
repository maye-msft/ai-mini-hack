import os
import PyPDF2
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
)
from dotenv import load_dotenv

from azure.search.documents import SearchClient

import uuid

load_dotenv(override=True)

# 🛠️ Configuration
PDF_DIR = os.path.join(os.path.dirname(__file__), "../data/brochures")
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
EMBEDDING_MODEL_DEPLOYMENT_API_VERSION = os.getenv(
    "EMBEDDING_MODEL_DEPLOYMENT_API_VERSION"
)
EMBEDDING_MODEL_DEPLOYMENT_NAME = os.getenv("EMBEDDING_MODEL_DEPLOYMENT_NAME")


# PDF text extraction
def extract_pdf(path: str) -> str:
    text = ""
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text


# Chunk large text
def chunk_text(text: str, max_chars=1500):
    for i in range(0, len(text), max_chars):
        yield text[i : i + max_chars]


def ensure_index(endpoint: str, api_key: str, index_name: str):
    client = SearchIndexClient(endpoint, AzureKeyCredential(api_key))

    fields = [
        SimpleField(name="id", key=True, type=SearchFieldDataType.String),
        SimpleField(name="city", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="filename", type=SearchFieldDataType.String, filterable=False),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="my-vector-profile",
        ),
    ]

    vector_search = VectorSearch(
        profiles=[
            VectorSearchProfile(
                name="my-vector-profile",
                algorithm_configuration_name="my-vector-config",
            )
        ],
        algorithms=[HnswAlgorithmConfiguration(name="my-vector-config")],
    )

    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    client.create_or_update_index(index)
    print(f"✅ Index '{index_name}' created/updated successfully")


# Generate embedding using Azure OpenAI
def get_embedding(client: AzureOpenAI, text: str):
    # Call the embedding endpoint
    response = client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL_DEPLOYMENT_NAME,
    )

    embedding_vector = response.data[0].embedding
    return embedding_vector


# Ingest all PDFs
def ingest():

    aisearch_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(AZURE_SEARCH_KEY),
    )
    ensure_index(AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_KEY, AZURE_SEARCH_INDEX_NAME)

    openai_client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=EMBEDDING_MODEL_DEPLOYMENT_API_VERSION,
    )

    for filename in os.listdir(PDF_DIR):
        if filename.endswith(".pdf"):
            # Extract metadata (e.g., city from filename)
            text = extract_pdf(os.path.abspath(os.path.join(PDF_DIR, filename)))
            city = filename.replace(" Brochure.pdf", "")
            print(f"Processing {city}: {filename}")

            for i, chunk in enumerate(chunk_text(text)):
                emb = get_embedding(openai_client, chunk)
                doc = {
                    "id": str(uuid.uuid4()),
                    "city": city,
                    "filename": filename,
                    "content": chunk,
                    "content_vector": emb,
                }
                aisearch_client.upload_documents(documents=[doc])
    print("✅ Ingestion complete.")


if __name__ == "__main__":
    ingest()
