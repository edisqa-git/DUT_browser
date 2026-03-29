# Changelog

All notable changes to DUT Browser will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [1.0.0] - 2026-03-28

### Added
- Single-entry desktop architecture based on Tauri.
- Root-level release metadata in `VERSION` and `release.json`.
- Managed desktop launcher that owns the FastAPI backend lifecycle.
- Startup version check against GitHub releases/tags with clear in-app messaging.
- Cross-platform update scripts: `update.sh` and `update.ps1`.
- Packaging/build scaffold for bundling the Python backend and Tauri shell.
- GitHub Actions CI and release workflows.

### Changed
- Repository entrypoint moved to the root `package.json`.
- Frontend API runtime now supports proxied browser dev mode and packaged desktop mode.
- Backend exposes product/version metadata and update-check endpoints.

### Deprecated
- Direct two-terminal startup via `python3 -m app.main` plus `npm run dev`.
- `dut-dashboard/README.md` as the primary onboarding document.
