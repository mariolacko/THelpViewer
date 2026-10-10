"""QuickBASIC 4.5 and 7.1 share one Help Files product menu."""

import json
from pathlib import Path
import shutil

import pytest

from thelpviewer.server.converter.writers.bundle import _product_metadata_for_group, export_bundle_tree


@pytest.mark.parametrize("group,expected_product,expected_version", [
    ("Microsoft QuickBASIC Extended 7.1", "qbx", "7.1"),
    ("Microsoft QuickBASIC 4.5", "qb45", "4.5"),
])
def test_quickbasic_group_metadata_has_one_product_name(group, expected_product, expected_version):
    assert _product_metadata_for_group(group) == (
        expected_product, "Microsoft QuickBASIC", expected_version,
    )


def test_quickbasic_exports_share_one_product_with_two_version_branches(tmp_path):
    originals = (
        Path("data/sources/Microsoft QuickBASIC Extended 7.1/BAS7QCK.HLP"),
        Path("data/sources/Microsoft QuickBASIC 4.5/QB45QCK.HLP"),
    )
    if not all(path.is_file() for path in originals):
        pytest.skip("QuickBASIC source help files were not downloaded")

    sources = tmp_path / "sources"
    for original in originals:
        target = sources / original.relative_to("data/sources")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)

    helps = tmp_path / "helps"
    export_bundle_tree(sources, helps, layout="helps")
    catalog = json.loads((helps / "catalog.json").read_text(encoding="utf-8"))

    assert len(catalog) == 2
    assert {entry["product_name"] for entry in catalog} == {"Microsoft QuickBASIC"}
    assert {entry["version"] for entry in catalog} == {"4.5", "7.1"}
    assert {entry["file"] for entry in catalog} == {
        "Microsoft QuickBASIC Extended 7.1/bas7qck.json.gz",
        "Microsoft QuickBASIC 4.5/qb45qck.json.gz",
    }
