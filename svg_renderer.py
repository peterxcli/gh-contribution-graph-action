import math
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from themes import Theme

CURVE_RATIO = 0.25
CHART_WIDTH = 1000
DEFAULT_X_AXIS_LABEL_MIN_SPACING = 90


def get_adaptive_x_axis_label_indices(
    month_count: int,
    chart_width: int = CHART_WIDTH,
    min_label_spacing: int = DEFAULT_X_AXIS_LABEL_MIN_SPACING,
) -> list[int]:
    if month_count <= 0:
        return []
    if month_count == 1:
        return [0]
    if chart_width <= 0 or min_label_spacing <= 0:
        return list(range(month_count))

    max_labels = max(2, math.floor(chart_width / min_label_spacing) + 1)
    if month_count <= max_labels:
        return list(range(month_count))

    interval = math.ceil((month_count - 1) / (max_labels - 1))
    indices = list(range(0, month_count, interval))
    last_index = month_count - 1

    if indices[-1] != last_index:
        month_spacing = chart_width / last_index
        last_gap = (last_index - indices[-1]) * month_spacing
        if last_gap < min_label_spacing:
            indices[-1] = last_index
        else:
            indices.append(last_index)

    return indices


def render_contribution_svg(
    username: str,
    repo_owner: str,
    repo_name: str,
    months: list,
    authored_values: list,
    reviewed_values: list,
    theme: Theme,
    output_dir: str = ".",
):
    """
    Generate an SVG contribution graph using the Jinja template.

    Args:
        username (str): GitHub username
        repo_owner (str): Owner of the repository
        repo_name (str): Name of the repository
        months (list): List of month labels (e.g., ["2023-01", "2023-02", ...])
        authored_values (list): List of authored PR counts per month
        reviewed_values (list): List of reviewed PR counts per month
        output_dir (str): Directory to save the output SVG file
        background_color (str): Background color of the SVG
        authored_color (str): Color for authored PRs line and points
        reviewed_color (str): Color for reviewed PRs line and points
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Calculate totals and max values
    total_authored = sum(authored_values)
    total_reviewed = sum(reviewed_values)
    max_authored_value = max(authored_values) if authored_values else 0
    max_reviewed_value = max(reviewed_values) if reviewed_values else 0
    x_axis_label_indices = get_adaptive_x_axis_label_indices(
        len(months), chart_width=CHART_WIDTH
    )

    # Set up Jinja environment
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("contribution-template.svg.jinja")

    # Render the template with our data
    rendered_svg = template.render(
        username=username,
        repo_owner=repo_owner,
        repo_name=repo_name,
        months=months,
        authored_values=authored_values,
        reviewed_values=reviewed_values,
        total_authored=total_authored,
        total_reviewed=total_reviewed,
        max_authored_value=max_authored_value,
        max_reviewed_value=max_reviewed_value,
        background_color=theme.background_color,
        title_color=theme.title_color,
        authored_color=theme.title_color,
        reviewed_color=theme.icon_color,
        text_color=theme.text_color,
        curve_ratio=CURVE_RATIO,
        x_axis_label_indices=x_axis_label_indices,
        chart_width=CHART_WIDTH,
    )

    # Save the rendered SVG to a file
    output_filename = (
        output_path / f"{username}-{repo_owner}-{repo_name}-contribution-graph.svg"
    )
    with open(output_filename, "w") as f:
        f.write(rendered_svg)

    print(f"\nContribution graph SVG saved as: {output_filename.absolute()}")

    return str(output_filename.absolute())


if __name__ == "__main__":
    # Example usage
    test_months = [
        "2024-10",
        "2024-11",
        "2024-12",
        "2025-01",
        "2025-02",
        "2025-03",
        "2025-04",
    ]
    test_authored = [6, 17, 16, 21, 13, 18, 2]
    test_reviewed = [3, 5, 6, 8, 14, 29, 26]

    render_contribution_svg(
        username="example_user",
        repo_owner="example_org",
        repo_name="example_repo",
        months=test_months,
        authored_values=test_authored,
        reviewed_values=test_reviewed,
        theme=Theme(
            title_color="#000000",
            icon_color="#000000",
            text_color="#000000",
            background_color="#FFFFFF",
            border_color="#CCCCCC",
            bg_color="gray",
        ),
        output_dir=".",
    )
