import pytest

from ifc_compliance_mvd.engine import ComplianceEngine


@pytest.fixture(scope="session")
def engine():
    instance = ComplianceEngine()
    instance.run(persist=False)
    return instance

