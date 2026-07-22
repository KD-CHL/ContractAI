"""Distribution-level checks for resources required at runtime."""

from importlib.resources import files

import pytest


@pytest.mark.parametrize(
    ("filename", "expected_fragment"),
    [
        ("index.html", "<!doctype html>"),
    ],
)
def test_installed_package_exposes_web_resources(
    filename: str,
    expected_fragment: str,
) -> None:
    """The UI must be readable through Python's installed-resource API."""

    resource = files("contract_guard").joinpath("web", filename)

    assert resource.is_file(), f"missing packaged web resource: {filename}"
    assert expected_fragment in resource.read_text(encoding="utf-8").lower()


def test_installed_package_exposes_default_knowledge_base() -> None:
    resource = files("contract_guard").joinpath("resources", "demo_knowledge_base.json")

    assert resource.is_file(), "missing packaged default knowledge base"
    assert '"CG-DEMO-K001"' in resource.read_text(encoding="utf-8")
