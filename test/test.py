# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # 10 us clock period (100 KHz)
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())

    # ── Reset ──────────────────────────────────────────────────────────
    dut._log.info("Reset")
    dut.ena.value    = 1
    dut.ui_in.value  = 0b01
    dut.uio_in.value = 0
    dut.rst_n.value  = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value  = 1
    await ClockCycles(dut.clk, 1)  # settle after reset release

    # ── Test 1: DRY → IRRIGATE (pump ON) ──────────────────────────────
    # ui_in[1:0] = 2'b00 → moisture_content = DRY
    dut._log.info("Test DRY condition → expect IRRIGATE (uo_out = 2)")
    dut.ui_in.value = 0b00000000  # comp1=0, comp0=0 → DRY
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 2, \
        f"DRY: expected uo_out=2 (pump ON), got {dut.uo_out.value}"

    # ── Test 2: MILD → IDLE (pump OFF) ────────────────────────────────
    # ui_in[1:0] = 2'b01 → moisture_content = MILD
    dut._log.info("Test MILD condition → expect IDLE (uo_out = 0)")
    dut.ui_in.value = 0b00000001  # comp1=0, comp0=1 → MILD
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 0, \
        f"MILD: expected uo_out=0 (pump OFF), got {dut.uo_out.value}"

    # ── Test 3: WET → SATURATED (pump OFF) ────────────────────────────
    # ui_in[1:0] = 2'b11 → moisture_content = WET
    dut._log.info("Test WET condition → expect SATURATED (uo_out = 0)")
    dut.ui_in.value = 0b00000011  # comp1=1, comp0=1 → WET
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 0, \
        f"WET: expected uo_out=0 (pump OFF), got {dut.uo_out.value}"

    # ── Test 4: INVALID comparator state (flag ON) ────────────────────
    # ui_in[1:0] = 2'b10 → impossible comparator reading
    dut._log.info("Test INVALID condition → expect INVALID (uo_out = 1)")
    dut.ui_in.value = 0b00000010  # comp1=1, comp0=0 → INVALID
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 1, \
        f"INVALID: expected uo_out=1 (invalid_flag ON), got {dut.uo_out.value}"

    # ── Test 5: Recovery from INVALID → IDLE on valid input ───────────
    dut._log.info("Test recovery from INVALID → IDLE")
    dut.ui_in.value = 0b00000001  # MILD → should recover to IDLE
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 0, \
        f"RECOVERY: expected uo_out=0 (back to IDLE), got {dut.uo_out.value}"

    # ── Test 6: Full cycle DRY → IRRIGATE → MILD → IDLE ──────────────
    dut._log.info("Test full irrigation cycle")
    dut.ui_in.value = 0b00000000  # DRY → IRRIGATE
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 2, "Cycle: expected pump ON while DRY"

    dut.ui_in.value = 0b00000001  # MILD → IDLE (soil reached mild)
    await ClockCycles(dut.clk, 1)
    assert dut.uo_out.value == 0, "Cycle: expected pump OFF after reaching MILD"

    dut._log.info("All tests passed!")
