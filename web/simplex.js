/**
 * Simplex Computer - Complete Client-Side Simulator & Assembler
 * Based on CS222 Computer Organization & Assembly Language Design Report (GIKI, 2021)
 * Authors: Asad Shahab, Shams Ghani, Mahad Iqbal, Ahmed Bin Faisal
 */

class SimplexComputer {
    constructor(opcodeMode = "CU") {
        this.opcodeMode = opcodeMode;
        this.memory = new Uint16Array(512);

        // Registers
        this.AC = 0;    // 16-bit
        this.DR = 0;    // 16-bit
        this.IR = 0;    // 16-bit
        this.AR = 0;    // 9-bit
        this.PC = 0;    // 9-bit
        this.INDR = 0;  // 9-bit
        this.IOB = 0;   // 9-bit / 16-bit
        this.INPR = 0;  // 8-bit
        this.OUTR = 0;  // 8-bit
        this.SC = 0;    // 4-bit (0..15)

        // Flip-flops
        this.E = 0;
        this.S = 0;
        this.R = 0;
        this.IEN = 0;
        this.FGI = 0;
        this.FGO = 1;

        // Statistics & State
        this.lastMicroOp = "System initialized";
        this.cycleCount = 0;
        this.instructionCount = 0;

        // I/O buffers
        this.inputQueue = [];
        this.outputHistory = [];

        this.initOpcodes();
    }

    initOpcodes() {
        if (this.opcodeMode === "TABLE") {
            this.mrefOpcodes = {
                "ADD": 0x0, "SUB": 0x1, "LDB": 0x2, "STB": 0x3,
                "AND": 0x4, "OR":  0x5, "CMP": 0x6, "JSR": 0x7,
                "JMP": 0x8, "EXG": 0x9, "DSZ": 0xA, "LDIN": 0xB,
                "ADDIN": 0xC, "SUBIN": 0xD, "ANDIN": 0xE, "ORIN": 0xF
            };
        } else {
            // CU Decoders Section 8/10
            this.mrefOpcodes = {
                "AND": 0x0, "OR":  0x1, "ADD": 0x2, "LDB": 0x3,
                "STB": 0x4, "JMP": 0x5, "JSR": 0x6, "DSZ": 0x7,
                "EXG": 0x8, "SUB": 0x9, "CMP": 0xA, "LDIN": 0xB,
                "ADDIN": 0xC, "SUBIN": 0xD, "ANDIN": 0xE, "ORIN": 0xF
            };
        }

        this.mrefLookup = {};
        for (let [k, v] of Object.entries(this.mrefOpcodes)) {
            this.mrefLookup[v] = k;
        }

        this.regRefOps = {
            0x0: "CLB", 0x1: "CLE", 0x2: "CMB", 0x3: "CRB",
            0x4: "CIL", 0x5: "CME", 0x6: "INB", 0x7: "SPB",
            0x8: "SZB", 0x9: "STP"
        };

        this.ioOps = {
            0xA: "INP", 0xB: "OUT", 0xC: "SKI", 0xD: "SKO",
            0xE: "ION", 0xF: "IOF"
        };
    }

    setOpcodeMode(mode) {
        this.opcodeMode = mode;
        this.initOpcodes();
    }

    reset() {
        this.AC = 0;
        this.DR = 0;
        this.IR = 0;
        this.AR = 0;
        this.PC = 0;
        this.INDR = 0;
        this.IOB = 0;
        this.INPR = 0;
        this.OUTR = 0;
        this.SC = 0;
        this.E = 0;
        this.S = 0;
        this.R = 0;
        this.IEN = 0;
        this.FGI = 0;
        this.FGO = 1;
        this.lastMicroOp = "Reset CPU";
        this.cycleCount = 0;
        this.instructionCount = 0;
    }

    clearMemory() {
        this.memory.fill(0);
    }

    loadProgram(codeDict, startPc = 0) {
        for (let [addrStr, val] of Object.entries(codeDict)) {
            let addr = parseInt(addrStr, 10);
            if (addr >= 0 && addr < 512) {
                this.memory[addr] = val & 0xFFFF;
            }
        }
        this.PC = startPc & 0x1FF;
        this.AR = this.PC;
        this.SC = 0;
        this.S = 1;
        this.lastMicroOp = `Loaded program at PC=0x${this.PC.toString(16).padStart(3, "0").toUpperCase()}`;
    }

