from api.poller import parse_reading


def test_parse_reading_formats_timestamp():
    raw = {
        "Timestamp": "4/14/2026 8:05:00 AM",
        "ValueInMgPerDl": 95,
        "TrendArrow": 3,
        "isHigh": False,
        "isLow": False,
        "MeasurementColor": 1,
    }
    result = parse_reading(raw)
    assert result["timestamp"] == "2026-04-14T08:05:00"
    assert result["value_mgdl"] == 95
    assert result["trend_arrow"] == 3
    assert result["is_high"] is False
    assert result["is_low"] is False


def test_parse_reading_pm_time():
    raw = {
        "Timestamp": "4/14/2026 2:30:00 PM",
        "ValueInMgPerDl": 150,
        "TrendArrow": 4,
        "isHigh": True,
        "isLow": False,
        "MeasurementColor": 2,
    }
    result = parse_reading(raw)
    assert result["timestamp"] == "2026-04-14T14:30:00"
