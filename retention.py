from collections.abc import Sequence
from datetime import datetime, timezone

import pandas as pd


def get_retention_month_index(
    retention_months: int,
    today: datetime | None = None,
) -> pd.DatetimeIndex:
    """
    Return the recent calendar months included by the retention setting.

    Args:
        retention_months (int): Number of recent calendar months to include.
        today (datetime | None): Reference date. Defaults to the current UTC date.

    Returns:
        pd.DatetimeIndex: Month-start timestamps from oldest to newest.

    Raises:
        ValueError: If ``retention_months`` is less than 1.
    """
    if retention_months < 1:
        raise ValueError("retention_months must be greater than 0")

    reference_date = today or datetime.now(timezone.utc)
    current_month = pd.Timestamp(
        year=reference_date.year,
        month=reference_date.month,
        day=1,
    )
    start_month = current_month - pd.DateOffset(months=retention_months - 1)

    return pd.date_range(start=start_month, periods=retention_months, freq="MS")


def build_monthly_contribution_data(
    authored_months: Sequence[str],
    reviewed_months: Sequence[str],
    retention_month_index: pd.DatetimeIndex | None = None,
) -> tuple[list[str], list[int], list[int]]:
    """
    Build aligned monthly contribution data for rendering.

    Args:
        authored_months (Sequence[str]): Months with authored PRs in ``YYYY-MM`` form.
        reviewed_months (Sequence[str]): Months with reviewed PRs in ``YYYY-MM`` form.
        retention_month_index (pd.DatetimeIndex | None): Optional retained month range.

    Returns:
        tuple[list[str], list[int], list[int]]: Month labels, authored counts, and reviewed counts.
    """
    contribution_counts = pd.concat(
        [
            _count_by_month(authored_months, "authored_count"),
            _count_by_month(reviewed_months, "reviewed_count"),
        ],
        axis=1,
    ).fillna(0)

    if retention_month_index is not None:
        contribution_counts = contribution_counts.reindex(
            retention_month_index,
            fill_value=0,
        )
    else:
        contribution_counts = contribution_counts.sort_index()

    contribution_counts = contribution_counts.astype(int)

    return (
        [month.strftime("%Y-%m") for month in contribution_counts.index],
        contribution_counts["authored_count"].tolist(),
        contribution_counts["reviewed_count"].tolist(),
    )


def _count_by_month(months: Sequence[str], count_name: str) -> pd.Series:
    if not months:
        return pd.Series(dtype="int64", name=count_name)

    parsed_months = pd.to_datetime(list(months), format="%Y-%m")
    return pd.Series(1, index=parsed_months, name=count_name).groupby(level=0).sum()
