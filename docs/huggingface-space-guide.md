# Hugging Face Space Guide — TickerTruth NSE Explorer

The [TickerTruth NSE Explorer](https://huggingface.co/spaces/tickertruth/tickertruth-nse-explorer)
is a Streamlit app for browsing a sample of the
[NSE India Security Master dataset](https://huggingface.co/datasets/tickertruth/nse-india-security-master)
without downloading anything. This guide covers what each tab shows and how
to read the results.

## Data behind the Space

The Space refreshes from the monthly TickerTruth release (15th of each
month). As of the 2026-08-15 release: 2,406 securities, 777 corporate
action events, and 19 adjustment factor rows. Symbol lineage detection
(renames, mergers, delistings) returned 0 events in this release — the
lineage and status-history tabs below will show sparse or empty results
until a release captures those events. Check `release-notes.md` in the
main repository for the current release's exact counts before relying on
a specific tab.

## Tabs

### Fix Broken Backtests
Looks up split and bonus events for a symbol and shows the adjustment
factor that should be applied to reconcile pre- and post-event pricing.
Only symbols with rows in `fact_adjustment_factor` return results.

### Reconcile Portfolio NAV
Shows dividend events for a symbol over a date range, for cross-checking
against a portfolio's recorded NAV impact.

### Track Symbol Renames
Looks up rename events in `fact_symbol_lineage_event` for a symbol.
Returns no results in releases where lineage detection found no events —
this is a known gap, not a lookup error. See the release notes for
whether the current release populated this table.

### Understand Delistings
Same source table as symbol renames, filtered to delisting/merger event
types. Subject to the same current-release gap.

### Validate Price Gaps
Cross-references a price discontinuity against corporate action events on
or near that date, to distinguish a real market move from an unadjusted
split/bonus.

### Calculate Adjustments
Walks through the cumulative adjustment factor chain for a symbol —
useful when a symbol has had multiple splits/bonuses and the combined
factor isn't obvious from a single event row.

## Questions

Open a discussion on the [dataset page](https://huggingface.co/datasets/tickertruth/nse-india-security-master/discussions)
or file an issue on [github.com/brkrishna/TickerTruth](https://github.com/brkrishna/TickerTruth).
