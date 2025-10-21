# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.models import Payload
from app.fill_docx import fill_docx
import os
import tempfile
import json
import datetime
import base64
import re
import unicodedata

# --- Paths & App setup ---
APP_ROOT = os.path.dirname(os.path.dirname(__file__))
TEMPLATE_PATH = os.path.join(APP_ROOT, "templates", "ANEXO_01_GQ175_Rev11_BASE.docx")

DOWNLOAD_DIR = os.path.join(APP_ROOT, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = FastAPI(title="ADVFARMA – Automação Anexo 01 Rev.11 (Rotulagem)")
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")


# --- Utils ---
def _safe_filename(name: str) -> str:
    """
    Normaliza o nome do arquivo para uso em URL e filesystem:
    - Remove acentos
    - Troca espaços por underscore
    - Remove caracteres não [A-Za-z0-9._-]
    - Evita sequências repetidas de underscore e pontas inválidas
    """
    if not name:
        return "documento.docx"
    nfkd = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    nfkd = nfkd.replace(" ", "_")
    nfkd = re.sub(r"[^A-Za-z0-9._-]+", "_", nfkd)
    nfkd = re.sub(r"_+", "_", nfkd).strip("._-")
    if not nfkd.lower().endswith(".docx"):
        nfkd += ".docx"
    return nfkd or "documento.docx"


def _build_doc(payload: Payload):
    """
    Constrói o DOCX em diretório temporário e retorna:
      (out_path, filename_seguro, report_dict)
    """
    doc, report = fill_docx(
        TEMPLATE_PATH,
        [i.model_dump() for i in payload.tabela3_simplificada],
        [i.model_dump() for i in payload.tabela4_simplificada],
    )
    raw_name = f"ANEXO01_{payload.nome_produto}_Rev11_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    fname = _safe_filename(raw_name)
    tmpdir = tempfile.mkdtemp()
    out_path = os.path.join(tmpdir, fname)
    doc.save(out_path)
    return out_path, fname, report


# --- Schemas auxiliares ---
class SaveB64Payload(BaseModel):
    filename: str
    file_b64: str  # Base64 puro do DOCX (sem prefixo data:)


# --- Endpoints ---
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}


@app.post("/gerar-docx")  # binário (opcional; alguns conectores não gostam)
def gerar_docx(payload: Payload):
    out_path, fname, report = _build_doc(payload)
    headers = {"X-ADVFARMA-Report": json.dumps(report, ensure_ascii=False)}
    return FileResponse(
        out_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=fname,
        headers=headers,
    )


@app.post("/gerar-docx-b64")
def gerar_docx_b64(payload: Payload):
    """
    Caminho mais estável para o GPT:
    - Gera o DOCX
    - Retorna como Base64 + report
    Depois use /save-b64 para transformar em URL de download.
    """
    out_path, fname, report = _build_doc(payload)
    with open(out_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return {"filename": fname, "file_b64": b64, "report": report}


@app.post("/save-b64")
def save_b64(payload: SaveB64Payload, request: Request):
    """
    Recebe {filename, file_b64}, grava em /downloads e devolve URL pública.
    Use após /gerar-docx-b64.
    """
    fname = _safe_filename(payload.filename)
    final_path = os.path.join(DOWNLOAD_DIR, fname)
    with open(final_path, "wb") as f:
        f.write(base64.b64decode(payload.file_b64))
    base_url = str(request.base_url).rstrip("/")
    return {"filename": fname, "url": f"{base_url}/downloads/{fname}"}
