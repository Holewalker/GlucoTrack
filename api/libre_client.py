import httpx

BASE_URL = "https://api-eu.libreview.io"
_HEADERS = {
    "product": "llu.android",
    "version": "4.2.1",
    "content-type": "application/json",
}


def _auth_headers(token: str) -> dict:
    return {**_HEADERS, "authorization": f"Bearer {token}"}


async def authenticate(
    email: str, password: str, client: httpx.AsyncClient | None = None
) -> str:
    if client is not None:
        resp = await client.post(
            f"{BASE_URL}/llu/auth/login",
            json={"email": email, "password": password},
            headers=_HEADERS,
        )
        resp.raise_for_status()
        return resp.json()["data"]["authTicket"]["token"]
    async with httpx.AsyncClient() as c:
        resp = await c.post(
            f"{BASE_URL}/llu/auth/login",
            json={"email": email, "password": password},
            headers=_HEADERS,
        )
        resp.raise_for_status()
        return resp.json()["data"]["authTicket"]["token"]


async def get_patient_id(
    token: str, client: httpx.AsyncClient | None = None
) -> str:
    if client is not None:
        resp = await client.get(
            f"{BASE_URL}/llu/connections",
            headers=_auth_headers(token),
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["patientId"]
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/llu/connections",
            headers=_auth_headers(token),
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["patientId"]


async def get_cgm_data(
    token: str, patient_id: str, client: httpx.AsyncClient | None = None
) -> dict:
    if client is not None:
        resp = await client.get(
            f"{BASE_URL}/llu/connections/{patient_id}/graph",
            headers=_auth_headers(token),
        )
        resp.raise_for_status()
        return resp.json()["data"]
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/llu/connections/{patient_id}/graph",
            headers=_auth_headers(token),
        )
        resp.raise_for_status()
        return resp.json()["data"]
