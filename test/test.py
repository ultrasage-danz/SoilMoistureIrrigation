# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

# Output bit positions
PUMP_BIT         = 0
INVALID_FLAG_BIT = 1

# Moisture input encoding on ui_in[1:0]
DRY      = 0b00   # comp1=0, comp0=0 → irrigate
MILD     = 0b01   # comp1=0, comp0=1 → idle
WET      = 0b11   # comp1=1, comp0=1 → saturated
INVALID  = 0b10   # comp1=1, comp0=0 → invalid

async def reset_dut(dut):
    dut.rst_n.value  = 0
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value  = 1
    await ClockCycles(dut.clk, 1)

def pump(dut):
    return (dut.uo_out.value.integer >> PUMP_BIT) & 1

def invalid_flag(dut):
    return (dut.uo_out.value.integer >> INVALID_FLAG_BIT) & 1

@cocotb.test()
async def test_reset_to_idle(dut):
    """After reset, pump should be off and no invalid flag."""
    cocotb.start_soon(Clock(dut.clk, 10, units="us").start())
    await reset_dut(dut)
    dut.ui_in.value = MILD
    await ClockCycles(dut.clk, 1)
    assert pump(dut) == 0,         f"Pump should be OFF in IDLE, got {pump(dut)}"
    assert invalid_flag(dut) == 0, f"Invalid flag should be 0 in IDLE"
    dut._log.info("PASS: reset_to_idle")

@cocotb.test()
async def test_dry_soil_triggers_pump(dut):
    """Dry soil (comp=00) should turn pump ON."""
    cocotb.start_soon(Clock(dut.clk, 10, units="us").start())
    await reset_dut(dut)
    dut.ui_in.value = DRY
    await ClockCycles(dut.clk, 2)
    assert pump(dut) == 1,         f"Pump should be ON for dry soil, got {pump(dut)}"
    assert invalid_flag(dut) == 0, "No invalid flag expected"
    dut._log.info("PASS: dry_soil_triggers_pump")

@cocotb.test()
async def test_wet_soil_pump_off(dut):
    """Wet soil (comp=11) should keep pump OFF."""
    cocotb.start_soon(Clock(dut.clk, 10, units="us").start())
    await reset_dut(dut)
    dut.ui_in.value = WET
    await ClockCycles(dut.clk, 2)
    assert pump(dut) == 0,         f"Pump should be OFF for wet soil"
    assert invalid_flag(dut) == 0, "No invalid flag expected"
    dut._log.info("PASS: wet_soil_pump_off")

@cocotb.test()
async def test_invalid_state(dut):
    """Invalid comparator reading (comp=10) should set invalid_flag."""
    cocotb.start_soon(Clock(dut.clk, 10, units="us").start())
    await reset_dut(dut)
    dut.ui_in.value = INVALID
    await ClockCycles(dut.clk, 2)
    assert pump(dut) == 0,         "Pump must be OFF in INVALID state"
    assert invalid_flag(dut) == 1, f"Invalid flag should be 1, got {invalid_flag(dut)}"
    dut._log.info("PASS: invalid_state")

@cocotb.test()
async def test_irrigate_to_idle_on_mild(dut):
    """Once irrigating, mild moisture should return to IDLE."""
    cocotb.start_soon(Clock(dut.clk, 10, units="us").start())
    await reset_dut(dut)
    # Start dry — enter IRRIGATE
    dut.ui_in.value = DRY
    await ClockCycles(dut.clk, 2)
    assert pump(dut) == 1, "Should be pumping"
    # Soil reaches mild — should go IDLE
    dut.ui_in.value = MILD
    await ClockCycles(dut.clk, 2)
    assert pump(dut) == 0, "Pump should turn OFF when mild"
    dut._log.info("PASS: irrigate_to_idle_on_mild")