    queueInput(data) {
        for (let i = 0; i < data.length; i++) {
            this.inputQueue.push(data.charCodeAt(i) & 0xFF);
        }
        if (this.inputQueue.length > 0 && this.FGI === 0) {
            this.INPR = this.inputQueue.shift();
            this.FGI = 1;
        }
    }

    decodeInstruction(word) {
        let mode = (word >> 14) & 0x3;
        let gpr = (word >> 13) & 0x1;
        let opcode = (word >> 9) & 0xF;
        let address = word & 0x1FF;
        return { mode, gpr, opcode, address };
    }

    disassemble(word) {
        let { mode, gpr, opcode, address } = this.decodeInstruction(word);
        if (mode === 3) {
            if (opcode in this.regRefOps) return this.regRefOps[opcode];
            if (opcode in this.ioOps) return this.ioOps[opcode];
            return `HEX ${word.toString(16).padStart(4, "0").toUpperCase()}`;
        } else {
            let mnemonic = this.mrefLookup[opcode] || `OP_${opcode.toString(16).toUpperCase()}`;
            let suffix = "";
            if (mode === 1) suffix = " I";
            else if (mode === 2) suffix = " X";
            return `${mnemonic} ${address.toString(16).padStart(3, "0").toUpperCase()}${suffix}`;
        }
    }

    stepMicro() {
        // Interrupt check at start of cycle
        if (this.SC === 0 && this.S === 1) {
            if (this.IEN === 1 && (this.FGI === 1 || this.FGO === 1)) {
                this.R = 1;
            }
        }

        if (this.R === 1) {
            let desc = this._stepInterruptCycle();
            this.cycleCount++;
            this.lastMicroOp = desc;
            return desc;
        }

        if (this.S === 0) {
            this.lastMicroOp = "Halted (S=0)";
            return this.lastMicroOp;
        }

        let desc = this._stepInstructionCycle();
        this.cycleCount++;
        this.lastMicroOp = desc;
        return desc;
    }

    _stepInterruptCycle() {
        let sc = this.SC;
        if (sc === 0) {
            this.AR = 0;
            this.DR = this.PC;
            this.SC = 1;
            return "RT0: AR ← 0, DR ← PC";
        } else if (sc === 1) {
            this.memory[this.AR] = this.DR & 0xFFFF;
            this.PC = 0;
            this.SC = 2;
            return "RT1: M[AR] ← DR, PC ← 0";
        } else if (sc === 2) {
            this.PC = (this.PC + 1) & 0x1FF;
            this.IEN = 0;
            this.R = 0;
            this.SC = 0;
            return "RT2: PC ← PC + 1, IEN ← 0, R ← 0, SC ← 0";
        } else {
            this.SC = 0;
            this.R = 0;
            return "Interrupt cycle reset";
        }
    }

    _stepInstructionCycle() {
        let sc = this.SC;
        let { mode, gpr, opcode, address } = this.decodeInstruction(this.IR);

        if (sc === 0) {
            this.IR = this.memory[this.PC];
            this.SC = 1;
            return `T0: IR ← M[PC=${this.PC.toString(16).padStart(3, "0").toUpperCase()}] (${this.IR.toString(16).padStart(4, "0").toUpperCase()})`;
        } else if (sc === 1) {
            let decoded = this.decodeInstruction(this.IR);
            this.AR = decoded.address;
            this.PC = (this.PC + 1) & 0x1FF;
            this.SC = 2;
            let dis = this.disassemble(this.IR);
            return `T1: AR ← ${decoded.address.toString(16).padStart(3, "0").toUpperCase()}, PC ← ${this.PC.toString(16).padStart(3, "0").toUpperCase()}, Decode [${dis}]`;
        } else if (sc === 2) {
            if (mode === 0) {
                this.SC = 3;
                return `T2 (Direct): Effective Address = ${this.AR.toString(16).padStart(3, "0").toUpperCase()}`;
            } else if (mode === 1) {
                let oldAr = this.AR;
                this.AR = this.memory[this.AR] & 0x1FF;
                this.SC = 3;
                return `T2 (Indirect): AR ← M[${oldAr.toString(16).padStart(3, "0").toUpperCase()}] = ${this.AR.toString(16).padStart(3, "0").toUpperCase()}`;
            } else if (mode === 2) {
                let oldAr = this.AR;
                this.AR = (this.AR + this.INDR) & 0x1FF;
                this.SC = 3;
                return `T2 (Indexed): AR ← AR(${oldAr.toString(16).padStart(3, "0").toUpperCase()}) + INDR(${this.INDR.toString(16).padStart(3, "0").toUpperCase()}) = ${this.AR.toString(16).padStart(3, "0").toUpperCase()}`;
            } else if (mode === 3) {
                let desc = this._execImplied(opcode);
                this.SC = 0;
                this.instructionCount++;
                return `T2 (Implied): ${desc}, SC ← 0`;
            }
        }

        return this._stepMemoryReference(sc, opcode);
    }

