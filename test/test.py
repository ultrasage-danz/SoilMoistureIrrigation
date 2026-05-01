# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

PUMP_BIT         = 0
INVALID_FLAG_BIT = 1

def pump(dut):
    return (dut.uo_out.value.to_unsigned() >> PUMP_BIT) & 1

def invalid_flag(dut):
    return (dut.uo_out.value.to_unsigned() >> INVALID_FLAG_BIT) & 1

async def do_reset(dut, ui_in_val=0b00000001):
    cocotb.start_soon(Clock(dut.clk, 10, unit="us").start())
    dut.ena.value    = 1
    dut.uio_in.value = 0
    dut.ui_in.value  = ui_in_val
    dut.rst_n.value  = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value  = 1
    await ClockCycles(dut.clk, 1)

@cocotb.test()
async def test_reset_to_idle(dut):
    """After reset, pump should be off and no invalid flag."""
    await do_reset(dut, ui_in_val=0b00000001)
    assert pump(dut) == 0,         f"Pump should be OFF in IDLE, got {pump(dut)}"
    assert invalid_flag(dut) == 0, f"Invalid flag should be 0 in IDLE, got {invalid_flag(dut)}"
    dut._log.info("PASS: reset_to_idle")

@cocotb.test()
async def test_dry_soil_triggers_pump(dut):
    """Dry soil (comp=00) should turn pump ON."""
    await do_reset(dut, ui_in_val=0b00000001)
    dut.ui_in.value = 0b00000000
    await ClockCycles(dut.clk, 1)
    assert pump(dut) == 1,         f"Pump should be ON for dry soil, got {pump(dut)}"
    assert invalid_flag(dut) == 0, f"Invalid flag should be 0, got {invalid_flag(dut)}"
    dut._log.info("PASS: dry_soil_triggers_pump")

@cocotb.test()
async def test_wet_soil_pump_off(dut):
    """Wet soil (comp=11) should keep pump OFF."""
    await do_reset(dut, ui_in_val=0b00000001)
    dut.ui_in.value = 0b00000011
    await ClockCycles(dut.clk, 1)
    assert pump(dut) == 0,         f"Pump should be OFF for wet soil, got {pump(dut)}"
    assert invalid_flag(dut) == 0, f"Invalid flag should be 0, got {invalid_flag(dut)}"
    dut._log.info("PASS: wet_soil_pump_off")

@cocotb.test()
async def test_invalid_state(dut):
    """Invalid comparator reading (comp=10) should set invalid_flag."""
    await do_reset(dut, ui_in_val=0b00000001)
    dut.ui_in.value = 0b00000010
    await ClockCycles(dut.clk, 1)
    assert pump(dut) == 0,         "Pump must be OFF in INVALID state"
    assert invalid_flag(dut) == 1, f"Invalid flag should be 1, got {invalid_flag(dut)}"
    dut._log.info("PASS: invalid_state")

@cocotb.test()
async def test_irrigate_to_idle_on_mild(dut):
    """Once irrigating, mild moisture should return to IDLE."""
    await do_reset(dut, ui_in_val=0b00000001)
    dut.ui_in.value = 0b00000000
    await ClockCycles(dut.clk, 1)
    assert pump(dut) == 1, "Should be pumping"
    dut.ui_in.value = 0b00000001
    await ClockCycles(dut.clk, 1)
    assert pump(dut) == 0,         "Pump should be OFF after reaching MILD"
    assert invalid_flag(dut) == 0, "No invalid flag after returning to IDLE"
    dut._log.info("PASS: irrigate_to_idle_on_mild")
