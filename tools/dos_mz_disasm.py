#!/usr/bin/env python3
"""Disassemble 16-bit DOS MZ executables and surface string xrefs.

Focused on reverse-engineering TD.EXE / TPROF.EXE runtime help code paths.

Examples:
    python tools/dos_mz_disasm.py /tmp/TD.EXE --default-help-strings
    python tools/dos_mz_disasm.py /tmp/TPROF.EXE --string tfhelp.tfh --string "First page"
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections import Counter
from collections import deque
from dataclasses import dataclass
from pathlib import Path
import re
import sys


DEFAULT_HELP_STRINGS: tuple[str, ...] = (
    "tdhelp.tdh",
    "tfhelp.tfh",
    "Index",
    "Previous page",
    "First page",
    "No help for this context",
    "Help file %s not found",
)


@dataclass(frozen=True, slots=True)
class MzRelocation:
    offset: int
    segment: int

    @property
    def linear_address(self) -> int:
        return self.segment * 16 + self.offset


@dataclass(frozen=True, slots=True)
class MzExecutable:
    path: Path
    data: bytes
    header_size: int
    image_offset: int
    image: bytes
    relocation_offset: int
    relocations: tuple[MzRelocation, ...]
    entry_cs: int
    entry_ip: int
    initial_ss: int
    initial_sp: int

    @property
    def entry_linear(self) -> int:
        return self.entry_cs * 16 + self.entry_ip


@dataclass(frozen=True, slots=True)
class StringMatch:
    needle: str
    image_offset: int

    @property
    def file_offset(self) -> int:
        raise RuntimeError("file_offset depends on the owning executable")


@dataclass(frozen=True, slots=True)
class InstructionRef:
    instruction_index: int
    instruction_address: int
    match_kind: str


@dataclass(frozen=True, slots=True)
class FarPointerRef:
    pointer_image_offset: int
    offset_word: int
    segment_word: int

    @property
    def linear_target(self) -> int:
        return self.segment_word * 16 + self.offset_word


@dataclass(frozen=True, slots=True)
class SegmentOffsetCandidate:
    segment_word: int
    offset_word: int
    frequency: int


@dataclass(frozen=True, slots=True)
class OverlayTableEntry:
    index: int
    image_offset: int
    load_segment_word: int
    load_segment_high_word: int
    size_word: int
    flags_word: int
    relocation_count: int
    file_start_segment_word: int
    file_end_segment_word: int
    file_name_offset: int
    file_name: str | None
    file_base_paragraph: int
    load_size_paragraphs: int

    @property
    def header_bytes(self) -> int:
        return ((self.relocation_count + 3) // 4) * 16

    def relative_file_bounds(self) -> tuple[int, int]:
        start = self.file_base_paragraph * 16
        end = start + self.header_bytes + self.load_size_paragraphs * 16
        return start, end

    def relative_body_bounds(self) -> tuple[int, int]:
        start, end = self.relative_file_bounds()
        return start + self.header_bytes, end


@dataclass(frozen=True, slots=True)
class OverlayStubRecord:
    image_offset: int
    dispatcher_offset_word: int
    dispatcher_segment_word: int
    overlay_index: int
    target_offset_word: int
    target_segment_word: int

    @property
    def dispatcher_linear(self) -> int:
        return self.dispatcher_segment_word * 16 + self.dispatcher_offset_word

    @property
    def target_linear(self) -> int:
        return self.target_segment_word * 16 + self.target_offset_word


@dataclass(frozen=True, slots=True)
class OverlayRelocationRecord:
    entry_index: int
    record_index: int
    offset_word: int
    site_segment_word: int
    relative_patch_offset: int
    raw_value_word: int | None

    @property
    def site_linear(self) -> int:
        return self.site_segment_word * 16 + self.offset_word

    def patched_value_word(self, relocation_base_word: int) -> int | None:
        if self.raw_value_word is None:
            return None
        return (self.raw_value_word + relocation_base_word) & 0xFFFF


@dataclass(frozen=True, slots=True)
class OverlayFarCallRecord:
    entry_index: int
    instruction_address: int
    mnemonic: str
    raw_segment_word: int
    raw_offset_word: int
    patched_segment_word: int | None

    @property
    def raw_linear(self) -> int:
        return self.raw_segment_word * 16 + self.raw_offset_word

    @property
    def patched_linear(self) -> int | None:
        if self.patched_segment_word is None:
            return None
        return self.patched_segment_word * 16 + self.raw_offset_word


def _load_capstone():
    try:
        from capstone import CS_ARCH_X86, CS_MODE_16, CS_OP_IMM, CS_OP_MEM, Cs
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "capstone is required for this helper. Install dependencies with 'pip install -r requirements.txt'."
        ) from exc
    return Cs, CS_ARCH_X86, CS_MODE_16, CS_OP_IMM, CS_OP_MEM


def parse_mz_executable(path: str | Path) -> MzExecutable:
    exe_path = Path(path)
    data = exe_path.read_bytes()
    if len(data) < 0x1C or data[:2] != b"MZ":
        raise ValueError(f"{exe_path} is not a DOS MZ executable")

    relocation_count = int.from_bytes(data[0x06:0x08], "little")
    header_paragraphs = int.from_bytes(data[0x08:0x0A], "little")
    initial_ss = int.from_bytes(data[0x0E:0x10], "little")
    initial_sp = int.from_bytes(data[0x10:0x12], "little")
    entry_ip = int.from_bytes(data[0x14:0x16], "little")
    entry_cs = int.from_bytes(data[0x16:0x18], "little")
    relocation_offset = int.from_bytes(data[0x18:0x1A], "little")
    image_offset = header_paragraphs * 16
    if image_offset <= 0 or image_offset >= len(data):
        raise ValueError(f"{exe_path} has an invalid MZ header size")

    relocations: list[MzRelocation] = []
    for index in range(relocation_count):
        item_offset = relocation_offset + index * 4
        if item_offset + 4 > len(data):
            break
        offset = int.from_bytes(data[item_offset : item_offset + 2], "little")
        segment = int.from_bytes(data[item_offset + 2 : item_offset + 4], "little")
        relocations.append(MzRelocation(offset=offset, segment=segment))

    return MzExecutable(
        path=exe_path,
        data=data,
        header_size=image_offset,
        image_offset=image_offset,
        image=data[image_offset:],
        relocation_offset=relocation_offset,
        relocations=tuple(relocations),
        entry_cs=entry_cs,
        entry_ip=entry_ip,
        initial_ss=initial_ss,
        initial_sp=initial_sp,
    )


def find_string_offsets(image: bytes, needle: str) -> list[int]:
    encoded = needle.encode("cp437", errors="strict")
    offsets: list[int] = []
    start = 0
    while True:
        offset = image.find(encoded, start)
        if offset < 0:
            return offsets
        offsets.append(offset)
        start = offset + 1


def read_c_string(image: bytes, offset: int, *, max_length: int = 260) -> str | None:
    if not (0 <= offset < len(image)):
        return None

    end = offset
    limit = min(len(image), offset + max_length)
    while end < limit and image[end] != 0:
        end += 1
    if end == offset or end >= limit:
        return None

    raw = image[offset:end]
    if any(byte < 0x20 or byte > 0x7E for byte in raw):
        return None
    return raw.decode("cp437")


def parse_overlay_table_entries(
    mz: MzExecutable,
    *,
    table_image_offset: int,
    max_entries: int,
) -> list[OverlayTableEntry]:
    entries: list[OverlayTableEntry] = []
    image = mz.image
    for index in range(max_entries):
        entry_offset = table_image_offset + index * 16
        entry_bytes = image[entry_offset : entry_offset + 16]
        if len(entry_bytes) < 16:
            break
        lookahead_bytes = image[entry_offset + 16 : entry_offset + 22]
        if len(lookahead_bytes) < 6:
            break

        words = [int.from_bytes(entry_bytes[word_offset : word_offset + 2], "little") for word_offset in range(0, 16, 2)]
        lookahead_words = [
            int.from_bytes(lookahead_bytes[word_offset : word_offset + 2], "little")
            for word_offset in range(0, 6, 2)
        ]
        file_name_offset = words[7]
        file_name = read_c_string(image, table_image_offset + file_name_offset)
        if file_name is None:
            break

        entries.append(
            OverlayTableEntry(
                index=index + 1,
                image_offset=entry_offset,
                load_segment_word=words[0],
                load_segment_high_word=words[1],
                size_word=words[2],
                flags_word=words[3],
                relocation_count=words[4],
                file_start_segment_word=words[5],
                file_end_segment_word=words[6],
                file_name_offset=file_name_offset,
                file_name=file_name,
                file_base_paragraph=lookahead_words[0] | (lookahead_words[1] << 16),
                load_size_paragraphs=lookahead_words[2],
            )
        )

    return entries


def parse_overlay_stub_records(
    mz: MzExecutable,
    *,
    start_image_offset: int,
    end_image_offset: int,
    dispatcher_linear: int | None,
) -> list[OverlayStubRecord]:
    image = mz.image
    scan_end = min(end_image_offset, len(image))
    records: list[OverlayStubRecord] = []
    offset = max(0, start_image_offset)
    while offset + 12 <= scan_end:
        if image[offset] != 0x9A or image[offset + 7] != 0xEA:
            offset += 1
            continue

        dispatcher_offset_word = int.from_bytes(image[offset + 1 : offset + 3], "little")
        dispatcher_segment_word = int.from_bytes(image[offset + 3 : offset + 5], "little")
        overlay_index = int.from_bytes(image[offset + 5 : offset + 7], "little")
        target_offset_word = int.from_bytes(image[offset + 8 : offset + 10], "little")
        target_segment_word = int.from_bytes(image[offset + 10 : offset + 12], "little")

        record = OverlayStubRecord(
            image_offset=offset,
            dispatcher_offset_word=dispatcher_offset_word,
            dispatcher_segment_word=dispatcher_segment_word,
            overlay_index=overlay_index,
            target_offset_word=target_offset_word,
            target_segment_word=target_segment_word,
        )
        if dispatcher_linear is not None and record.dispatcher_linear != dispatcher_linear:
            offset += 1
            continue
        records.append(record)
        offset += 12

    return records


def parse_overlay_relocation_records(
    entry: OverlayTableEntry,
    *,
    source_bytes: bytes,
) -> list[OverlayRelocationRecord]:
    relative_start, relative_end = entry.relative_file_bounds()
    header_end = min(relative_start + entry.header_bytes, relative_end)
    if not (0 <= relative_start < header_end <= len(source_bytes)):
        return []

    records: list[OverlayRelocationRecord] = []
    for record_index in range(entry.relocation_count):
        record_offset = relative_start + record_index * 4
        if record_offset + 4 > header_end:
            break

        offset_word = int.from_bytes(source_bytes[record_offset : record_offset + 2], "little")
        site_segment_word = int.from_bytes(source_bytes[record_offset + 2 : record_offset + 4], "little")
        relative_patch_offset = (site_segment_word - entry.file_start_segment_word) * 16 + offset_word
        raw_value_word = None
        patch_offset = relative_start + relative_patch_offset
        if 0 <= patch_offset + 2 <= relative_end:
            raw_value_word = int.from_bytes(source_bytes[patch_offset : patch_offset + 2], "little")

        records.append(
            OverlayRelocationRecord(
                entry_index=entry.index,
                record_index=record_index,
                offset_word=offset_word,
                site_segment_word=site_segment_word,
                relative_patch_offset=relative_patch_offset,
                raw_value_word=raw_value_word,
            )
        )

    return records


def collect_overlay_far_call_records(
    mz: MzExecutable,
    entry: OverlayTableEntry,
    *,
    source_bytes: bytes,
) -> list[OverlayFarCallRecord]:
    body_start, body_end = entry.relative_body_bounds()
    if not (0 <= body_start < body_end <= len(source_bytes)):
        return []

    body_base_linear = entry.file_start_segment_word * 16 + entry.header_bytes
    relocation_by_site = {
        record.site_linear: record
        for record in parse_overlay_relocation_records(entry, source_bytes=source_bytes)
    }

    Cs, CS_ARCH_X86, CS_MODE_16, _CS_OP_IMM, _CS_OP_MEM = _load_capstone()
    disassembler = Cs(CS_ARCH_X86, CS_MODE_16)
    disassembler.detail = True
    disassembler.skipdata = True

    far_pattern = re.compile(r"^0x([0-9a-f]+),\s*0x([0-9a-f]+)$", re.IGNORECASE)
    records: list[OverlayFarCallRecord] = []
    for instruction in disassembler.disasm(source_bytes[body_start:body_end], body_base_linear):
        mnemonic = instruction.mnemonic.lower()
        if mnemonic not in {"call", "lcall", "jmp", "ljmp"}:
            continue
        match = far_pattern.fullmatch(instruction.op_str.strip())
        if not match:
            continue

        raw_segment_word = int(match.group(1), 16)
        raw_offset_word = int(match.group(2), 16)
        patched_segment_word = None
        relocation_record = relocation_by_site.get(instruction.address + 3)
        if relocation_record is not None:
            patched_segment_word = relocation_record.patched_value_word(mz.entry_cs)

        records.append(
            OverlayFarCallRecord(
                entry_index=entry.index,
                instruction_address=instruction.address,
                mnemonic=instruction.mnemonic,
                raw_segment_word=raw_segment_word,
                raw_offset_word=raw_offset_word,
                patched_segment_word=patched_segment_word,
            )
        )

    return records


def disassemble_image(mz: MzExecutable):
    Cs, CS_ARCH_X86, CS_MODE_16, _CS_OP_IMM, _CS_OP_MEM = _load_capstone()
    disassembler = Cs(CS_ARCH_X86, CS_MODE_16)
    disassembler.detail = True
    disassembler.skipdata = True
    return list(disassembler.disasm(mz.image, 0))


def disassemble_image_range(
    mz: MzExecutable,
    *,
    start_image_offset: int,
    end_image_offset: int,
    address_base: int | None = None,
):
    if not (0 <= start_image_offset < end_image_offset <= len(mz.image)):
        raise ValueError(
            "image range must satisfy 0 <= start < end <= image size; "
            f"got 0x{start_image_offset:05X}-0x{end_image_offset:05X} for 0x{len(mz.image):05X}-byte image"
        )

    Cs, CS_ARCH_X86, CS_MODE_16, _CS_OP_IMM, _CS_OP_MEM = _load_capstone()
    disassembler = Cs(CS_ARCH_X86, CS_MODE_16)
    disassembler.detail = True
    disassembler.skipdata = True
    start_address = start_image_offset if address_base is None else address_base
    return list(disassembler.disasm(mz.image[start_image_offset:end_image_offset], start_address))


def parse_direct_target(op_str: str) -> int | None:
    direct_match = re.fullmatch(r"\s*(0x[0-9a-fA-F]+)\s*", op_str)
    if direct_match:
        return int(direct_match.group(1), 0)

    far_match = re.fullmatch(r"\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*", op_str)
    if far_match:
        segment_word = int(far_match.group(1), 0)
        offset_word = int(far_match.group(2), 0)
        return segment_word * 16 + offset_word

    return None


def disassemble_reachable_image(mz: MzExecutable):
    Cs, CS_ARCH_X86, CS_MODE_16, _CS_OP_IMM, _CS_OP_MEM = _load_capstone()
    disassembler = Cs(CS_ARCH_X86, CS_MODE_16)
    disassembler.detail = True
    disassembler.skipdata = False

    pending: deque[int] = deque([mz.entry_linear])
    decoded_by_address: dict[int, object] = {}
    image_size = len(mz.image)

    while pending:
        linear = pending.popleft()
        if not (0 <= linear < image_size):
            continue

        while 0 <= linear < image_size:
            if linear in decoded_by_address:
                break

            decoded = list(disassembler.disasm(mz.image[linear:], linear, count=1))
            if not decoded:
                break

            instruction = decoded[0]
            decoded_by_address[instruction.address] = instruction
            mnemonic = instruction.mnemonic.lower()
            target = parse_direct_target(instruction.op_str)
            in_image = target is not None and 0 <= target < image_size

            if mnemonic in {"call", "lcall"}:
                if in_image:
                    pending.append(target)
                linear += instruction.size
                continue

            if mnemonic in {"jmp", "ljmp"}:
                if in_image:
                    pending.append(target)
                break

            if mnemonic.startswith("j") or mnemonic in {"loop", "loope", "loopne", "loopnz", "loopz"}:
                if in_image:
                    pending.append(target)
                linear += instruction.size
                continue

            if mnemonic in {"ret", "retf", "iret", "iretd", "iretq", "hlt"}:
                break

            linear += instruction.size

    return [decoded_by_address[address] for address in sorted(decoded_by_address)]


def collect_operand_value_references(instructions, operand_targets: set[int]) -> dict[int, list[InstructionRef]]:
    _Cs, _CS_ARCH_X86, _CS_MODE_16, CS_OP_IMM, CS_OP_MEM = _load_capstone()
    matches: dict[int, list[InstructionRef]] = defaultdict(list)
    for index, instruction in enumerate(instructions):
        if instruction.id == 0:
            continue
        operands = getattr(instruction, "operands", ())
        for operand in operands:
            if operand.type == CS_OP_IMM:
                target = operand.imm & 0xFFFF
                if target in operand_targets:
                    matches[target].append(
                        InstructionRef(
                            instruction_index=index,
                            instruction_address=instruction.address,
                            match_kind="imm",
                        )
                    )
            elif operand.type == CS_OP_MEM:
                target = operand.mem.disp & 0xFFFF
                if target in operand_targets:
                    matches[target].append(
                        InstructionRef(
                            instruction_index=index,
                            instruction_address=instruction.address,
                            match_kind="disp",
                        )
                    )
    return matches


def collect_string_references(instructions, string_offsets: set[int]) -> dict[int, list[InstructionRef]]:
    return collect_operand_value_references(instructions, string_offsets)


def collect_direct_target_references(instructions, direct_targets: set[int]) -> dict[int, list[InstructionRef]]:
    matches: dict[int, list[InstructionRef]] = defaultdict(list)
    for index, instruction in enumerate(instructions):
        if instruction.id == 0:
            continue
        mnemonic = instruction.mnemonic.lower()
        if mnemonic not in {"call", "lcall", "jmp", "ljmp"}:
            continue
        target = parse_direct_target(instruction.op_str)
        if target not in direct_targets:
            continue
        matches[target].append(
            InstructionRef(
                instruction_index=index,
                instruction_address=instruction.address,
                match_kind="target",
            )
        )
    return matches


def collect_far_pointer_references(mz: MzExecutable, string_offsets: set[int]) -> dict[int, list[FarPointerRef]]:
    matches: dict[int, list[FarPointerRef]] = defaultdict(list)
    image_size = len(mz.image)
    for relocation in mz.relocations:
        segment_word_offset = relocation.linear_address
        if segment_word_offset < 2 or segment_word_offset + 2 > image_size:
            continue
        pointer_image_offset = segment_word_offset - 2
        offset_word = int.from_bytes(mz.image[pointer_image_offset : pointer_image_offset + 2], "little")
        segment_word = int.from_bytes(mz.image[segment_word_offset : segment_word_offset + 2], "little")
        linear_target = segment_word * 16 + offset_word
        if linear_target not in string_offsets:
            continue
        matches[linear_target].append(
            FarPointerRef(
                pointer_image_offset=pointer_image_offset,
                offset_word=offset_word,
                segment_word=segment_word,
            )
        )
    return matches


def build_segment_histogram(mz: MzExecutable) -> Counter[int]:
    histogram: Counter[int] = Counter()
    image_size = len(mz.image)
    for relocation in mz.relocations:
        segment_word_offset = relocation.linear_address
        if segment_word_offset + 2 > image_size:
            continue
        segment_word = int.from_bytes(mz.image[segment_word_offset : segment_word_offset + 2], "little")
        histogram[segment_word] += 1
    return histogram


def collect_segment_candidates(
    segment_histogram: Counter[int],
    linear_target: int,
    *,
    max_candidates: int,
) -> list[SegmentOffsetCandidate]:
    candidates: list[SegmentOffsetCandidate] = []
    for segment_word, frequency in segment_histogram.most_common():
        offset_word = linear_target - segment_word * 16
        if not (0 <= offset_word <= 0xFFFF):
            continue
        candidates.append(
            SegmentOffsetCandidate(
                segment_word=segment_word,
                offset_word=offset_word,
                frequency=frequency,
            )
        )
        if len(candidates) >= max_candidates:
            break
    return candidates


def format_instruction_window(instructions, center_index: int, context: int) -> list[str]:
    start = max(0, center_index - context)
    end = min(len(instructions), center_index + context + 1)
    lines: list[str] = []
    for index in range(start, end):
        instruction = instructions[index]
        marker = ">" if index == center_index else " "
        raw_bytes = instruction.bytes.hex(" ").upper()
        lines.append(
            f"{marker} {instruction.address:05X}: {raw_bytes:<20} {instruction.mnemonic:<8} {instruction.op_str}".rstrip()
        )
    return lines


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path, help="Path to one extracted DOS MZ executable (for example TD.EXE or TPROF.EXE).")
    parser.add_argument(
        "--string",
        action="append",
        default=[],
        dest="needles",
        help="ASCII/CP437 string to search and trace inside the loaded EXE image. Can be repeated.",
    )
    parser.add_argument(
        "--default-help-strings",
        action="store_true",
        help="Add the standard TD/TPROF runtime help strings (tdhelp.tdh, tfhelp.tfh, Index, Previous page, First page, ...).",
    )
    parser.add_argument(
        "--reachable-only",
        action="store_true",
        help="Disassemble only code that is directly reachable from the MZ entry point via direct calls/jumps.",
    )
    parser.add_argument(
        "--image-range-start",
        type=lambda value: int(value, 0),
        help="Optional raw image start offset for a focused linear-sweep disassembly range.",
    )
    parser.add_argument(
        "--image-range-end",
        type=lambda value: int(value, 0),
        help="Optional raw image end offset (one past the last byte) for a focused linear-sweep disassembly range.",
    )
    parser.add_argument(
        "--range-address-base",
        type=lambda value: int(value, 0),
        help="Optional rebased start address to use when disassembling --image-range-start/--image-range-end.",
    )
    parser.add_argument(
        "--dump-instructions",
        action="store_true",
        help="Print the decoded instruction stream from the selected disassembly mode.",
    )
    parser.add_argument(
        "--call-target",
        action="append",
        default=[],
        dest="call_targets",
        type=lambda value: int(value, 0),
        help="Linear image address of a direct call/jump target to trace. Can be repeated.",
    )
    parser.add_argument(
        "--memory-target",
        action="append",
        default=[],
        dest="memory_targets",
        type=lambda value: int(value, 0),
        help="Immediate or displacement value to trace in decoded operands (for example 0x6A79). Can be repeated.",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=3,
        help="Number of instructions to print before and after each candidate xref.",
    )
    parser.add_argument(
        "--max-xrefs",
        type=int,
        default=8,
        help="Maximum number of candidate xrefs to print for each string occurrence.",
    )
    parser.add_argument(
        "--max-segment-candidates",
        type=int,
        default=8,
        help="Maximum number of segment:offset candidates to print when a string sits above 64 KB and no direct xref is found.",
    )
    parser.add_argument(
        "--overlay-table-image-offset",
        type=lambda value: int(value, 0),
        help="Image offset of a 16-byte-per-entry overlay/resource table to dump.",
    )
    parser.add_argument(
        "--overlay-max-entries",
        type=int,
        default=64,
        help="Maximum number of overlay/resource entries to dump when --overlay-table-image-offset is set.",
    )
    parser.add_argument(
        "--overlay-file",
        type=Path,
        help="Optional external file referenced by the overlay table (for example TD.OVL) used to validate relative byte ranges.",
    )
    parser.add_argument(
        "--overlay-stub-region-start",
        type=lambda value: int(value, 0),
        help="Image offset of the first byte in an overlay export-stub region.",
    )
    parser.add_argument(
        "--overlay-stub-region-end",
        type=lambda value: int(value, 0),
        help="Image offset one past the last byte in an overlay export-stub region.",
    )
    parser.add_argument(
        "--overlay-dispatcher-target",
        type=lambda value: int(value, 0),
        help="Optional linear target used to filter overlay export stubs (for example 0x1F6FC for segment:offset 1F67:02BC).",
    )
    parser.add_argument(
        "--overlay-relocations-entry",
        type=int,
        help="1-based overlay table entry index whose 4-byte relocation records should be dumped.",
    )
    parser.add_argument(
        "--overlay-relocations-limit",
        type=int,
        default=16,
        help="Maximum number of relocation records to print when --overlay-relocations-entry is set.",
    )
    parser.add_argument(
        "--overlay-call-summary-entry",
        type=int,
        help="1-based overlay table entry index whose far call/jump targets should be summarized with relocation-normalized segments.",
    )
    parser.add_argument(
        "--overlay-call-summary-limit",
        type=int,
        default=32,
        help="Maximum number of far call/jump records to print when --overlay-call-summary-entry is set.",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    needles = list(args.needles)
    if args.default_help_strings:
        needles.extend(DEFAULT_HELP_STRINGS)
    deduped_needles = tuple(dict.fromkeys(needle for needle in needles if needle))
    if (
        not deduped_needles
        and args.overlay_table_image_offset is None
        and args.overlay_stub_region_start is None
        and args.overlay_stub_region_end is None
        and not args.dump_instructions
        and not args.memory_targets
        and not args.call_targets
    ):
        parser.error("add at least one --string/--memory-target or use --default-help-strings")

    mz = parse_mz_executable(args.executable)

    if (args.image_range_start is None) != (args.image_range_end is None):
        parser.error("provide both --image-range-start and --image-range-end")
    if args.reachable_only and args.image_range_start is not None:
        parser.error("--reachable-only cannot be combined with --image-range-start/--image-range-end")

    disassembly_mode = "reachable-only" if args.reachable_only else "linear-sweep"
    if args.image_range_start is not None and args.image_range_end is not None:
        instructions = disassemble_image_range(
            mz,
            start_image_offset=args.image_range_start,
            end_image_offset=args.image_range_end,
            address_base=args.range_address_base,
        )
        disassembly_mode = f"linear-range 0x{args.image_range_start:05X}-0x{args.image_range_end:05X}"
        if args.range_address_base is not None:
            disassembly_mode += f" rebased-to 0x{args.range_address_base:05X}"
    else:
        instructions = disassemble_reachable_image(mz) if args.reachable_only else disassemble_image(mz)

    print(f"Executable: {mz.path}")
    print(f"Header size: 0x{mz.header_size:04X}")
    print(f"Image size: 0x{len(mz.image):05X}")
    print(f"Entry point: {mz.entry_cs:04X}:{mz.entry_ip:04X} (linear 0x{mz.entry_linear:05X})")
    print(f"Initial stack: {mz.initial_ss:04X}:{mz.initial_sp:04X}")
    print(f"Relocations: {len(mz.relocations)} entries at 0x{mz.relocation_offset:04X}")
    print(f"Disassembly mode: {disassembly_mode}")
    print(f"Disassembled instructions: {len(instructions)}")
    print()

    if args.dump_instructions:
        for instruction in instructions:
            raw_bytes = instruction.bytes.hex(" ").upper()
            print(
                f"{instruction.address:05X}: {raw_bytes:<20} "
                f"{instruction.mnemonic:<8} {instruction.op_str}".rstrip()
            )
        print()

    if args.overlay_table_image_offset is not None:
        overlay_entries = parse_overlay_table_entries(
            mz,
            table_image_offset=args.overlay_table_image_offset,
            max_entries=args.overlay_max_entries,
        )
        if not overlay_entries:
            print(f"Overlay/resource table: no valid entries at image offset 0x{args.overlay_table_image_offset:05X}")
            print()
        else:
            overlay_file_size = None
            if args.overlay_file is not None:
                overlay_file_size = args.overlay_file.stat().st_size

            print(
                "Overlay/resource table: "
                f"start=0x{args.overlay_table_image_offset:05X}, entries={len(overlay_entries)}, "
                f"relative-base-segment=0x{mz.entry_cs:04X}"
            )
            for entry in overlay_entries:
                relative_start, relative_end = entry.relative_file_bounds()
                body_start, body_end = entry.relative_body_bounds()
                summary = (
                    f"  entry {entry.index:02d}: "
                    f"name={entry.file_name!r}, load={entry.load_segment_word:04X}, size={entry.size_word:04X}, "
                    f"flags={entry.flags_word:04X}, reloc={entry.relocation_count:04X}, "
                    f"mem={entry.file_start_segment_word:04X}-{entry.file_end_segment_word:04X}, "
                    f"file-base=0x{entry.file_base_paragraph * 16:05X}, "
                    f"relative=0x{relative_start:05X}-0x{relative_end:05X}, header=0x{entry.header_bytes:04X}"
                )
                if overlay_file_size is not None:
                    in_range = 0 <= relative_start <= relative_end <= overlay_file_size
                    body_bytes = max(body_end - body_start, 0)
                    summary += (
                        f", body=0x{body_bytes:04X}, body-range=0x{body_start:05X}-0x{body_end:05X}, "
                        f"in-range={in_range}"
                    )
                print(summary)
            print()
    else:
        overlay_entries = []

    if (args.overlay_stub_region_start is None) != (args.overlay_stub_region_end is None):
        parser.error("provide both --overlay-stub-region-start and --overlay-stub-region-end")

    if args.overlay_stub_region_start is not None and args.overlay_stub_region_end is not None:
        overlay_stub_records = parse_overlay_stub_records(
            mz,
            start_image_offset=args.overlay_stub_region_start,
            end_image_offset=args.overlay_stub_region_end,
            dispatcher_linear=args.overlay_dispatcher_target,
        )
        if not overlay_stub_records:
            print(
                "Overlay export stubs: no matching records in "
                f"0x{args.overlay_stub_region_start:05X}-0x{args.overlay_stub_region_end:05X}"
            )
            print()
        else:
            print(
                "Overlay export stubs: "
                f"region=0x{args.overlay_stub_region_start:05X}-0x{args.overlay_stub_region_end:05X}, "
                f"records={len(overlay_stub_records)}"
            )
            records_by_index: dict[int, list[OverlayStubRecord]] = defaultdict(list)
            for record in overlay_stub_records:
                records_by_index[record.overlay_index].append(record)
            for overlay_index in sorted(records_by_index):
                group = records_by_index[overlay_index]
                entry_label = ""
                if 1 <= overlay_index <= len(overlay_entries):
                    entry = overlay_entries[overlay_index - 1]
                    entry_label = f" name={entry.file_name!r} mem={entry.file_start_segment_word:04X}-{entry.file_end_segment_word:04X}"
                print(f"  index {overlay_index:02d}: exports={len(group)}{entry_label}")
                for record in group[: args.max_xrefs]:
                    print(
                        "    "
                        f"stub=0x{record.image_offset:05X} dispatcher={record.dispatcher_segment_word:04X}:{record.dispatcher_offset_word:04X} "
                        f"target={record.target_segment_word:04X}:{record.target_offset_word:04X}"
                    )
            print()

    if args.overlay_relocations_entry is not None:
        if not overlay_entries:
            parser.error("--overlay-relocations-entry requires --overlay-table-image-offset")
        if args.overlay_file is None:
            parser.error("--overlay-relocations-entry requires --overlay-file")
        if not (1 <= args.overlay_relocations_entry <= len(overlay_entries)):
            parser.error(
                f"--overlay-relocations-entry must be between 1 and {len(overlay_entries)}"
            )

        relocation_source = args.overlay_file.read_bytes()
        entry = overlay_entries[args.overlay_relocations_entry - 1]
        relative_start, relative_end = entry.relative_file_bounds()
        relocation_records = parse_overlay_relocation_records(entry, source_bytes=relocation_source)
        print(
            "Overlay relocations: "
            f"entry={entry.index:02d} name={entry.file_name!r} load={entry.file_start_segment_word:04X} "
            f"records={len(relocation_records)} file-range=0x{relative_start:05X}-0x{relative_end:05X}"
        )
        if not relocation_records:
            print("  no relocation records decoded")
        for record in relocation_records[: args.overlay_relocations_limit]:
            in_body = entry.header_bytes <= record.relative_patch_offset < (entry.header_bytes + entry.load_size_paragraphs * 16)
            patched_value_word = record.patched_value_word(mz.entry_cs)
            patched_text = "n/a" if patched_value_word is None else f"{patched_value_word:04X}"
            raw_text = "n/a" if record.raw_value_word is None else f"{record.raw_value_word:04X}"
            print(
                "  "
                f"record {record.record_index:03d}: site={record.site_segment_word:04X}:{record.offset_word:04X} "
                f"linear=0x{record.site_linear:05X} relative=0x{record.relative_patch_offset:04X} "
                f"raw={raw_text} patched-static={patched_text} in-body={in_body}"
            )
        print()

    if args.overlay_call_summary_entry is not None:
        if not overlay_entries:
            parser.error("--overlay-call-summary-entry requires --overlay-table-image-offset")
        if args.overlay_file is None:
            parser.error("--overlay-call-summary-entry requires --overlay-file")
        if not (1 <= args.overlay_call_summary_entry <= len(overlay_entries)):
            parser.error(
                f"--overlay-call-summary-entry must be between 1 and {len(overlay_entries)}"
            )

        overlay_bytes = args.overlay_file.read_bytes()
        entry = overlay_entries[args.overlay_call_summary_entry - 1]
        far_call_records = collect_overlay_far_call_records(mz, entry, source_bytes=overlay_bytes)
        print(
            "Overlay far calls: "
            f"entry={entry.index:02d} name={entry.file_name!r} records={len(far_call_records)}"
        )
        if not far_call_records:
            print("  no far call/jump immediates decoded")
        for record in far_call_records[: args.overlay_call_summary_limit]:
            patched_text = "n/a"
            if record.patched_segment_word is not None:
                patched_text = (
                    f"{record.patched_segment_word:04X}:{record.raw_offset_word:04X}"
                    f" linear=0x{record.patched_linear:05X}"
                )
            print(
                "  "
                f"at 0x{record.instruction_address:05X}: {record.mnemonic:<4} "
                f"raw={record.raw_segment_word:04X}:{record.raw_offset_word:04X} linear=0x{record.raw_linear:05X} "
                f"patched={patched_text}"
            )
        print()

    all_offsets: set[int] = set()
    matches_by_needle: dict[str, list[int]] = {}
    for needle in deduped_needles:
        offsets = find_string_offsets(mz.image, needle)
        matches_by_needle[needle] = offsets
        all_offsets.update(offsets)

    references = collect_string_references(instructions, all_offsets)
    far_pointer_references = collect_far_pointer_references(mz, all_offsets)
    direct_target_references = collect_direct_target_references(instructions, set(args.call_targets))
    memory_target_references = collect_operand_value_references(instructions, set(args.memory_targets))
    segment_histogram = build_segment_histogram(mz)

    for needle in deduped_needles:
        offsets = matches_by_needle[needle]
        print(f"String: {needle!r}")
        if not offsets:
            print("  not found in loaded image")
            print()
            continue
        for occurrence_index, offset in enumerate(offsets, start=1):
            file_offset = mz.image_offset + offset
            print(f"  occurrence {occurrence_index}: image=0x{offset:05X}, file=0x{file_offset:05X}")
            far_pointer_hits = far_pointer_references.get(offset, [])
            if far_pointer_hits:
                for ref in far_pointer_hits[: args.max_xrefs]:
                    pointer_file_offset = mz.image_offset + ref.pointer_image_offset
                    print(
                        "    farptr "
                        f"image=0x{ref.pointer_image_offset:05X}, file=0x{pointer_file_offset:05X}, "
                        f"value={ref.segment_word:04X}:{ref.offset_word:04X}"
                    )
            candidate_refs = references.get(offset, [])
            if not candidate_refs:
                if not far_pointer_hits:
                    print("    no immediate/displacement or relocation-backed far-pointer xrefs found")
                    if offset > 0xFFFF:
                        segment_candidates = collect_segment_candidates(
                            segment_histogram,
                            offset,
                            max_candidates=args.max_segment_candidates,
                        )
                        if segment_candidates:
                            print("    segment-normalized candidates from relocated segment words:")
                            for candidate in segment_candidates:
                                print(
                                    "      "
                                    f"{candidate.segment_word:04X}:{candidate.offset_word:04X} "
                                    f"(segment frequency {candidate.frequency})"
                                )
                continue
            for ref in candidate_refs[: args.max_xrefs]:
                print(f"    xref {ref.match_kind} at 0x{ref.instruction_address:05X}")
                for line in format_instruction_window(instructions, ref.instruction_index, args.context):
                    print(f"      {line}")
        print()

    for target in args.call_targets:
        print(f"Direct target: 0x{target:05X}")
        target_refs = direct_target_references.get(target, [])
        if not target_refs:
            print("  no direct reachable call/jump xrefs found")
            print()
            continue
        for ref in target_refs[: args.max_xrefs]:
            print(f"  xref {ref.match_kind} at 0x{ref.instruction_address:05X}")
            for line in format_instruction_window(instructions, ref.instruction_index, args.context):
                print(f"    {line}")
        print()

    for target in args.memory_targets:
        print(f"Memory target: 0x{target:04X}")
        target_refs = memory_target_references.get(target, [])
        if not target_refs:
            print("  no immediate/displacement xrefs found")
            print()
            continue
        for ref in target_refs[: args.max_xrefs]:
            print(f"  xref {ref.match_kind} at 0x{ref.instruction_address:05X}")
            for line in format_instruction_window(instructions, ref.instruction_index, args.context):
                print(f"    {line}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())