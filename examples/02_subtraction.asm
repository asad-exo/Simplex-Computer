/ Program: 02_subtraction.asm
/ Demonstrates 2's complement subtraction: DIFF = A - B
/ Also demonstrates SPB (skip if positive) conditional check

ORG 000
        LDB A           / Load A into AC
        SUB B           / Subtract B from AC (AC = AC - B)
        STB DIFF        / Store difference
        SPB             / Skip next instruction if AC >= 0 (positive)
        JMP NEGATIVE    / Jump if negative
        LDB ONE         / Positive flag = 1
        STB IS_POS
        STP
NEGATIVE, LDB ZERO      / Negative flag = 0
        STB IS_POS
        STP

A,      DEC 80
B,      DEC 35
DIFF,   DEC 0
IS_POS, DEC 0
ZERO,   DEC 0
ONE,    DEC 1
END
