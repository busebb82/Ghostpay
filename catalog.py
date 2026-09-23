"""Bilinen abonelik servisleri: banka dökümündeki açıklama → servis bilgisi.

Hem sentetik veri üretimi hem abonelik tespiti fiyatları buradan okur.
"""

CATEGORIES = ["Video", "Müzik", "Üretkenlik", "Yapay Zekâ"]

# fiyat: güncel liste fiyatı (₺), gun: ayın çekim günü
# doviz: dolar bazlı servis, çekilen tutar kura göre her ay biraz oynar
# zam: (eski fiyat, kaç ay önce yürürlüğe girdi; 0 = bu ay)
SERVICES = {
    "NETFLIX":         {"ad": "Netflix",         "kategori": "Video",      "fiyat": 289.99,  "gun": 3,
                        "zam": (249.99, 2)},
    "DISNEY+":         {"ad": "Disney+",         "kategori": "Video",      "fiyat": 249.90,  "gun": 7},
    "YOUTUBE PREMIUM": {"ad": "Youtube Premium", "kategori": "Video",      "fiyat": 119.99,  "gun": 21},
    "SPOTIFY":         {"ad": "Spotify",         "kategori": "Müzik",      "fiyat": 99.00,   "gun": 5,
                        "zam": (79.99, 1)},
    "YOUTUBE MUSIC":   {"ad": "Youtube Music",   "kategori": "Müzik",      "fiyat": 89.99,   "gun": 11},
    "APPLE MUSIC":     {"ad": "Apple Music",     "kategori": "Müzik",      "fiyat": 59.99,   "gun": 14},
    "CANVA PRO":       {"ad": "Canva Pro",       "kategori": "Üretkenlik", "fiyat": 757.50,  "gun": 19,
                        "zam": (704.70, 3)},
    "ADOBE CREATIVE":  {"ad": "Adobe Creative",  "kategori": "Üretkenlik", "fiyat": 379.00,  "gun": 23,
                        "doviz": True},
    "CHATGPT PLUS":    {"ad": "ChatGPT Plus",    "kategori": "Yapay Zekâ", "fiyat": 1019.49, "gun": 16,
                        "doviz": True},
    "CLAUDE PRO":      {"ad": "Claude Pro",      "kategori": "Yapay Zekâ", "fiyat": 1010.00, "gun": 15,
                        "doviz": True},
    "GEMINI":          {"ad": "Gemini",          "kategori": "Yapay Zekâ", "fiyat": 1000.00, "gun": 25,
                        "doviz": True},
}

# Demo kullanıcısının başlangıç durumu: daha önce dondurduğu kartlar ve
# zamdan sonra eski fiyatta bıraktığı limitler
INITIAL_CARD_STATE = {
    "DISNEY+":       {"durum": "Donduruldu"},
    "YOUTUBE MUSIC": {"durum": "Donduruldu"},
    "CLAUDE PRO":    {"durum": "Donduruldu"},
    "CANVA PRO":     {"limit": 704.70},
    "CHATGPT PLUS":  {"limit": 808.33},
}

CARD_NUMBERS = {
    "NETFLIX": "4821", "DISNEY+": "3390", "YOUTUBE PREMIUM": "9931",
    "SPOTIFY": "2205", "YOUTUBE MUSIC": "6614", "APPLE MUSIC": "5017",
    "CANVA PRO": "1140", "ADOBE CREATIVE": "7788", "CHATGPT PLUS": "3072",
    "CLAUDE PRO": "8456", "GEMINI": "6203",
}
