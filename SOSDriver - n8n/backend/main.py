from fastapi import FastAPI
from prestadores_api import router

app = FastAPI(title="SOS Driver - MVP")
app.include_router(router)


@app.get("/")
def raiz():
    return {"status": "ok", "servico": "SOS Driver MVP"}