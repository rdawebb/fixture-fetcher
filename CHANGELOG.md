# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.4.0]

### Added

- TypeScript support for static frontend with compilation to public/
- `scripts/build_site.js` for building static assets with TypeScript compilation
- `scripts/build_calendars.py` for building fixture calendars with argument support
- Multi-team support in `build()` function for batch calendar generation
- API rate limiting configuration with `API_RATE_LIMIT_DELAY` setting
- Node.js development dependencies (TypeScript ^5.9.3)
- Package.json and package-lock.json for Node.js dependency management

### Changed

- Refactored build script from `scripts/build.py` to `scripts/build_calendars.py` with enhanced CLI
- Updated GitHub Actions workflow to support Node.js 20 for static asset compilation
- Changed static file copy from shell `cp` to JavaScript build script
- Updated `build()` function signature: `team` parameter → `teams` (list-based)
- Enhanced build workflow to compile TypeScript and bundle static assets
- Improved CLI output with team-specific logging during batch operations
- Moved inline JavaScript from HTML into TypeScript module (`main.ts`)
- Updated development dependencies: prek→0.2.30, ruff→0.14.13, ty→0.0.12
- Improved web UX with separate copy-to-clipboard and download buttons
- Enhanced instructions to explain new options
- Added visual download icon


## [0.3.0] - 2026/01/10

### Added

- Manifest generation module for calendar indexing
- Pre-commit configuration for code quality checks
- Enhanced API client with venue information support in team cache
- Improved cache validation with structure checking before save operations
- Better error handling for invalid cache structures
- Text fixtures for API and storage modules
- Static stylesheet for web interface

### Changed

- Improved error handling in API client with null safety checks
- Enhanced type hints using modern Python union syntax (str | None)
- Refined shell interaction module for better user experience
- Updated dependency locks with uv package manager
- Refactored logging messages to remove file paths for output clarity
- Enhanced cache auto-loading on missing cache files
- Improved error handling logic in API response processing
- Simplified import paths throughout codebase
- Refactored test suite with parameterisation for better maintainability
- Improved test coverage for Football Data API client and error handling

### Fixed

- Cache validation to prevent corrupted cache data
- API error handling for edge cases with null status codes


## [0.2.0] - 2025-12-27

### Added

- Automated calendar generation via GitHub Actions workflow
- Deployment to GitHub Pages for public calendar access
- TV enrichment data support with tv_overrides.yaml configuration
- Team data cache with league organisation
- League-based snapshot directory structure (league/team_slug/)
- Fixture change detection with TV status tracking
- Calendar comparison module for tracking changes between builds
- Improved error handling with TeamNotFoundError and TeamsCacheError exceptions

### Changed

- Restructured API client cache to organize teams by league
- Migrated build configuration to pyproject.toml
- Refactored codebase into modular architecture with dedicated modules
- Improved ICS event descriptions for better calendar compatibility
- Centralized logging setup for consistent application logging

### Fixed

- GitHub Actions workflow permissions and reliability
- iCal compatibility issues with event descriptions


## [0.1.0] - 2025-11-07

### Added

- Initial CLI for interactive fixture fetching
- Football Data API client for fetching fixtures
- ICS calendar file export (iCalendar format)
- Fixture filtering by home/away, scheduled status, televised status, and date range
- Configuration management system
- Data models for fixture representation
- Centralised error handling with custom exception classes
- Comprehensive logging setup


[Unreleased]: https://github.com/rdawebb/fixture-fetcher/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/rdawebb/fixture-fetcher/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/rdawebb/fixture-fetcher/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rdawebb/fixture-fetcher/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/rdawebb/fixture-fetcher/releases/tag/v0.1.0
