"""Normalize Pipeline

Parses, cleans, and standardizes raw source files into normalized intermediate datasets.
This layer applies schema validation, data type conversions, and basic quality checks.

Module structure:
- normalizer.py: Core normalization engine
- transformers/: Source-specific parsing and transformation logic
- validators.py: Type, range, and cardinality validation
- schema_definitions.yaml: Field specifications for each data source

See README.md for detailed responsibilities and implementation notes.
"""

__version__ = "1.0.0"
