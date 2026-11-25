# SPDX-License-Identifier: Apache-2.0
from random import Random

import cocotb
from cocotb.triggers import Timer

DONE = 1 << 4
READY = 1 << 5


def drive(dut, channels=0, arm=0, address=0, uio=None):
    dut.ui_in.value = ((address & 7) << 5) | (arm << 4) | channels
    dut.uio_in.value = address >> 3 if uio is None else uio


async def tick(dut, **inputs):
    dut.clk.value = 0
    drive(dut, **inputs)
    await Timer(20, unit="ns")
    dut.clk.value = 1
    await Timer(20, unit="ns")
    return int(dut.uo_out.value)


async def reset(dut):
    dut.ena.value = 1
    dut.rst_n.value = 0
    assert await tick(dut) == 0
    dut.rst_n.value = 1
    assert int(dut.uio_oe.value) == 0
    assert int(dut.uio_out.value) == 0


async def arm_capture(dut, mask, value, channels=0):
    assert await tick(dut, channels=channels, arm=1, uio=(mask << 4) | value) == 0


async def read_capture(dut, expected):
    dut.clk.value = 0
    for address in reversed(range(32)):
        drive(dut, address=address)
        await Timer(20, unit="ns")
        assert int(dut.uo_out.value) == DONE | expected[address], f"Address {address}"


@cocotb.test()
async def test_patterns_and_wraparound(dut):
    """Exercise every nonzero mask/value pair and every physical trigger address."""
    await reset(dut)
    rng = Random(32)
    for mask in range(1, 16):
        for value in range(16):
            matching = [s for s in range(16) if s & mask == value & mask]
            outside = [s for s in range(16) if s not in matching]
            await arm_capture(dut, mask, value)
            history = []
            # Sweep contiguous trigger addresses with multiple revolutions of the buffer.
            length = 16 + (((mask - 1) * 16 + value) % 80)
            for index in range(length):
                sample = rng.randrange(16) if index < 15 else rng.choice(outside)
                history.append(sample)
                # Toggle configuration pins and pulse ARM while waiting.
                status = await tick(dut, channels=sample, arm=int(index == 8), uio=rng.randrange(256))
                assert status == (READY if index >= 15 else 0), (mask, value, index)
            trigger = rng.choice(matching)
            assert await tick(dut, channels=trigger) == 0
            post = [rng.randrange(16) for _ in range(15)]
            for index, sample in enumerate(post):
                status = await tick(dut, channels=sample, arm=1, address=16)
                assert status == (DONE | trigger if index == 14 else 0)
            assert await tick(dut, arm=1, address=31) == DONE | post[-1]
            await read_capture(dut, history[-16:] + [trigger] + post)
            assert await tick(dut) == DONE | history[-16]


@cocotb.test()
async def test_masked_edge_and_reset(dut):
    await reset(dut)
    # An all-zero mask never triggers, even after more than two full wraps.
    await arm_capture(dut, 0, 15)
    for i in range(80):
        assert await tick(dut, channels=i % 16) == (READY if i >= 15 else 0)
    await reset(dut)

    # Hold selected bits at 01 from ARM through prefill. Unselected bits toggle.
    await arm_capture(dut, 0b0101, 0b0001, channels=1)
    for i in range(32):
        assert await tick(dut, channels=1 | ((i << 1) & 0b1010)) == (READY if i >= 15 else 0)
    assert await tick(dut, channels=5) == READY
    assert await tick(dut, channels=1) == 0
    for _ in range(14):
        assert await tick(dut) == 0
    await reset(dut)  # abort just before DONE
    for i in range(32):
        assert await tick(dut, channels=i % 16) == 0

    # Re-arm, capture on the first eligible edge and reset a frozen record.
    await arm_capture(dut, 1, 0)
    for i in range(16):
        assert await tick(dut, channels=3) == (READY if i == 15 else 0)
    assert await tick(dut, channels=2) == 0
    for i in range(15):
        assert await tick(dut, channels=i, address=31) == (DONE | 14 if i == 14 else 0)
    await read_capture(dut, [3] * 16 + [2] + list(range(15)))
    dut.rst_n.value = 0
    await Timer(20, unit="ns")
    assert int(dut.uo_out.value) == DONE | 3
    assert await tick(dut) == 0
