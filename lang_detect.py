from langdetect import detect, DetectorFactory
DetectorFactory.seed = 42

def is_malay(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    try:
        code = detect(t)
        return code in ("ms",)
    except:
        tl = " " + t.lower() + " "
        bm_hits = sum(x in tl for x in [" ialah ", " anda ", " kami ", " yang ", " bila ", " bagaimana ", " di ", " ke ", " untuk ", " akan "])
        en_hits = sum(x in tl for x in [" the ", " and ", " is ", " are ", " you ", " we "])
        return bm_hits >= max(2, en_hits+1)
