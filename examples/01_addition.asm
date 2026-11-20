/ Program: 01_addition.asm
/ Simplex Computer Assembly Example
/ Calculates RESULT = NUM1 + NUM2

ORG 000
        LDB NUM1        / Load NUM1 into AC
        ADD NUM2        / Add NUM2 to AC (AC = AC + NUM2)
        STB RESULT      / Store AC into RESULT
        STP             / Halt computer

/ Data segment
NUM1,   DEC 45
NUM2,   DEC 55
RESULT, DEC 0
END
