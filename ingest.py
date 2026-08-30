import io
import os
import sys

import tiktoken
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from openai import AzureOpenAI
from pypdf import PdfReader

# 1. Load configuration from .env file
load_dotenv()

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
STORAGE_ACCOUNT = os.getenv("STORAGE_ACCOUNT_NAME")
EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
INDEX_NAME = "kb-index"
CONTAINER_NAME = "kb-documents"

if not all([SEARCH_ENDPOINT, OPENAI_ENDPOINT, STORAGE_ACCOUNT]):
    print("Error: Missing one or more environment variables in .env file.")
    sys.exit(1)

print("--> Initializing Azure Clients using DefaultAzureCredential...")
credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")

# 2. Initialize Clients
openai_client = AzureOpenAI(
    azure_endpoint=OPENAI_ENDPOINT, azure_ad_token_provider=token_provider, api_version="2024-06-01"
)

index_client = SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential)
search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)

blob_service = BlobServiceClient(account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net", credential=credential)


# 3. Create or update Vector Search Index Schema
def setup_index():
    print(f"--> Creating / Updating Search Index: '{INDEX_NAME}'...")
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="contentVector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="kb-vector-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="kb-hnsw-algo")],
        profiles=[VectorSearchProfile(name="kb-vector-profile", algorithm_configuration_name="kb-hnsw-algo")],
    )

    index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)
    index_client.create_or_update_index(index)
    print(f"Index '{INDEX_NAME}' is ready.")


# 4. Text Chunking
def chunk_text(text: str, max_tokens: int = 400, overlap: int = 50):
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens - overlap):
        chunk_tokens = tokens[i : i + max_tokens]
        chunks.append(enc.decode(chunk_tokens))
    return chunks


# 5. Extract Text (Supports .pdf, .md, .txt, .json, etc.)
def extract_text_from_blob(blob_name: str, blob_bytes: bytes) -> str:
    if blob_name.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(blob_bytes))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    else:
        return blob_bytes.decode("utf-8", errors="ignore")


# 6. Ingestion Pipeline
def run_ingestion():
    setup_index()

    print(f"--> Fetching blobs from container '{CONTAINER_NAME}' in '{STORAGE_ACCOUNT}'...")
    container_client = blob_service.get_container_client(CONTAINER_NAME)
    blobs = list(container_client.list_blobs())

    if not blobs:
        print(f"Notice: No documents found in '{CONTAINER_NAME}'.")
        return

    print(f"Found {len(blobs)} files in container. Processing...")

    documents_to_upload = []
    for blob in blobs:
        print(f"--> Processing: {blob.name}")
        raw_bytes = container_client.download_blob(blob.name).readall()
        extracted_text = extract_text_from_blob(blob.name, raw_bytes)

        if not extracted_text.strip():
            print(f"    Skipping empty/unextractable file: {blob.name}")
            continue

        chunks = chunk_text(extracted_text)
        print(f"    Split into {len(chunks)} chunks. Generating embeddings...")

        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in blob.name)

        for idx, chunk in enumerate(chunks):
            doc_id = f"{safe_name}_{idx}"

            embedding_response = openai_client.embeddings.create(input=chunk, model=EMBEDDING_DEPLOYMENT)
            embedding = embedding_response.data[0].embedding

            documents_to_upload.append({"id": doc_id, "title": blob.name, "content": chunk, "contentVector": embedding})

            # Batch upload in chunks of 50 documents
            if len(documents_to_upload) >= 50:
                search_client.upload_documents(documents=documents_to_upload)
                print(f"    Uploaded batch of {len(documents_to_upload)} chunks to AI Search.")
                documents_to_upload = []

    # Upload any remaining documents
    if documents_to_upload:
        search_client.upload_documents(documents=documents_to_upload)
        print(f"    Uploaded final batch of {len(documents_to_upload)} chunks.")

    print(f"--> Successfully indexed all documents from '{CONTAINER_NAME}' into '{INDEX_NAME}'!")


if __name__ == "__main__":
    run_ingestion()
