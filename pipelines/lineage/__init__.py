"""Lineage Pipeline

Builds and reconciles symbol lineage chains, entity identity graphs, and ticker-to-security mappings.
Constructs dim_security_master, dim_symbol_alias, and fact_symbol_lineage_event.

Module structure:
- lineage_builder.py: Core lineage resolution engine
- entity_resolver.py: Company entity deduplication
- symbol_resolver.py: Ticker chain construction
- status_tracker.py: Listing status timeline builder

See README.md for detailed responsibilities and implementation notes.
"""

__version__ = "1.0.0"
