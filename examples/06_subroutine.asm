/ Program: 06_subroutine.asm
/ Demonstrates subroutine call using JSR (Jump and Save Return Address)
/ And subroutine return using indirect JMP

ORG 000
        LDB VALUE
        JSR SQUARE
        STB RESULT
        STP

VALUE,  DEC 7
RESULT, DEC 0

/ Subroutine: multiplies AC by itself by repeated addition
SQUARE, HEX 0000        / Reserved word: JSR stores return address here
        STB OP1
        STB COUNTER
        CLB
        STB ACCUM
SQ_LOOP,
        LDB ACCUM
        ADD OP1
        STB ACCUM
        DSZ COUNTER
        JMP SQ_LOOP
        LDB ACCUM
        JMP SQUARE I    / Indirect jump back to caller!

OP1,     DEC 0
COUNTER, DEC 0
ACCUM,   DEC 0
END
