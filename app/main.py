import re
from app.src.helpers import (
    split_text_into_chunks,
    search_web,
    SimpleAgent,
)
from app.src.schemas import QueryReq
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import requests
from bs4 import BeautifulSoup
from fastapi import (
    FastAPI, status, HTTPException
)
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application starting...")
    yield
    print("Application shutting down...")

agent = SimpleAgent(name="CompanyResearchAgent", version="1.0.0")
app = FastAPI(lifespan=lifespan, 
              title="Company Research Agent API", 
              description="This is a sample FastAPI application.", 
              version="1.0.0",
        )


assert isinstance(app, FastAPI), "app is not an instance of FastAPI"
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")
    

@app.get("/api/hello")
def read_root_api():
    return {"message": "Hello from FastAPI!"}


def resolve_company_entity(company_name: str, hint: str = None) -> dict:
    """Performs an initial search to verify company identity and prevent name collisions."""
    query = f"{company_name} {hint}" if hint else f"{company_name} company overview"
    
    results = search_web(query, max_results=5)
    
    # Simple heuristic/feedback: extract domains and snippet clues
    candidates = []
    for r in results:
        candidates.append({
            "title": r["title"],
            "url": r["url"],
            "snippet": r["snippet"]
        })
        
    return {
        "query": company_name,
        "candidates": candidates,
        "status": "requires_disambiguation" if len(
            set(c["title"].split()[0] for c in candidates)
        ) > 2 else "resolved"
    }


        


@app.post("/api/v1/search")
def search(data: QueryReq):
    company_name = data.query
    search_results = resolve_company_entity(company_name)

    result = fetch_clean_page(url)

    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

    chunked_text = split_text_into_chunks(result['text'], chunk_size=500, chunk_overlap=50)

    prompt = f"""
    Extract the details of this company from this web search result for a company brief and cold email outreach 
    with every factual information and details about the company alongside citation of the source URL. 
    Indicate if there is no available information on the company.
    Context: {chunked_text}
    Company: {data.query}
    """

    # Call LLM
    answer_text = agent.generate_response(prompt)

    return {
        "query": data.query,
        "answer": answer_text,
    }

