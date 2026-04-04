import os
from qdrant_client import QdrantClient, models
from typing import List, Dict

class VectorStore:
    def __init__(self):
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME")
        self.vector_size = 3072

    def recreate_collection(self):
        try:
            self.client.delete_collection(self.collection_name)
            print(f"Deleted existing collection '{self.collection_name}'")
        except Exception as e:
            print(f"Collection delete error (ok if new): {e}")
            
            self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=self.vector_size, distance=models.Distance.COSINE),
        )
        print(f"Collection '{self.collection_name}' created.")

    def upsert_vectors(self, contents: List[str], embeddings: List[List[float]], metadatas: List[Dict]):
        points = []
        for i, (content, embedding, metadata) in enumerate(zip(contents, embeddings, metadatas)):
            points.append(models.PointStruct(
                id=i,
                vector=embedding,
                payload={
                    "content": content,
                    **metadata
                }
            ))
        batch_size = 100
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
                points=points[i:i + batch_size]
            )
        print(f"Upserted {len(points)} vectors into '{self.collection_name}'.")

    def search_vectors(self, query_embedding: List[float], limit: int = 3) -> List[Dict]:
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            append_payload=True
        )
        results = []
        for hit in hits:
            results.append({
                "content": hit.payload["content"],
                "filepath": hit.payload["filepath"],
                "score": hit.score,
                "start_token": hit.payload.get("start_token", ""),
                "end_token": hit.payload.get("end_token", "")
            })
        return results

if __name__ == "_main_":
    from dotenv import load_dotenv
    load_dotenv()