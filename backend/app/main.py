from fastapi import FastAPI
from app.api import auth, inspection, risks, rules

app = FastAPI(title="运维巡检系统", version="1.0.0")

app.include_router(auth.router)
app.include_router(inspection.router)
app.include_router(risks.router)
app.include_router(rules.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
