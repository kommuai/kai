"""Pick an intent-appropriate clarifying question when the agent has no grounding.

Used by `agent_loop.py` as the substitute when an ungrounded `direct_answer`
is downgraded to `clarifying_question`. Replaces the prior single
car/brand/model/dongle string which leaked into office/pricing/warranty/QR
turns and pushed users toward LA unnecessarily.

Stays a pure function: no I/O, no LLM call, no provider dependency.
"""

from __future__ import annotations

import re


_VEHICLE_BRANDS = (
    "myvi", "alza", "ativa", "perodua", "proton", "axia", "saga",
    "x50", "x70", "x90", "s70",
    "honda", "city", "civic", "crv", "cr-v", "hrv", "hr-v",
    "vios", "toyota", "alphard", "vellfire", "corolla",
    "byd", "atto", "seal", "sealion",
    "mazda", "lexus", "mercedes", "bmw", "audi",
    "tiggo", "chery", "jaecoo",
    "kereta",
)


def _lower(text: str) -> str:
    return (text or "").lower()


def _has_any(text: str, keys: tuple[str, ...]) -> bool:
    return any(k in text for k in keys)


def _is_vehicle_query(text: str) -> bool:
    t = _lower(text)
    if _has_any(t, _VEHICLE_BRANDS):
        return True
    # standalone "car" / "vehicle" / "kereta" cues
    return bool(re.search(r"\b(car|vehicle|kereta)\b", t))


