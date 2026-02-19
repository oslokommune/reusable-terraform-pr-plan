# reusable-terraform-pr-plan

Reusable GitHub Actions workflow for running Terraform plan on pull requests.

## Usage

### Basic usage

```yaml
name: "Terraform PR"

on:
  pull_request:
  issue_comment:
    types: [edited]

jobs:
  plan:
    uses: oslokommune/reusable-terraform-pr-plan/.github/workflows/reusable-terraform-pr-plan.yml@v1
    secrets:
      ssh-private-key: ${{ secrets.GOLDEN_PATH_IAC_PRIVATE_DEPLOY_KEY }}
```

### With manual trigger

Add `workflow_dispatch` to allow manually running plans for specific stacks.

```yaml
name: "Terraform PR"

on:
  pull_request:
  issue_comment:
    types: [edited]
  workflow_dispatch:
    inputs:
      selected-stacks:
        description: 'Stacks to plan (e.g., "stacks/dev/{dns,iam}", "stacks/dev/app-*", "stacks/**")'
        required: true
        type: string

jobs:
  plan:
    uses: oslokommune/reusable-terraform-pr-plan/.github/workflows/reusable-terraform-pr-plan.yml@v1
    with:
      selected-stacks: ${{ inputs.selected-stacks }}
    secrets:
      ssh-private-key: ${{ secrets.GOLDEN_PATH_IAC_PRIVATE_DEPLOY_KEY }}
```

### With automerge

The `pr-automerge` input expression determines whether to add or remove the `automerge` label, which will be picked up by Renovate later on to perform the actual merge. The example below enables automerge for Renovate PRs that target a dev environment as long as there are no major updates and all Terraform plans are successful.

```yaml
name: "Terraform PR"

on:
  pull_request:
  issue_comment:
    types: [edited]

jobs:
  plan:
    uses: oslokommune/reusable-terraform-pr-plan/.github/workflows/reusable-terraform-pr-plan.yml@v1
    with:
      pr-automerge: >-
        ${{
          contains(github.event.pull_request.labels.*.name, 'env/dev')
          && !contains(github.event.pull_request.labels.*.name, 'Major update ⚠️')
        }}
      pr-automerge-when: any-changes # NOTE: Set this to 'no-changes' to only allow automerge if all plans have no changes
    secrets:
      ssh-private-key: ${{ secrets.GOLDEN_PATH_IAC_PRIVATE_DEPLOY_KEY }}
```
