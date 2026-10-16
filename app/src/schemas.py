from pydantic import BaseModel
from typing import Optional

class ResearchRequest(BaseModel):
    company_details: str # Tesla, Inc. or Tesla, Inc. (Automotive) or Amazon.com, Inc. (E-commerce)


class ResearchPayload(BaseModel):
    query: str
    brief: str
    email_draft: str