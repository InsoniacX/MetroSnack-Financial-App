# test_login.py — versi debug 2
from db.connection import fetch_one
import bcrypt

username = input("Username: ")
password = input("Password: ")

print("Username mentah (sebelum dibersihkan):", repr(username))

username = username.strip()  # buang spasi/karakter tak terlihat di awal-akhir

print("Username setelah strip():", repr(username))

row = fetch_one(
    "SELECT id, username, password_hash, nama_lengkap, role, aktif FROM users WHERE username=%s",
    (username,),
)

if row is None:
    print("User tidak ditemukan di database.")
else:
    uid, uname, phash, nama, role, aktif = row
    print("Hash dari DB   :", repr(phash))
    print("Password input :", repr(password))
    print("Nama Lengkap :", repr(nama))
    print("Jabatan :", repr(role))
    print("Aktif?         :", aktif)
    hasil = bcrypt.checkpw(password.strip().encode(), phash.encode())
    print("bcrypt.checkpw hasil:", hasil)