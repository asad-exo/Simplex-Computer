/ Program: 07_echo_io.asm
/ Demonstrates polling character I/O:
/ Checks SKI until character entered, loads via INP, prints via OUT

ORG 000
POLL_IN,
        SKI             / Skip next instruction if input flag FGI == 1
        JMP POLL_IN     / Keep waiting for user keypress
        INP             / Read character into AC
        OUT             / Echo back to console
        CMP ESC_KEY     / Compare with ESC key (ASCII 27 = 0x1B)
        SZB             / Skip if zero (match)
        JMP POLL_IN     / Continue polling
        STP             / Exit on ESC

ESC_KEY, HEX 001B       / ESC ASCII code
END
