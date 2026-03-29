# Release Guide

This document defines the release procedure for DUT Browser.

The goal is to produce a reproducible desktop release from `main` with:
- a known semantic version
- a matching Git tag
- a matching `CHANGELOG.md` entry
- GitHub Release artifacts for macOS, Linux, and Windows

## Release Model

- `main` is the release branch.
- Feature work happens on short-lived branches and merges into `main` through pull requests.
- CI runs on pull requests and pushes to `main`.
- Desktop release packaging runs only for Git tags matching `v*`.
- The version source of truth is [VERSION](/Users/nelsonchang/Documents/DUT_browser/VERSION).

## Required Files

Before cutting a release, these files must be correct:

- [VERSION](/Users/nelsonchang/Documents/DUT_browser/VERSION)
- [CHANGELOG.md](/Users/nelsonchang/Documents/DUT_browser/CHANGELOG.md)
- [release.json](/Users/nelsonchang/Documents/DUT_browser/release.json)

## Branching Rules

- Do not release from a feature branch.
- Merge the feature branch into `main` first.
- Tag the release from `main` only.
- The Git tag must match the semantic version in `VERSION`.

Example:

- `VERSION` contains `1.0.0`
- release tag must be `v1.0.0`

## Pre-Release Checklist

Run this checklist before creating a tag:

1. Confirm you are on `main`.
2. Confirm `main` is up to date with GitHub.
3. Confirm the working tree is clean.
4. Confirm `VERSION` contains the intended release version.
5. Confirm `CHANGELOG.md` has an entry for that version.
6. Confirm CI is green on the latest `main` commit.
7. Confirm the desktop migration or feature changes are merged.

Commands:

```bash
git checkout main
git pull origin main
git status --short
cat VERSION
```

The expected `git status --short` output is empty.

## Local Validation

Run local validation before tagging:

```bash
python3 -m compileall dut-dashboard/backend/app scripts
python3 -m py_compile dut-dashboard/backend/run_backend.py
npm install
npm install --prefix dut-dashboard/frontend
npm run build:web
python3 scripts/build_backend.py
```

If the release machine has Rust and Tauri prerequisites installed, also run:

```bash
npm run package
```

## Standard Release Procedure

### 1. Update version and changelog

Edit:

- [VERSION](/Users/nelsonchang/Documents/DUT_browser/VERSION)
- [CHANGELOG.md](/Users/nelsonchang/Documents/DUT_browser/CHANGELOG.md)

Example version bump:

```text
1.0.1
```

### 2. Commit the release metadata

```bash
git checkout main
git pull origin main
git add VERSION CHANGELOG.md
git commit -m "Prepare release v1.0.1"
git push origin main
```

### 3. Create and push the tag

```bash
git tag v1.0.1
git push origin v1.0.1
```

This triggers the GitHub Actions release workflow in [.github/workflows/release.yml](/Users/nelsonchang/Documents/DUT_browser/.github/workflows/release.yml#L1).

### 4. Monitor the release workflow

GitHub Actions will:

- build on Ubuntu, macOS, and Windows
- package the Python backend sidecar
- package the Tauri desktop application
- upload bundle artifacts
- publish artifacts to the GitHub Release for the tag

Review the workflow run in the Actions tab and confirm all matrix jobs succeeded.

### 5. Verify the GitHub Release

Open the GitHub Releases page and confirm:

- release title exists for `v1.0.1`
- artifacts are attached
- artifact set includes desktop bundles from all target operating systems
- release notes match the intended changelog content

## Hotfix Release Procedure

If a production issue requires a fast follow-up release:

1. Create a hotfix branch from `main`.
2. Apply the minimal patch only.
3. Open and merge a PR into `main`.
4. Bump `VERSION` and update `CHANGELOG.md`.
5. Tag the next patch version.

Example:

- bad release: `v1.0.1`
- hotfix release: `v1.0.2`

Do not reuse or move an existing tag.

## Rollback Policy

If a release is bad:

- do not rewrite Git history
- do not delete and recreate the same tag as the primary fix path
- cut a new patch release that supersedes the bad release

Preferred rollback response:

1. mark the GitHub Release notes for the bad version as deprecated
2. create a fix on `main`
3. release the next patch version

## CI/CD Workflow Summary

### CI workflow

File: [.github/workflows/ci.yml](/Users/nelsonchang/Documents/DUT_browser/.github/workflows/ci.yml#L1)

Trigger:

- push to `main`
- all pull requests

What it does:

- installs Python 3.11
- installs Node 20
- installs backend dependencies
- installs frontend and root JavaScript dependencies
- validates backend importability
- runs backend tests
- builds the frontend
- validates packaged backend scaffold generation

This workflow protects `main`.

### Release workflow

File: [.github/workflows/release.yml](/Users/nelsonchang/Documents/DUT_browser/.github/workflows/release.yml#L1)

Trigger:

- push tag matching `v*`
- manual workflow dispatch

What it does:

- runs on Ubuntu, macOS, and Windows
- installs Python, Node, and Rust
- installs Linux desktop packaging prerequisites when needed
- builds the backend sidecar
- builds the Tauri desktop bundles
- uploads artifacts
- publishes artifacts to GitHub Releases for tagged builds

This workflow produces the distributable application.

## Update Flow For Source Users

Source users update with:

macOS/Linux:

```bash
./update.sh
```

Windows:

```powershell
.\update.ps1
```

These scripts:

- refuse to run on a dirty working tree
- fetch tags
- pull latest code with `--ff-only`
- rebuild dependencies safely
- avoid promoting a new Python environment until installation succeeds

## Post-Release Tasks

After a successful release:

1. Confirm startup version check detects the new release.
2. Confirm the packaged app opens and backend starts correctly.
3. Confirm update scripts still work from a clean checkout.
4. Announce the release to QA/test users with the GitHub Release link.

## Common Commands

Initialize and run in source mode:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
npm install --prefix dut-dashboard/frontend
npm run dev
```

Build backend sidecar:

```bash
python3 scripts/build_backend.py
```

Package desktop app:

```bash
npm run package
```

Create release tag:

```bash
git checkout main
git pull origin main
git tag vX.Y.Z
git push origin vX.Y.Z
```

## Do Not Do These Things

- Do not release from `Tauri` or any feature branch.
- Do not skip the `CHANGELOG.md` update.
- Do not tag a version that does not match `VERSION`.
- Do not force-push `main` as part of release handling.
- Do not reuse a tag name after a bad release.
