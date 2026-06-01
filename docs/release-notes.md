# Release Notes

<!-- Add new releases at the top of this file, above older entries. -->
<!-- Each entry must follow the format defined at the bottom of this file. -->
<!-- Do not publish a release entry until the pipeline run for that month is complete. -->

<!-- STUB: Replace this entry with actual numbers after the June 2026 pipeline run. -->
# Release 2026-06 — [Title TBD]

**Released:** 2026-06-30
**Records Updated:** TBD
**New Symbols:** TBD
**Corrections:** TBD

### Highlights
- TBD

### Data Changes
- **Dimension updates:** TBD
- **Corporate actions:** TBD
- **Adjustments:** TBD

### Quality Improvements
- TBD

### Known Issues
- None.

### Next Release
- TBD

---

<!-- ============================================================ -->
<!-- REFERENCE: Format and example below — do not publish these.  -->
<!-- ============================================================ -->

## Format for Monthly Releases

```
# Release YYYY-MM — <Short Title>

**Released:** YYYY-MM-DD
**Records Updated:** <count>
**New Symbols:** <count>
**Corrections:** <count>

### Highlights
- <Key change or addition>
- <Major fix or enhancement>
- <Feedback incorporated from subscribers>

### Data Changes
- **Dimension updates:** <e.g., 5 new issuers, 2 renamed companies>
- **Corporate actions:** <e.g., 12 new dividend records, 3 splits, 1 merger>
- **Adjustments:** <e.g., refactored split adjustment logic>

### Quality Improvements
- <QA check added or fixed>
- <Data validation enhanced>

### Known Issues
- <Any outstanding data gaps or limitations>

### Next Release
- <Planned work for next month>
```

## Example Release

# Release 2026-06 — Symbol Cleanup and Dividend Normalization

**Released:** 2026-06-30  
**Records Updated:** 1,247  
**New Symbols:** 8  
**Corrections:** 12

### Highlights
- Fixed 12 historical symbol mapping errors reported by subscribers
- Added dividend normalization for bonus-adjusted equities
- Implemented new QA check for listing date consistency

### Data Changes
- **Dimension updates:** 8 new IPO listings, 2 rebranding corrections
- **Corporate actions:** 156 new dividend records normalized, 3 split adjustments corrected
- **Adjustments:** Refactored bonus-dividend calculation logic

### Quality Improvements
- Added validation for corporate action date ordering
- Enhanced symbol lineage cycle detection

### Known Issues
- BSE data not yet integrated; NSE-only for v1
- Some historical dividend records pre-2015 are incomplete

### Next Release
- Planned: dividend yield series and liquidity metrics