    _execImplied(opcode) {
        if (opcode <= 0x9) {
            switch (opcode) {
                case 0x0: this.AC = 0; return "CLB: AC ← 0";
                case 0x1: this.E = 0; return "CLE: E ← 0";
                case 0x2: this.AC = (~this.AC) & 0xFFFF; return "CMB: AC ← AC'";
                case 0x3: {
                    let bit0 = this.AC & 1;
                    this.AC = ((this.AC >> 1) | (this.E << 15)) & 0xFFFF;
                    this.E = bit0;
                    return "CRB: AC ← SHR(AC), AC[15] ← E, E ← AC[0]";
                }
                case 0x4: {
                    let bit15 = (this.AC >> 15) & 1;
                    this.AC = (((this.AC << 1) & 0xFFFE) | this.E) & 0xFFFF;
                    this.E = bit15;
                    return "CIL: AC ← SHL(AC), AC[0] ← E, E ← AC[15]";
                }
                case 0x5: this.E = 1 - this.E; return "CME: E ← E'";
                case 0x6: this.AC = (this.AC + 1) & 0xFFFF; return "INB: AC ← AC + 1";
                case 0x7: {
                    let isPos = (this.AC & 0x8000) === 0;
                    if (isPos) {
                        this.PC = (this.PC + 1) & 0x1FF;
                        return `SPB: AC is positive, PC ← ${this.PC.toString(16).padStart(3, "0").toUpperCase()}`;
                    }
                    return "SPB: AC is negative, no skip";
                }
                case 0x8: {
                    if (this.AC === 0) {
                        this.PC = (this.PC + 1) & 0x1FF;
                        return `SZB: AC is zero, PC ← ${this.PC.toString(16).padStart(3, "0").toUpperCase()}`;
                    }
                    return "SZB: AC is not zero, no skip";
                }
                case 0x9: this.S = 0; return "STP: S ← 0 (Halted)";
            }
        } else {
            switch (opcode) {
                case 0xA: {
                    this.IOB = this.INPR & 0x1FF;
                    this.AC = (this.AC & 0xFF00) | (this.INPR & 0xFF);
                    this.FGI = 0;
                    if (this.inputQueue.length > 0) {
                        this.INPR = this.inputQueue.shift();
                        this.FGI = 1;
                    }
                    return `INP: AC[7..0] ← INPR (0x${this.INPR.toString(16).padStart(2, "0").toUpperCase()})`;
                }
                case 0xB: {
                    let b = this.AC & 0xFF;
                    this.OUTR = b;
                    this.IOB = this.AC & 0x1FF;
                    this.outputHistory.push(b);
                    this.FGO = 1;
                    let charRep = (b >= 32 && b <= 126) ? `'${String.fromCharCode(b)}'` : `0x${b.toString(16).padStart(2, "0").toUpperCase()}`;
                    return `OUT: OUTR ← AC[7..0] (${charRep}), FGO ← 1`;
                }
                case 0xC: {
                    if (this.FGI === 1) {
                        this.PC = (this.PC + 1) & 0x1FF;
                        return `SKI: FGI=1, PC ← ${this.PC.toString(16).padStart(3, "0").toUpperCase()}`;
                    }
                    return "SKI: FGI=0, no skip";
                }
                case 0xD: {
                    if (this.FGO === 1) {
                        this.PC = (this.PC + 1) & 0x1FF;
                        return `SKO: FGO=1, PC ← ${this.PC.toString(16).padStart(3, "0").toUpperCase()}`;
                    }
                    return "SKO: FGO=0, no skip";
                }
                case 0xE: this.IEN = 1; return "ION: IEN ← 1 (Interrupt Enabled)";
                case 0xF: this.IEN = 0; return "IOF: IEN ← 0 (Interrupt Disabled)";
            }
        }
        return `Unknown implied opcode ${opcode.toString(16)}`;
    }

