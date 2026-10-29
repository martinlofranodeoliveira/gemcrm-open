"""Local frontend asset guard core."""
MAX_ASSETS = 50
MAX_ASSET_LENGTH = 1000
MIN_ASSET_LENGTH = 1
PREFIX_HTTP = "http://"
PREFIX_HTTPS = "https://"
PREFIX_PROTOCOL_RELATIVE = "//"


def _is_external(trimmed):
    folded = trimmed.casefold()
    if folded.startswith(PREFIX_HTTP):
        return True
    if folded.startswith(PREFIX_HTTPS):
        return True
    if folded.startswith(PREFIX_PROTOCOL_RELATIVE):
        return True
    return False


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be dict")
    if "assets" in payload:
        assets = payload["assets"]
    else:
        assets = []
    if assets is None:
        raise ValueError("assets must be list")
    if not isinstance(assets, list):
        raise ValueError("assets must be list")
    if len(assets) > MAX_ASSETS:
        raise ValueError("assets over 50")
    external = []
    local = []
    for asset in assets:
        if not isinstance(asset, str):
            raise ValueError("asset must be str")
        if len(asset) < MIN_ASSET_LENGTH:
            raise ValueError("asset length invalid")
        if len(asset) > MAX_ASSET_LENGTH:
            raise ValueError("asset length invalid")
        trimmed = asset.strip()
        if trimmed == "":
            raise ValueError("asset blank")
        if _is_external(trimmed):
            external.append(trimmed)
        else:
            local.append(trimmed)
    total = len(external) + len(local)
    external_count = len(external)
    local_count = len(local)
    if external_count == 0:
        allows_offline = True
    else:
        allows_offline = False
    return {"total": total, "external_count": external_count, "local_count": local_count, "allows_offline": allows_offline, "external": external, "local": local}
