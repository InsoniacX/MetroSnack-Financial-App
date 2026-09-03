from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import APP_TITLE, CORS_ORIGINS
from database.connection import init_pool, close_pool
from api import (
    routes_auth,
    routes_cabang,
    routes_users,
    routes_folder,
    routes_invoice,
    routes_transaksi,
    routes_activity,
    routes_dashboard,
    routes_pendapatan_pengeluaran,
    routes_supir_kenek,
    routes_pengambilan_kas,
    routes_operasional_mobil,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_pool()

    try:
        yield
    finally:
        close_pool()


app = FastAPI(
    title=APP_TITLE,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(routes_supir_kenek.router)
app.include_router(routes_operasional_mobil.router)
app.include_router(routes_pengambilan_kas.router)
app.include_router(routes_pendapatan_pengeluaran.router)

# Jalankan lokal dengan:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000