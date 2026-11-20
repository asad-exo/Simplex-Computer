"""
Simplex Computer Core Simulator
Based on CS222 Computer Organization & Assembly Language Design Report (GIKI, 2021)
Authors: Asad Shahab, Shams Ghani, Mahad Iqbal, Ahmed Bin Faisal

Architecture:
- 16-bit Von Neumann architecture
- 512 words of 16-bit memory (9-bit address space: 0x000 to 0x1FF)
- Registers:
    AC: 16-bit Accumulator
    DR (TDR): 16-bit Data Register
    IR: 16-bit Instruction Register
    AR: 9-bit Address Register
    PC: 9-bit Program Counter
    INDR: 9-bit Index Register
    IOB: 9-bit / 16-bit I/O Buffer
    INPR: 8-bit Input Register
    OUTR: 8-bit Output Register
    SC: 4-bit Sequence Counter (0..15)
- Flip-Flops:
    E: Carry bit (1 bit)
    S: Start/Stop running flag (1 = running, 0 = halted)
    R: Interrupt pending flag (1 bit)
    IEN: Interrupt enable (1 bit)
    FGI: Input flag (1 = input ready)
    FGO: Output flag (1 = output ready)
"""

from typing import List, Dict, Optional, Tuple, Callable


class SimplexComputer:
    # Opcode mappings
    # Mode A: Section 8 / 10 / 11 / 12 (Hardwired Control Unit decoders M0..M15)
    OPCODE_MAP_CU = {
        "AND": 0x0,
        "OR":  0x1,
        "ADD": 0x2,
        "LDB": 0x3,
        "STB": 0x4,
        "JMP": 0x5,
        "JSR": 0x6,
        "DSZ": 0x7,
        "EXG": 0x8,
        "SUB": 0x9,
        "CMP": 0xA,
        "LDIN": 0xB,
        "ADDIN": 0xC,
        "SUBIN": 0xD,
        "ANDIN": 0xE,
        "ORIN": 0xF,
    }

    # Mode B: Section 5 Table 5.2 (Page 9 table listing)
    OPCODE_MAP_TABLE = {
        "ADD": 0x0,
        "SUB": 0x1,
        "LDB": 0x2,
        "STB": 0x3,
        "AND": 0x4,
        "OR":  0x5,
        "CMP": 0x6,
        "JSR": 0x7,
        "JMP": 0x8,
        "EXG": 0x9,
        "DSZ": 0xA,
        "LDIN": 0xB,
        "ADDIN": 0xC,
        "SUBIN": 0xD,
        "ANDIN": 0xE,
        "ORIN": 0xF,
    }

    # Register Reference opcodes (Mode = 11, bits 12-9: 0..9)
    REG_REF_OPS = {
        0x0: "CLB",   # Clear Accumulator
        0x1: "CLE",   # Clear Extended (E)
        0x2: "CMB",   # Complement Accumulator
        0x3: "CRB",   # Circulate Right Accumulator
        0x4: "CIL",   # Circulate Left Accumulator (called CLB in table p22)
        0x5: "CME",   # Complement Extended (E)
        0x6: "INB",   # Increment Accumulator
        0x7: "SPB",   # Skip if Accumulator Positive
        0x8: "SZB",   # Skip if Accumulator Zero
        0x9: "STP",   # Stop Computer
    }

    # I/O opcodes (Mode = 11, bits 12-9: 10..15)
    IO_OPS = {
        0xA: "INP",   # Input to Accumulator / IOB
        0xB: "OUT",   # Output from Accumulator / IOB
        0xC: "SKI",   # Skip on Input Flag
        0xD: "SKO",   # Skip on Output Flag
        0xE: "ION",   # Interrupt Enable On
        0xF: "IOF",   # Interrupt Enable Off
    }

    def __init__(self, opcode_mode: str = "CU"):
        """
        opcode_mode: 'CU' (Section 8/10 CU decoders) or 'TABLE' (Section 5 Table 5.2)
        """
        self.opcode_mode = opcode_mode
        self.set_opcode_mode(opcode_mode)

        # 512 words of 16-bit memory
        self.memory = [0] * 512

        # Registers
        self.AC = 0    # 16-bit
        self.DR = 0    # 16-bit (Data register / TDR)
        self.IR = 0    # 16-bit (Instruction register)
        self.AR = 0    # 9-bit (Address register)
        self.PC = 0    # 9-bit (Program counter)
        self.INDR = 0  # 9-bit (Index register)
        self.IOB = 0   # 9-bit I/O Buffer
        self.INPR = 0  # 8-bit input character
        self.OUTR = 0  # 8-bit output character
        self.SC = 0    # 4-bit Sequence counter (T0..T15)

        # Flip-flops
        self.E = 0     # 1-bit carry
        self.S = 0     # 1-bit running state (1=running, 0=stopped)
        self.R = 0     # 1-bit interrupt pending
        self.IEN = 0   # 1-bit interrupt enable
        self.FGI = 0   # 1-bit input flag
        self.FGO = 1   # 1-bit output flag (initially ready for output)

        # I/O devices buffers
        self.input_queue: List[int] = []
        self.output_log: List[int] = []

        # Micro-operation trace
        self.last_micro_op: str = "Idle"
        self.cycle_count: int = 0
        self.instruction_count: int = 0

    def set_opcode_mode(self, mode: str):
        self.opcode_mode = mode
        if mode == "TABLE":
            self.mref_opcodes = dict(self.OPCODE_MAP_TABLE)
        else:
            self.mref_opcodes = dict(self.OPCODE_MAP_CU)
        self.mref_lookup = {v: k for k, v in self.mref_opcodes.items()}

    def reset(self):
        """Reset CPU registers to initial state; preserves memory."""
        self.AC = 0
        self.DR = 0
        self.IR = 0
        self.AR = 0
        self.PC = 0
        self.INDR = 0
        self.IOB = 0
        self.INPR = 0
        self.OUTR = 0
        self.SC = 0
        self.E = 0
        self.S = 0
        self.R = 0
        self.IEN = 0
        self.FGI = 0
        self.FGO = 1
        self.last_micro_op = "Reset"
        self.cycle_count = 0
        self.instruction_count = 0

    def clear_memory(self):
        self.memory = [0] * 512

    def load_program(self, code_dict: Dict[int, int], start_pc: int = 0):
        for addr, val in code_dict.items():
            if 0 <= addr < 512:
                self.memory[addr] = val & 0xFFFF
        self.PC = start_pc & 0x1FF
        self.AR = self.PC
        self.SC = 0
        self.S = 1

    def queue_input(self, data: str):
        """Queue characters for input."""
        for ch in data:
            self.input_queue.append(ord(ch) & 0xFF)
        if self.input_queue and self.FGI == 0:
            self.INPR = self.input_queue.pop(0)
            self.FGI = 1

    def queue_input_bytes(self, values: List[int]):
        for val in values:
            self.input_queue.append(val & 0xFF)
        if self.input_queue and self.FGI == 0:
            self.INPR = self.input_queue.pop(0)
            self.FGI = 1

    def decode_instruction(self, word: int) -> Tuple[int, int, int, int]:
        """
        Decodes a 16-bit word:
        - mode: bits 15-14 (2 bits: 00=direct, 01=indirect, 10=indexed, 11=implied)
        - gpr: bit 13 (1 bit)
        - opcode: bits 12-9 (4 bits: 0..15)
        - address: bits 8-0 (9 bits: 0..511)
        """
        mode = (word >> 14) & 0x3
        gpr = (word >> 13) & 0x1
        opcode = (word >> 9) & 0xF
        address = word & 0x1FF
        return mode, gpr, opcode, address

    def disassemble(self, word: int) -> str:
        mode, gpr, opcode, address = self.decode_instruction(word)
        if mode == 3:  # Implied
            if opcode in self.REG_REF_OPS:
                return self.REG_REF_OPS[opcode]
            elif opcode in self.IO_OPS:
                return self.IO_OPS[opcode]
            return f"HEX {word:04X}"
        else:
            mnemonic = self.mref_lookup.get(opcode, f"OP_{opcode:X}")
            mode_str = ""
            if mode == 0:
                mode_str = ""  # Direct
            elif mode == 1:
                mode_str = " I"  # Indirect
            elif mode == 2:
                mode_str = " X"  # Indexed
            return f"{mnemonic} {address:03X}{mode_str}"

    def step_micro(self) -> str:
        """
        Executes a single clock pulse (one micro-operation),
        incrementing or clearing SC.
        Returns the micro-operation description.
        """
        # Check interrupt condition when beginning a cycle (SC == 0 and not halted)
        if self.SC == 0 and self.S == 1:
            # T0' T1' (IEN)(FGI + FGO): R <- 1
            if self.IEN == 1 and (self.FGI == 1 or self.FGO == 1):
                self.R = 1

        # Interrupt Cycle handling
        if self.R == 1:
            desc = self._step_interrupt_cycle()
            self.cycle_count += 1
            self.last_micro_op = desc
            return desc

        if self.S == 0:
            self.last_micro_op = "Halted (S=0)"
            return self.last_micro_op

        # Instruction Cycle
        desc = self._step_instruction_cycle()
        self.cycle_count += 1
        self.last_micro_op = desc
        return desc

    def _step_interrupt_cycle(self) -> str:
        sc = self.SC
        if sc == 0:
            # RT0: AR <- 0, DR <- PC
            self.AR = 0
            self.DR = self.PC
            self.SC = 1
            return "RT0: AR ← 0, DR ← PC"
        elif sc == 1:
            # RT1: M[AR] <- DR, PC <- 0
            self.memory[self.AR] = self.DR & 0xFFFF
            self.PC = 0
            self.SC = 2
            return "RT1: M[AR] ← DR, PC ← 0"
        elif sc == 2:
            # RT2: PC <- PC + 1, IEN <- 0, R <- 0, SC <- 0
            self.PC = (self.PC + 1) & 0x1FF
            self.IEN = 0
            self.R = 0
            self.SC = 0
            return "RT2: PC ← PC + 1, IEN ← 0, R ← 0, SC ← 0"
        else:
            self.SC = 0
            self.R = 0
            return "Interrupt cycle reset"

    def _step_instruction_cycle(self) -> str:
        sc = self.SC
        mode, gpr, opcode, address = self.decode_instruction(self.IR)

        if sc == 0:
            # T0: Fetch
            # IR <- M[PC]
            self.IR = self.memory[self.PC]
            self.SC = 1
            return f"T0: IR ← M[PC={self.PC:03X}] ({self.IR:04X})"

        elif sc == 1:
            # T1: Decode
            # AR <- IR(8-0), PC <- PC + 1, decode opcode & mode
            mode, gpr, opcode, address = self.decode_instruction(self.IR)
            self.AR = address
            self.PC = (self.PC + 1) & 0x1FF
            self.SC = 2
            mnemonic = self.disassemble(self.IR)
            return f"T1: AR ← {address:03X}, PC ← {self.PC:03X}, Decode [{mnemonic}]"

        elif sc == 2:
            # T2: Determine addressing mode or execute implied
            if mode == 0:
                # Direct addressing: nothing at T2, proceed to execute at T3
                self.SC = 3
                return f"T2 (Direct): AR = {self.AR:03X}, prepare T3"
            elif mode == 1:
                # Indirect addressing: AR <- M[AR]
                old_ar = self.AR
                self.AR = self.memory[self.AR] & 0x1FF
                self.SC = 3
                return f"T2 (Indirect): AR ← M[{old_ar:03X}] = {self.AR:03X}"
            elif mode == 2:
                # Indexed addressing: AR <- AR + INDR
                old_ar = self.AR
                self.AR = (self.AR + self.INDR) & 0x1FF
                self.SC = 3
                return f"T2 (Indexed): AR ← AR({old_ar:03X}) + INDR({self.INDR:03X}) = {self.AR:03X}"
            elif mode == 3:
                # Implied: Register Reference or I/O
                desc = self._exec_implied(opcode)
                self.SC = 0
                self.instruction_count += 1
                return f"T2 (Implied): {desc}, SC ← 0"

        # Memory Reference Instructions Execute Phase (T3..T6)
        return self._step_memory_reference(sc, opcode)

    def _exec_implied(self, opcode: int) -> str:
        if opcode <= 0x9:
            # Register reference instructions
            if opcode == 0x0:
                # CLB: Clear AC
                self.AC = 0
                return "CLB: AC ← 0"
            elif opcode == 0x1:
                # CLE: Clear E
                self.E = 0
                return "CLE: E ← 0"
            elif opcode == 0x2:
                # CMB: Complement AC
                self.AC = (~self.AC) & 0xFFFF
                return "CMB: AC ← AC'"
            elif opcode == 0x3:
                # CRB: Circulate Right AC through E
                bit0 = self.AC & 1
                self.AC = ((self.AC >> 1) | (self.E << 15)) & 0xFFFF
                self.E = bit0
                return "CRB: AC ← SHR(AC), AC[15] ← E, E ← AC[0]"
            elif opcode == 0x4:
                # CIL: Circulate Left AC through E
                bit15 = (self.AC >> 15) & 1
                self.AC = (((self.AC << 1) & 0xFFFE) | self.E) & 0xFFFF
                self.E = bit15
                return "CIL: AC ← SHL(AC), AC[0] ← E, E ← AC[15]"
            elif opcode == 0x5:
                # CME: Complement E
                self.E = 1 - self.E
                return "CME: E ← E'"
            elif opcode == 0x6:
                # INB: Increment AC
                self.AC = (self.AC + 1) & 0xFFFF
                return "INB: AC ← AC + 1"
            elif opcode == 0x7:
                # SPB: Skip if AC is positive
                is_pos = (self.AC & 0x8000) == 0
                if is_pos:
                    self.PC = (self.PC + 1) & 0x1FF
                    return f"SPB: AC({self.AC:04X}) is positive, PC ← {self.PC:03X}"
                return f"SPB: AC({self.AC:04X}) is negative, no skip"
            elif opcode == 0x8:
                # SZB: Skip if AC is zero
                if self.AC == 0:
                    self.PC = (self.PC + 1) & 0x1FF
                    return f"SZB: AC is zero, PC ← {self.PC:03X}"
                return f"SZB: AC({self.AC:04X}) is not zero, no skip"
            elif opcode == 0x9:
                # STP: Stop
                self.S = 0
                return "STP: S ← 0 (Halt)"
        else:
            # I/O instructions
            if opcode == 0xA:
                # INP: Input Character
                self.IOB = self.INPR & 0x1FF
                self.AC = (self.AC & 0xFF00) | (self.INPR & 0xFF)
                self.FGI = 0
                # If there are more bytes in queue, prepare next
                if self.input_queue:
                    self.INPR = self.input_queue.pop(0)
                    self.FGI = 1
                return f"INP: AC[7..0] ← INPR({self.INPR:02X}), FGI ← {self.FGI}"
            elif opcode == 0xB:
                # OUT: Output Character
                out_byte = self.AC & 0xFF
                self.OUTR = out_byte
                self.IOB = self.AC & 0x1FF
                self.output_log.append(out_byte)
                self.FGO = 0
                # Device promptly sets FGO = 1 once character accepted
                self.FGO = 1
                ch = chr(out_byte) if 32 <= out_byte < 127 else f"\\x{out_byte:02x}"
                return f"OUT: OUTR ← AC[7..0] ('{ch}'), FGO ← 1"
            elif opcode == 0xC:
                # SKI: Skip on input flag
                if self.FGI == 1:
                    self.PC = (self.PC + 1) & 0x1FF
                    return f"SKI: FGI=1, PC ← {self.PC:03X}"
                return "SKI: FGI=0, no skip"
            elif opcode == 0xD:
                # SKO: Skip on output flag
                if self.FGO == 1:
                    self.PC = (self.PC + 1) & 0x1FF
                    return f"SKO: FGO=1, PC ← {self.PC:03X}"
                return "SKO: FGO=0, no skip"
            elif opcode == 0xE:
                # ION: Interrupt enable on
                self.IEN = 1
                return "ION: IEN ← 1"
            elif opcode == 0xF:
                # IOF: Interrupt enable off
                self.IEN = 0
                return "IOF: IEN ← 0"

        return f"Unknown implied opcode {opcode:X}"

    def _step_memory_reference(self, sc: int, opcode: int) -> str:
        mnemonic = self.mref_lookup.get(opcode, "UNKNOWN")

        # Standard memory-reference instructions
        if sc == 3:
            if mnemonic in ("ADD", "SUB", "LDB", "AND", "OR", "CMP", "DSZ",
                            "LDIN", "ADDIN", "SUBIN", "ANDIN", "ORIN"):
                self.DR = self.memory[self.AR]
                self.SC = 4
                return f"T3: DR ← M[AR={self.AR:03X}] ({self.DR:04X})"

            elif mnemonic == "STB":
                self.memory[self.AR] = self.AC & 0xFFFF
                self.SC = 0
                self.instruction_count += 1
                return f"T3: M[AR={self.AR:03X}] ← AC({self.AC:04X}), SC ← 0"

            elif mnemonic == "JMP":
                self.PC = self.AR
                self.SC = 0
                self.instruction_count += 1
                return f"T3: PC ← AR({self.AR:03X}), SC ← 0"

            elif mnemonic == "JSR":
                # M[AR] <- PC, PC <- AR + 1
                self.memory[self.AR] = self.PC
                self.PC = (self.AR + 1) & 0x1FF
                self.SC = 0
                self.instruction_count += 1
                return f"T3: M[AR={self.AR:03X}] ← PC, PC ← {self.PC:03X}, SC ← 0"

            elif mnemonic == "EXG":
                self.DR = self.AC
                self.SC = 4
                return f"T3: DR ← AC({self.AC:04X})"

        elif sc == 4:
            if mnemonic in ("ADD", "ADDIN"):
                full_sum = self.AC + self.DR
                self.E = (full_sum >> 16) & 1
                self.AC = full_sum & 0xFFFF
                self.SC = 0
                self.instruction_count += 1
                return f"T4: AC ← AC + DR = {self.AC:04X}, E ← {self.E}, SC ← 0"

            elif mnemonic in ("LDB", "LDIN"):
                self.AC = self.DR & 0xFFFF
                self.SC = 0
                self.instruction_count += 1
                return f"T4: AC ← DR({self.DR:04X}), SC ← 0"

            elif mnemonic in ("AND", "ANDIN"):
                self.AC = (self.AC & self.DR) & 0xFFFF
                self.SC = 0
                self.instruction_count += 1
                return f"T4: AC ← AC ∧ DR = {self.AC:04X}, SC ← 0"

            elif mnemonic in ("OR", "ORIN"):
                self.AC = (self.AC | self.DR) & 0xFFFF
                self.SC = 0
                self.instruction_count += 1
                return f"T4: AC ← AC ∨ DR = {self.AC:04X}, SC ← 0"

            elif mnemonic == "CMP":
                self.AC = (self.AC ^ self.DR) & 0xFFFF
                self.SC = 0
                self.instruction_count += 1
                return f"T4: AC ← AC ⊕ DR = {self.AC:04X}, SC ← 0"

            elif mnemonic in ("SUB", "SUBIN"):
                # Report Section 8: T4: DR <- DR' (1's complement)
                self.DR = (~self.DR) & 0xFFFF
                self.SC = 5
                return f"T4: DR ← DR' = {self.DR:04X}"

            elif mnemonic == "EXG":
                # T4: AC <- M[AR]
                self.AC = self.memory[self.AR]
                self.SC = 5
                return f"T4: AC ← M[AR={self.AR:03X}] ({self.AC:04X})"

            elif mnemonic == "DSZ":
                # T4: DR <- DR - 1
                self.DR = (self.DR - 1) & 0xFFFF
                self.SC = 5
                return f"T4: DR ← DR - 1 = {self.DR:04X}"

        elif sc == 5:
            if mnemonic in ("SUB", "SUBIN"):
                # T5: DR <- DR + 1 (2's complement), then AC <- AC + DR
                self.DR = (self.DR + 1) & 0xFFFF
                full_sum = self.AC + self.DR
                self.E = (full_sum >> 16) & 1
                self.AC = full_sum & 0xFFFF
                self.SC = 0
                self.instruction_count += 1
                return f"T5: DR ← DR + 1, AC ← AC + DR = {self.AC:04X}, E ← {self.E}, SC ← 0"

            elif mnemonic == "EXG":
                # T5: M[AR] <- DR, SC <- 0
                self.memory[self.AR] = self.DR & 0xFFFF
                self.SC = 0
                self.instruction_count += 1
                return f"T5: M[AR={self.AR:03X}] ← DR({self.DR:04X}), SC ← 0"

            elif mnemonic == "DSZ":
                # T5: M[AR] <- DR, if DR == 0 then PC <- PC + 1, SC <- 0
                self.memory[self.AR] = self.DR & 0xFFFF
                skip = (self.DR == 0)
                if skip:
                    self.PC = (self.PC + 1) & 0x1FF
                self.SC = 0
                self.instruction_count += 1
                skip_msg = f", PC ← {self.PC:03X} (skipped)" if skip else ""
                return f"T5: M[AR] ← DR({self.DR:04X}){skip_msg}, SC ← 0"

        # Fallback if unknown
        self.SC = 0
        return f"Unknown micro-step sc={sc} for {mnemonic}"

    def step_instruction(self) -> List[str]:
        """
        Executes one full instruction (from SC=0 until SC resets to 0,
        or machine halts).
        Returns a list of micro-operations executed.
        """
        if self.S == 0:
            return ["Halted"]
        steps = []
        max_substeps = 32
        while max_substeps > 0:
            desc = self.step_micro()
            steps.append(desc)
            if self.SC == 0 or self.S == 0:
                break
            max_substeps -= 1
        return steps

    def run(self, max_instructions: int = 10000) -> int:
        """Runs until halt (S=0) or max_instructions reached."""
        count = 0
        while self.S == 1 and count < max_instructions:
            self.step_instruction()
            count += 1
        return count

    def get_output_text(self) -> str:
        return "".join(chr(b) for b in self.output_log)
