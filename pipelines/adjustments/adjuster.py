"""
AdjustmentFactorBuilder — builds fact_adjustment_factor rows from
fact_corporate_action_event data produced by the normalization pipeline.
"""

import pandas as pd

from pipelines.adjustments.calculator import AdjustmentCalculator

# Action codes that affect price adjustment factors
_ADJUSTABLE_CODES = frozenset({"SPLIT", "BONUS", "REVERSE_SPLIT"})

# Sanity bounds for individual event factors
_MIN_FACTOR = 1e-6   # anything smaller is almost certainly bad data
_MAX_FACTOR = 1e6    # anything larger is almost certainly bad data


class AdjustmentFactorBuilder:
    """
    Builds fact_adjustment_factor rows from a fact_corporate_action_event DataFrame.

    Output schema matches dolt/schema.sql:
        security_id, as_of_date,
        cumulative_split_adjustment, cumulative_bonus_adjustment,
        cumulative_dividend_adjustment, total_adjustment_factor

    Usage:
        builder = AdjustmentFactorBuilder()
        factors = builder.build_from_corporate_actions(actions_df, securities_df)
        factors.to_csv("data/curated/fact_adjustment_factor.csv", index=False)
    """

    def build_from_corporate_actions(
        self,
        actions: pd.DataFrame,
        symbols: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute cumulative adjustment factors for every security that has
        at least one split or bonus action.

        For each security:
          1. Filter actions to SPLIT / BONUS / REVERSE_SPLIT
          2. Sort chronologically
          3. Compute running cumulative factors via AdjustmentCalculator
          4. Emit one output row per event date (as_of_date)
          5. Apply sanity checks and flag anomalies

        Args:
            actions: fact_corporate_action_event DataFrame with columns:
                     security_id, action_code, event_date, old_value
            symbols: dim_security_master DataFrame (used for validation only)

        Returns:
            fact_adjustment_factor DataFrame with one row per
            (security_id, as_of_date) where a split or bonus occurred.
        """
        required = ["security_id", "action_code", "event_date"]
        missing  = [c for c in required if c not in actions.columns]
        if missing:
            raise ValueError(
                f"actions DataFrame missing required columns: {missing}. "
                f"Got: {list(actions.columns)}"
            )

        # Filter to price-adjustable actions only
        adjustable = actions[
            actions["action_code"].str.upper().isin(_ADJUSTABLE_CODES)
        ].copy()

        if adjustable.empty:
            return pd.DataFrame(columns=[
                "security_id", "as_of_date",
                "cumulative_split_adjustment", "cumulative_bonus_adjustment",
                "cumulative_dividend_adjustment", "total_adjustment_factor",
            ])

        # Parse dates and sort
        adjustable["event_date"] = pd.to_datetime(
            adjustable["event_date"], errors="coerce"
        )
        adjustable = adjustable.dropna(subset=["event_date"])
        adjustable = adjustable.sort_values(["security_id", "event_date"])

        output_rows: list[dict] = []

        for security_id, group in adjustable.groupby("security_id"):
            split_acc = 1.0
            bonus_acc = 1.0
            warnings:  list[str] = []

            for _, row in group.iterrows():
                code  = str(row["action_code"]).upper()
                value = row.get("old_value")

                try:
                    factors = AdjustmentCalculator.calculate_cumulative_adjustment(
                        pd.DataFrame([row])
                    )
                    event_split = factors["cumulative_split_adjustment"]
                    event_bonus = factors["cumulative_bonus_adjustment"]
                except ValueError as exc:
                    warnings.append(f"{row['event_date'].date()}: {exc}")
                    continue

                # Validate individual event factor
                event_factor = event_split * event_bonus
                if not (_MIN_FACTOR <= event_factor <= _MAX_FACTOR):
                    warnings.append(
                        f"{row['event_date'].date()}: factor {event_factor} out of bounds"
                    )
                    continue

                split_acc *= event_split
                bonus_acc *= event_bonus
                total      = round(split_acc * bonus_acc, 8)

                output_rows.append({
                    "security_id":                  security_id,
                    "as_of_date":                   row["event_date"].date().isoformat(),
                    "cumulative_split_adjustment":   round(split_acc, 8),
                    "cumulative_bonus_adjustment":   round(bonus_acc, 8),
                    "cumulative_dividend_adjustment": 1.0,   # dividends not adjusted by default
                    "total_adjustment_factor":        total,
                    "_warnings":                     "; ".join(warnings) if warnings else "",
                })

        if not output_rows:
            return pd.DataFrame(columns=[
                "security_id", "as_of_date",
                "cumulative_split_adjustment", "cumulative_bonus_adjustment",
                "cumulative_dividend_adjustment", "total_adjustment_factor",
            ])

        df = pd.DataFrame(output_rows)
        self._validate_factors(df)
        return df

    # ── validation ────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_factors(df: pd.DataFrame) -> None:
        """
        Sanity-check the output factor DataFrame and raise if critical
        invariants are violated.

        Checks:
          - All factors > 0
          - total = split × bonus (within float tolerance)
          - No (security_id, as_of_date) duplicates
        """
        factor_cols = [
            "cumulative_split_adjustment",
            "cumulative_bonus_adjustment",
            "total_adjustment_factor",
        ]
        for col in factor_cols:
            if col not in df.columns:
                continue
            non_positive = (df[col] <= 0).sum()
            if non_positive:
                raise ValueError(
                    f"{non_positive} rows have non-positive {col} — "
                    "check for zero or negative old_value in source data"
                )

        # total should equal split × bonus within floating-point tolerance
        if all(c in df.columns for c in ["cumulative_split_adjustment",
                                          "cumulative_bonus_adjustment",
                                          "total_adjustment_factor"]):
            computed = (
                df["cumulative_split_adjustment"] *
                df["cumulative_bonus_adjustment"]
            ).round(6)
            actual = df["total_adjustment_factor"].round(6)
            mismatched = (abs(computed - actual) > 1e-5).sum()
            if mismatched:
                raise ValueError(
                    f"{mismatched} rows have total_adjustment_factor ≠ split × bonus"
                )

        # No duplicate (security_id, as_of_date) pairs
        if "security_id" in df.columns and "as_of_date" in df.columns:
            dupes = df.duplicated(subset=["security_id", "as_of_date"]).sum()
            if dupes:
                raise ValueError(
                    f"{dupes} duplicate (security_id, as_of_date) rows in adjustment output"
                )
