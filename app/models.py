from typing import List
from pydantic import BaseModel, Field

class ItemDesc(BaseModel):
    item: str = Field(..., description="Rótulo da segunda coluna")
    descricao: str = Field(..., description="Terceira coluna")

class Payload(BaseModel):
    nome_produto: str
    tabela3_simplificada: List[ItemDesc]
    tabela4_simplificada: List[ItemDesc]