def pick_clarify_for_intent(
    user_text: str,
    lang: str = "EN",
    session_topics: dict[str, str] | None = None,
) -> str:
    """Return one short clarifying question that matches the user's apparent intent.

    Falls back to a friendly menu when intent is unclear (not a vehicle question).
    Never returns a hedge preamble (`clarify_validation` rules still apply).
    """
    t = _lower(user_text)
    bm = (lang or "EN").upper() == "BM"
    topics = session_topics or {}
    last_vehicle = (topics.get("last_vehicle") or "").strip()
    last_year = (topics.get("last_vehicle_year") or "").strip()
    last_topic = (topics.get("last_topic") or "").strip()

    # Vehicle thread with model already known — do not re-ask year/ACC
    if last_vehicle and (
        last_topic == "vehicle_support"
        or _is_vehicle_query(user_text)
        or len((user_text or "").split()) <= 8
    ):
        veh = last_vehicle
        if last_year and last_year not in veh:
            veh = f"{veh} ({last_year})"
        return (
            f"Saya semak senarai sokongan rasmi untuk {veh} — sebentar."
            if bm else
            f"I'll check our official support list for {veh} now."
        )

    # Office / hours / location
    if _has_any(t, (
        "office", "address", "alamat", "location", "lokasi",
        "where are you", "where is", "directions", "arah",
        "open today", "buka", "tutup", "closed", "hours", "operating",
        "waktu pejabat",
    )):
        return (
            "Anda nak tahu waktu pejabat, alamat, atau arah ke HQ kami?"
            if bm else
            "Are you asking about our office hours, address, or directions to HQ?"
        )

    # Pricing / RTO
    if _has_any(t, (
        "price", "harga", "cost", "berapa", "how much",
        "rto", "rent to own", "rent-to-own", "ansuran", "installment",
        "one-off", "one off", "deposit",
    )):
        return (
            "Tentang harga \u2014 RM4,999 sekali bayar atau RM175/bulan + RM1,999 deposit (RTO). Yang mana lebih sesuai?"
            if bm else
            "On pricing \u2014 RM4,999 one-off or RM175/month + RM1,999 deposit (Rent-to-Own). Which suits you better?"
        )

    # Supported list
    if _has_any(t, ("supported list", "support list", "list of cars", "list of support", "compatible", "senarai")):
        return (
            "Senarai rasmi di kommu.ai/support. Kereta apa yang anda pertimbangkan?"
            if bm else
            "The official supported list is at kommu.ai/support. Which car are you considering?"
        )

    # Warranty / dongle
    if _has_any(t, ("warranty", "waranti", "dongle")):
        return (
            "Sila kongsi ID dongle anda, saya akan semak status waranti."
            if bm else
            "Share your dongle ID and I'll check the warranty status."
        )

    # Short follow-up with state name (FAQ: regional_installer_followup)
    if re.search(
        r"\b(penang|johor|ipoh|melaka|sabah|sarawak|kedah|perak|kl|selangor)\b", t, re.I
    ) and re.search(r"\b(one|installer|pemasang)\b", t, re.I):
        return (
            "Ya — kami ada pemasang rakan kongsi di Penang. Kongsi poskod/kawasan anda."
            if bm and "penang" in t else
            "Yes — we have a partner installer in Penang. Share your postcode or area."
            if "penang" in t else
            "Yes — we have partner installers in several states. Share your postcode or area."
        )

    # Partner installer — before install check ("installer" contains "install")
    if re.search(r"\binstallers?\b", user_text, re.I) or re.search(
        r"\b(pemasang|partner\s+install)\b", user_text, re.I
    ):
        return (
            "Ya — kami ada pemasang rakan kongsi di Penang dan negeri lain. Kongsi poskod/kawasan anda."
            if bm else
            "Yes — we have partner installers in Penang and other states. Share your postcode or area."
        )

    # Install / video / guide (not installer)
    if re.search(r"\binstallers?\b", user_text, re.I):
        pass
    elif re.search(r"\b(install(?:ation)?|pasang|pemasangan|diy)\b", user_text, re.I) or _has_any(
        t, ("video", "guide", "tutorial", "panduan")
    ):
        return (
            "Tentang pemasangan \u2014 anda nak buat sendiri (ada video panduan) atau buat janji temu di HQ?"
            if bm else
            "About installation \u2014 self-install (we have a video guide) or schedule an HQ appointment?"
        )

    # Visitor pass / QR access
    if _has_any(t, ("qr", "visitor pass", "visitor link", "access link", "akses", "pas masuk", "pass link")):
        return (
            "Untuk QR pas masuk Emhub: sila bagi tarikh dan masa lawatan."
            if bm else
            "For the Emhub visitor QR: please share your visit date and time."
        )

    # Order / payment status
    if _has_any(t, ("order", "shipment", "tracking", "courier", "paid", "payment status", "invoice")):
        return (
            "Tentang pesanan \u2014 sila kongsi nombor order atau invois supaya saya boleh semak."
            if bm else
            "About your order \u2014 share the order or invoice number so I can check."
        )

    # Diagnostic / device
    if _has_any(t, ("error", "issue", "rosak", "tak boleh", "not working", "cannot", "can't", "problem", "masalah", "blue screen", "process error")):
        return (
            "Tentang masalah peranti \u2014 kereta apa, error code apa (boleh ambil gambar dari KommuAI \u2192 Visualization)?"
            if bm else
            "About the device issue \u2014 which car, and what exact error or symptom (screenshot from KommuAI \u2192 Visualization helps)?"
        )

    # Vehicle compatibility (only when query actually looks vehicle-y)
    if _is_vehicle_query(user_text):
        return (
            "Tahun kereta anda berapa, dan adakah ada ACC (Adaptive Cruise Control) + LKA (Lane Keep Assist) dari kilang?"
            if bm else
            "What year is your car, and does it have factory ACC (Adaptive Cruise Control) + LKA (Lane Keep Assist)?"
        )

    # Default: friendly menu (not a car/dongle interrogation)
    return (
        "Saya boleh bantu dengan harga, sokongan kereta, pemasangan, akses QR, waranti, atau masalah peranti. Apa yang anda perlukan?"
        if bm else
        "I can help with pricing, vehicle compatibility, installation, QR access, warranty, or device issues. What do you need?"
    )
