import pytest
from api.predictor import linear_regression, _get_confidence

# ── linear_regression ──────────────────────────────────────────────────────────

def test_linear_regression_positive_slope():
    points = [(0, 80), (5, 85), (10, 90), (15, 95), (20, 100)]
    slope, _ = linear_regression(points)
    assert slope > 0

def test_linear_regression_flat():
    points = [(0, 90), (5, 90), (10, 90), (15, 90), (20, 90)]
    slope, _ = linear_regression(points)
    assert abs(slope) < 0.01

def test_linear_regression_negative_slope():
    points = [(0, 100), (5, 95), (10, 90), (15, 85), (20, 80)]
    slope, _ = linear_regression(points)
    assert slope < 0

def test_linear_regression_single_point_returns_zero_slope():
    slope, _ = linear_regression([(0, 90)])
    assert slope == 0.0

def test_linear_regression_two_points():
    slope, intercept = linear_regression([(0, 100), (10, 80)])
    assert abs(slope - (-2.0)) < 0.001

# ── _get_confidence ────────────────────────────────────────────────────────────

def test_confidence_high_when_trend_descending():
    assert _get_confidence(1) == "high"
    assert _get_confidence(2) == "high"

def test_confidence_normal_when_trend_flat():
    assert _get_confidence(3) == "normal"

def test_confidence_low_when_trend_contradicts():
    assert _get_confidence(4) == "low"
    assert _get_confidence(5) == "low"

def test_confidence_low_when_trend_none():
    assert _get_confidence(None) == "low"

def test_confidence_low_when_trend_unknown():
    assert _get_confidence(99) == "low"


# ── _get_confidence (hyper) ────────────────────────────────────────────────────

def test_confidence_hyper_high_when_ascending():
    assert _get_confidence(4, "hyper") == "high"
    assert _get_confidence(5, "hyper") == "high"

def test_confidence_hyper_normal_when_flat():
    assert _get_confidence(3, "hyper") == "normal"

def test_confidence_hyper_low_when_descending():
    assert _get_confidence(1, "hyper") == "low"
    assert _get_confidence(2, "hyper") == "low"

def test_confidence_hyper_low_when_none():
    assert _get_confidence(None, "hyper") == "low"
