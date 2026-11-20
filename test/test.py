# SPDX-License-Identifier: Apache-2.0

from random import Random

import cocotb
from cocotb.triggers import Timer

DONE = 1 << 4
READY = 1 << 5


def drive_inputs(dut, channels=0, arm=0, address=0, falling=0):
    dut.ui_in.value = ((address & 7) << 5) | (arm << 4) | channels
    dut.uio_in.value = (falling << 1) | (address >> 3)


async def tick(dut, **inputs):
    dut.clk.value = 0
    drive_inputs(dut, **inputs)
    await Timer(20, unit="ns")
    dut.clk.value = 1
    await Timer(20, unit="ns")
    return int(dut.uo_out.value)


async def reset(dut):
    dut.ena.value = 1
    dut.rst_n.value = 0
    assert await tick(dut) == 0
    dut.rst_n.value = 1
    await Timer(20, unit="ns")
    assert int(dut.uio_oe.value) == 0
    assert int(dut.uio_out.value) == 0


async def read_capture(dut, expected):
    dut.clk.value = 0
    # Read addresses in reverse order without clocking the capture engine.
    for address in range(15, -1, -1):
        drive_inputs(dut, address=address)
        await Timer(20, unit="ns")
        assert int(dut.uo_out.value) == (DONE | expected[address]), (
            f"Wrong sample at address {address}, expected {expected[address]:x}"
        )


@cocotb.test()
async def test_both_edges_at_every_ring_address(dut):
    await reset(dut)
    rng = Random(16)

    for falling in (0, 1):
        # Offsets 8 through 23 cover every trigger write address modulo 16.
        for history_length in range(8, 24):
            assert await tick(dut, arm=1, falling=falling) == 0
            history = []
            for index in range(history_length):
                # During prefill, deliberately present qualifying edges. After
                # prefill, hold CH0 opposite the requested trigger level.
                ch0 = (index % 2) ^ falling if index < 7 else falling
                sample = (rng.randrange(8) << 1) | ch0
                history.append(sample)
                status = await tick(dut, channels=sample, falling=1 - falling)
                assert status == (READY if index >= 7 else 0)

            trigger_sample = (rng.randrange(8) << 1) | (1 - falling)
            assert await tick(dut, channels=trigger_sample, falling=1 - falling) == 0
            post = [rng.randrange(16) for _ in range(7)]
            expected = history[-8:] + [trigger_sample] + post
            for index, sample in enumerate(post, start=1):
                # ARM during capture must be ignored, even when held into DONE.
                status = await tick(dut, channels=sample, arm=1, address=8)
                assert status == ((DONE | trigger_sample) if index == 7 else 0)
            assert await tick(dut, channels=0xF, arm=1, address=15) == (DONE | post[-1])
            await read_capture(dut, expected)
            assert await tick(dut) == (DONE | expected[0])


@cocotb.test()
async def test_reset_and_first_eligible_edge(dut):
    await reset(dut)
    for _ in range(2):
        assert await tick(dut, channels=1) == 0
        assert await tick(dut, channels=0) == 0

    # CH0 rises with ARM and stays high through prefill. A high level alone
    # does not trigger once the eight preceding samples become valid.
    assert await tick(dut, channels=1, arm=1) == 0
    for index in range(8):
        assert await tick(dut, channels=1, arm=1) == (READY if index == 7 else 0)
    assert await tick(dut, channels=1) == READY
    assert await tick(dut, channels=0) == READY
    assert await tick(dut, channels=1) == 0

    # Synchronous reset aborts the partial capture.
    await reset(dut)
    for index in range(16):
        assert await tick(dut, channels=index) == 0

    assert await tick(dut, arm=1) == 0
    expected = [0x0, 0x2, 0x4, 0x6, 0x8, 0xA, 0xC, 0xE,
                0xF, 0xA, 0x3, 0x1, 0x8, 0x5, 0xC, 0x2]
    for index, sample in enumerate(expected):
        status = await tick(dut, channels=sample, address=15)
        expected_status = {7: READY, 15: DONE | expected[15]}.get(index, 0)
        assert status == expected_status
    await read_capture(dut, expected)

    dut.rst_n.value = 0
    await Timer(20, unit="ns")
    assert int(dut.uo_out.value) == (DONE | expected[0])
    assert await tick(dut) == 0
