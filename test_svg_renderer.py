from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from svg_renderer import (
    DEFAULT_X_AXIS_LABEL_MIN_SPACING,
    CHART_WIDTH,
    get_adaptive_x_axis_label_indices,
    render_contribution_svg,
)
from themes import Theme


def _months(count):
    return [f"{2024 + index // 12}-{index % 12 + 1:02d}" for index in range(count)]


def _theme():
    return Theme(
        title_color="#000000",
        icon_color="#111111",
        text_color="#222222",
        background_color="#FFFFFF",
        border_color="#CCCCCC",
        bg_color="gray",
    )


def test_x_axis_label_indices_keep_all_labels_when_they_fit():
    assert get_adaptive_x_axis_label_indices(4) == [0, 1, 2, 3]


def test_x_axis_label_indices_reduce_dense_months_without_crowding_edges():
    indices = get_adaptive_x_axis_label_indices(24)
    month_spacing = CHART_WIDTH / (24 - 1)

    assert indices[0] == 0
    assert indices[-1] == 23
    assert len(indices) < 24
    assert all(
        (right - left) * month_spacing >= DEFAULT_X_AXIS_LABEL_MIN_SPACING
        for left, right in zip(indices, indices[1:])
    )


def test_rendered_svg_only_includes_adaptive_x_axis_labels(tmp_path):
    months = _months(24)

    svg_path = render_contribution_svg(
        username="example_user",
        repo_owner="example_org",
        repo_name="example_repo",
        months=months,
        authored_values=[0] * len(months),
        reviewed_values=[0] * len(months),
        theme=_theme(),
        output_dir=tmp_path,
    )

    svg = Path(svg_path).read_text()
    visible_indices = set(get_adaptive_x_axis_label_indices(len(months)))

    for index, month in enumerate(months):
        if index in visible_indices:
            assert month in svg
        else:
            assert month not in svg


def test_renderer_passes_chart_width_to_template(monkeypatch, tmp_path):
    captured_context = {}

    class FakeTemplate:
        def render(self, **context):
            captured_context.update(context)
            return "<svg />"

    class FakeEnvironment:
        def __init__(self, **_kwargs):
            pass

        def get_template(self, _template_name):
            return FakeTemplate()

    monkeypatch.setattr("svg_renderer.Environment", FakeEnvironment)

    render_contribution_svg(
        username="example_user",
        repo_owner="example_org",
        repo_name="example_repo",
        months=_months(3),
        authored_values=[0, 1, 0],
        reviewed_values=[1, 0, 1],
        theme=_theme(),
        output_dir=tmp_path,
    )

    assert captured_context["chart_width"] == CHART_WIDTH


@pytest.mark.parametrize(
    ("exclude_authored_from_reviewed", "reviewed_url"),
    [
        (
            False,
            "https://github.com/example_org/example_repo/pulls?q=is%3Apr+reviewed-by%3Aexample_user",
        ),
        (
            True,
            "https://github.com/example_org/example_repo/pulls?q=is%3Apr+reviewed-by%3Aexample_user+-author%3Aexample_user",
        ),
    ],
)
def test_total_labels_link_to_matching_pull_requests(
    tmp_path, exclude_authored_from_reviewed, reviewed_url
):
    svg_path = render_contribution_svg(
        username="example_user",
        repo_owner="example_org",
        repo_name="example_repo",
        months=_months(1),
        authored_values=[1],
        reviewed_values=[2],
        theme=_theme(),
        output_dir=tmp_path,
        exclude_authored_from_reviewed=exclude_authored_from_reviewed,
    )

    links = ET.parse(svg_path).getroot().findall(
        ".//{http://www.w3.org/2000/svg}a"
    )

    assert "Total PRs Authored" in "".join(links[0].itertext())
    assert links[0].attrib["href"] == (
        "https://github.com/example_org/example_repo/pulls?q=is%3Apr+author%3Aexample_user"
    )
    assert "Total PRs Reviewed" in "".join(links[1].itertext())
    assert links[1].attrib["href"] == reviewed_url