    _stepMemoryReference(sc, opcode) {
        let mnemonic = this.mrefLookup[opcode] || "UNKNOWN";

        if (sc === 3) {
            if (["ADD", "SUB", "LDB", "AND", "OR", "CMP", "DSZ",
                 "LDIN", "ADDIN", "SUBIN", "ANDIN", "ORIN"].includes(mnemonic)) {
                this.DR = this.memory[this.AR];
                this.SC = 4;
                return `T3: DR ← M[AR=${this.AR.toString(16).padStart(3, "0").toUpperCase()}] (0x${this.DR.toString(16).padStart(4, "0").toUpperCase()})`;
            } else if (mnemonic === "STB") {
                this.memory[this.AR] = this.AC & 0xFFFF;
                this.SC = 0;
                this.instructionCount++;
                return `T3: M[AR=${this.AR.toString(16).padStart(3, "0").toUpperCase()}] ← AC(0x${this.AC.toString(16).padStart(4, "0").toUpperCase()}), SC ← 0`;
            } else if (mnemonic === "JMP") {
                this.PC = this.AR;
                this.SC = 0;
                this.instructionCount++;
                return `T3: PC ← AR (${this.AR.toString(16).padStart(3, "0").toUpperCase()}), SC ← 0`;
            } else if (mnemonic === "JSR") {
                this.memory[this.AR] = this.PC;
                this.PC = (this.AR + 1) & 0x1FF;
                this.SC = 0;
                this.instructionCount++;
                return `T3: M[AR=${this.AR.toString(16).padStart(3, "0").toUpperCase()}] ← PC, PC ← ${this.PC.toString(16).padStart(3, "0").toUpperCase()}, SC ← 0`;
            } else if (mnemonic === "EXG") {
                this.DR = this.AC;
                this.SC = 4;
                return `T3: DR ← AC (0x${this.AC.toString(16).padStart(4, "0").toUpperCase()})`;
            }
        } else if (sc === 4) {
            if (mnemonic === "ADD" || mnemonic === "ADDIN") {
                let sum = this.AC + this.DR;
                this.E = (sum >> 16) & 1;
                this.AC = sum & 0xFFFF;
                this.SC = 0;
                this.instructionCount++;
                return `T4: AC ← AC + DR = 0x${this.AC.toString(16).padStart(4, "0").toUpperCase()}, E ← ${this.E}, SC ← 0`;
            } else if (mnemonic === "LDB" || mnemonic === "LDIN") {
                this.AC = this.DR & 0xFFFF;
                this.SC = 0;
                this.instructionCount++;
                return `T4: AC ← DR (0x${this.DR.toString(16).padStart(4, "0").toUpperCase()}), SC ← 0`;
            } else if (mnemonic === "AND" || mnemonic === "ANDIN") {
                this.AC = (this.AC & this.DR) & 0xFFFF;
                this.SC = 0;
                this.instructionCount++;
                return `T4: AC ← AC ∧ DR = 0x${this.AC.toString(16).padStart(4, "0").toUpperCase()}, SC ← 0`;
            } else if (mnemonic === "OR" || mnemonic === "ORIN") {
                this.AC = (this.AC | this.DR) & 0xFFFF;
                this.SC = 0;
                this.instructionCount++;
                return `T4: AC ← AC ∨ DR = 0x${this.AC.toString(16).padStart(4, "0").toUpperCase()}, SC ← 0`;
            } else if (mnemonic === "CMP") {
                this.AC = (this.AC ^ this.DR) & 0xFFFF;
                this.SC = 0;
                this.instructionCount++;
                return `T4: AC ← AC ⊕ DR = 0x${this.AC.toString(16).padStart(4, "0").toUpperCase()}, SC ← 0`;
            } else if (mnemonic === "SUB" || mnemonic === "SUBIN") {
                this.DR = (~this.DR) & 0xFFFF;
                this.SC = 5;
                return `T4: DR ← DR' (0x${this.DR.toString(16).padStart(4, "0").toUpperCase()})`;
            } else if (mnemonic === "EXG") {
                this.AC = this.memory[this.AR];
                this.SC = 5;
                return `T4: AC ← M[AR=${this.AR.toString(16).padStart(3, "0").toUpperCase()}] (0x${this.AC.toString(16).padStart(4, "0").toUpperCase()})`;
            } else if (mnemonic === "DSZ") {
                this.DR = (this.DR - 1) & 0xFFFF;
                this.SC = 5;
                return `T4: DR ← DR - 1 (0x${this.DR.toString(16).padStart(4, "0").toUpperCase()})`;
            }
        } else if (sc === 5) {
            if (mnemonic === "SUB" || mnemonic === "SUBIN") {
                this.DR = (this.DR + 1) & 0xFFFF;
                let sum = this.AC + this.DR;
                this.E = (sum >> 16) & 1;
                this.AC = sum & 0xFFFF;
                this.SC = 0;
                this.instructionCount++;
                return `T5: DR ← DR + 1, AC ← AC + DR = 0x${this.AC.toString(16).padStart(4, "0").toUpperCase()}, E ← ${this.E}, SC ← 0`;
            } else if (mnemonic === "EXG") {
                this.memory[this.AR] = this.DR & 0xFFFF;
                this.SC = 0;
                this.instructionCount++;
                return `T5: M[AR=${this.AR.toString(16).padStart(3, "0").toUpperCase()}] ← DR (0x${this.DR.toString(16).padStart(4, "0").toUpperCase()}), SC ← 0`;
            } else if (mnemonic === "DSZ") {
                this.memory[this.AR] = this.DR & 0xFFFF;
                let skip = (this.DR === 0);
                if (skip) {
                    this.PC = (this.PC + 1) & 0x1FF;
                }
                this.SC = 0;
                this.instructionCount++;
                let msg = skip ? `, DR=0 -> PC skipped to ${this.PC.toString(16).padStart(3, "0").toUpperCase()}` : "";
                return `T5: M[AR] ← DR(0x${this.DR.toString(16).padStart(4, "0").toUpperCase()})${msg}, SC ← 0`;
            }
        }

        this.SC = 0;
        return `Micro-op end for ${mnemonic}`;
    }

