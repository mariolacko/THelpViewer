#!/usr/bin/env python3
"""Inspect compiled HLX files for reverse-engineering work."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from thelpviewer.server.converter.readers.hlx_binary import HlxBinaryReader, _scan_hlx_index_records
from thelpviewer.server.converter.readers.hlx_binary import _resolve_hlx_address
from thelpviewer.server.converter.readers.hlx_deterministic import parse_hlx_deterministic


@dataclass(frozen=True, slots=True)
class ControlByteContextSample:
    control_byte: int
    offset: int
    printable_score: int
    modes: tuple[str, ...]
    hex_context: str
    ascii_context: str


@dataclass(frozen=True, slots=True)
class ProbeResult:
    path: Path
    size: int
    pool_candidate: int
    pool_offset: int
    hlx_kind: str
    hlx_family: str
    topic_count: int
    index_entry_count: int
    pointer_count: int
    hotspot_count: int
    index_record_count: int
    index_flag_counts: tuple[tuple[int, int], ...]
    index_target_stride_counts: tuple[tuple[int, int], ...]
    index_flag_stride_fit: tuple[tuple[int, int, int, int], ...]
    repeated_target_count: int
    avg_lines_per_topic: float
    single_line_ratio: float
    rtf_ref_count: int
    control_byte_total_ptr4_ratio: float
    control_byte_0_ptr4_ratio: float
    control_byte_1_ptr4_ratio: float
    control_byte_dominant: tuple[int, ...]
    control_byte_valid_hits: tuple[tuple[int, int], ...]
    control_byte_ptr2_hits: tuple[tuple[int, int], ...]
    control_byte_ptr4_hits: tuple[tuple[int, int], ...]
    control_byte_contexts: tuple[ControlByteContextSample, ...]
    first_strings: tuple[tuple[int, str], ...]
    pointer_sample: tuple[tuple[int, int], ...]


def _coerce_control_byte_list(values: object) -> tuple[int, ...]:
    if not isinstance(values, list):
        return ()
    result: list[int] = []
    for value in values:
        if isinstance(value, int):
            result.append(value)
            continue
        if isinstance(value, str) and value.isdigit():
            result.append(int(value))
    return tuple(result)


def _coerce_control_byte_hits(values: object) -> tuple[tuple[int, int], ...]:
    if not isinstance(values, dict):
        return ()
    result: list[tuple[int, int]] = []
    for raw_key, raw_value in values.items():
        key = str(raw_key)
        if not key.isdigit():
            continue
        if not isinstance(raw_value, int):
            continue
        result.append((int(key), raw_value))
    result.sort(key=lambda item: (-item[1], item[0]))
    return tuple(result)


def _summarize_index_records(
    records: list[object],
) -> tuple[
    tuple[tuple[int, int], ...],
    tuple[tuple[int, int], ...],
    tuple[tuple[int, int, int, int], ...],
    int,
]:
    flag_counts = Counter(getattr(record, "flags") for record in records)
    target_counts = Counter(getattr(record, "target_offset") for record in records)
    target_offsets = [getattr(record, "target_offset") for record in records]
    target_offsets.sort()
    by_flag = Counter()
    exact_stride_matches = Counter()
    stride_counts = Counter(
        second - first
        for first, second in zip(target_offsets, target_offsets[1:])
    )
    sorted_records = sorted(records, key=lambda record: (getattr(record, "target_offset"), getattr(record, "file_offset")))
    for first, second in zip(sorted_records, sorted_records[1:]):
        stride = getattr(second, "target_offset") - getattr(first, "target_offset")
        flag = int(getattr(first, "flags"))
        by_flag[flag] += 1
        if stride == flag * 4:
            exact_stride_matches[flag] += 1
    repeated_target_count = sum(1 for count in target_counts.values() if count > 1)
    stride_fit = tuple(
        (flag, flag * 4, exact_stride_matches[flag], by_flag[flag])
        for flag, _count in flag_counts.most_common(8)
        if by_flag[flag] > 0
    )
    return (
        tuple(flag_counts.most_common(5)),
        tuple(stride_counts.most_common(5)),
        stride_fit,
        repeated_target_count,
    )


def _format_control_bytes(values: tuple[int, ...]) -> str:
    if not values:
        return "-"
    return "/".join(str(value) for value in values)


def _merge_control_byte_modes(
    ptr2_hits: tuple[tuple[int, int], ...],
    ptr4_hits: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int, int], ...]:
    merged: dict[int, list[int]] = {}
    for control_byte, hit_count in ptr2_hits:
        merged.setdefault(control_byte, [0, 0])[0] = hit_count
    for control_byte, hit_count in ptr4_hits:
        merged.setdefault(control_byte, [0, 0])[1] = hit_count
    result = [
        (control_byte, counts[0], counts[1])
        for control_byte, counts in merged.items()
    ]
    result.sort(key=lambda item: (-(item[1] + item[2]), item[0]))
    return tuple(result)


def _extract_strings(data: bytes) -> list[tuple[int, str]]:
    size = len(data)
    result: list[tuple[int, str]] = []
    index = 0
    while index < size:
        value = data[index]
        if value != 0 and value >= 0x20 and value != 0x7F:
            end = index
            while end < size and data[end] != 0 and data[end] >= 0x20 and data[end] != 0x7F:
                end += 1
            raw = data[index:end]
            result.append((index, raw.decode("cp437", errors="replace")))
            index = end + 1
            continue
        index += 1
    return result


def _printable_score(data: bytes) -> int:
    return sum(1 for value in data if 0x20 <= value < 0x7F)


def _ascii_preview(data: bytes) -> str:
    chars: list[str] = []
    for value in data:
        if 0x20 <= value < 0x7F:
            chars.append(chr(value))
        else:
            chars.append(".")
    return "".join(chars)


def _collect_control_byte_contexts(
    data: bytes,
    pool_offset: int,
    dominant: tuple[int, ...],
    *,
    samples_per_byte: int,
    context_bytes: int,
) -> tuple[ControlByteContextSample, ...]:
    size = len(data)
    if samples_per_byte <= 0 or context_bytes <= 0:
        return ()

    dominant_set = set(dominant)
    candidates: dict[int, list[ControlByteContextSample]] = {value: [] for value in dominant}

    for offset, control_byte in enumerate(data):
        if control_byte not in dominant_set:
            continue

        modes: list[str] = []
        if offset + 3 <= size:
            raw2 = int.from_bytes(data[offset + 1 : offset + 3], "little")
            addr2 = _resolve_hlx_address(raw2, pool_offset, size)
            if addr2 is not None:
                modes.append(f"ptr2={addr2:#06x}")
        if offset + 5 <= size:
            raw4 = int.from_bytes(data[offset + 1 : offset + 5], "little")
            addr4 = _resolve_hlx_address(raw4, pool_offset, size)
            if addr4 is not None:
                modes.append(f"ptr4={addr4:#06x}")
        if not modes:
            continue

        left = data[max(0, offset - context_bytes) : offset]
        right = data[offset + 1 : min(size, offset + 1 + context_bytes)]
        chunk = left + bytes([control_byte]) + right
        candidates[control_byte].append(
            ControlByteContextSample(
                control_byte=control_byte,
                offset=offset,
                printable_score=_printable_score(chunk),
                modes=tuple(modes),
                hex_context=(
                    f"{left.hex(' ')} [{control_byte:02x}] {right.hex(' ')}".strip()
                ),
                ascii_context=(
                    f"{_ascii_preview(left)}[{_ascii_preview(bytes([control_byte]))}]{_ascii_preview(right)}"
                ),
            )
        )

    selected: list[ControlByteContextSample] = []
    min_spacing = max(4, context_bytes)
    for control_byte in dominant:
        ranked = sorted(
            candidates.get(control_byte, ()),
            key=lambda item: (-item.printable_score, item.offset),
        )
        chosen: list[ControlByteContextSample] = []
        for sample in ranked:
            if any(abs(sample.offset - existing.offset) <= min_spacing for existing in chosen):
                continue
            chosen.append(sample)
            if len(chosen) >= samples_per_byte:
                break
        selected.extend(chosen)
    return tuple(selected)


def _pool_offset(data: bytes) -> tuple[int, int]:
    size = len(data)
    candidate = int.from_bytes(data[4:6], "little") if size >= 6 else 0
    if 0x100 <= candidate < size:
        return candidate, candidate
    return candidate, (0x800 if 0x800 < size else max(256, size // 8))


def probe_file(
    path: Path,
    *,
    samples_per_byte: int = 3,
    context_bytes: int = 12,
) -> ProbeResult:
    data = path.read_bytes()
    pool_candidate, pool_offset = _pool_offset(data)
    reader = HlxBinaryReader(source_name=path.name, source_path=path)
    document = reader.read_bytes(data)
    index_records = _scan_hlx_index_records(data)
    deterministic = parse_hlx_deterministic(data, min_topics=1)
    if len(deterministic) == 3:
        _topics, index_entries, pointer_map = deterministic
    else:
        _topics, index_entries = deterministic
        pointer_map = {}

    strings = _extract_strings(data)
    pool_strings = [(off, text) for off, text in strings if off >= pool_offset]
    hotspot_count = sum(len(topic.positional_keywords) for topic in document.topics)
    metadata = document.metadata if isinstance(document.metadata, dict) else {}
    index_flag_counts, index_target_stride_counts, index_flag_stride_fit, repeated_target_count = _summarize_index_records(index_records)
    return ProbeResult(
        path=path,
        size=len(data),
        pool_candidate=pool_candidate,
        pool_offset=pool_offset,
        hlx_kind=str(metadata.get("hlx_kind", "?")),
        hlx_family=str(metadata.get("hlx_family", "?")),
        topic_count=len(document.topics),
        index_entry_count=len(index_entries),
        pointer_count=len(pointer_map),
        hotspot_count=hotspot_count,
        index_record_count=len(index_records),
        index_flag_counts=index_flag_counts,
        index_target_stride_counts=index_target_stride_counts,
        index_flag_stride_fit=index_flag_stride_fit,
        repeated_target_count=repeated_target_count,
        avg_lines_per_topic=float(metadata.get("avg_lines_per_topic", 0.0)),
        single_line_ratio=float(metadata.get("single_line_ratio", 0.0)),
        rtf_ref_count=int(metadata.get("rtf_ref_count", 0)),
        control_byte_total_ptr4_ratio=float(metadata.get("control_byte_total_ptr4_ratio", 0.0)),
        control_byte_0_ptr4_ratio=float(metadata.get("control_byte_0_ptr4_ratio", 0.0)),
        control_byte_1_ptr4_ratio=float(metadata.get("control_byte_1_ptr4_ratio", 0.0)),
        control_byte_dominant=_coerce_control_byte_list(metadata.get("control_byte_dominant")),
        control_byte_valid_hits=_coerce_control_byte_hits(metadata.get("control_byte_valid_hits"))[:5],
        control_byte_ptr2_hits=_coerce_control_byte_hits(metadata.get("control_byte_ptr2_hits"))[:5],
        control_byte_ptr4_hits=_coerce_control_byte_hits(metadata.get("control_byte_ptr4_hits"))[:5],
        control_byte_contexts=_collect_control_byte_contexts(
            data,
            pool_offset,
            _coerce_control_byte_list(metadata.get("control_byte_dominant")),
            samples_per_byte=samples_per_byte,
            context_bytes=context_bytes,
        ),
        first_strings=tuple(pool_strings[:8]),
        pointer_sample=tuple(sorted(pointer_map.items())[:8]),
    )


def _iter_targets(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(path.rglob("*.HLX"))
    return [path]


def _filter_results(
    results: list[ProbeResult],
    min_ptr4_ratio: float,
    min_b1_ratio: float,
) -> list[ProbeResult]:
    return [
        item
        for item in results
        if item.control_byte_total_ptr4_ratio >= min_ptr4_ratio
        and item.control_byte_1_ptr4_ratio >= min_b1_ratio
    ]


def _sort_results(
    results: list[ProbeResult],
    sort_key: str,
    reverse: bool,
) -> list[ProbeResult]:
    key_funcs = {
        "file": lambda item: item.path.name.lower(),
        "family": lambda item: (item.hlx_family, item.path.name.lower()),
        "topics": lambda item: (item.topic_count, item.path.name.lower()),
        "hotspots": lambda item: (item.hotspot_count, item.path.name.lower()),
        "ptr4_ratio": lambda item: (item.control_byte_total_ptr4_ratio, item.path.name.lower()),
        "b1_ratio": lambda item: (item.control_byte_1_ptr4_ratio, item.path.name.lower()),
    }
    return sorted(results, key=key_funcs[sort_key], reverse=reverse)


def _print_summary(results: list[ProbeResult]) -> None:
    counts = Counter(item.hlx_kind for item in results)
    print("kind_counts:", ", ".join(f"{kind}={counts[kind]}" for kind in sorted(counts)))
    print(
        f"{'kind':<15} {'family':<18} {'file':<16} {'topics':>6} {'pointers':>8} {'hotspots':>8} "
        f"{'avg_lines':>9} {'rtf_refs':>8} {'ptr4_ratio':>10} {'b1_ratio':>8} {'ctrl':<8}"
    )
    for item in results:
        print(
            f"{item.hlx_kind:<15} {item.hlx_family:<18} {item.path.name:<16} {item.topic_count:>6} "
            f"{item.pointer_count:>8} {item.hotspot_count:>8} {item.avg_lines_per_topic:>9.2f} "
            f"{item.rtf_ref_count:>8} {item.control_byte_total_ptr4_ratio:>10.3f} "
            f"{item.control_byte_1_ptr4_ratio:>8.3f} {_format_control_bytes(item.control_byte_dominant):<8}"
        )


def _print_details(results: list[ProbeResult]) -> None:
    for item in results:
        print(f"=== {item.path}")
        print(f"size: {item.size}")
        print(f"pool_candidate: {item.pool_candidate}")
        print(f"pool_offset: {item.pool_offset}")
        print(f"hlx_kind: {item.hlx_kind}")
        print(f"hlx_family: {item.hlx_family}")
        print(f"topic_count: {item.topic_count}")
        print(f"index_entry_count: {item.index_entry_count}")
        print(f"pointer_count: {item.pointer_count}")
        print(f"hotspot_count: {item.hotspot_count}")
        print(f"index_record_count: {item.index_record_count}")
        print(f"repeated_target_count: {item.repeated_target_count}")
        print("index_flag_counts:")
        for flag_value, count in item.index_flag_counts:
            print(f"  {flag_value}: {count}")
        print("index_target_stride_counts:")
        for stride, count in item.index_target_stride_counts:
            print(f"  {stride}: {count}")
        print("index_flag_stride_fit:")
        for flag_value, expected_stride, match_count, total_count in item.index_flag_stride_fit:
            ratio = match_count / total_count if total_count else 0.0
            print(
                f"  flag {flag_value}: expects +{expected_stride} -> "
                f"{match_count}/{total_count} ({ratio:.2%})"
            )
        print(f"avg_lines_per_topic: {item.avg_lines_per_topic:.2f}")
        print(f"single_line_ratio: {item.single_line_ratio:.2f}")
        print(f"rtf_ref_count: {item.rtf_ref_count}")
        print(f"control_byte_total_ptr4_ratio: {item.control_byte_total_ptr4_ratio:.3f}")
        print(f"control_byte_0_ptr4_ratio: {item.control_byte_0_ptr4_ratio:.3f}")
        print(f"control_byte_1_ptr4_ratio: {item.control_byte_1_ptr4_ratio:.3f}")
        print(f"control_byte_dominant: {_format_control_bytes(item.control_byte_dominant)}")
        print("control_byte_valid_hits:")
        for control_byte, hit_count in item.control_byte_valid_hits:
            print(f"  {control_byte}: {hit_count}")
        print("control_byte_modes:")
        for control_byte, ptr2_count, ptr4_count in _merge_control_byte_modes(item.control_byte_ptr2_hits, item.control_byte_ptr4_hits):
            print(f"  {control_byte}: ptr2={ptr2_count} ptr4={ptr4_count}")
        print("control_byte_contexts:")
        for control_byte in item.control_byte_dominant:
            matching = [sample for sample in item.control_byte_contexts if sample.control_byte == control_byte]
            if not matching:
                continue
            print(f"  byte {control_byte}:")
            for sample in matching:
                print(
                    f"    @{sample.offset:#06x} score={sample.printable_score} "
                    f"{' '.join(sample.modes)}"
                )
                print(f"      hex: {sample.hex_context}")
                print(f"      txt: {sample.ascii_context}")
        print("first_pool_strings:")
        for off, text in item.first_strings:
            print(f"  {off:#06x} {text[:80]}")
        print("pointer_sample:")
        for addr, context_id in item.pointer_sample:
            print(f"  {addr:#06x} -> {context_id}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="One .HLX file or a directory tree with compiled HLX files")
    parser.add_argument("--details", action="store_true", help="Print per-file details for reverse engineering")
    parser.add_argument(
        "--sort",
        choices=("file", "family", "topics", "hotspots", "ptr4_ratio", "b1_ratio"),
        default="file",
        help="Sort summary/details by the selected field",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Reverse the selected sort order",
    )
    parser.add_argument(
        "--min-ptr4-ratio",
        type=float,
        default=0.0,
        help="Keep only files with control_byte_total_ptr4_ratio >= this value",
    )
    parser.add_argument(
        "--min-b1-ratio",
        type=float,
        default=0.0,
        help="Keep only files with control_byte_1_ptr4_ratio >= this value",
    )
    parser.add_argument(
        "--samples-per-byte",
        type=int,
        default=3,
        help="How many hexdump context samples to print per dominant control byte in --details output",
    )
    parser.add_argument(
        "--context-bytes",
        type=int,
        default=12,
        help="How many bytes to include on each side of a sampled control byte in --details output",
    )
    args = parser.parse_args()

    target = Path(args.path)
    results = [
        probe_file(
            path,
            samples_per_byte=args.samples_per_byte,
            context_bytes=args.context_bytes,
        )
        for path in _iter_targets(target)
    ]
    if not results:
        raise SystemExit(f"No .HLX files found under {target}")

    results = _filter_results(results, args.min_ptr4_ratio, args.min_b1_ratio)
    if not results:
        raise SystemExit(
            "No HLX files matched the active filters "
            f"(min_ptr4_ratio={args.min_ptr4_ratio}, min_b1_ratio={args.min_b1_ratio})"
        )
    results = _sort_results(results, args.sort, args.reverse)

    _print_summary(results)
    if args.details:
        print()
        _print_details(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())