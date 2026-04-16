import hashlib
import httpx

BASE_URL = "https://api-eu.libreview.io"
_HEADERS = {
    "accept-encoding": "gzip",
    "cache-control": "no-cache",
    "connection": "Keep-Alive",
    "content-type": "application/json",
    "product": "llu.android",
    "version": "4.17.0",
}


def _account_id_hash(account_id: str) -> str:
    return hashlib.sha256(str(account_id).encode("utf-8")).hexdigest()


class LibreViewError(Exception):
    """Raised when LibreView returns a non-zero status."""
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"LibreView error status={status}: {message}")


def _check_status(body: dict) -> None:
    status = body.get("status", 0)
    if status != 0:
        msg = body.get("error", {}).get("message", "") or body.get("data", {}).get("message", "") if isinstance(body.get("data"), dict) else ""
        raise LibreViewError(status, msg)


def _auth_headers(token: str, account_id: str) -> dict:
    hashed = _account_id_hash(account_id)
    return {
        **_HEADERS,
        "authorization": f"Bearer {token}",
        "Account-Id": hashed,
        "account-id": hashed,
    }


async def _post(client: httpx.AsyncClient, url: str, **kwargs) -> dict:
    resp = await client.post(url, **kwargs)
    resp.raise_for_status()
    body = resp.json()
    _check_status(body)
    return body


async def _get(client: httpx.AsyncClient, url: str, **kwargs) -> dict:
    resp = await client.get(url, **kwargs)
    resp.raise_for_status()
    body = resp.json()
    _check_status(body)
    return body


async def authenticate(
    email: str, password: str, client: httpx.AsyncClient | None = None
) -> tuple[str, str]:
    """Returns (token, account_id)."""
    async def _do(c: httpx.AsyncClient) -> tuple[str, str]:
        body = await _post(
            c, f"{BASE_URL}/llu/auth/login",
            json={"email": email, "password": password},
            headers=_HEADERS,
        )
        token = body["data"]["authTicket"]["token"]
        account_id = body["data"]["user"]["id"]
        return token, account_id

    if client is not None:
        return await _do(client)
    async with httpx.AsyncClient() as c:
        return await _do(c)


async def get_patient_id(
    token: str, account_id: str, client: httpx.AsyncClient | None = None
) -> str:
    async def _do(c: httpx.AsyncClient) -> str:
        body = await _get(
            c, f"{BASE_URL}/llu/connections",
            headers=_auth_headers(token, account_id),
        )
        return body["data"][0]["patientId"]

    if client is not None:
        return await _do(client)
    async with httpx.AsyncClient() as c:
        return await _do(c)


async def get_cgm_data(
    token: str, account_id: str, patient_id: str,
    client: httpx.AsyncClient | None = None,
) -> dict:
    async def _do(c: httpx.AsyncClient) -> dict:
        body = await _get(
            c, f"{BASE_URL}/llu/connections/{patient_id}/graph",
            headers=_auth_headers(token, account_id),
        )
        return body["data"]

    if client is not None:
        return await _do(client)
    async with httpx.AsyncClient() as c:
        return await _do(c)
