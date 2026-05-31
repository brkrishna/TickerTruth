# Release Notes

## Release Format

Each monthly release includes:

- **Records Updated** — count of changed rows across all tables
- **New Symbols** — newly listed or recovered historical symbols
- **Corrections** — fixes to prior release data
- **Highlights** — key additions and improvements
- **Known Issues** — outstanding gaps or limitations
- **Next Release** — planned work for the following month

---

## Example Release

### Release 2026-06 — Symbol Cleanup and Dividend Normalization

**Released:** 2026-06-30
**Records Updated:** 1,247
**New Symbols:** 8
**Corrections:** 12

#### Highlights
- Fixed 12 historical symbol mapping errors reported by subscribers
- Added dividend normalization for bonus-adjusted equities
- Implemented new QA check for listing date consistency

#### Data Changes
- **Dimension updates:** 8 new IPO listings, 2 rebranding corrections
- **Corporate actions:** 156 new dividend records normalized, 3 split adjustments corrected
- **Adjustments:** Refactored bonus-dividend calculation logic

#### Quality Improvements
- Added validation for corporate action date ordering
- Enhanced symbol lineage cycle detection

#### Known Issues
- BSE data not yet integrated; NSE-only for v1
- Some historical dividend records pre-2015 are incomplete

#### Next Release
- Planned: dividend yield series and liquidity metrics