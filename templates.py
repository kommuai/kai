EN_GREETING = (
    "Hi ! i'm Kai - Kommu Chatbot\n"
    
)

BM_GREETING = (
    "Hai! Saya Kai - Chatbot Kommu\n"
    
)

def reply_about(lang="EN"):
    if lang == "BM":
        return ("Kommu menghasilkan KommuAssist, sistem bantuan pemanduan Tahap 2 (ADAS) untuk kereta yang serasi. "
                "Ia menambah pengekalan lorong, kawalan jelajah adaptif (ACC) dan stop-and-go melalui perkakasan plug-and-play. "
                "Maklumat: https://kommu.ai/  Produk: https://kommu.ai/products/  FAQ: https://kommu.ai/faq/")
    return ("Kommu builds KommuAssist, a Level 2 driver-assistance (ADAS) upgrade for compatible cars. "
            "It adds lane centering, adaptive cruise control (ACC) and stop-and-go via plug-and-play hardware. "
            "Learn more: https://kommu.ai/  Product: https://kommu.ai/products/  FAQ: https://kommu.ai/faq/")

def reply_how(lang="EN"):
    if lang == "BM":
        return ("KommuAssist berfungsi dengan perkakasan plug-and-play yang menjalankan model bantuan pemanduan "
                "yang ditala untuk jalan raya Malaysia. Ia mengekalkan kereta di tengah lorong, mengekalkan jarak (ACC), "
                "dan mengendalikan trafik henti-gerak. Butiran: https://kommu.ai/")
    return ("KommuAssist works via plug-and-play hardware running a driver-assistance model tuned for Malaysian roads. "
            "It keeps the car centered, maintains distance (ACC) and handles stop-and-go. Details: https://kommu.ai/")

def reply_buy(lang="EN"):
    if lang=="BM":
        return ("Tempah KommuAssist 1s: https://kommu.ai/products/ "
                "(anggaran hantar ~1 minggu; pemasangan percuma di HQ dgn janji temu). "
                "Semak sokongan: https://kommu.ai/support/ — beritahu jenama/model/tahun/varian + ACC & LKAS.")
    return ("Order KommuAssist 1s: https://kommu.ai/products/ "
            "(ships ~1 week; free install at HQ by appointment). "
            "Check support: https://kommu.ai/support/ — tell me make/model/year/trim + ACC & LKAS.")

def reply_test_drive(lang="EN"):
    link = "https://calendly.com/kommuassist/test-drive?month=2025-08"
    if lang=="BM":
        return f"Tempah pandu uji di sini: {link}"
    return f"Book a test drive here: {link}"

def reply_office_hours(lang="EN"):
    if lang=="BM":
        return ("Waktu pejabat: Isnin–Jumaat, 10:00–18:00 (MYT). "
                "Alamat: C/105B, Block C, Jalan PJU 10/2a, Damansara Damai, 47830 Petaling Jaya, Selangor. "
                "Waze: https://waze.com/ul?ll=3.2137,101.6056&navigate=yes")
    return ("Office hours: Mon–Fri, 10:00–18:00 (MYT). "
            "Address: C/105B, Block C, Jalan PJU 10/2a, Damansara Damai, 47830 Petaling Jaya, Selangor. "
            "Waze: https://waze.com/ul?ll=3.2137,101.6056&navigate=yes")

def reply_not_blinking(lang="EN"):
    if lang=="BM":
        return ("Semakan kuasa: 1) Ignition ON; 2) Cabut/pasang semula USB-C & relay harness; "
                "3) Soft reboot (cabut kuasa 30s, sambung semula). "
                "Jika masih tiada LED, hantar video/gambar + emel/telefon pesanan. "
                "Rujukan: Produk https://kommu.ai/products/ · FAQ https://kommu.ai/faq/")
    return ("Power checks: 1) Ignition ON; 2) Reseat USB-C & relay harness; "
            "3) Soft reboot (unplug 30s, plug back). "
            "If still no LED, share a short clip + order email/phone. "
            "Refs: Product https://kommu.ai/products/ · FAQ https://kommu.ai/faq/")

def reply_part_replacement(lang="EN"):
    if lang=="BM":
        return ("Boleh — kongsi bahagian (Vision/Relay/Harness/Kabel), penerangan isu + foto/video, "
                "dan emel/telefon pesanan. Saya akan buka tiket; ejen manusia akan hubungi tentang harga & stok. "
                "FAQ: https://kommu.ai/faq/")
    return ("Sure — share the part (Vision/Relay/Harness/Cable), issue details + photo/video, "
            "and your order email/phone. I’ll open a ticket; a human will follow up with price & stock. "
            "FAQ: https://kommu.ai/faq/")

FALLBACK_EN = ("I can help with price, support check, installation, office hours, part replacement, and test drives. "
               "Try: 'Buy Kommu', 'What is Kommu', 'How does it work', 'Office time', 'Test drive'. Need a live agent? Type LA.")
FALLBACK_BM = ("Saya boleh bantu harga, semakan sokongan, pemasangan, waktu pejabat, penggantian bahagian dan pandu uji. "
               "Cuba: 'Beli Kommu', 'Apa itu Kommu', 'Bagaimana ia berfungsi', 'Waktu pejabat', 'Pandu uji'. Perlu ejen manusia? Taip LA.")
