"""Extract Pipeline

Downloads and archives untouched source data from NSE, NSDL, BSE, and other external sources.
This is the ingestion layer of the ETL pipeline.

Module structure:
- download_manager.py: Core orchestration for downloading from multiple sources
- source_registry.yaml: URL and configuration for each data source
- requirements.txt: External dependencies (requests, boto3, etc.)

See README.md for detailed responsibilities and implementation notes.
"""

__version__ = "1.0.0"
