from __future__ import annotations

import pytest

from app.parser.sysmon_parser import SysMonParser


# ---------------------------------------------------------------------------
# Regex pattern tests
# ---------------------------------------------------------------------------

SNAPSHOT_MATCH_CASES = [
    "= Test Time: 1, 2025-01-15 08:30:00 ====",
    "= Test Time: 42, 2025-12-31 23:59:59 =",
    "= Test Time: 0, 2024-06-01 00:00:00 ===========================",
]

SNAPSHOT_NO_MATCH_CASES = [
    "Test Time: 1, 2025-01-15 08:30:00",
    "= Test Time: abc, 2025-01-15 08:30:00 =",
    "= Test Time: 1, 2025-1-15 08:30:00 =",
    "",
    "= Test Time: 1, 2025-01-15 =",
]


@pytest.mark.parametrize("line", SNAPSHOT_MATCH_CASES)
def test_snapshot_re_match(line: str) -> None:
    assert SysMonParser.SNAPSHOT_RE.match(line) is not None


@pytest.mark.parametrize("line", SNAPSHOT_NO_MATCH_CASES)
def test_snapshot_re_no_match(line: str) -> None:
    assert SysMonParser.SNAPSHOT_RE.match(line) is None


def test_snapshot_re_captures_fields() -> None:
    m = SysMonParser.SNAPSHOT_RE.match("= Test Time: 7, 2025-03-10 12:00:00 ===")
    assert m is not None
    assert m.group(1) == "7"
    assert m.group(2) == "2025-03-10 12:00:00"


CPU_MATCH_CASES = [
    "CPU0:  5.2% usr  1.1% sys  0.0% nic 93.5% idle  0.0% io  0.0% irq  0.0%% sirq",
    "CPU1:  0.0% usr  0.0% sys  0.0% nic 100.0% idle  0.0% io  0.0% irq  0.0%% sirq",
    "CPU3: 10.5% usr  2.3% sys  0.1% nic 87.1% idle  0.0% io  0.0% irq  0.0%% sirq",
]

CPU_NO_MATCH_CASES = [
    "cpu0:  5.2% usr  1.1% sys  0.0% nic 93.5% idle  0.0% io  0.0% irq  0.0%% sirq",
    "CPU0:  usr  sys  nic idle io irq sirq",
    "Mem: 256K used, 512K free, 128K shrd, 64K buff, 200K cached",
    "",
]


@pytest.mark.parametrize("line", CPU_MATCH_CASES)
def test_cpu_re_match(line: str) -> None:
    assert SysMonParser.CPU_RE.match(line) is not None


@pytest.mark.parametrize("line", CPU_NO_MATCH_CASES)
def test_cpu_re_no_match(line: str) -> None:
    assert SysMonParser.CPU_RE.match(line) is None


def test_cpu_re_captures_fields() -> None:
    line = "CPU0:  5.2% usr  1.1% sys  0.0% nic 93.5% idle  0.0% io  0.2% irq  0.0%% sirq"
    m = SysMonParser.CPU_RE.match(line)
    assert m is not None
    assert m.group(1) == "0"
    assert float(m.group(2)) == pytest.approx(5.2)
    assert float(m.group(5)) == pytest.approx(93.5)  # idle


MEM_MATCH_CASES = [
    "Mem: 256K used, 512K free, 128K shrd, 64K buff, 200K cached",
    "Mem: 0K used, 1024K free",
    "Mem: 131072K used, 65536K free, trailing stuff here",
]

MEM_NO_MATCH_CASES = [
    "mem: 256K used, 512K free",
    "Mem: used, free",
    "Memory: 256K used, 512K free",
    "",
]


@pytest.mark.parametrize("line", MEM_MATCH_CASES)
def test_mem_re_match(line: str) -> None:
    assert SysMonParser.MEM_RE.match(line) is not None


@pytest.mark.parametrize("line", MEM_NO_MATCH_CASES)
def test_mem_re_no_match(line: str) -> None:
    assert SysMonParser.MEM_RE.match(line) is None


def test_mem_re_captures_fields() -> None:
    m = SysMonParser.MEM_RE.match("Mem: 131072K used, 65536K free, extras")
    assert m is not None
    assert int(m.group(1)) == 131072
    assert int(m.group(2)) == 65536


# ---------------------------------------------------------------------------
# SysMonParser.feed() integration tests
# ---------------------------------------------------------------------------

def _make_parser() -> tuple[SysMonParser, list[dict]]:
    events: list[dict] = []
    parser = SysMonParser(on_event=events.append)
    return parser, events


def test_feed_snapshot_header_starts_snapshot() -> None:
    parser, events = _make_parser()
    parser.feed("= Test Time: 1, 2025-01-15 08:30:00 ===\n")
    # snapshot header alone doesn't emit snapshot_update yet
    cpu_line = "CPU0:  5.0% usr  1.0% sys  0.0% nic 94.0% idle  0.0% io  0.0% irq  0.0%% sirq\n"
    parser.feed(cpu_line)
    snapshot_events = [e for e in events if e["type"] == "snapshot_update"]
    assert len(snapshot_events) >= 1
    snap = snapshot_events[-1]["snapshot"]
    assert snap["test_count"] == 1
    assert snap["device_ts"] == "2025-01-15 08:30:00"
    assert "0" in snap["cpu"]
    assert snap["cpu"]["0"]["usr"] == pytest.approx(5.0)


def test_feed_mem_emits_memory_update() -> None:
    parser, events = _make_parser()
    parser.feed("= Test Time: 1, 2025-01-15 08:30:00 ===\n")
    parser.feed("Mem: 200K used, 824K free, 0K shrd\n")
    mem_events = [e for e in events if e["type"] == "memory_update"]
    assert len(mem_events) == 1
    assert mem_events[0]["used_kb"] == 200
    assert mem_events[0]["free_kb"] == 824
    assert mem_events[0]["total_kb"] == 1024


def test_feed_non_matching_line_emits_console_batch() -> None:
    parser, events = _make_parser()
    for _ in range(20):
        parser.feed("some random log line\n")
    console_events = [e for e in events if e["type"] == "console_line_batch"]
    assert len(console_events) >= 1
    all_lines = [l for e in console_events for l in e["lines"]]
    assert all(line == "some random log line" for line in all_lines)


def test_feed_two_snapshots_emit_separate_updates() -> None:
    parser, events = _make_parser()
    for ts, count in [("2025-01-01 00:00:00", 1), ("2025-01-01 00:01:00", 2)]:
        parser.feed(f"= Test Time: {count}, {ts} ===\n")
        parser.feed(
            f"CPU0:  {count}.0% usr  0.0% sys  0.0% nic {100 - count}.0% idle  0.0% io  0.0% irq  0.0%% sirq\n"
        )
    parser.flush()
    snapshot_events = [e for e in events if e["type"] == "snapshot_update"]
    assert len(snapshot_events) >= 2
    counts = [e["snapshot"]["test_count"] for e in snapshot_events]
    assert 1 in counts
    assert 2 in counts
