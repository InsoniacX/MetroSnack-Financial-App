from pydantic import BaseModel, model_validator, field_validator, Field
from datetime import date
from decimal import Decimal
from typing import Optional, Literal


def _strip_required_text(value):
    if not isinstance(value, str):
        return value

    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Field wajib diisi")

    return cleaned


def _validate_bcrypt_password(value, min_length):
    if not isinstance(value, str):
        return value

    if not value.strip():
        raise ValueError("Password wajib diisi")

    if len(value) < min_length:
        raise ValueError(f"Password minimal {min_length} karakter")

    # bcrypt hanya memproses maksimal 72 byte.
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password maksimal 72 byte")

    return value


class LoginRequest(BaseModel):
    username: str = Field(..., max_length=50)
    password: str

    @field_validator("username", mode="before")
    @classmethod
    def _validate_username(cls, value):
        return _strip_required_text(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value):
        # Login tetap menerima password lama yang mungkin kurang dari 6 karakter.
        return _validate_bcrypt_password(value, min_length=1)


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
    nama_cabang: str = Field(..., max_length=100)
    alamat: Optional[str] = None

    @field_validator("nama_cabang", mode="before")
    @classmethod
    def _validate_nama_cabang(cls, value):
        return _strip_required_text(value)


class CabangUpdate(BaseModel):
    nama_cabang: str = Field(..., max_length=100)
    alamat: Optional[str] = None

    @field_validator("nama_cabang", mode="before")
    @classmethod
    def _validate_nama_cabang(cls, value):
        return _strip_required_text(value)


class UserCreate(BaseModel):
    username: str = Field(..., max_length=50)
    password: str
    nama_lengkap: str = Field(..., max_length=100)
    role: Literal["admin", "karyawan"]
    cabang_id: Optional[int] = Field(default=None, gt=0)

    @field_validator("username", "nama_lengkap", mode="before")
    @classmethod
    def _validate_required_text(cls, value):
        return _strip_required_text(value)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value):
        # Disamakan dengan validasi client saat ini.
        return _validate_bcrypt_password(value, min_length=6)

    @model_validator(mode="after")
    def _karyawan_wajib_cabang(self):
        if self.role == "karyawan" and self.cabang_id is None:
            raise ValueError(
                "User dengan role 'karyawan' wajib memiliki cabang_id"
            )
        return self


class UserUpdate(BaseModel):
    nama_lengkap: str = Field(..., max_length=100)
    role: Literal["admin", "karyawan"]

    @field_validator("nama_lengkap", mode="before")
    @classmethod
    def _validate_nama_lengkap(cls, value):
        return _strip_required_text(value)


class FolderCreate(BaseModel):
    bulan: int = Field(..., ge=1, le=12)
    tahun: int = Field(..., ge=2000, le=2100)
    cabang_id: int = Field(..., gt=0)


class InvoiceCreate(BaseModel):
    no_laporan: Optional[str] = Field(default=None, max_length=50)
    tanggal_dibuat: date
    tanggal_laporan: date
    invoice_bon: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=15,
        decimal_places=2,
    )


class InvoiceUpdate(BaseModel):
    no_laporan: Optional[str] = Field(default=None, max_length=50)
    tanggal_dibuat: date
    tanggal_laporan: date
    invoice_bon: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=15,
        decimal_places=2,
    )


class TransaksiCreate(BaseModel):
    tanggal: date
    masuk_barang: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    masuk_uang: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    nota: Optional[str] = Field(default=None, max_length=100)


class TransaksiUpdate(BaseModel):
    tanggal: date
    masuk_barang: Decimal = Field(
        ...,
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    masuk_uang: Decimal = Field(
        ...,
        ge=0,
        max_digits=15,
        decimal_places=2,
    )
    nota: Optional[str] = Field(default=None, max_length=100)


class SisaBarangUpdate(BaseModel):
    sisa_barang_manual: Decimal = Field(
        ...,
        ge=0,
        max_digits=15,
        decimal_places=2,
    )


class ResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _validate_new_password(cls, value):
        return _validate_bcrypt_password(value, min_length=6)

class PendapatanPengeluaranCreate(BaseModel):
    cabang_id: int = Field(..., gt=0)
    tanggal: date
    jenis: Literal["pendapatan", "pengeluaran"]
    nama_pengeluaran: str = Field(..., min_length=1, max_length=150)
    nominal: Decimal = Field(
        ...,
        gt=0,
        max_digits=14,
        decimal_places=2,
    )


class PendapatanPengeluaranUpdate(BaseModel):
    tanggal: date
    jenis: Literal["pendapatan", "pengeluaran"]
    nama_pengeluaran: str = Field(..., min_length=1, max_length=150)
    nominal: Decimal = Field(
        ...,
        gt=0,
        max_digits=14,
        decimal_places=2,
    )