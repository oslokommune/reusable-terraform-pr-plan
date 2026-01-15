# reusable-terraform-pr-plan

Reusable GitHub Actions workflow for running Terraform plan on pull requests.

## Usage

```yaml
name: "Terraform PR"

on:
  pull_request:
    paths:
      - stacks/**
  issue_comment:
    types: [edited]

jobs:
  plan:
    uses: oslokommune/reusable-terraform-pr-plan/.github/workflows/reusable-terraform-pr-plan.yml@v1
    secrets:
      ssh-private-key: ${{ secrets.GOLDEN_PATH_IAC_PRIVATE_DEPLOY_KEY }}
```
