"""Beginner-friendly tests for the balance sheet service."""

import importlib
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pytest

service_module = importlib.import_module("src.app.api.v1.services.k_balance.balance_sheet_service")


@dataclass
class SimpleUser:
    """Small helper object to mimic the real user model."""

    role: str
    id_user: int = 1


@dataclass
class SimpleUserCompany:
    """Represents a connection between a user and a company."""

    id_user: int
    id_company: int


class QueryDescriptor:
    """Descriptor used to reproduce SQLAlchemy's chained query style."""

    def __get__(self, instance: Any, owner: Any) -> "QueryWrapper":
        return QueryWrapper(owner)


class QueryWrapper:
    """Simple query implementation supporting filter_by().first()."""

    def __init__(self, owner: Any, records: Optional[List[Any]] = None) -> None:
        self._owner = owner
        self._records = records if records is not None else list(owner.entries)

    def filter_by(self, **filters: Any) -> "QueryWrapper":
        filtered = [
            record
            for record in self._records
            if all(getattr(record, key) == value for key, value in filters.items())
        ]
        return QueryWrapper(self._owner, filtered)

    def order_by(self, *_args: Any, **_kwargs: Any) -> "QueryWrapper":
        """
        Support SQLAlchemy-style .order_by() chaining in tests.
        The in-memory list is already deterministic for our purposes, so we
        simply ignore the ordering arguments and return self.
        """
        return self

    def first(self) -> Optional[Any]:
        return self._records[0] if self._records else None


class TbUserCompanyStub:
    """In-memory version of the TbUserCompany model used in tests."""

    entries: List[SimpleUserCompany] = []
    query = QueryDescriptor()

    @classmethod
    def set_entries(cls, entries: List[SimpleUserCompany]) -> None:
        cls.entries = list(entries)


class _IdBalanceColumn:
    """Minimal stand-in for SQLAlchemy Column used only for .desc() calls in tests."""

    def desc(self) -> "_IdBalanceColumn":
        return self


class BalanceRecord:
    """Small balance record with the fields used by the service."""

    counter = 1

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.id_balance = BalanceRecord.counter
        BalanceRecord.counter += 1
        self.id_company = payload["id_company"]
        self.year = payload["year"]
        self.month = payload["month"]
        self.type = payload["type"]
        self.mode = payload["mode"]
        self.note = payload.get("note")
        self.balance = payload.get("balance")
        self.file = payload.get("file")
        self.created_at = None
        self.updated_at = None
        self.is_deleted = False
        self.deleted_at = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id_balance": self.id_balance,
            "id_company": self.id_company,
            "year": self.year,
            "month": self.month,
            "type": self.type,
            "mode": self.mode,
            "note": self.note,
            "balance": self.balance,
            "file": self.file,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at,
        }


class KbaiBalanceStub:
    """In-memory substitute for the real KbaiBalance model."""

    # Provide an id_balance attribute with a .desc() method so that
    # KbaiBalanceStub.id_balance.desc() used in _check_existing_balance
    # does not fail during tests.
    id_balance = _IdBalanceColumn()

    # Minimal query interface to support KbaiBalance.query.filter_by(...).order_by(...).first()
    entries: List[BalanceRecord] = []
    query = QueryDescriptor()

    create_error: Optional[str] = None
    create_should_raise: bool = False
    find_error: Optional[str] = None
    find_should_raise: bool = False
    find_items: List[BalanceRecord] = []
    findone_result: Optional[BalanceRecord] = None
    findone_should_raise: bool = False

    @classmethod
    def create(cls, balance_data: Dict[str, Any]) -> Tuple[Optional[BalanceRecord], Optional[str]]:
        if cls.create_should_raise:
            raise RuntimeError("unexpected create failure")
        if cls.create_error:
            return None, cls.create_error
        record = BalanceRecord(balance_data)
        return record, None

    @classmethod
    def find(cls, **kwargs: Any) -> Tuple[List[BalanceRecord], int, Optional[str]]:
        if cls.find_should_raise:
            raise RuntimeError("unexpected find failure")
        if cls.find_error:
            return [], 0, cls.find_error
        return list(cls.find_items), len(cls.find_items), None

    @classmethod
    def findOne(cls, **kwargs: Any) -> Optional[BalanceRecord]:
        if cls.findone_should_raise:
            raise RuntimeError("unexpected findOne failure")
        return cls.findone_result


