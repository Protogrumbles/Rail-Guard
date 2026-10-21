"""Retrieval for the support agent. Deliberately vulnerable; do not deploy."""
from vectordb import Client

client = Client(url="http://localhost:6333")
COLLECTION = "support_docs"


def search_documents(query: str, top_k: int = 5) -> list[str]:
    hits = client.search(collection=COLLECTION, query=query, limit=top_k)
    return [hit.payload["text"] for hit in hits]


def search_documents_for_tenant(query: str, tenant_id: str, top_k: int = 5) -> list[str]:
    hits = client.search(collection=COLLECTION, query=query, limit=top_k, filter={"tenant_id": tenant_id})
    return [hit.payload["text"] for hit in hits]


def index_document(text: str, tenant_id: str) -> None:
    client.upsert(collection=COLLECTION, payload={"text": text, "tenant_id": tenant_id})
