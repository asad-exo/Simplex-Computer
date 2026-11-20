#!/usr/bin/env python3
"""
Simplex Computer CLI & Web Runner
Usage:
    python run_simulator.py                    # Launches the interactive Web UI
    python run_simulator.py --file code.asm    # Runs an assembly file in CLI
    python run_simulator.py --test             # Runs the full unit test suite
"""

import sys
import os
import argparse
import unittest

from simulator.simplex_core import SimplexComputer
from simulator.assembler import Assembler
from simulator.server import run_server


def run_cli_file(asm_path: str, mode: str = "CU", trace: bool = False):
    if not os.path.exists(asm_path):
        print(f"Error: File '{asm_path}' not found.")
        sys.exit(1)

    with open(asm_path, "r", encoding="utf-8") as f:
        src = f.read()

    print(f"Assembling '{asm_path}' with mode={mode}...")
    assembler = Assembler(opcode_mode=mode)
    try:
        mc, listing, symbols = assembler.assemble(src)
    except Exception as e:
        print(f"Assembly Error:\n{e}")
        sys.exit(1)

    print("\n--- Assembler Listing ---")
    for line in listing:
        print(line)

    print("\n--- Symbols ---")
    for k, v in symbols.items():
        print(f"{k:12} = 0x{v:03X} ({v})")

    computer = SimplexComputer(opcode_mode=mode)
    computer.load_program(mc, start_pc=0)

    print("\n--- Executing Program ---")
    while computer.S == 1:
        steps = computer.step_instruction()
        if trace:
            for s in steps:
                print(f"  {s}")

    print("\n--- Execution Complete ---")
    print(f"Cycles: {computer.cycle_count} | Instructions: {computer.instruction_count}")
    print(f"Registers: AC=0x{computer.AC:04X} ({computer.AC}) | PC=0x{computer.PC:03X} | DR=0x{computer.DR:04X} | E={computer.E} | S={computer.S}")
    out = computer.get_output_text()
    if out:
        print(f"Console Output:\n{out}")


def main():
    parser = argparse.ArgumentParser(description="Simplex Computer 16-Bit Simulator & WebUI")
    parser.add_argument("--file", "-f", type=str, help="Path to .asm file to run in CLI mode")
    parser.add_argument("--trace", "-t", action="store_true", help="Print micro-operation trace in CLI mode")
    parser.add_argument("--mode", "-m", choices=["CU", "TABLE"], default="CU", help="Opcode mapping mode")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Web server port (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    parser.add_argument("--test", action="store_true", help="Run unittest test suite")

    args = parser.parse_args()

    if args.test:
        suite = unittest.defaultTestLoader.discover(os.path.join(os.path.dirname(__file__), "simulator"))
        runner = unittest.TextTestRunner(verbosity=2)
        res = runner.run(suite)
        sys.exit(0 if res.wasSuccessful() else 1)

    if args.file:
        run_cli_file(args.file, mode=args.mode, trace=args.trace)
    else:
        run_server(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
