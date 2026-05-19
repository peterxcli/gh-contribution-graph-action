# OSS Contribution Graph Generator

A GitHub Action that generates contribution graph showing the number of pull requests authored and reviewed by a user in specific repositories over time.

## Usage

```yaml
- uses: peterxcli/gh-contribution-graph-action@v2.0
  with:
    targets: 'username@owner/repo [username@owner/repo ...]'
    github_token: ${{ secrets.GITHUB_TOKEN }}
    output_dir: 'path/to/output'  # Optional, defaults to current directory
    exclude_authored_from_reviewed: true  # Optional, defaults to false
    retention_months: 6  # Optional, defaults to all history
```

### Inputs

- `targets`: Comma-separated list of targets in the format `username@owner/repo`. Multiple targets can be specified with spaces.
- `github_token`: GitHub token for API access. Required for authentication.
- `output_dir`: Directory where the generated SVG files will be saved. Optional, defaults to the current directory.
- `exclude_authored_from_reviewed`: Whether to exclude PRs authored by the user from the reviewed count. Optional, defaults to `false`.
- `retention_months`: Number of recent calendar months to show, for example `6`. Optional, defaults to all history.

### [Example](https://github.com/peterxcli/peterxcli/blob/ba023f1647814d655845888fb66f904b851300ac/.github/workflows/oss-contribution-graph.yml)

```yaml
name: OSS Contribution Graph

on:
  schedule:
    - cron: '0 0 * * *'  # Run on at midnight UTC
  workflow_dispatch:
    inputs:
      targets:
        description: 'Target repositories and usernames (format: username,owner/repo [username,owner/repo ...])'
        required: true
        type: string
        default: 'peterxcli@apache/ozone, peterxcli@apache/kafka'

      exclude_review:
        description: 'Exclude review contributions'
        required: false
        type: boolean
        default: false

env:
  DEFAULT_TARGETS: 'peterxcli@apache/ozone, peterxcli@apache/kafka'
  EXCLUDE_REVIEW: 'false'

jobs:
  update-histogram:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Generate Contribution Graph
        uses: peterxcli/gh-contribution-graph-action@2.0
        with:
          targets: ${{ github.event.inputs.targets || env.DEFAULT_TARGETS }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          output_dir: 'images'
          exclude_authored_from_reviewed: ${{ github.event.inputs.exclude_review || env.EXCLUDE_REVIEW }}
          retention_months: 6

      - name: Commit and push updated image
        run: |
          git config --global user.name 'GitHub Action'
          git config --global user.email 'action@github.com'
          git add images/*.svg
          git commit -m "Update PR histogram" || echo "No changes to commit"
          git push
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Output

The action generates SVG files named in the format:
`{username}-{repo_owner}-{repo_name}-contribution-graph.svg`

Each graph shows:
- Number of PRs authored by the user
- Number of PRs reviewed by the user
- Total counts for both authored and reviewed PRs
- Monthly breakdown of contributions

Example:

![peterxcli-apache-ozone-contribution-graph](https://raw.githubusercontent.com/peterxcli/peterxcli/refs/heads/main/images/peterxcli-apache-ozone-contribution-graph.svg)

![jason810496-apache-airflow-contribution-graph](https://raw.githubusercontent.com/jason810496/jason810496/refs/heads/main/histograms/jason810496-apache-airflow-contribution-histogram.svg)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
