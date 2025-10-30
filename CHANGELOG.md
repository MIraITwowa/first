# Changelog

## [Unreleased]

### Added
- Flow diagnostics management command (`diagnose_flows`) to exercise checkout and payment journeys locally and surface errors in logs.
- Configurable flow logging toggled by `ENABLE_FLOW_DEBUG`, emitting contextual checkout, payment, and refund traces when enabled.

### Changed
- Migrated order monetary fields to `DecimalField` and updated calculations/serializers to preserve currency precision end-to-end.
- Hardened checkout to skip incomplete cart items and cleaned up the user cart signal to avoid creating empty rows for new accounts.
- Secured mock payment processing with amount validation, transactional status updates, and resilient task scheduling.

### Fixed
- Added regression coverage for currency arithmetic, cart initialization, and payment validation to prevent future regressions.
