from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import APP_TITLE, CORS_ORIGINS
from database.connection import init_pool
from api import (
    routes_auth, routes_cabang, routes_users, routes_folder,
    routes_invoice, routes_transaksi, routes_activity, routes_dashboard,
    routes_pendapatan_pengeluaran,
)

app = FastAPI(title=APP_TITLE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_pool()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(routes_auth.router)
app.include_router(routes_cabang.router)
app.include_router(routes_users.router)
app.include_router(routes_folder.router)
app.include_router(routes_invoice.router)
app.include_router(routes_transaksi.router)
app.include_router(routes_activity.router)
app.include_router(routes_dashboard.router)
app.include_router(routes_pendapatan_pengeluaran.router)

# Jalankan lokal dengan: uvicorn main:app --reload --host 0.0.0.0 --port 8000
