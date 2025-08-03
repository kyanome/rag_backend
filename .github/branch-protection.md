# Branch Protection Rules

This document outlines the branch protection rules for this repository.

## Main Branch Protection

The `main` branch should have the following protection rules:

### Required Status Checks
- CI / Test Python 3.11
- CI / Code Quality Checks
- CI / Build Package

### Requirements
- Require branches to be up to date before merging
- Require status checks to pass before merging
- Require pull request reviews before merging (at least 1 approval)
- Dismiss stale pull request approvals when new commits are pushed
- Require review from CODEOWNERS
- Include administrators in these restrictions

### Additional Settings
- Do not allow force pushes
- Do not allow deletions

## Develop Branch Protection

The `develop` branch should have the following protection rules:

### Required Status Checks
- CI / Test Python 3.11
- CI / Code Quality Checks

### Requirements
- Require status checks to pass before merging
- Require pull request reviews before merging (at least 1 approval)

## Branch Naming Convention

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Emergency fixes for production
- `release/*` - Release preparation