/ Program: 08_interrupt.asm
/ Demonstrates Interrupt-Driven execution
/ Memory location 0 stores the return address
/ Memory location 1 is the Interrupt Service Routine (ISR) entry point

ORG 000
        HEX 0000        / Address 0: Hardware saves return address here
        / Address 1: ISR entry
ISR,    LDB TICK_COUNT
        INB
        STB TICK_COUNT
        ION             / Re-enable interrupts
        JMP 000 I       / Return to interrupted program

ORG 010
MAIN,   ION             / Enable interrupts
BUSY,   JMP BUSY        / Background work loop

TICK_COUNT, DEC 0
END
