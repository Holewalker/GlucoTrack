import pytest
import httpx
from api.libre_client import authenticate, get_patient_id, get_cgm_data

AUTH_RESPONSE = {
    "status": 0,
    "data": {
        "authTicket": {"token": "test-jwt-token", "expires": 9999999999, "duration": 1}
    },
}

CONNECTIONS_RESPONSE = {
    "status": 0,
    "data": [{"patientId": "patient-123"}],
}

GRAPH_RESPONSE = {
    "status": 0,
    "data": {
        "glucoseMeasurement": {
            "Timestamp": "4/14/2026 8:00:00 AM",
            "ValueInMgPerDl": 95,
            "TrendArrow": 3,
            "isHigh": False,
            "isLow": False,
            "MeasurementColor": 1,
        },
        "graphData": [
            {
                "Timestamp": "4/14/2026 7:55:00 AM",
                "ValueInMgPerDl": 90,
                "TrendArrow": 3,
                "isHigh": False,
                "isLow": False,
                "MeasurementColor": 1,
            }
        ],
    },
}


async def test_authenticate_returns_token():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=AUTH_RESPONSE)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        token = await authenticate("email@test.com", "pass", client=client)
    assert token == "test-jwt-token"


async def test_get_patient_id():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=CONNECTIONS_RESPONSE)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        pid = await get_patient_id("token", client=client)
    assert pid == "patient-123"


async def test_get_cgm_data_returns_data():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=GRAPH_RESPONSE)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        data = await get_cgm_data("token", "patient-123", client=client)
    assert data["glucoseMeasurement"]["ValueInMgPerDl"] == 95
    assert len(data["graphData"]) == 1
