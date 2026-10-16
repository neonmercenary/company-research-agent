from pydantic import BaseModel, Field




class QueryReq(BaseModel):
    query: str