    stepInstruction() {
        if (this.S === 0) return ["Halted"];
        let steps = [];
        let guard = 32;
        while (guard-- > 0) {
            let desc = this.stepMicro();
            steps.push(desc);
            if (this.SC === 0 || this.S === 0) break;
        }
        return steps;
    }

    getOutputText() {
        return this.outputHistory.map(b => String.fromCharCode(b)).join("");
    }
}

/**
 * Assembler class for Simplex Computer
 */
class Assembler {
    constructor(opcodeMode = "CU") {
        this.computer = new SimplexComputer(opcodeMode);
    }

    parseAddr(str) {
        str = str.trim();
        if (str.startsWith("0x") || str.startsWith("0X")) return parseInt(str, 16);
        let parsed = parseInt(str, 16);
        if (isNaN(parsed)) parsed = parseInt(str, 10);
        return isNaN(parsed) ? 0 : parsed;
    }

    parseNum(str) {
        str = str.trim();
        if (str.startsWith("0x") || str.startsWith("0X")) return parseInt(str, 16);
        if (str.startsWith("0b") || str.startsWith("0B")) return parseInt(str.slice(2), 2);
        let val = parseInt(str, 10);
        if (val < 0) val = (val + 0x10000) & 0xFFFF;
        return isNaN(val) ? 0 : val;
    }

