from pydantic import BaseModel, model_validator, Field
from datetime import date
from decimal import Decimal
from typing import Optional, Literal


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id: int
    username: str
    role: str
    nama: Optional[str] = None
    cabang_id: Optional[int] = None
    nama_cabang: Optional[str] = None


class CabangCreate(BaseModel):
    nama_cabang: str
    alamat: Optional[str] = None


class CabangUpdate(BaseModel):
    nama_cabang: str
    alamat: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    password: str
    nama_lengkap: str
    # Sesuai CHECK constraint asli di tabel users: cuma 2 role yang valid.
    role: Literal["admin", "karyawan"]
    cabang_id: Optional[int] = None

    @model_validator(mode="after")
    def _karyawan_wajib_cabang(self):
        # Cerminan chk_karyawan_has_cabang di database: karyawan wajib
        # punya cabang_id, supaya error ketahuan di sini (pesan jelas)
        # sebelum sampai jadi IntegrityError mentah dari database.
        if self.role == "karyawan" and self.cabang_id is None:
            raise ValueError("User dengan role 'karyawan' wajib memiliki cabang_id")
        return self


class UserUpdate(BaseModel):
    nama_lengkap: str
    role: Literal["admin", "karyawan"]


class FolderCreate(BaseModel):
    bulan: int
    tahun: int
    cabang_id: int


class InvoiceCreate(BaseModel):
    no_laporan: Optional[str] = None
    tanggal_dibuat: date
    tanggal_laporan: date
    # invoice_bon = Modal Pusat / Nilai Awal dari kantor pusat ke cabang
    # (dikonfirmasi 19 Agustus 2026), bukan nomor bon/nota.
    invoice_bon: Decimal = Decimal("0")


class InvoiceUpdate(BaseModel):
    no_laporan: Optional[str] = None
    tanggal_dibuat: date
    tanggal_laporan: date
    invoice_bon: Decimal = Decimal("0")


class TransaksiCreate(BaseModel):
    tanggal: date
    masuk_barang: Decimal = Decimal("0")
    masuk_uang: Decimal = Decimal("0")
    nota: Optional[str] = None


class TransaksiUpdate(BaseModel):
    tanggal: date
    masuk_barang: Decimal
    masuk_uang: Decimal
    nota: Optional[str] = None


class SisaBarangUpdate(BaseModel):
    sisa_barang_manual: Decimal


class ResetPasswordRequest(BaseModel):
    new_password: str

class PendapatanPengeluaranCreate(BaseModel):
    cabang_id: int
    tanggal: date
    jenis: Literal["pendapatan", "pengeluaran"]
    nama_pengeluaran: str = Field(..., min_length=1, max_length=150)
    nominal: Decimal = Field(..., gt=0)


class PendapatanPengeluaranUpdate(BaseModel):
    tanggal: date
    jenis: Literal["pendapatan", "pengeluaran"]
    nama_pengeluaran: str = Field(..., min_length=1, max_length=150)
    nominal: Decimal = Field(..., gt=0)