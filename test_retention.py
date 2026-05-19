from datetime import datetime, timezone

import pytest

from retention import build_monthly_contribution_data, get_retention_month_index


def test_get_retention_month_index_uses_recent_calendar_months():
    """Test retention includes the current month and previous calendar months."""
    month_index = get_retention_month_index(
        6,
        today=datetime(2026, 5, 19, tzinfo=timezone.utc),
    )

    assert [month.strftime("%Y-%m") for month in month_index] == [
        "2025-12",
        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
        "2026-05",
    ]


def test_get_retention_month_index_rejects_invalid_month_count():
    """Test retention requires a positive number of months."""
    with pytest.raises(ValueError, match="greater than 0"):
        get_retention_month_index(0)


def test_build_monthly_contribution_data_zero_fills_retained_months():
    """Test retained months are fixed and missing counts are zero-filled."""
    month_index = get_retention_month_index(
        4,
        today=datetime(2026, 5, 19, tzinfo=timezone.utc),
    )

    months, authored_values, reviewed_values = build_monthly_contribution_data(
        authored_months=["2026-02", "2026-05", "2026-05"],
        reviewed_months=["2026-04"],
        retention_month_index=month_index,
    )

    assert months == ["2026-02", "2026-03", "2026-04", "2026-05"]
    assert authored_values == [1, 0, 0, 2]
    assert reviewed_values == [0, 0, 1, 0]


def test_build_monthly_contribution_data_renders_empty_retained_months():
    """Test retained months render even when there are no contributions."""
    month_index = get_retention_month_index(
        3,
        today=datetime(2026, 5, 19, tzinfo=timezone.utc),
    )

    months, authored_values, reviewed_values = build_monthly_contribution_data(
        authored_months=[],
        reviewed_months=[],
        retention_month_index=month_index,
    )

    assert months == ["2026-03", "2026-04", "2026-05"]
    assert authored_values == [0, 0, 0]
    assert reviewed_values == [0, 0, 0]


def test_build_monthly_contribution_data_without_retention_uses_data_months():
    """Test unrestricted graphs keep only months that have contribution data."""
    months, authored_values, reviewed_values = build_monthly_contribution_data(
        authored_months=["2026-03", "2026-01", "2026-03"],
        reviewed_months=["2026-02"],
    )

    assert months == ["2026-01", "2026-02", "2026-03"]
    assert authored_values == [1, 0, 2]
    assert reviewed_values == [0, 1, 0]
