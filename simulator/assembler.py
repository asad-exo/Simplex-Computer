"""
Simplex Computer Two-Pass Assembler
Supports labels, pseudo-ops, direct, indirect, and indexed addressing.
"""

from typing import Dict, List, Tuple, Optional
import re
from .simplex_core import SimplexComputer


class AssemblyError(Exception):
    def __init__(self, message: str, line_no: int, line_text: str):
        super().__init__(f"Line {line_no}: {message} -> '{line_text}'")
        self.line_no = line_no
        self.line_text = line_text


class Assembler:
    def __init__(self, opcode_mode: str = "CU"):
        self.opcode_mode = opcode_mode
        self.computer_defs = SimplexComputer(opcode_mode)
        self.symbols: Dict[str, int] = {}
        self.errors: List[str] = []

    def parse_number(self, val_str: str) -> int:
        val_str = val_str.strip()
        if val_str.startswith("0x") or val_str.startswith("0X"):
            return int(val_str, 16)
        if val_str.startswith("0b") or val_str.startswith("0B"):
            return int(val_str, 2)
        # Try decimal or signed decimal
        try:
            val = int(val_str)
            if val < 0:
                val = (val + 0x10000) & 0xFFFF
            return val
        except ValueError:
            # Maybe hex without prefix if purely hex digits?
            # Standard Mano assembly treats HEX / DEC explicitly.
            raise ValueError(f"Invalid numeric literal: '{val_str}'")

    def assemble(self, source_code: str) -> Tuple[Dict[int, int], List[str], Dict[str, int]]:
        """
        Two-pass assembler.
        Returns:
            machine_code: Dict[address, 16-bit word]
            listing: List of formatted listing lines
            symbols: Symbol table dict
        """
        lines = source_code.splitlines()
        self.symbols = {}
        self.errors = []
        loc_counter = 0

        parsed_lines: List[Tuple[int, Optional[str], Optional[str], List[str], str]] = []

        # Helper to parse addresses (hex by default in Mano architecture)
        def parse_addr(val_str: str) -> int:
            val_str = val_str.strip()
            if val_str.startswith("0x") or val_str.startswith("0X"):
                return int(val_str, 16)
            try:
                # Default Mano address is hex
                return int(val_str, 16)
            except ValueError:
                return int(val_str, 10)

        # ================= PASS 1 =================
        for line_idx, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            # Remove comments (/ or ; or #)
            cleaned = re.split(r"[/;#]", line, maxsplit=1)[0].strip()
            if not cleaned:
                parsed_lines.append((line_idx, None, None, [], raw_line))
                continue

            label = None
            rest = cleaned

            # Check for label: e.g. "LOOP," or "LOOP:"
            if "," in cleaned:
                parts = cleaned.split(",", 1)
                label = parts[0].strip()
                rest = parts[1].strip()
            elif ":" in cleaned:
                parts = cleaned.split(":", 1)
                label = parts[0].strip()
                rest = parts[1].strip()

            tokens = rest.split()
            if not tokens:
                if label:
                    self.symbols[label.upper()] = loc_counter
                parsed_lines.append((line_idx, label, None, [], raw_line))
                continue

            first_token = tokens[0].upper()

            # If no colon/comma was used, first token might be a label if it's not a known mnemonic or pseudo-op
            is_mnemonic = (first_token in self.computer_defs.mref_opcodes or
                           first_token in [v for v in self.computer_defs.REG_REF_OPS.values()] or
                           first_token in [v for v in self.computer_defs.IO_OPS.values()] or
                           first_token in ("ORG", "HEX", "DEC", "BIN", "CHR", "END", "STR"))

            if not label and not is_mnemonic and len(tokens) > 1:
                label = first_token
                tokens = tokens[1:]
                first_token = tokens[0].upper()

            if label:
                label_up = label.upper()
                if label_up in self.symbols:
                    self.errors.append(f"Line {line_idx}: Duplicate symbol '{label}'")
                self.symbols[label_up] = loc_counter

            parsed_lines.append((line_idx, label, first_token, tokens[1:], raw_line))

            # Handle ORG or address advancement
            if first_token == "ORG":
                if tokens[1:]:
                    try:
                        loc_counter = parse_addr(tokens[1]) & 0x1FF
                    except Exception:
                        self.errors.append(f"Line {line_idx}: Invalid ORG address '{tokens[1]}'")
                continue
            elif first_token == "END":
                break
            elif first_token == "STR":
                # String pseudo-op: each character gets a word
                # Extract string inside quotes from raw_line
                m = re.search(r'["\'](.*)["\']', cleaned)
                str_len = len(m.group(1)) if m else len(" ".join(tokens[1:]))
                loc_counter = (loc_counter + str_len) & 0x1FF
            else:
                loc_counter = (loc_counter + 1) & 0x1FF

        if self.errors:
            raise AssemblyError("\n".join(self.errors), 0, "")

        # ================= PASS 2 =================
        machine_code: Dict[int, int] = {}
        listing: List[str] = []
        loc_counter = 0

        for line_idx, label, mnemonic, args, raw_line in parsed_lines:
            if not mnemonic:
                listing.append(f"               {raw_line}")
                continue

            if mnemonic == "ORG":
                try:
                    loc_counter = parse_addr(args[0]) & 0x1FF
                except Exception:
                    raise AssemblyError(f"Invalid ORG address '{args[0]}'", line_idx, raw_line)
                listing.append(f"{loc_counter:03X}          {raw_line}")
                continue

            if mnemonic == "END":
                listing.append(f"               {raw_line}")
                break

            current_addr = loc_counter
            word = 0

            # 1. Pseudo-ops
            if mnemonic == "HEX":
                if not args:
                    raise AssemblyError("HEX requires an argument", line_idx, raw_line)
                word = int(args[0], 16) & 0xFFFF
                machine_code[current_addr] = word
                listing.append(f"{current_addr:03X}  {word:04X}     {raw_line}")
                loc_counter = (loc_counter + 1) & 0x1FF
                continue

            elif mnemonic == "DEC":
                if not args:
                    raise AssemblyError("DEC requires an argument", line_idx, raw_line)
                val = int(args[0])
                if val < 0:
                    val = (val + 0x10000) & 0xFFFF
                word = val & 0xFFFF
                machine_code[current_addr] = word
                listing.append(f"{current_addr:03X}  {word:04X}     {raw_line}")
                loc_counter = (loc_counter + 1) & 0x1FF
                continue

            elif mnemonic == "BIN":
                if not args:
                    raise AssemblyError("BIN requires an argument", line_idx, raw_line)
                word = int(args[0], 2) & 0xFFFF
                machine_code[current_addr] = word
                listing.append(f"{current_addr:03X}  {word:04X}     {raw_line}")
                loc_counter = (loc_counter + 1) & 0x1FF
                continue

            elif mnemonic == "CHR":
                if not args:
                    raise AssemblyError("CHR requires an argument", line_idx, raw_line)
                char_str = args[0]
                ch_code = ord(char_str[1] if (char_str.startswith("'") or char_str.startswith('"')) else char_str[0])
                word = ch_code & 0xFFFF
                machine_code[current_addr] = word
                listing.append(f"{current_addr:03X}  {word:04X}     {raw_line}")
                loc_counter = (loc_counter + 1) & 0x1FF
                continue

            elif mnemonic == "STR":
                m = re.search(r'["\'](.*)["\']', raw_line)
                chars = m.group(1) if m else " ".join(args)
                for ch in chars:
                    machine_code[loc_counter] = ord(ch) & 0xFFFF
                    loc_counter = (loc_counter + 1) & 0x1FF
                listing.append(f"{current_addr:03X}  [STR]    {raw_line}")
                continue

            # 2. Register Reference Instructions (Mode = 11, Opcode = 0..9)
            # Find in REG_REF_OPS
            reg_op = None
            for opc, name in self.computer_defs.REG_REF_OPS.items():
                if name == mnemonic:
                    reg_op = opc
                    break

            if reg_op is not None:
                # Mode = 11 (binary 11 = 3 -> bits 15-14 = 3 -> 0xC000)
                # Opcode = reg_op in bits 12-9: (reg_op << 9)
                word = (0b11 << 14) | (reg_op << 9)
                machine_code[current_addr] = word
                listing.append(f"{current_addr:03X}  {word:04X}     {raw_line}")
                loc_counter = (loc_counter + 1) & 0x1FF
                continue

            # 3. Input/Output Instructions (Mode = 11, Opcode = 10..15)
            io_op = None
            for opc, name in self.computer_defs.IO_OPS.items():
                if name == mnemonic:
                    io_op = opc
                    break

            if io_op is not None:
                word = (0b11 << 14) | (io_op << 9)
                machine_code[current_addr] = word
                listing.append(f"{current_addr:03X}  {word:04X}     {raw_line}")
                loc_counter = (loc_counter + 1) & 0x1FF
                continue

            # 4. Memory Reference Instructions
            if mnemonic in self.computer_defs.mref_opcodes:
                opcode = self.computer_defs.mref_opcodes[mnemonic]

                # Determine default mode: indexed instructions (LDIN, ADDIN, etc.) imply mode 10 and GPR=1
                is_indexed_mnemonic = mnemonic.endswith("IN") and mnemonic != "INP"
                mode = 0b10 if is_indexed_mnemonic else 0b00
                gpr = 1 if is_indexed_mnemonic else 0

                if not args:
                    raise AssemblyError(f"Memory reference instruction {mnemonic} requires address", line_idx, raw_line)

                addr_token = args[0].strip()

                # Check for indirect symbol '@' or trailing 'I'
                if addr_token.startswith("@"):
                    mode = 0b01
                    addr_token = addr_token[1:]

                # Check trailing modifiers (e.g., "ADD NUM I" or "ADD NUM X")
                if len(args) > 1:
                    mod = args[1].upper().strip()
                    if mod == "I":
                        mode = 0b01  # Indirect
                    elif mod == "X":
                        mode = 0b10  # Indexed
                        gpr = 1

                # Resolve address operand
                target_addr = 0
                addr_token_up = addr_token.upper()
                if addr_token_up in self.symbols:
                    target_addr = self.symbols[addr_token_up] & 0x1FF
                else:
                    try:
                        target_addr = parse_addr(addr_token) & 0x1FF
                    except Exception:
                        raise AssemblyError(f"Unresolved symbol '{addr_token}'", line_idx, raw_line)

                word = (mode << 14) | (gpr << 13) | (opcode << 9) | (target_addr & 0x1FF)
                machine_code[current_addr] = word
                listing.append(f"{current_addr:03X}  {word:04X}     {raw_line}")
                loc_counter = (loc_counter + 1) & 0x1FF
                continue

            raise AssemblyError(f"Unknown instruction mnemonic: '{mnemonic}'", line_idx, raw_line)

        return machine_code, listing, self.symbols