def simple_extract(_: str) -> Dict[str, Any]:
    """Deterministic extractor used by most tests."""

    return {"assets": 100, "liabilities": 40}


class FakeFile:
    """Tiny file-like object powering the upload flow tests."""

    def __init__(self, filename: str, content: str = "data") -> None:
        self.filename = filename
        self._content = content
        self.saved_path: Optional[str] = None

    def save(self, target_path: str) -> None:
        with open(target_path, "w", encoding="utf-8") as handle:
            handle.write(self._content)
        self.saved_path = target_path


class RemoveErrorOS:
    """Wrapper that mirrors os but always fails when removing files."""

    def __init__(self, real_os: Any) -> None:
        self._real_os = real_os
        self.path = real_os.path

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real_os, name)

    def remove(self, *_: Any, **__: Any) -> None:
        raise PermissionError("blocked removal")


@pytest.fixture(autouse=True)
def patch_service_dependencies() -> None:
    """Ensure every test works with the lightweight in-memory doubles."""

    original_tb_user_company = service_module.TbUserCompany
    original_kbai_balance = service_module.KbaiBalance
    original_extract = service_module.extract_balance_from_pdf

    service_module.TbUserCompany = TbUserCompanyStub
    service_module.KbaiBalance = KbaiBalanceStub
    service_module.extract_balance_from_pdf = simple_extract

    TbUserCompanyStub.set_entries([])
    KbaiBalanceStub.entries = []
    KbaiBalanceStub.create_error = None
    KbaiBalanceStub.create_should_raise = False
    KbaiBalanceStub.find_error = None
    KbaiBalanceStub.find_should_raise = False
    KbaiBalanceStub.find_items = []
    KbaiBalanceStub.findone_result = None
    KbaiBalanceStub.findone_should_raise = False
    BalanceRecord.counter = 1

    yield

    service_module.TbUserCompany = original_tb_user_company
    service_module.KbaiBalance = original_kbai_balance
    service_module.extract_balance_from_pdf = original_extract


@pytest.fixture
def service_instance() -> service_module.BalanceSheetService:
    return service_module.BalanceSheetService()


def test_check_company_access_allows_privileged_roles(service_instance: service_module.BalanceSheetService) -> None:
    for role in ("superadmin", "staff"):
        user = SimpleUser(role=role)
        has_access, message = service_instance.check_company_access(user, company_id=5)
        assert has_access is True
        assert message == ""


def test_check_company_access_allows_assigned_user(service_instance: service_module.BalanceSheetService) -> None:
    TbUserCompanyStub.set_entries([SimpleUserCompany(id_user=1, id_company=7)])
    user = SimpleUser(role="admin", id_user=1)
    has_access, message = service_instance.check_company_access(user, company_id=7)
    assert has_access is True
    assert message == ""


def test_check_company_access_blocks_unassigned_user(service_instance: service_module.BalanceSheetService) -> None:
    user = SimpleUser(role="user", id_user=2)
    has_access, message = service_instance.check_company_access(user, company_id=99)
    assert has_access is False
    assert "do not have access" in message.lower()


def test_check_company_access_rejects_unknown_role(service_instance: service_module.BalanceSheetService) -> None:
    user = SimpleUser(role="observer")
    has_access, message = service_instance.check_company_access(user, company_id=1)
    assert has_access is False
    assert "unknown user role" in message.lower()


def test_balance_sheet_rejects_missing_file(service_instance: service_module.BalanceSheetService) -> None:
    response, status = service_instance.balance_sheet(
        file=None,
        company_id=1,
        year=2024,
        month=1,
        type="annual",
        mode="manual",
    )
    assert status == 400
    assert response["error"] == "Validation error"


def test_balance_sheet_rejects_non_pdf(service_instance: service_module.BalanceSheetService) -> None:
    fake_file = FakeFile(filename="report.txt")
    response, status = service_instance.balance_sheet(
        file=fake_file,
        company_id=1,
        year=2024,
        month=1,
        type="annual",
        mode="manual",
    )
    assert status == 400
    assert response["message"] == "Only PDF, XLSX, and XBRL/XML files are allowed"


