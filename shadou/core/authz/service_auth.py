from shadou.settings import get_settings


def _parse_scoped_keys() -> dict[str, set[str]]:
    """
    Format:
    SHADOU_SERVICE_KEYS="key1:public_info.read|repo.read,key2:public_info.read"
    """
    raw = get_settings().shadou_service_keys_raw
    mapping: dict[str, set[str]] = {}
    for item in [x.strip() for x in raw.split(",") if x.strip()]:
        if ":" not in item:
            mapping[item] = {"public_info.read"}
            continue
        key, scopes = item.split(":", 1)
        mapping[key.strip()] = {s.strip() for s in scopes.split("|") if s.strip()}
    return mapping


def authorize(api_key: str | None, required_scope: str) -> bool:
    if not api_key:
        return False
    scoped = _parse_scoped_keys()
    scopes = scoped.get(api_key, set())
    return required_scope in scopes

