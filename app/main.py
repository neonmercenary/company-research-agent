from app.src.helpers import (
    split_text_into_chunks,
    SimpleAgent,
)
from app.src.schemas import ResearchRequest as QueryReq
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi import (
    FastAPI
)
from contextlib import asynccontextmanager
from pydantic import BaseModel
import json


class PersonalizeEmailRequest(BaseModel):
    company_context: str
    email_draft: str


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


def _clean_json_response(raw_response: str) -> str:
    cleaned_response = raw_response.strip()
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[7:]
    elif cleaned_response.startswith("```"):
        cleaned_response = cleaned_response[3:]
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3]
    return cleaned_response.strip()


@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")


@app.get("/api/hello")
def read_root_api():
    return {"message": "Hello from FastAPI!"}


@app.post("/api/v1/search")
def search(data: QueryReq):
    company_query = data.company_details
    search_results = agent.search_web(company_query, max_results=3)

    formatted_contexts = []
    use_mini_chunks = True  # Testing

    for result in search_results:
        title = result.get("title", "Unknown Source")
        url = result.get("url", "#")
        content = result.get("content", "")

        if not content or "Error:" in content or "Failed" in content:
            continue

        # Chunk text while maintaining traceability
        chunked_text = split_text_into_chunks(content)

        # KEY FIX: Take only the first 2 chunks per source to keep context lightweight for local models
        for chunk in chunked_text[:4]:
            formatted_contexts.append(f"""
            --- SOURCE METADATA ---
            Title: {title}
            URL: {url}
            Content Segment: {chunk}
            -----------------------
            """)

    if not formatted_contexts:
        return {
            "query": company_query,
            "brief": "No reliable web data could be fetched for this company.",
            "email_draft": "Could not generate email due to lack of source data."
        }

    combined_context = "".join(formatted_contexts)

    prompt = f"""
    Using ONLY the provided source context below, generate two distinct outputs:
        1. An Executive Brief summarizing the company, products, and recent updates.
        2. A tailored Cold Email Draft pitching a relevant service to this company.

    Every factual claim, statistic, or feature MUST include an explicit inline Markdown link citation using the exact format: [Source Title](URL).
    Use ONLY the URLs and Titles provided in the source metadata. Do not hallucinate or guess links.
    Explicitly state if context is not available for the query.

    SOURCE CONTEXT: {combined_context if use_mini_chunks else chunked_text}
    TARGET COMPANY QUERY: {company_query}

    Return a JSON object containing the "company_brief" and the "email_draft".
    """

    raw_response = agent.generate_response(prompt, timeout=300)
    cleaned_response = _clean_json_response(raw_response)

    try:
        parsed_data = json.loads(cleaned_response)
        brief_text = parsed_data.get("company_brief", "Error parsing brief.")
        email_text = parsed_data.get("email_draft", "Error parsing email draft.")
    except json.JSONDecodeError:
        print("Warning: Failed to parse LLM output as JSON. Falling back to raw text.")
        brief_text = raw_response
        email_text = "Failed to parse email draft."

    return {
        "query": company_query,
        "brief": brief_text,
        "email_draft": email_text
    }


@app.post("/api/v1/personalize-email")
def personalize_email(data: PersonalizeEmailRequest):
    company_context = (data.company_context or "").strip()
    email_draft = (data.email_draft or "").strip()

    if not company_context or not email_draft:
        return {"email_draft": email_draft or ""}

    prompt = f"""
    Rewrite the email below so it is tailored to the company context provided.
    Keep the email professional, concise, and relevant. Preserve the intent and tone,
    but make it specifically sound like it was written for this company.
    Only use the information provided in the company context and the original email draft.
    Do not invent ungrounded facts.

    Return a JSON object with a single key named "email_draft".

    COMPANY CONTEXT:
    {company_context}

    CURRENT EMAIL DRAFT:
    {email_draft}
    """

    raw_response = agent.generate_response(prompt, timeout=300)
    cleaned_response = _clean_json_response(raw_response)

    try:
        parsed_data = json.loads(cleaned_response)
        new_email = parsed_data.get("email_draft", email_draft)
        
    except json.JSONDecodeError:
        print("Warning: Failed to personalize email draft; returning original draft.")
        new_email = email_draft

    return {"email_draft": new_email}
