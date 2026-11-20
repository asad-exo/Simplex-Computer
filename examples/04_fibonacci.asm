/ Program: 04_fibonacci.asm
/ Computes first 8 Fibonacci numbers into memory locations FIB_BASE..

ORG 000
        / Store fib(0) = 0 and fib(1) = 1
        LDB ZERO
        STB FIB0
        LDB ONE
        STB FIB1

        / Compute loop for next numbers
FIB_LOOP,
        LDB FIB0
        ADD FIB1
        STB NEXT_FIB
        / Shift: FIB0 = FIB1, FIB1 = NEXT_FIB using EXG
        LDB FIB1
        STB FIB0
        LDB NEXT_FIB
        STB FIB1

        DSZ COUNT
        JMP FIB_LOOP
        STP

FIB0,     DEC 0
FIB1,     DEC 1
NEXT_FIB, DEC 0
COUNT,    DEC 6         / Compute 6 more terms
ZERO,     DEC 0
ONE,      DEC 1
END
