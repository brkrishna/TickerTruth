import pandas as pd


class QualityMetadata:
    def add_quality_flags(normalized_df: pd.DataFrame) -> pd.DataFrame:
        # Add columns:
        # - _source_file: which raw file this came from
        # - _extracted_date: when data was extracted
        # - _quality_issues: list of any validation warnings
        # - _confidence_score: 1.0 (high) to 0.5 (requires review)
        # - _manual_review_required: boolean flag
        pass