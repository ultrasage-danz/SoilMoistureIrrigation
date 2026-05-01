# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

# ── Bit positions (must match Verilog: uo_out = {6'b0, invalid_flag, pump}) ──
PUMP_BIT         = 0
INVALID_FLAG_BIT = 1

def pump(dut):
    return (dut.uo_out.value.to_unsigned() >> PUMP_BIT) & 1

def invalid_flag(dut):
    return (dut.uo_out.value.to_unsigned() >> INVALID_FLAG_BIT) & 1

async def do_reset(dut, ui_in_val=0b00000001):
    """Helper: start clock, apply reset, release. ui_in_val=MILD by default to stay in IDLE."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="us").start())
    dut.ena.value    = 1
    dut.uio_in.value = 0
    dut.ui_in.value  = ui_in_val
    dut.rst_n.value  = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value  = 1
    await ClockCycles(dut.clk, 1)  # settle

# ─────────────────────────────────────────────────────────────────────────────

@cocotb.test()
async def test_reset_to_idle(dut):
    """After reset, pump should be off and no invalid flag."""
    await do_reset(dut, ui_in_val=0b00000001)  # MILD keeps FSM in IDLE

    assert pump(dut) == 0,         f"Pump should be OFF in IDLE, got {pump(dut)}"
    assert invalid_flag(dut) == 0, f"Invalid flag should be 0 in IDLE, got {invalid_flag(dut)}"
    dut._log.info("PASS: reset_to_idle")

@cocotb.test()
async def test_dry_soil_tr
