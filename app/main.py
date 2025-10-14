from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from app.models import Payload
from app.fill_docx import fill_docx
import os, tempfile, json, datetime

APP_ROOT = os.path.dirname(os.path.dirname(__file__))
TEMPLATE_PATH = os.path.join(APP_ROOT, 'templates', 'ANEXO_01_GQ175_Rev11_BASE.docx')

app = FastAPI(title='ADVFARMA – Automação Anexo 01 Rev.11 (Hidroral)')

@app.get('/health')
def health():
    return {'status':'ok','time': datetime.datetime.utcnow().isoformat()}

@app.get('/schema')
def schema():
    return JSONResponse(Payload.model_json_schema())

@app.post('/gerar-docx')
def gerar_docx(payload: Payload):
    doc, report = fill_docx(TEMPLATE_PATH,
        [i.model_dump() for i in payload.tabela3_simplificada],
        [i.model_dump() for i in payload.tabela4_simplificada])
    out_dir = tempfile.mkdtemp()
    fname = f"ANEXO01_{payload.nome_produto}_Rev11_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    out_path = os.path.join(out_dir, fname)
    doc.save(out_path)
    headers = {'X-ADVFARMA-Report': json.dumps(report, ensure_ascii=False)}
    return FileResponse(out_path, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', filename=fname, headers=headers)
