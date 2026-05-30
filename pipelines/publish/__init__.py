"""Publish Pipeline

Exports curated datasets into Dolt, generates public-facing samples, and prepares distribution artifacts.
Handles data import validation, sample generation, CDN uploads, and release documentation.

Module structure:
- dolt_importer.py: Load curated data into Dolt repository
- sample_generator.py: Export queries for free and paid tiers
- data_validator.py: Post-import validation and quality checks
- cdn_uploader.py: S3/CDN upload and distribution
- manifest_builder.py: Generate metadata documentation

See README.md for detailed responsibilities and implementation notes.
"""

__version__ = "1.0.0"
