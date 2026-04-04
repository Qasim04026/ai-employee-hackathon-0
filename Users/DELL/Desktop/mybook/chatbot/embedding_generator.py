import os
import time 
from google import genai
from typing import List, Dict


class EmbeddingGenerator:
    def __init__(self):
        self.model = "models/gemini-embedding-001"
        self.client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a list of texts using Google Gemini API."""
        if not texts:
            return []
        try:
            embeddings = []
            for text in texts:
                result = self.client.models.embed_content(
                    model=self.model,
                    contents=text
                )
                embeddings.append(result.embeddings[0].values)
                time.sleep(0.5)  # Add a small delay to avoid hitting rate limits
            return embeddings
        except Exception as e:
            import traceback
        print(f"Error generating embeddings: {e}")
        print(traceback.format_exc())    
        return []

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    if os.getenv("GEMINI_API_KEY"):
        embedding_generator = EmbeddingGenerator()
        test_texts = [
            "This is a test sentence.",
            "Another sentence for embedding."
        ]
        embeddings = embedding_generator.generate_embeddings(test_texts)

        if embeddings:
            print(f"Generated {len(embeddings)} embeddings. Each embedding has dimension {len(embeddings[0])}.")
        else:
            print("Failed to generate embeddings.")
    else:
        print("GEMINI_API_KEY not set.")