    assemble(sourceCode) {
        let lines = sourceCode.split(/\r?\n/);
        let symbols = {};
        let errors = [];
        let locCounter = 0;
        let parsedLines = [];

        // Pass 1
        for (let i = 0; i < lines.length; i++) {
            let rawLine = lines[i];
            let cleaned = rawLine.split(/[/;#]/)[0].trim();
            if (!cleaned) {
                parsedLines.push({ lineNo: i + 1, label: null, mnemonic: null, args: [], rawLine });
                continue;
            }

            let label = null;
            let rest = cleaned;

            if (cleaned.includes(",")) {
                let parts = cleaned.split(",");
                label = parts[0].trim();
                rest = parts.slice(1).join(",").trim();
            } else if (cleaned.includes(":")) {
                let parts = cleaned.split(":");
                label = parts[0].trim();
                rest = parts.slice(1).join(":").trim();
            }

            let tokens = rest.split(/\s+/).filter(Boolean);
            if (tokens.length === 0) {
                if (label) symbols[label.toUpperCase()] = locCounter;
                parsedLines.push({ lineNo: i + 1, label, mnemonic: null, args: [], rawLine });
                continue;
            }

            let firstToken = tokens[0].toUpperCase();
            let isMnemonic = (
                firstToken in this.computer.mrefOpcodes ||
                Object.values(this.computer.regRefOps).includes(firstToken) ||
                Object.values(this.computer.ioOps).includes(firstToken) ||
                ["ORG", "HEX", "DEC", "BIN", "CHR", "STR", "END"].includes(firstToken)
            );

            if (!label && !isMnemonic && tokens.length > 1) {
                label = firstToken;
                tokens = tokens.slice(1);
                firstToken = tokens[0].toUpperCase();
            }

            if (label) {
                let up = label.toUpperCase();
                if (up in symbols) errors.push(`Line ${i + 1}: Duplicate symbol '${label}'`);
                symbols[up] = locCounter;
            }

            parsedLines.push({ lineNo: i + 1, label, mnemonic: firstToken, args: tokens.slice(1), rawLine });

            if (firstToken === "ORG") {
                if (tokens.length > 1) {
                    locCounter = this.parseAddr(tokens[1]) & 0x1FF;
                }
            } else if (firstToken === "END") {
                break;
            } else if (firstToken === "STR") {
                let m = cleaned.match(/["'](.*)["']/);
                let len = m ? m[1].length : tokens.slice(1).join(" ").length;
                locCounter = (locCounter + len) & 0x1FF;
            } else {
                locCounter = (locCounter + 1) & 0x1FF;
            }
        }

        if (errors.length > 0) {
            throw new Error(errors.join("\n"));
        }

        // Pass 2
        let machineCode = {};
        let listing = [];
        locCounter = 0;

        for (let item of parsedLines) {
            let { lineNo, label, mnemonic, args, rawLine } = item;
            if (!mnemonic) {
                listing.push(`               ${rawLine}`);
                continue;
            }

            if (mnemonic === "ORG") {
                locCounter = this.parseAddr(args[0]) & 0x1FF;
                listing.push(`${locCounter.toString(16).padStart(3, "0").toUpperCase()}          ${rawLine}`);
                continue;
            }

            if (mnemonic === "END") {
                listing.push(`               ${rawLine}`);
                break;
            }

            let currentAddr = locCounter;
            let word = 0;

            if (mnemonic === "HEX") {
                word = parseInt(args[0], 16) & 0xFFFF;
                machineCode[currentAddr] = word;
                listing.push(`${currentAddr.toString(16).padStart(3, "0").toUpperCase()}  ${word.toString(16).padStart(4, "0").toUpperCase()}     ${rawLine}`);
                locCounter = (locCounter + 1) & 0x1FF;
                continue;
            } else if (mnemonic === "DEC") {
                word = this.parseNum(args[0]) & 0xFFFF;
                machineCode[currentAddr] = word;
                listing.push(`${currentAddr.toString(16).padStart(3, "0").toUpperCase()}  ${word.toString(16).padStart(4, "0").toUpperCase()}     ${rawLine}`);
                locCounter = (locCounter + 1) & 0x1FF;
                continue;
            } else if (mnemonic === "BIN") {
                word = parseInt(args[0], 2) & 0xFFFF;
                machineCode[currentAddr] = word;
                listing.push(`${currentAddr.toString(16).padStart(3, "0").toUpperCase()}  ${word.toString(16).padStart(4, "0").toUpperCase()}     ${rawLine}`);
                locCounter = (locCounter + 1) & 0x1FF;
                continue;
            } else if (mnemonic === "CHR") {
                let chStr = args[0] || " ";
                let ch = (chStr.startsWith("'") || chStr.startsWith('"')) ? chStr[1] : chStr[0];
                word = ch.charCodeAt(0) & 0xFFFF;
                machineCode[currentAddr] = word;
                listing.push(`${currentAddr.toString(16).padStart(3, "0").toUpperCase()}  ${word.toString(16).padStart(4, "0").toUpperCase()}     ${rawLine}`);
                locCounter = (locCounter + 1) & 0x1FF;
                continue;
            } else if (mnemonic === "STR") {
                let m = rawLine.match(/["'](.*)["']/);
                let chars = m ? m[1] : args.join(" ");
                for (let i = 0; i < chars.length; i++) {
                    machineCode[locCounter] = chars.charCodeAt(i) & 0xFFFF;
                    locCounter = (locCounter + 1) & 0x1FF;
                }
                listing.push(`${currentAddr.toString(16).padStart(3, "0").toUpperCase()}  [STR]    ${rawLine}`);
                continue;
            }

            // Register Reference
            let regOp = null;
            for (let [k, v] of Object.entries(this.computer.regRefOps)) {
                if (v === mnemonic) { regOp = parseInt(k, 10); break; }
            }
            if (regOp !== null) {
                word = (0b11 << 14) | (regOp << 9);
                machineCode[currentAddr] = word;
                listing.push(`${currentAddr.toString(16).padStart(3, "0").toUpperCase()}  ${word.toString(16).padStart(4, "0").toUpperCase()}     ${rawLine}`);
                locCounter = (locCounter + 1) & 0x1FF;
                continue;
            }

            // I/O Instructions
            let ioOp = null;
            for (let [k, v] of Object.entries(this.computer.ioOps)) {
                if (v === mnemonic) { ioOp = parseInt(k, 10); break; }
            }
            if (ioOp !== null) {
                word = (0b11 << 14) | (ioOp << 9);
                machineCode[currentAddr] = word;
                listing.push(`${currentAddr.toString(16).padStart(3, "0").toUpperCase()}  ${word.toString(16).padStart(4, "0").toUpperCase()}     ${rawLine}`);
                locCounter = (locCounter + 1) & 0x1FF;
                continue;
            }

            // Memory Reference
            if (mnemonic in this.computer.mrefOpcodes) {
                let opcode = this.computer.mrefOpcodes[mnemonic];
                let isIndexed = mnemonic.endsWith("IN") && mnemonic !== "INP";
                let mode = isIndexed ? 0b10 : 0b00;
                let gpr = isIndexed ? 1 : 0;

                if (args.length === 0) {
                    throw new Error(`Line ${lineNo}: Instruction ${mnemonic} requires an address`);
                }

                let addrToken = args[0].trim();
                if (addrToken.startsWith("@")) {
                    mode = 0b01;
                    addrToken = addrToken.slice(1);
                }

                if (args.length > 1) {
                    let mod = args[1].toUpperCase().trim();
                    if (mod === "I") mode = 0b01;
                    else if (mod === "X") { mode = 0b10; gpr = 1; }
                }

                let targetAddr = 0;
                let upToken = addrToken.toUpperCase();
                if (upToken in symbols) {
                    targetAddr = symbols[upToken] & 0x1FF;
                } else {
                    targetAddr = this.parseAddr(addrToken) & 0x1FF;
                }

                word = (mode << 14) | (gpr << 13) | (opcode << 9) | (targetAddr & 0x1FF);
                machineCode[currentAddr] = word;
                listing.push(`${currentAddr.toString(16).padStart(3, "0").toUpperCase()}  ${word.toString(16).padStart(4, "0").toUpperCase()}     ${rawLine}`);
                locCounter = (locCounter + 1) & 0x1FF;
                continue;
            }

            throw new Error(`Line ${lineNo}: Unknown mnemonic '${mnemonic}'`);
        }

        return { machineCode, listing, symbols };
    }
}

// Export for node or browser
if (typeof module !== "undefined" && module.exports) {
    module.exports = { SimplexComputer, Assembler };
}
