def rp(value):
    """ Format angka menjadi teks Rupiah, contoh: 10000 menjadi Rp 10.000"""
    if value is None:
        value = 0
    value = int(value)
    return "Rp " + f"{value:,.0f}".replace(",", ".")