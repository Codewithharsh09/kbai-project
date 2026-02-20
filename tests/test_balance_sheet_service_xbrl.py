"""XBRL-specific tests for `BalanceSheetService`.

These tests focus on:
- mode / file-extension validation for XBRL/XML uploads
- wiring to `extract_balance_from_xbrl`
- period validation logic when the source file is XBRL/XML
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

import importlib
import os

import pytest


service_module = importlib.import_module("src.app.api.v1.services.k_balance.balance_sheet_service")


@dataclass
class SimpleUser:
    """Tiny stand-in for the real user model."""

    role: str
    id_user: int = 1


class FakeFile:
    """Minimal file-like object used to simulate uploads."""

    def __init__(self, filename: str, content: str = "<xbrli:xbrl />") -> None:
        self.filename = filename
        self._content = content
        self.saved_path: str | None = None

    def save(self, target_path: str) -> None:
        with open(target_path, "w", encoding="utf-8") as handle:
            handle.write(self._content)
        self.saved_path = target_path


@pytest.fixture(autouse=True)
def patch_xbrl_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch out heavy dependencies with lightweight fakes for XBRL tests."""

    # Stub for the XBRL extractor
    calls: Dict[str, Any] = {"paths": []}

    def fake_extract_balance_from_xbrl(path: str) -> Dict[str, Any]:  # type: ignore[override]
        calls["paths"].append(path)
        return {"source": "xbrl", "path": os.path.basename(path)}

    monkeypatch.setattr(service_module, "extract_balance_from_xbrl", fake_extract_balance_from_xbrl)

    # Stub for the KbaiBalance model used in `create`
    class DummyBalance:
        def __init__(self, payload: Dict[str, Any]) -> None:
            self.id_balance = 1
            self.id_company = payload["id_company"]

    class KbaiBalanceFake:
        @classmethod
        def create(cls, data: Dict[str, Any]) -> Tuple[DummyBalance, None]:  # type: ignore[override]
            return DummyBalance(data), None

    monkeypatch.setattr(service_module, "KbaiBalance", KbaiBalanceFake)

    # Avoid touching the real database when checking for existing balances
    def fake_check_existing_balance(  # type: ignore[override]
        self: service_module.BalanceSheetService,
        company_id: int,
        year: int,
        month: int,
    ) -> Tuple[None, None]:
        return None, None

    monkeypatch.setattr(service_module.BalanceSheetService, "_check_existing_balance", fake_check_existing_balance)


@pytest.fixture
def service_instance() -> service_module.BalanceSheetService:
    return service_module.BalanceSheetService()


class TestBalanceSheetServiceXbrl:
    def test_balance_sheet_accepts_xbrl_mode(
        self,
        service_instance: service_module.BalanceSheetService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Ensure period validation passes by matching the payload period.
        monkeypatch.setattr(
            service_instance,
            "_extract_period_from_file",
            lambda _path: (2024, 1),
        )

        fake_file = FakeFile(filename="balance.xbrl")

        response, status = service_instance.balance_sheet(
            file=fake_file,
            company_id=1,
            year=2024,
            month=1,
            type="annual",
            mode="xbrl",
        )

        assert status == 201
        assert response["success"] is True
        assert response["message"] == "Balance sheet uploaded successfully."
        assert response["data"]["balance_id"] == 1

    def test_balance_sheet_accepts_xml_for_xbrl(
        self,
        service_instance: service_module.BalanceSheetService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Ensure period validation passes by matching the payload period.
        monkeypatch.setattr(
            service_instance,
            "_extract_period_from_file",
            lambda _path: (2024, 6),
        )

        fake_file = FakeFile(filename="balance.xml")

        response, status = service_instance.balance_sheet(
            file=fake_file,
            company_id=2,
            year=2024,
            month=6,
            type="annual",
            mode="xml",
        )

        assert status == 201
        assert response["success"] is True
        assert response["message"] == "Balance sheet uploaded successfully."

    def test_balance_sheet_rejects_mode_mismatch_for_xbrl(
        self,
        service_instance: service_module.BalanceSheetService,
    ) -> None:
        fake_file = FakeFile(filename="balance.xbrl")

        response, status = service_instance.balance_sheet(
            file=fake_file,
            company_id=1,
            year=2024,
            month=1,
            type="annual",
            mode="pdf",
        )

        assert status == 400
        assert response["error"] == "Validation error"
        assert "Mode is set to" in response["message"]
        assert "PDF" in response["message"]
        assert "XBRL" in response["message"]

    def test_balance_sheet_validates_period_for_xbrl_year_mismatch(
        self,
        service_instance: service_module.BalanceSheetService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If the XBRL period does not match the payload year, a 400 is returned."""

        fake_file = FakeFile(filename="year_mismatch.xbrl")

        def fake_extract_period_from_file(_: str) -> Tuple[int, int]:
            # XBRL file reports 2023, but payload says 2024
            return 2023, 1

        monkeypatch.setattr(service_instance, "_extract_period_from_file", fake_extract_period_from_file)

        response, status = service_instance.balance_sheet(
            file=fake_file,
            company_id=3,
            year=2024,
            month=1,
            type="annual",
            mode="xbrl",
        )

        assert status == 400
        assert response["error"] == "Validation error"
        # The error message should clearly indicate a year mismatch coming from XBRL
        assert "Year mismatch" in response["message"]
        assert "XBRL reports 2023" in response["message"]

    def test_balance_sheet_validates_period_for_xbrl_month_mismatch(
        self,
        service_instance: service_module.BalanceSheetService,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If the XBRL period month does not match the payload month, a 400 is returned."""

        fake_file = FakeFile(filename="month_mismatch.xbrl")

        def fake_extract_period_from_file(_: str) -> Tuple[int, int]:
            # Same year but different month
            return 2024, 12

        monkeypatch.setattr(service_instance, "_extract_period_from_file", fake_extract_period_from_file)

        response, status = service_instance.balance_sheet(
            file=fake_file,
            company_id=4,
            year=2024,
            month=1,
            type="annual",
            mode="xbrl",
        )

        assert status == 400
        assert response["error"] == "Validation error"
        assert "Month mismatch" in response["message"]
        assert "XBRL reports 12" in response["message"]

    def test_extract_period_from_text_handles_multiple_patterns(self) -> None:
        """Directly cover `_extract_period_from_text` for PDF/XBRL text."""
        service = service_module.BalanceSheetService()

        # Explicit date
        year, month = service._extract_period_from_text("Bilancio al 31/12/2023")
        assert (year, month) == (2023, 12)

        # Textual month
        year2, month2 = service._extract_period_from_text("esercizio chiuso a dicembre 2022")
        assert (year2, month2) == (2022, 12)

        # Context word "bilancio al 2021"
        year3, month3 = service._extract_period_from_text("bilancio al 2021")
        assert year3 == 2021
        assert month3 is None

        # Fallback generic year
        year4, month4 = service._extract_period_from_text("Rif. 2019")
        assert year4 == 2019
        assert month4 is None


