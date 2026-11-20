# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.triggers import Timer

DONE = 1 << 4
DEMO_SAMPLES = (0x1, 0x2, 0x6, 0x4, 0xF, 0x8, 0xA, 0x3)


def inputs(channels=0, arm=0, address=0):
    return (address << 5) | (arm << 4) | channels


async def tick(dut, channels=0, arm=0, address=0):
    dut.clk.value = 0
    dut.ui_in.value = inputs(channels, arm, address)
    await Timer(20, unit="ns")
    dut.clk.value = 1
    await Timer(20, unit="ns")
    return int(dut.uo_out.value)


async def reset(dut):
    dut.ena.value = 1
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    assert await tick(dut) == 0
    dut.rst_n.value = 1
    await Timer(20, unit="ns")
    assert int(dut.uio_oe.value) == 0
    assert int(dut.uio_out.value) == 0


async def read_capture(dut, expected):
    dut.clk.value = 0
    for address, sample in reversed(list(enumerate(expected))):
        dut.ui_in.value = inputs(address=address)
        await Timer(20, unit="ns")
        assert int(dut.uo_out.value) == (DONE | sample), f"Wrong sample at address {address}"


@cocotb.test()
async def test_trigger_capture_and_rearm(dut):
    await reset(dut)

    # A rise on the same edge as ARM does not start the recording.
    assert await tick(dut, channels=0x1, arm=1) == 0
    for _ in range(3):
        assert await tick(dut, channels=0xF, arm=1) == 0

    assert await tick(dut, channels=0x8, arm=1) == 0
    for address, sample in enumerate(DEMO_SAMPLES):
        # A second ARM edge while capturing must be ignored.
        arm = int(address != 1)
        status = await tick(dut, channels=sample, arm=arm, address=0)
        expected = (DONE | DEMO_SAMPLES[0]) if address == 7 else 0
        assert status == expected, f"Unexpected output after capturing sample {address}"

    # Continued clocks and a held ARM must not overwrite the record.
    for channels in (0xF, 0x0, 0xF):
        assert await tick(dut, channels=channels, arm=1) == (DONE | DEMO_SAMPLES[0])
    await read_capture(dut, DEMO_SAMPLES)

    assert await tick(dut, channels=0, arm=0) == (DONE | DEMO_SAMPLES[0])
    assert await tick(dut, channels=0, arm=1) == 0

    next_samples = (0x9, 0xA, 0xC, 0x0, 0x4, 0x6, 0xE, 0xD)
    for address, sample in enumerate(next_samples):
        status = await tick(dut, channels=sample)
        assert status == ((DONE | next_samples[0]) if address == 7 else 0)
    await read_capture(dut, next_samples)


@cocotb.test()
async def test_reset_aborts_partial_capture(dut):
    await reset(dut)
    assert await tick(dut, arm=1) == 0
    assert await tick(dut, channels=0x1) == 0
    assert await tick(dut, channels=0x2) == 0

    await reset(dut)
    for _ in range(8):
        assert await tick(dut, channels=0x1) == 0
        assert await tick(dut, channels=0x0) == 0

    assert await tick(dut, arm=1) == 0
    for address, sample in enumerate(DEMO_SAMPLES):
        status = await tick(dut, channels=sample, address=7)
        assert status == ((DONE | DEMO_SAMPLES[7]) if address == 7 else 0)

    # An asserted reset has no effect on the frozen output before a rising edge.
    dut.clk.value = 0
    dut.rst_n.value = 0
    await Timer(20, unit="ns")
    assert int(dut.uo_out.value) == (DONE | DEMO_SAMPLES[7])
    assert await tick(dut) == 0
