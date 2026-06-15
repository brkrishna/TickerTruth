"""
Tests for pipelines/extract/bse_extractor.py

All network calls are mocked — no live BSE requests in tests.
"""

import zipfile
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pipelines.extract.bse_extractor import BSERawDataExtractor


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def extractor(tmp_path):
    return BSERawDataExtractor(output_dir=tmp_path)


def _make_zip_csv(rows: list[dict], filename: str = "EQ01062026_CSV.csv") -> bytes:
    """Build an in-memory ZIP containing a CSV from a list of row dicts."""
    csv_text = pd.DataFrame(rows).to_csv(index=False)
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, csv_text)
    return buf.getvalue()


def _mock_response(json_data=None, text=None, status_code=200, raise_for_status=None):
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    if text is not None:
        resp.text = text
    if raise_for_status:
        resp.raise_for_status.side_effect = raise_for_status
    else:
        resp.raise_for_status.return_value = None
    return resp


# ── equity master tests ───────────────────────────────────────────────────────


class TestFetchBSEEquityMaster:
    def _make_master_records(self, n=4500):
        return [
            {
                "Scrip_Cd": str(500000 + i).zfill(6),
                "SC_NAME": f"SCRIP{i}",
                "COMPANY_NAME": f"Company {i} Ltd",
                "ISIN_CODE": f"INE{i:09d}",
                "Status": "Active",
                "Segment": "Equity",
            }
            for i in range(n)
        ]

    def test_returns_dataframe_with_canonical_columns(self, extractor):
        records = self._make_master_records(4500)
        mock_resp = _mock_response(json_data=records)
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            df = extractor.fetch_bse_equity_master()
        assert "SCRIP_CODE" in df.columns
        assert "ISIN" in df.columns
        assert "SCRIP_NAME" in df.columns
        assert len(df) == 4500

    def test_scrip_code_zero_padded_to_six_digits(self, extractor):
        # Use a short code (< 6 digits) to verify zero-padding, with enough unique codes
        records = [
            {
                "Scrip_Cd": str(1000 + i),
                "SC_NAME": f"S{i}",
                "ISIN_CODE": f"INE{i:09d}",
                "Status": "Active",
            }
            for i in range(4500)
        ]
        mock_resp = _mock_response(json_data=records)
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            df = extractor.fetch_bse_equity_master()
        # All codes should be 6-char strings (zero-padded from 4-digit inputs)
        assert all(len(c) == 6 for c in df["SCRIP_CODE"])

    def test_uses_cache_on_second_call(self, extractor, tmp_path):
        """Second call should read cached CSV, not hit network."""
        records = self._make_master_records(4500)
        mock_resp = _mock_response(json_data=records)
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ) as mock_get:
            extractor.fetch_bse_equity_master()
            extractor.fetch_bse_equity_master()
        assert mock_get.call_count == 1

    def test_raises_on_too_few_rows(self, extractor):
        mock_resp = _mock_response(
            json_data=[{"Scrip_Cd": "500325", "SC_NAME": "X", "ISIN_CODE": "INE001"}]
        )
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            with pytest.raises(ValueError, match="only 1 rows"):
                extractor.fetch_bse_equity_master()

    def test_raises_on_api_failure(self, extractor):
        import requests as req

        mock_resp = _mock_response(raise_for_status=req.HTTPError("503"))
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            with pytest.raises(RuntimeError, match="API returned no data"):
                extractor.fetch_bse_equity_master()

    def test_wrapped_json_response(self, extractor):
        """API sometimes wraps list under 'Table' key."""
        records = self._make_master_records(4500)
        mock_resp = _mock_response(json_data={"Table": records})
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            df = extractor.fetch_bse_equity_master()
        assert len(df) == 4500

    def test_status_synthesized_when_absent(self, extractor):
        records = [
            {
                "Scrip_Cd": str(500000 + i),
                "SC_NAME": f"S{i}",
                "ISIN_CODE": f"INE{i:09d}",
            }
            for i in range(4500)
        ]
        mock_resp = _mock_response(json_data=records)
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            df = extractor.fetch_bse_equity_master()
        assert "STATUS" in df.columns
        assert (df["STATUS"] == "Active").all()


