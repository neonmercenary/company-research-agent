import os
import re
import httpx
import asyncio
from crawl4ai import AsyncWebCrawler
from urllib.parse import urljoin, urlparse
from ddgs import DDGS
from bs4 import BeautifulSoup


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

    def search_web(self, query: str, max_results: int = 3) -> list[dict]:
        """Searches the web and returns top results with titles, snippets, and URLs."""
        results = []
        result = DDGS().text(query, max_results=max_results)
        for r in result:
            
            # Try to include a short snippet if available from DDGS result
            snippet =r.get("body") or ""
            url = r.get("href")
            content = asyncio.run(
                self.follow_url(url)) if url else ""
            results.append({
                "title": r.get("title"),
                "url": url,
                "snippet": snippet,
                "content": content,
            })
            

        return results


    async def follow_url(self, url: str) -> str:
        """Fetches the content of a URL using a browser User-Agent to bypass basic 403 blocks."""
        try:
            # Explicitly check and skip domains known to heavily block scrapers
            if any(blocked in url.lower() for blocked in ["amazon.com", "linkedin.com", "dashboard", "login"]):
                print(f"Skipping restricted domain: {url}")
                return ""

            # Spin up the AI-native headless crawler
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(url=url)
                
                if result.success and result.markdown:
                    return f"# Source URL: {url}\n\n{result.markdown}"
                else:
                    error_msg = getattr(result, "error_message", "Unknown extraction failure")
                    return f"Error: Could not crawl {url}. Details: {error_msg}"
                    
        except Exception as e:
            return f"Failed to execute Crawl4AI on {url}: {str(e)}"
        

    def generate_response(self, prompt: str, timeout: float = 180.0) -> str:
            """Sends prompt to local Ollama instance with an extended timeout."""
            try:
                response = httpx.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "gemma4_e4b_custom", 
                        "prompt": prompt,
                        "stream": False,
                    },
                    timeout=timeout  # Increased timeout for local model heavy lifting
                )
                
                result = response.json()
                answer_text = result.get("response", "Error generating response from local LLM.")
        
            except Exception as e:
                print(f"Ollama Connection Error: {str(e)}")
                answer_text = f"Failed to connect to local Ollama server or timed out: {str(e)}"
        
            return answer_text
        
    def __str__(self):
        return f"{self.name}/{self.version}"
    