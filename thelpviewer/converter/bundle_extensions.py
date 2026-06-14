"""Dispatch bundle export extension hooks supplied by individual readers."""

from __future__ import annotations

from pathlib import Path

from .base import HelpDocument
from .bundle_types import BundleDocumentVariant, BundleSourceGroup
from .readers import game_cheater_bundle, scorpion_bundle


BUNDLE_GROUP_PROVIDERS = (
    scorpion_bundle.bundle_source_groups,
)

BUNDLE_VARIANT_PROVIDERS = (
    scorpion_bundle.document_variants,
    game_cheater_bundle.document_variants,
)


def discover_bundle_source_groups(paths: list[Path]) -> list[BundleSourceGroup]:
    groups: list[BundleSourceGroup] = []
    for provider in BUNDLE_GROUP_PROVIDERS:
        groups.extend(provider(paths))
    return groups


def document_bundle_variants(document: HelpDocument) -> list[BundleDocumentVariant]:
    variants: list[BundleDocumentVariant] = []
    for provider in BUNDLE_VARIANT_PROVIDERS:
        variants.extend(provider(document))
    return variants
