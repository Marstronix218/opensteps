from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    public_key: str

