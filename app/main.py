from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.models import Payload
from app.fill_docx import fill_docx
import os, tempfile, json, datetime, base64

APP_ROOT = os.path.dirname(os.path.dirname(__file__))
TEMPLATE_PATH = os.path.join(APP_ROOT, "templates", "ANEXO_01_GQ175_Rev11_BASE.docx")

# pasta para servir downloads via HTTP
DOWNLOAD_DIR = os.path.join(APP_ROOT, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = FastAPI(title="ADVFARMA – Automação Anexo 01 Rev.11 (Hidroral)")
app.mount("/downloads", StaticFiles(directory=DOWNLOAD_DIR), name="downloads")

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}

def _build_doc(payload: Payload):
    doc, report = fill_docx(
        TEMPLATE_PATH,
        [i.model_dump() for i in payload.tabela3_simplificada],
        [i.model_dump() for i in payload.tabela4_simplificada],
    )
    fname = f"ANEXO01_{payload.nome_produto}_Rev11_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    tmpdir = tempfile.mkdtemp()
    out_path = os.path.join(tmpdir, fname)
    doc.save(out_path)
    return out_path, fname, report

@app.post("/gerar-docx")
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
    out_path, fname, report = _build_doc(payload)
    with open(out_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return {
        "filename": fname,
        "file_b64": b64,
        "report": report,
    }

@app.post("/gerar-docx-url")
def gerar_docx_url(payload: Payload, request: Request):
    out_path, fname, report = _build_doc(payload)
    # mover o arquivo gerado para a pasta servida (/downloads)
    final_path = os.path.join(DOWNLOAD_DIR, fname)
    os.replace(out_path, final_path)
    base_url = str(request.base_url).rstrip("/")
    return {
        "filename": fname,
        "url": f"{base_url}/downloads/{fname}",
        "report": report,
    }
