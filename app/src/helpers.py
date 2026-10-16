import httpx
from duckduckgo_search import DDGS



def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Searches the web and returns top results with titles, snippets, and URLs."""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title"),
                "url": r.get("href"),
                "snippet": r.get("body")
            })
            
    return results

def split_text_into_chunks(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """Splits text into chunks of a given character size with a specified overlap."""
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunks.append(text[start:end])
        # Move forward by chunk_size minus the overlap to create the sliding window
        start += chunk_size - chunk_overlap
        
    return chunks


class SimpleAgent:
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    def generate_response(self, prompt: str) -> str:
        try:
            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "gemma4_e4b_custom", 
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120.0
            )
            
            # Print status and raw text to your FastAPI terminal to debug
            # print(f"Ollama Status Code: {response.status_code}")
            # print(f"Ollama Raw Response: {response.text}")
            
            result = response.json()
            answer_text = result.get("response", "Error generating response from local LLM.")
    
        except Exception as e:
            print(f"Ollama Connection Error: {str(e)}")
            answer_text = f"Failed to connect to local Ollama server: {str(e)}"
    
        return answer_text
        
    def __str__(self):
        return f"{self.name}/{self.version}"
    