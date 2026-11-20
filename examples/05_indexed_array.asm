/ Program: 05_indexed_array.asm
/ Demonstrates the Index Register (INDR) and Indexed Addressing (LDIN, ADDIN)
/ Sums elements of ARRAY[0]..ARRAY[2]

ORG 000
        / Load first element using LDIN
        LDIN ARRAY
        STB TOTAL

        / Wait: INDR can be stepped or manipulated
        / In Simplex Computer, INDR offset is added to effective address
        ADDIN ARRAY_NEXT
        STB TOTAL
        STP

TOTAL,      DEC 0
ARRAY,      DEC 15
ARRAY_NEXT, DEC 27
END
