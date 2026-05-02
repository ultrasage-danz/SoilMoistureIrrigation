# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer, ReadOnly

PUMP_BIT         = 0
INVALID_FLAG_BIT = 1

def pump(dut):
    return (dut.uo_out.value.to_unsigned() >> PUMP_BIT) & 1

def invalid_flag(dut):
    return (dut.uo_out.value.to_unsigned() >> INVALID_FLAG_BIT) & 1

async def do_reset(dut, ui_in_val=0b00000001):
    cocotb.start_soon(Clock(dut.clk, 10, unit="us").start())
    dut.ena.value   = 1
    dut.uio_in.value = 0
    dut.ui_in.value = ui_in_val
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

async def settle_after_clock(dut, cycles=1, delay_ns=1):
    """
    Gate-level sims add propagation delay, so outputs may not be stable
    immediately after a clock edge. Wait a small amount of time, then sample
    during the ReadOnly phase to avoid race conditions.
    """
    await ClockCycles(dut.clk, cycles)
    await Timer(delay_ns, "ns")
    await ReadOnly()

@cocotb.test()
async def test_reset_to_idle(dut):
    """After reset, pump should be off and no invalid flag."""
    await do_reset(dut, ui_in_val=0b00000001)
    await settle_after_clock(dut, cycles=0)   # sample immediately after reset — no extra cycles needed
    assert pump(dut) == 0,         f"Pump should be OFF in IDLE, got {pump(dut)}"
    assert invalid_flag(dut) == 0, f"Invalid flag should be 0 in IDLE, got {invalid_flag(dut)}"
    dut._log.info("PASS: reset_to_idle")

@cocotb.test()
async def test_dry_soil_triggers_pump(dut):
    """Dry soil (comp=00) should turn pump ON."""
    await do_reset(dut, ui_in_val=0b00000001)
    dut.ui_in.value = 0b00000000
    # FIX: cycles=1 only computed next_state; need cycles=2 to latch IRRIGATE
    await settle_after_clock(dut, cycles=2)
    assert pump(dut) == 1,         f"Pump should be ON for dry soil, got {pump(dut)}"
    assert invalid_flag(dut) == 0, f"Invalid flag should be 0, got {invalid_flag(dut)}"
    dut._log.info("PASS: dry_soil_triggers_pump")

@cocotb.test()
async def test_wet_soil_pump_off(dut):
    """Wet soil (comp=11) should keep pump OFF."""
    await do_reset(dut, ui_in_val=0b00000001)
    dut.ui_in.value = 0b00000011
    # cycles=1 happens to pass because IDLE->SATURATED also has pump=0,
    # but use cycles=2 for consistency so this tests the latched state
    await settle_after_clock(dut, cycles=2)
    assert pump(dut) == 0,         f"Pump should be OFF for wet soil, got {pump(dut)}"
    assert invalid_flag(dut) == 0, f"Invalid flag should be 0, got {invalid_flag(dut)}"
    dut._log.info("PASS: wet_soil_pump_off")

@cocotb.test()
async def test_invalid_state(dut):
    """Invalid comparator reading (comp=10) should set invalid_flag."""
    await do_reset(dut, ui_in_val=0b00000001)
    dut.ui_in.value = 0b00000010
    # FIX: cycles=1 only computed next_state=INVALID; need cycles=2 to latch it
    await settle_after_clock(dut, cycles=2)
    assert pump(dut) == 0,         "Pump must be OFF in INVALID state"
    assert invalid_flag(dut) == 1, f"Invalid flag should be 1, got {invalid_flag(dut)}"
    dut._log.info("PASS: invalid_state")

@cocotb.test()
async def test_irrigate_to_idle_on_mild(dut):
    """Once irrigating, mild moisture should return to IDLE."""
    await do_reset(dut, ui_in_val=0b00000001)

    # Step 1: drive dry soil and wait for IRRIGATE to latch
    dut.ui_in.value = 0b00000000
    # FIX: cycles=1 only computed next_state=IRRIGATE; need cycles=2 to latch it
    await settle_after_clock(dut, cycles=2)
    assert pump(dut) == 1, "Should be pumping"

    # Step 2: drive mild soil and wait for IDLE to latch
    dut.ui_in.value = 0b00000001
    # FIX: same — need 2 cycles so IRRIGATE->IDLE transition latches
    await settle_after_clock(dut, cycles=2)
    assert pump(dut) == 0,         "Pump should be OFF after reaching MILD"
    assert invalid_flag(dut) == 0, "No invalid flag after returning to IDLE"
    dut._log.info("PASS: irrigate_to_idle_on_mild")
