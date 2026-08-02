import os
import sys
from datetime import datetime
from pathlib import Path

import click
import pandas as pd
from tqdm import tqdm
import requests

from svg_renderer import render_contribution_svg
from themes import THEME_URI, Theme, get_themes
from target_parser import parse_targets


def generate_contribution_graph(
    username: str,
    repo_owner: str,
    repo_name: str,
    theme: Theme,
    output_dir: str = ".",
    exclude_authored_from_reviewed: bool = False,
):
    """
    Generate a contribution graph for a user's PRs in a specific repository.

    Args:
        username (str): GitHub username to analyze
        repo_owner (str): Owner of the repository
        repo_name (str): Name of the repository
        output_dir (str): Directory to save the output PNG file
        exclude_authored_from_reviewed (bool): Whether to exclude PRs authored by the user from the reviewed count
        theme (Theme): Theme object for styling the SVG
    """
    # GitHub API setup
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable is not set")

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    HEADERS = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    def run_graphql_query(query, variables=None):
        response = requests.post(
            "https://api.github.com/graphql",
            headers=HEADERS,
            json={"query": query, "variables": variables},
        )
        if response.status_code != 200:
            raise Exception(f"Query failed: {response.status_code} - {response.text}")
        return response.json()

    def get_month_year(date_str):
        # Handle both formats: with and without timezone
        if "+" in date_str:
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
        else:
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return date.strftime("%Y-%m")

    def fetch_prs_with_cursor(query, variables, desc):
        prs = []
        has_next_page = True
        end_cursor = None

        with tqdm(desc=desc) as pbar:
            while has_next_page:
                variables["cursor"] = end_cursor
                result = run_graphql_query(query, variables)

                if "errors" in result:
                    raise Exception(f"GraphQL Error: {result['errors']}")

                prs_data = result["data"]["search"]["edges"]
                prs.extend([edge["node"] for edge in prs_data])

                page_info = result["data"]["search"]["pageInfo"]
                has_next_page = page_info["hasNextPage"]
                end_cursor = page_info["endCursor"]

                pbar.update(len(prs_data))

        return prs

    # GraphQL query template
    prs_query = """
    query($cursor: String, $searchQuery: String!) {
      search(
        query: $searchQuery
        type: ISSUE
        first: 100
        after: $cursor
      ) {
        edges {
          node {
            ... on PullRequest {
              createdAt
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """

    # Fetch authored PRs
    print(f"Fetching PRs authored by {username}...")
    authored_variables = {
        "searchQuery": f"repo:{repo_owner}/{repo_name} is:pr author:{username}"
    }
    authored_prs = fetch_prs_with_cursor(
        prs_query, authored_variables, "Fetching authored PRs"
    )
    authored_dates = [get_month_year(pr["createdAt"]) for pr in authored_prs]

    # Fetch reviewed PRs
    print(f"\nFetching PRs reviewed by {username}...")
    reviewed_query = f"repo:{repo_owner}/{repo_name} is:pr reviewed-by:{username}"
    if exclude_authored_from_reviewed:
        reviewed_query += f" -author:{username}"
    reviewed_variables = {"searchQuery": reviewed_query}
    reviewed_prs = fetch_prs_with_cursor(
        prs_query, reviewed_variables, "Fetching reviewed PRs"
    )
    reviewed_dates = [get_month_year(pr["createdAt"]) for pr in reviewed_prs]

    # Create DataFrames for counting
    authored_df = (
        pd.DataFrame(authored_dates, columns=["month"])
        .groupby("month")
        .size()
        .reset_index(name="authored_count")
    )
    reviewed_df = (
        pd.DataFrame(reviewed_dates, columns=["month"])
        .groupby("month")
        .size()
        .reset_index(name="reviewed_count")
    )

    # Merge DataFrames
    merged_df = pd.merge(authored_df, reviewed_df, on="month", how="outer").fillna(0)
    merged_df = merged_df.astype({"authored_count": int, "reviewed_count": int})
    merged_df["month"] = pd.to_datetime(merged_df["month"], format="%Y-%m")

    # Ensure the dataframe is sorted by month
    merged_df = merged_df.sort_values("month")

    # Format month strings
    months = [dt.strftime("%Y-%m") for dt in merged_df["month"]]

    # Get values
    authored_values = merged_df["authored_count"].tolist()
    reviewed_values = merged_df["reviewed_count"].tolist()

    render_contribution_svg(
        username=username,
        repo_owner=repo_owner,
        repo_name=repo_name,
        months=months,
        authored_values=authored_values,
        reviewed_values=reviewed_values,
        theme=theme,
        output_dir=output_path,
    )


@click.command()
@click.option(
    "--targets",
    required=True,
    help="List of targets in the format 'username@owner/repo'. Multiple targets can be separated by spaces or commas.",
)
@click.option(
    "--output-dir",
    required=True,
    help="Directory to save the output PNG files",
)
@click.option(
    "--exclude-authored-from-reviewed",
    is_flag=True,
    help="Exclude PRs authored by the user from the reviewed count",
)
@click.option(
    "--theme",
    default="default",
    help=f"Theme for the SVG. Available themes: {THEME_URI}. Default: 'default'",
)
@click.option(
    "--authored-color",
    help="Color for authored PRs line and points",
)
@click.option(
    "--reviewed-color",
    help="Color for reviewed PRs line and points",
)
def main(
    targets,
    output_dir,
    exclude_authored_from_reviewed,
    theme,
    authored_color,
    reviewed_color,
):
    """
    Generate contribution graphs for multiple targets.

    Args:
        targets (str): List of targets in the format 'username@owner/repo'. Multiple targets can be separated by spaces or commas.
        output_dir (str): Directory to save the output PNG files
        exclude_authored_from_reviewed (bool): Whether to exclude PRs authored by the user from the reviewed count
        theme (str): Theme for the SVG
        authored_color (str): Color for authored PRs line and points
        reviewed_color (str): Color for reviewed PRs line and points
    """
    available_themes = get_themes()
    theme: Theme = available_themes.get(theme)
    if not theme:
        raise click.BadParameter(
            f"Theme '{theme}' not found. Available themes: {available_themes.keys()}"
        )
    # override theme colors if provided authored_color or reviewed_color
    if authored_color:
        theme.title_color = f"#{authored_color}"
    if reviewed_color:
        theme.icon_color = f"#{reviewed_color}"

    try:
        parsed_targets = parse_targets(targets)
    except ValueError as e:
        raise click.BadParameter(str(e))

    for target in parsed_targets:
        try:
            generate_contribution_graph(
                target[0],
                target[1],
                target[2],
                theme,
                output_dir,
                exclude_authored_from_reviewed,
            )
        except Exception as e:
            click.echo(
                f"Error generating graph for {target[0]} in {target[1]}/{target[2]}: {str(e)}",
                err=True,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
