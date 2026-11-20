"""Endpoint do MVP SOS Driver que recebe os prestadores aprovados pela automação n8n.
Uso: no seu app FastAPI existente -> from prestadores_api import router; app.include_router(router)
"""
import os
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/prestadores", tags=["prestadores"])
DB = os.getenv("SOSDRIVER_DB", "sosdriver.db")
API_KEY = os.getenv("SOSDRIVER_API_KEY", "troque-esta-chave")


def _conn():
    con = sqlite3.connect(DB)
    con.execute(
        """CREATE TABLE IF NOT EXISTS prestadores (
            id_externo TEXT PRIMARY KEY, nome TEXT, tipo_servico TEXT, cidade TEXT,
            telefone TEXT, validade_habilitacao TEXT, ativo INTEGER DEFAULT 1, atualizado_em TEXT)"""
    )
    return con


class Prestador(BaseModel):
    id_externo: str
    nome: str
    tipo_servico: str
    cidade: str
    telefone: str
    validade_habilitacao: str


@router.post("")
def registrar(p: Prestador, x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="chave invalida")
    con = _conn()
    # upsert por id_externo: reenviar o mesmo prestador nao duplica (idempotencia)
    con.execute(
        """INSERT INTO prestadores (id_externo, nome, tipo_servico, cidade, telefone, validade_habilitacao, atualizado_em)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(id_externo) DO UPDATE SET nome=excluded.nome, tipo_servico=excluded.tipo_servico,
           cidade=excluded.cidade, telefone=excluded.telefone,
           validade_habilitacao=excluded.validade_habilitacao, atualizado_em=excluded.atualizado_em""",
        (p.id_externo, p.nome, p.tipo_servico, p.cidade, p.telefone, p.validade_habilitacao,
         datetime.now(timezone.utc).isoformat()),
    )
    con.commit()
    con.close()
    return {"id_externo": p.id_externo, "status": "registrado"}


@router.get("")
def listar(cidade: str | None = None, tipo_servico: str | None = None):
    """Consumido pelo matching do app: lista prestadores ativos (sem telefone completo)."""
    con = _conn()
    q, args = "SELECT id_externo, nome, tipo_servico, cidade FROM prestadores WHERE ativo=1", []
    if cidade:
        q += " AND lower(cidade)=lower(?)"; args.append(cidade)
    if tipo_servico:
        q += " AND tipo_servico=?"; args.append(tipo_servico)
    rows = [dict(zip(("id_externo", "nome", "tipo_servico", "cidade"), r)) for r in con.execute(q, args)]
    con.close()
    return rows