def test_balance_sheet_rejects_invalid_year(service_instance: service_module.BalanceSheetService) -> None:
    fake_file = FakeFile(filename="report.pdf")
    response, status = service_instance.balance_sheet(
        file=fake_file,
        company_id=1,
        year=1800,
        month=1,
        type="annual",
        mode="manual",
    )
    assert status == 400
    assert response["message"] == "Invalid year. Must be between 1900 and 2100"


def test_balance_sheet_checks_permissions(service_instance: service_module.BalanceSheetService) -> None:
    user = SimpleUser(role="user", id_user=1)
    response, status = service_instance.balance_sheet(
        file=FakeFile(filename="report.pdf"),
        company_id=42,
        year=2024,
        month=1,
        type="annual",
        mode="manual",
        current_user=user,
    )
    assert status == 403
    assert response["error"] == "Permission denied"


def test_balance_sheet_handles_extraction_error(service_instance: service_module.BalanceSheetService) -> None:
    def failing_extract(_: str) -> Dict[str, Any]:
        raise ValueError("bad pdf")

    service_module.extract_balance_from_pdf = failing_extract
    fake_file = FakeFile(filename="report.pdf")
    response, status = service_instance.balance_sheet(
        file=fake_file,
        company_id=1,
        year=2024,
        month=1,
        type="annual",
        mode="manual",
    )
    assert status == 500
    assert response["error"] == "Extraction error"
    if fake_file.saved_path:
        os.remove(fake_file.saved_path)


def test_balance_sheet_returns_database_error(service_instance: service_module.BalanceSheetService) -> None:
    KbaiBalanceStub.create_error = "db down"
    fake_file = FakeFile(filename="report.pdf")
    response, status = service_instance.balance_sheet(
        file=fake_file,
        company_id=1,
        year=2024,
        month=None,
        type="quarterly",
        mode="manual",
        note="check",
    )
    assert status == 500
    # Service includes the low-level message ('db down') in the error string;
    # we only require that it is reported as a database error.
    assert response["error"].startswith("Database error")
    if fake_file.saved_path:
        os.remove(fake_file.saved_path)


def test_balance_sheet_success_flow(service_instance: service_module.BalanceSheetService) -> None:
    fake_file = FakeFile(filename="report.pdf")
    response, status = service_instance.balance_sheet(
        file=fake_file,
        company_id=3,
        year=2024,
        month=None,
        type="annual",
        mode="manual",
        note="ok",
    )
    assert status == 201
    assert response["success"] is True
    # Service returns the created balance identifier; presence is enough here.
    assert "balance_id" in response["data"]
    assert not os.path.exists(fake_file.saved_path or "")


def test_balance_sheet_reports_cleanup_issue(service_instance: service_module.BalanceSheetService) -> None:
    fake_file = FakeFile(filename="report.pdf")
    real_os = service_module.os
    service_module.os = RemoveErrorOS(real_os)
    try:
        response, status = service_instance.balance_sheet(
            file=fake_file,
            company_id=4,
            year=2024,
            month=None,
            type="annual",
            mode="manual",
        )
        assert status == 201
        assert response["success"] is True
    finally:
        service_module.os = real_os
    if fake_file.saved_path and os.path.exists(fake_file.saved_path):
        os.remove(fake_file.saved_path)


def test_balance_sheet_handles_unexpected_failure(service_instance: service_module.BalanceSheetService) -> None:
    KbaiBalanceStub.create_should_raise = True
    fake_file = FakeFile(filename="report.pdf")
    response, status = service_instance.balance_sheet(
        file=fake_file,
        company_id=1,
        year=2024,
        month=None,
        type="annual",
        mode="manual",
    )
    assert status == 500
    assert response["error"] == "Internal server error"
    if fake_file.saved_path and os.path.exists(fake_file.saved_path):
        os.remove(fake_file.saved_path)


