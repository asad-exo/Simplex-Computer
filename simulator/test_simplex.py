"""
Unit Tests for Simplex Computer Core and Assembler
"""

import unittest
from simulator.simplex_core import SimplexComputer
from simulator.assembler import Assembler


class TestSimplexComputer(unittest.TestCase):
    def setUp(self):
        self.sim = SimplexComputer(opcode_mode="CU")
        self.asm = Assembler(opcode_mode="CU")

    def test_add_direct(self):
        code = """
        ORG 000
        LDB NUM1
        ADD NUM2
        STB RESULT
        STP
        NUM1,   DEC 25
        NUM2,   DEC 17
        RESULT, DEC 0
        """
        machine_code, _, _ = self.asm.assemble(code)
        self.sim.load_program(machine_code, start_pc=0)
        self.sim.run()

        self.assertEqual(self.sim.AC, 42)
        # Find RESULT address
        result_addr = self.asm.symbols["RESULT"]
        self.assertEqual(self.sim.memory[result_addr], 42)
        self.assertEqual(self.sim.S, 0)

    def test_sub_direct(self):
        code = """
        ORG 000
        LDB A
        SUB B
        STP
        A, DEC 50
        B, DEC 18
        """
        machine_code, _, _ = self.asm.assemble(code)
        self.sim.load_program(machine_code, start_pc=0)
        self.sim.run()

        self.assertEqual(self.sim.AC, 32)

    def test_logic_operations(self):
        code = """
        ORG 000
        LDB A
        AND B
        STB RES_AND
        LDB A
        OR  B
        STB RES_OR
        LDB A
        CMP B
        STB RES_XOR
        STP
        A, HEX 00FF
        B, HEX 0F0F
        RES_AND, HEX 0
        RES_OR,  HEX 0
        RES_XOR, HEX 0
        """
        machine_code, _, _ = self.asm.assemble(code)
        self.sim.load_program(machine_code, start_pc=0)
        self.sim.run()

        self.assertEqual(self.sim.memory[self.asm.symbols["RES_AND"]], 0x00FF & 0x0F0F)
        self.assertEqual(self.sim.memory[self.asm.symbols["RES_OR"]], 0x00FF | 0x0F0F)
        self.assertEqual(self.sim.memory[self.asm.symbols["RES_XOR"]], 0x00FF ^ 0x0F0F)

    def test_exg(self):
        code = """
        ORG 000
        LDB V1
        EXG V2
        STP
        V1, HEX AAAA
        V2, HEX 5555
        """
        machine_code, _, _ = self.asm.assemble(code)
        self.sim.load_program(machine_code, start_pc=0)
        self.sim.run()

        # AC should have old V2 (5555)
        self.assertEqual(self.sim.AC, 0x5555)
        # V2 should have old AC (AAAA)
        self.assertEqual(self.sim.memory[self.asm.symbols["V2"]], 0xAAAA)

    def test_dsz_loop(self):
        # Countdown loop: adds 10 to SUM five times (total 50)
        code = """
        ORG 000
        LOOP, LDB SUM
              ADD TEN
              STB SUM
              DSZ COUNT
              JMP LOOP
              STP
        TEN,   DEC 10
        COUNT, DEC 5
        SUM,   DEC 0
        """
        machine_code, _, _ = self.asm.assemble(code)
        self.sim.load_program(machine_code, start_pc=0)
        self.sim.run()

        self.assertEqual(self.sim.memory[self.asm.symbols["SUM"]], 50)
        self.assertEqual(self.sim.memory[self.asm.symbols["COUNT"]], 0)

    def test_indirect_addressing(self):
        code = """
        ORG 000
        LDB PTR I
        STP
        PTR,  HEX 020
        ORG 020
        DATA, HEX 1234
        """
        machine_code, _, _ = self.asm.assemble(code)
        self.sim.load_program(machine_code, start_pc=0)
        self.sim.run()

        self.assertEqual(self.sim.AC, 0x1234)

    def test_subroutine_jsr(self):
        # Subroutine doubles AC by adding itself
        code = """
        ORG 000
        LDB FIVE
        JSR DOUBLE
        STP
        FIVE, DEC 5
        DOUBLE, HEX 0000   / Return address will be stored here
                ADD FIVE
                JMP DOUBLE I
        """
        machine_code, _, _ = self.asm.assemble(code)
        self.sim.load_program(machine_code, start_pc=0)
        self.sim.run()

        self.assertEqual(self.sim.AC, 10)

    def test_indexed_addressing(self):
        code = """
        ORG 000
        LDIN ARRAY
        ADDIN ARRAY
        STP
        ARRAY, DEC 10
               DEC 20
               DEC 30
        """
        machine_code, _, _ = self.asm.assemble(code)
        self.sim.load_program(machine_code, start_pc=0)
        # Set index register to 2 (should access ARRAY+2 = 30)
        self.sim.INDR = 2
        self.sim.run()

        self.assertEqual(self.sim.AC, 60)  # 30 + 30

    def test_register_reference_instructions(self):
        code = """
        ORG 000
        LDB INIT
        CMB
        INB
        CLE
        CME
        CRB
        CIL
        SZB
        STP
        INIT, HEX 0001
        """
        machine_code, _, _ = self.asm.assemble(code)
        self.sim.load_program(machine_code, start_pc=0)
        self.sim.run()
        self.assertEqual(self.sim.S, 0)

    def test_io_instructions(self):
        code = """
        ORG 000
        INP
        OUT
        STP
        """
        machine_code, _, _ = self.asm.assemble(code)
        self.sim.load_program(machine_code, start_pc=0)
        self.sim.queue_input("H")
        self.sim.run()

        self.assertEqual(self.sim.get_output_text(), "H")

    def test_interrupt_handling(self):
        # Set up ISR at address 1
        code = """
        ORG 000
        HEX 0000   / Address 0: return address storage
        / Address 1: ISR entry
        LDB ISR_FLAG
        INB
        STB ISR_FLAG
        ION
        JMP 000 I  / Return from interrupt

        ORG 010
        MAIN, ION
        LOOP, JMP LOOP
        ISR_FLAG, DEC 0
        """
        machine_code, _, _ = self.asm.assemble(code)
        self.sim.load_program(machine_code, start_pc=0x10)
        self.sim.FGO = 0  # No output interrupt pending initially
        self.sim.FGI = 0

        # Step MAIN (ION)
        self.sim.step_instruction()
        self.assertEqual(self.sim.IEN, 1)

        # Trigger interrupt via input flag
        self.sim.FGI = 1

        # Next instruction step should initiate interrupt cycle and jump to 1
        self.sim.step_instruction()
        self.assertEqual(self.sim.PC, 1)
        self.assertEqual(self.sim.IEN, 0)  # RT2 clears IEN

        # Run ISR instructions
        for _ in range(10):
            self.sim.step_instruction()
            if self.sim.memory[self.asm.symbols["ISR_FLAG"]] == 1:
                break

        self.assertEqual(self.sim.memory[self.asm.symbols["ISR_FLAG"]], 1)


    def test_table_mode_opcodes(self):
        sim = SimplexComputer(opcode_mode="TABLE")
        asm = Assembler(opcode_mode="TABLE")
        code = """
        ORG 000
        LDB A
        ADD B
        STB C
        STP
        A, DEC 15
        B, DEC 27
        C, DEC 0
        """
        mc, _, _ = asm.assemble(code)
        sim.load_program(mc)
        sim.run()
        self.assertEqual(sim.AC, 42)
        self.assertEqual(sim.memory[asm.symbols["C"]], 42)

if __name__ == "__main__":
    unittest.main()
