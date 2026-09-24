# Contributing Guidelines for Cyllo

Thank you for considering contributing to Cyllo! We welcome your input and appreciate the community effort to make this project even better.  
By participating in this project, you agree to abide by our [Code of Conduct](./CODE_OF_CONDUCT.md).

---

## Table of Contents

- [Getting Started](#getting-started)
- [How to Fork & Clone](#how-to-fork--clone)
- [Branch Naming Convention](#branch-naming-convention)
- [Commit Message Format](#commit-message-format)
- [Pull Request Process](#pull-request-process)
- [Code Style Guidelines](#code-style-guidelines)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [What We Don't Accept](#what-we-dont-accept)

---

## Getting Started

1. Check the [open issues](https://github.com/cyllo-opensource/cyllo/issues) to see if someone is already working on what you want to do.
2. If not, **open a new issue** first to discuss the change before writing any code.
3. Wait for a maintainer to assign the issue to you before you start working.

---

## How to Fork & Clone

### Step 1 — Fork the Repository
Click the **"Fork"** button at the top-right of the repository page.

### Step 2 — Clone Your Fork
```bash
git clone https://github.com/cyllo-opensource/cyllo.git
cd cyllo
```

### Step 3 — Add the Upstream Remote
```bash
git remote add upstream https://github.com/cyllo-opensource/cyllo.git
```

Verify remotes:
```bash
git remote -v
# origin    https://github.com/cyllo-opensource/cyllo.git (fetch)
# upstream  https://github.com/cyllo-opensource/cyllo.git (fetch)
```

### Step 4 — Sync Before Starting Work
Always keep your fork up to date:
```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

---

## Branch Naming Convention

Always create a new branch from `main`. **Never commit directly to `main`.**

| Type        | Format                           | Example                        |
|-------------|----------------------------------|--------------------------------|
| Feature     | `feature/short-description`      | `feature/add-user-auth`        |
| Bug Fix     | `fix/short-description`          | `fix/login-null-crash`         |
| Docs        | `docs/short-description`         | `docs/update-api-reference`    |
| Hotfix      | `hotfix/short-description`       | `hotfix/payment-failure`       |
| Refactor    | `refactor/short-description`     | `refactor/cleanup-db-queries`  |
| Tests       | `test/short-description`         | `test/add-auth-unit-tests`     |
| Release     | `release/version`                | `release/v2.1.0`               |

```bash
# Create and switch to a new branch
git checkout -b feature/your-feature-name
```

---

## Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Format
```
<type>(<optional scope>): <short summary>

[optional body — wrap at 72 chars]

[optional footer — e.g. Fixes #123, BREAKING CHANGE: ...]
```

### Types

| Type       | When to Use                                  |
|------------|----------------------------------------------|
| `feat`     | A new feature                                |
| `fix`      | A bug fix                                    |
| `docs`     | Documentation only changes                   |
| `style`    | Formatting, missing semicolons (no logic)    |
| `refactor` | Code change that isn't a fix or feature      |
| `test`     | Adding or fixing tests                       |
| `chore`    | Build process, tooling, dependency updates   |
| `perf`     | Performance improvements                     |
| `ci`       | CI configuration changes                     |

### Examples
```
feat(auth): add OAuth2 Google login
fix(api): handle null response from /users endpoint
docs: update installation instructions in README
test(cart): add unit tests for discount calculation
chore: upgrade dependencies to latest versions
```

---

## Pull Request Process

1. **Sync your branch** with upstream before submitting:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all checks locally** before pushing:
   ```bash
   # Run linting
   # Run tests
   # Verify build passes
   ```

3. **Push your branch** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Open a Pull Request** against the `main` branch of the upstream repo.

5. **Fill out the PR template** completely — PRs with incomplete templates will be closed.

6. **Link related issues** using keywords:
   - `Fixes #123` — closes the issue when PR merges
   - `Relates to #456` — links without closing

7. **Respond to review feedback** — address all comments before re-requesting review.

8. **Do NOT merge your own PR** — wait for a maintainer to approve and merge.

### PR Review SLA
- Maintainers aim to review PRs within **5 business days**.
- PRs with no activity for **30 days** will be closed automatically.

---

## Code Style Guidelines

- Follow the existing code style in the project.
- Use meaningful variable and function names.
- Write comments for complex or non-obvious logic.
- Keep functions small and focused (single responsibility).
- Remove debug logs, commented-out code, and unused imports before submitting.

---

## Reporting Bugs

Use the [Bug Report](./.github/ISSUE_TEMPLATE/bug_report.yml) template.  
**Do not open a public issue for security vulnerabilities** — see [SECURITY.md](./SECURITY.md).

---

## Suggesting Features

Use the [Feature Request](./.github/ISSUE_TEMPLATE/feature_request.yml) template.  
Discuss significant changes in [Discussions](https://github.com/cyllo-opensource/cyllo/discussions) before opening an issue.

---

## What We Don't Accept

- PRs without a linked and assigned issue
- Breaking changes without prior maintainer discussion
- PRs that fail CI checks
- Massive refactors without sign-off
- Unrelated changes bundled into one PR
- PRs with merge conflicts — please resolve them first
- AI-generated code dumps without review and understanding

---

## Thank You

Every contribution — big or small — makes a difference. We appreciate your time and effort!