# ── bhavcopy tests ────────────────────────────────────────────────────────────


class TestFetchBSEBhavcopy:
    def _make_bhavcopy_rows(self, n=3000):
        return [
            {
                "SC_CODE": str(500000 + i).zfill(6),
                "SC_NAME": f"SCRIP{i}",
                "SC_GROUP": "A",
                "OPEN": 100.0,
                "HIGH": 105.0,
                "LOW": 98.0,
                "CLOSE": 102.0,
                "LAST": 102.0,
                "PREVCLOSE": 100.0,
                "NO_TRADES": 500,
                "NET_TURNOV": 510000.0,
            }
            for i in range(n)
        ]

    def test_returns_canonical_columns(self, extractor):
        zip_bytes = _make_zip_csv(self._make_bhavcopy_rows(3000))
        mock_resp = _mock_response()
        mock_resp.content = zip_bytes
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            df = extractor.fetch_bse_bhavcopy(date(2026, 6, 1))
        assert "SCRIP_CODE" in df.columns
        assert "CLOSE" in df.columns

    def test_builds_correct_url(self, extractor):
        """URL must follow BSE naming: EQ{DDMMYYYY}_CSV.ZIP"""
        zip_bytes = _make_zip_csv(self._make_bhavcopy_rows(3000))
        mock_resp = _mock_response()
        mock_resp.content = zip_bytes
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ) as m:
            extractor.fetch_bse_bhavcopy(date(2026, 6, 1))
        called_url = m.call_args[0][0]
        assert "EQ01062026_CSV.ZIP" in called_url

    def test_raises_on_404(self, extractor):
        import requests as req

        err = req.HTTPError(response=MagicMock(status_code=404))
        mock_resp = _mock_response(raise_for_status=err)
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            with pytest.raises(RuntimeError, match="not found"):
                extractor.fetch_bse_bhavcopy(date(2026, 6, 7))  # Saturday / holiday

    def test_raises_on_too_few_rows(self, extractor):
        zip_bytes = _make_zip_csv(self._make_bhavcopy_rows(10))
        mock_resp = _mock_response()
        mock_resp.content = zip_bytes
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            with pytest.raises(ValueError, match="only 10 rows"):
                extractor.fetch_bse_bhavcopy(date(2026, 6, 1))

    def test_ohlc_warning_logged(self, extractor, caplog):
        import logging

        rows = self._make_bhavcopy_rows(3000)
        rows[0]["LOW"] = 200.0  # LOW > CLOSE: invalid
        zip_bytes = _make_zip_csv(rows)
        mock_resp = _mock_response()
        mock_resp.content = zip_bytes
        with caplog.at_level(logging.WARNING):
            with patch(
                "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
            ):
                extractor.fetch_bse_bhavcopy(date(2026, 6, 1))
        assert any("OHLC sanity" in r.message for r in caplog.records)


# ── corporate actions tests ───────────────────────────────────────────────────