def test_balance_sheet_cleanup_failure_on_error(service_instance: service_module.BalanceSheetService) -> None:
    KbaiBalanceStub.create_should_raise = True
    fake_file = FakeFile(filename="report.pdf")
    real_os = service_module.os
    service_module.os = RemoveErrorOS(real_os)
    try:
        response, status = service_instance.balance_sheet(
            file=fake_file,
            company_id=6,
            year=2024,
            month=None,
            type="annual",
            mode="manual",
        )
        assert status == 500
        assert response["error"] == "Internal server error"
    finally:
        service_module.os = real_os
    if fake_file.saved_path and os.path.exists(fake_file.saved_path):
        os.remove(fake_file.saved_path)


def test_get_by_company_id_checks_permissions(service_instance: service_module.BalanceSheetService) -> None:
    user = SimpleUser(role="admin", id_user=10)
    response, status = service_instance.get_by_company_id(
        company_id=5,
        page=1,
        per_page=2,
        current_user=user,
    )
    assert status == 403
    assert response["error"] == "Permission denied"


def test_get_by_company_id_validates_company(service_instance: service_module.BalanceSheetService) -> None:
    response, status = service_instance.get_by_company_id(company_id=0)
    assert status == 400
    assert response["message"] == "Valid company_id is required"


def test_get_by_company_id_returns_database_error(service_instance: service_module.BalanceSheetService) -> None:
    KbaiBalanceStub.find_error = "db error"
    response, status = service_instance.get_by_company_id(company_id=2)
    assert status == 500
    assert response["error"] == "Database error"


def test_get_by_company_id_success(service_instance: service_module.BalanceSheetService) -> None:
    records = [
        BalanceRecord({
            "id_company": 2,
            "year": 2024,
            "month": 1,
            "type": "annual",
            "mode": "manual",
            "note": "note",
            "balance": {"assets": 1},
        })
    ]
    KbaiBalanceStub.find_items = records
    response, status = service_instance.get_by_company_id(company_id=2, page=1, per_page=10)
    assert status == 200
    assert response["success"] is True
    assert "balance" not in response["data"][0]
    assert response["pagination"]["total"] == 1


def test_get_by_company_id_handles_unexpected_failure(service_instance: service_module.BalanceSheetService) -> None:
    KbaiBalanceStub.find_should_raise = True
    response, status = service_instance.get_by_company_id(company_id=1)
    assert status == 500
    assert response["error"] == "Internal server error"


def test_get_by_id_validates_identifier(service_instance: service_module.BalanceSheetService) -> None:
    response, status = service_instance.get_by_id(id_balance=0)
    assert status == 400
    assert response["message"] == "Valid id_balance is required"


def test_get_by_id_handles_missing_record(service_instance: service_module.BalanceSheetService) -> None:
    KbaiBalanceStub.findone_result = None
    response, status = service_instance.get_by_id(id_balance=5)
    assert status == 404
    assert response["error"] == "Not found"


def test_get_by_id_checks_permissions(service_instance: service_module.BalanceSheetService) -> None:
    record = BalanceRecord({
        "id_company": 9,
        "year": 2024,
        "month": 1,
        "type": "annual",
        "mode": "manual",
        "balance": {},
    })
    KbaiBalanceStub.findone_result = record
    user = SimpleUser(role="user", id_user=3)
    response, status = service_instance.get_by_id(id_balance=record.id_balance, current_user=user)
    assert status == 403
    assert response["error"] == "Permission denied"


def test_get_by_id_success(service_instance: service_module.BalanceSheetService) -> None:
    record = BalanceRecord({
        "id_company": 1,
        "year": 2024,
        "month": 1,
        "type": "annual",
        "mode": "manual",
        "balance": {"assets": 5},
    })
    KbaiBalanceStub.findone_result = record
    TbUserCompanyStub.set_entries([SimpleUserCompany(id_user=1, id_company=1)])
    user = SimpleUser(role="admin", id_user=1)
    response, status = service_instance.get_by_id(id_balance=record.id_balance, current_user=user)
    assert status == 200
    assert response["success"] is True
    assert response["data"]["id_balance"] == record.id_balance


def test_get_by_id_handles_unexpected_failure(service_instance: service_module.BalanceSheetService) -> None:
    KbaiBalanceStub.findone_should_raise = True
    response, status = service_instance.get_by_id(id_balance=5)
    assert status == 500
    assert response["error"] == "Internal server error"

