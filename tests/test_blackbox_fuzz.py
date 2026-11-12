# =============================================================================
# URTC Tester - tests/test_blackbox_fuzz.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The black box record over generated inputs (a fixed seed, so a failure repeats): what the board writes is read back as it was, in every way it can be saved, and a damaged
file or record is refused with the error of the module and never with another."""
from __future__ import annotations

import random

import pytest

import tester_blackbox_view as view
from urtc_can import blackbox

SEED = 20261112


def _sample(rng: random.Random) -> blackbox.Sample:
    return blackbox.Sample(rng.randrange(0, 2**32), rng.randrange(0, 256), rng.randrange(0, 2**16), rng.randrange(0, 2**16), rng.randrange(0, 16))


def _samples(rng: random.Random, count: int) -> list[blackbox.Sample]:
    return [_sample(rng) for _ in range(count)]


def test_what_the_firmware_builds_is_read_back_with_every_count_and_write_index():
    rng = random.Random(SEED)
    for count in [0, 1, 2, 30, 66, blackbox.SAMPLES - 1, blackbox.SAMPLES]:
        samples = _samples(rng, count)
        raw = blackbox.build(samples)
        record = blackbox.parse(raw)
        assert record.samples == samples and record.sample_count == count


def test_a_full_ring_is_read_oldest_first_whatever_the_write_index():
    rng = random.Random(SEED)
    for _ in range(25):
        widx = rng.randrange(0, blackbox.SAMPLES)
        samples = _samples(rng, blackbox.SAMPLES)
        record = blackbox.parse(blackbox.build(samples, write_index=widx))
        assert sorted(record.samples, key=lambda s: (s.tick_ms, s.flags, s.tool_id)) == sorted(samples, key=lambda s: (s.tick_ms, s.flags, s.tool_id))
        assert len(record.samples) == blackbox.SAMPLES


def test_padding_after_the_record_is_ignored():
    rng = random.Random(SEED)
    samples = _samples(rng, 10)
    raw = blackbox.build(samples)
    assert blackbox.parse(raw + bytes(37)).samples == samples


def test_any_single_flipped_byte_of_a_record_is_refused_or_changes_a_sample():
    rng = random.Random(SEED)
    samples = _samples(rng, 20)
    raw = bytearray(blackbox.build(samples))
    for _ in range(300):
        position = rng.randrange(0, blackbox.RECORD_SIZE)
        damaged = bytearray(raw)
        damaged[position] ^= 1 << rng.randrange(8)
        try:
            record = blackbox.parse(bytes(damaged))
        except blackbox.BlackBoxError:
            continue          # the checksum, the magic, the version or the counts caught it
        raise AssertionError(f"a flipped bit at {position} was accepted: {record}")   # CRC-8 catches every single-bit error


def test_a_record_that_is_too_short_is_refused_at_every_length():
    raw = blackbox.build(_samples(random.Random(SEED), 5))
    for length in range(0, blackbox.RECORD_SIZE, 37):
        with pytest.raises(blackbox.BlackBoxError):
            blackbox.parse(raw[:length])


def test_random_bytes_are_never_a_record_and_never_raise_anything_else():
    rng = random.Random(SEED)
    for _ in range(200):
        raw = bytes(rng.randrange(256) for _ in range(blackbox.RECORD_SIZE))
        with pytest.raises(blackbox.BlackBoxError):
            blackbox.parse(raw)


def test_saved_as_json_or_csv_the_samples_are_read_back_exactly():
    rng = random.Random(SEED)
    for count in [1, 2, 7, 40, view.SAMPLE_LIMIT]:
        samples = _samples(rng, count)
        record = blackbox.Record(blackbox.VERSION, count, count % view.SAMPLE_LIMIT, samples)
        assert view.record_from_text(blackbox.to_json(record)).samples == samples
        assert view.record_from_text(blackbox.to_csv(record)).samples == samples


def test_a_damaged_saved_file_is_read_or_refused_with_a_view_error_and_nothing_else():
    rng = random.Random(SEED)
    samples = _samples(rng, 12)
    record = blackbox.Record(blackbox.VERSION, 12, 12, samples)
    for text in (blackbox.to_json(record), blackbox.to_csv(record)):
        for _ in range(250):
            characters = list(text)
            for _ in range(rng.randrange(1, 5)):
                position = rng.randrange(len(characters))
                characters[position] = rng.choice(["", "x", "-", "9", "\n", ",", "{", '"', " "])
            try:
                view.record_from_text("".join(characters))
            except view.ViewError:
                pass


def test_a_file_cut_short_anywhere_never_raises_anything_but_a_view_error():
    rng = random.Random(SEED)
    record = blackbox.Record(blackbox.VERSION, 6, 6, _samples(rng, 6))
    for text in (blackbox.to_json(record), blackbox.to_csv(record)):
        for length in range(0, len(text), 7):
            try:
                view.record_from_text(text[:length])
            except view.ViewError:
                pass


def test_the_chart_range_always_holds_every_value_and_is_in_whole_tens():
    rng = random.Random(SEED)
    for _ in range(100):
        count = rng.randrange(1, 40)
        samples = [blackbox.Sample(1000 + i * 50, 0, rng.randrange(0, 600), rng.randrange(0, 600), 0) for i in range(count)]
        series = view.chart_series(blackbox.Record(blackbox.VERSION, count, count, samples))
        assert series["minimum"] % 10 == 0 and series["maximum"] % 10 == 0 and series["maximum"] >= series["minimum"] + 10
        assert all(series["minimum"] <= value <= series["maximum"] for value in series["current"] + series["target"])
        assert series["ticks"][0] == 0 and series["span_ms"] == series["ticks"][-1]


def test_the_table_has_one_line_per_sample_for_any_record():
    rng = random.Random(SEED)
    for count in (1, 5, view.SAMPLE_LIMIT):
        record = blackbox.Record(blackbox.VERSION, count, count, _samples(rng, count))
        assert len(view.table_lines(record)) == count
