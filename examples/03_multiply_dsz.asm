/ Program: 03_multiply_dsz.asm
/ Multiplies X * Y using repeated addition and DSZ (decrement and skip if zero)

ORG 000
        CLB             / Clear AC to 0
        STB PRODUCT     / Initialize PRODUCT = 0
LOOP,   LDB PRODUCT     / Load current product
        ADD MULTIPLICAND/ Add X
        STB PRODUCT     / Store back to PRODUCT
        DSZ MULTIPLIER  / Decrement Y; if Y == 0, skip JMP LOOP
        JMP LOOP        / Repeat addition
        STP             / Done: PRODUCT contains X * Y

MULTIPLICAND, DEC 12    / X = 12
MULTIPLIER,   DEC 6     / Y = 6 (Total product = 72)
PRODUCT,      DEC 0
END
