"""Bundle variants for Game-Cheater database sections."""

from __future__ import annotations

from pathlib import Path

from ..base import ContentNode, HelpDocument
from ..bundle_types import BundleDocumentVariant


GAME_CHEATER_SECTION_BUNDLES = (
    ("Cheaty", "cheaty", ("CHEATDBS.000", "CHEATDBS.T00")),
    ("Firmy", "firmy", ("FIRMY.000", "FIRMY.T00")),
    ("Internetové adresy", "internetove-adresy", ("GCNETADR.000", "GCNETADR.T00")),
    ("Nápověda", "napoveda", ("GCHLP.000", "GCHLP.T00")),
    ("Informace", "informace", ("DBSNFO.000", "DBSNFO.T00", "GCPRM.000")),
)


def _section_document(
    document: HelpDocument,
    label: str,
    source_file: str,
) -> HelpDocument | None:
    section = next((node for node in document.contents if node.label == label), None)
    if section is None:
        return None
    topic_ids = {child.topic_id for child in section.children if child.topic_id is not None}
    topics = [topic for topic in document.topics if topic.context_id in topic_ids]
    if not topics:
        return None
    index_entries = [
        entry
        for entry in document.index_entries
        if entry.context_id in topic_ids or entry.topic_id in topic_ids
    ]
    base_title = str(document.metadata.get("title") or document.display_name).strip()
    title = f"{base_title} - {label}" if base_title else label
    metadata = dict(document.metadata)
    metadata.update(
        {
            "title": title,
            "display_name": title,
            "description": title,
            "game_cheater_section": label,
            "record_count": len(topics),
        }
    )
    if label == "Nápověda":
        metadata["show_topic_titles"] = False
    transport_keys = metadata.get("transport_metadata_keys")
    keys = [key for key in transport_keys if isinstance(key, str)] if isinstance(transport_keys, list) else []
    if "game_cheater_section" not in keys:
        keys.append("game_cheater_section")
    if label == "Nápověda" and "show_topic_titles" not in keys:
        keys.append("show_topic_titles")
    metadata["transport_metadata_keys"] = keys
    return HelpDocument(
        format_name=document.format_name,
        source_name=str(Path(document.source_name).with_name(source_file)),
        topics=topics,
        index_entries=index_entries,
        contents=[
            ContentNode(
                label=label,
                children=[
                    ContentNode(
                        label=topic.names[0] if topic.names else str(topic.context_id),
                        topic_id=topic.context_id,
                    )
                    for topic in topics
                ],
            )
        ],
        comments=list(document.comments),
        metadata=metadata,
        binary_data=document.binary_data,
    )


def document_variants(document: HelpDocument) -> list[BundleDocumentVariant]:
    if document.format_name != "game-cheater":
        return []
    variants: list[BundleDocumentVariant] = []
    available_files = document.metadata.get("source_files")
    available = set(available_files) if isinstance(available_files, list) else set()
    for label, bundle_stem, source_files in GAME_CHEATER_SECTION_BUNDLES:
        section_document = _section_document(document, label, source_files[0])
        if section_document is None:
            continue
        variants.append(
            BundleDocumentVariant(
                bundle_stem=bundle_stem,
                document=section_document,
                source_files=tuple(name for name in source_files if name in available),
            )
        )
    return variants