class TestFetchBSECorporateActions:
    def _make_action_records(self, n=50):
        return [
            {
                "scrip_code": str(500000 + i).zfill(6),
                "scrip_name": f"SCRIP{i}",
                "Purpose": "Dividend",
                "ExDate": "01/06/2026",
                "RdDate": "02/06/2026",
                "PdDate": "10/06/2026",
            }
            for i in range(n)
        ]

    def test_returns_canonical_columns(self, extractor):
        records = self._make_action_records(50)
        mock_resp = _mock_response(json_data=records)
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            df = extractor.fetch_bse_corporate_actions(
                from_date=date(2026, 5, 1), to_date=date(2026, 5, 30)
            )
        assert "SCRIP_CODE" in df.columns
        assert "ACTION_TYPE_RAW" in df.columns
        assert "EX_DATE" in df.columns

    def test_date_params_use_ddmmyyyy_format(self, extractor):
        """BSE API requires DD/MM/YYYY, not DD-MM-YYYY like NSE."""
        records = self._make_action_records(5)
        mock_resp = _mock_response(json_data=records)
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ) as m:
            extractor.fetch_bse_corporate_actions(
                from_date=date(2026, 5, 1), to_date=date(2026, 5, 30)
            )
        call_params = m.call_args[1]["params"]
        assert call_params["FromDate"] == "01/05/2026"
        assert call_params["ToDate"] == "30/05/2026"

    def test_deduplicates_on_scrip_code_ex_date_action(self, extractor):
        records = self._make_action_records(5) * 3  # 15 rows, 5 unique
        mock_resp = _mock_response(json_data=records)
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            df = extractor.fetch_bse_corporate_actions(
                from_date=date(2026, 5, 1), to_date=date(2026, 5, 30)
            )
        assert len(df) == 5

    def test_uses_stale_cache_on_api_failure(self, extractor, tmp_path):
        # Write a stale cache file
        stale_df = pd.DataFrame(
            [
                {
                    "SCRIP_CODE": "500325",
                    "ACTION_TYPE_RAW": "Dividend",
                    "EX_DATE": "01/05/2026",
                }
            ]
        )
        stale_path = tmp_path / "bse_actions_2026-04-01_2026-04-30.csv"
        stale_df.to_csv(stale_path, index=False)

        import requests as req

        mock_resp = _mock_response(raise_for_status=req.HTTPError("503"))
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            df = extractor.fetch_bse_corporate_actions(
                from_date=date(2026, 5, 1), to_date=date(2026, 5, 30)
            )
        assert len(df) == 1

    def test_raises_when_no_data_and_no_stale_cache(self, extractor):
        mock_resp = _mock_response(json_data=[])
        with patch(
            "pipelines.extract.bse_extractor.requests.get", return_value=mock_resp
        ):
            with pytest.raises(RuntimeError, match="No stale cache"):
                extractor.fetch_bse_corporate_actions(
                    from_date=date(2026, 5, 1), to_date=date(2026, 5, 30)
                )


# ── consolidate to staging tests ─────────────────────────────────────────────


class TestConsolidateBSEToStaging:
    def test_consolidates_multiple_master_files(self, extractor, tmp_path):
        for i in range(3):
            rows = [
                {
                    "SCRIP_CODE": str(500000 + j).zfill(6),
                    "SCRIP_NAME": f"S{j}",
                    "ISIN": f"INE{j:09d}",
                }
                for j in range(100)
            ]
            pd.DataFrame(rows).to_csv(
                tmp_path / f"bse_equity_master_2026-06-0{i + 1}.csv", index=False
            )

        report = extractor.consolidate_bse_to_staging(staging_dir=tmp_path / "staging")
        assert report["scrips"]["files_found"] == 3
        assert (
            report["scrips"]["rows_after_dedup"] == 100
        )  # all same 100 scrips deduped

    def test_idempotent_on_rerun(self, extractor, tmp_path):
        rows = [
            {
                "SCRIP_CODE": str(500000 + j).zfill(6),
                "SCRIP_NAME": f"S{j}",
                "ISIN": f"INE{j:09d}",
            }
            for j in range(100)
        ]
        pd.DataFrame(rows).to_csv(
            tmp_path / "bse_equity_master_2026-06-01.csv", index=False
        )
        staging = tmp_path / "staging"
        report1 = extractor.consolidate_bse_to_staging(staging_dir=staging)
        report2 = extractor.consolidate_bse_to_staging(staging_dir=staging)
        # Counts should be identical across runs
        assert (
            report1["scrips"]["rows_after_dedup"]
            == report2["scrips"]["rows_after_dedup"]
        )

    def test_empty_staging_when_no_raw_files(self, extractor, tmp_path):
        report = extractor.consolidate_bse_to_staging(staging_dir=tmp_path / "staging")
        assert report["scrips"]["files_found"] == 0
        assert report["scrips"]["rows_after_dedup"] == 0
