import sys

from Coder import Coder
from Parser import Parser
from SymbolTable import SymbolTable

infile = sys.argv[1]
outfile = infile.replace(".asm", ".hack")

parser = Parser(infile)
coder = Coder()
symbols = SymbolTable()

# first pass: labels point at the next real instruction
line = 0
while parser.hasMoreCommands():
    parser.advance()
    if parser.commandType() == "L":
        symbols.addEntry(parser.symbol(), line)
    else:
        line += 1

# second pass
parser.reset()
nextVar = 16
with open(outfile, "w") as out:
    while parser.hasMoreCommands():
        parser.advance()
        t = parser.commandType()
        if t == "L":
            continue
        if t == "A":
            sym = parser.symbol()
            if sym.isdigit():
                num = int(sym)
            else:
                # new symbol that isn't a label must be a variable
                if not symbols.contains(sym):
                    symbols.addEntry(sym, nextVar)
                    nextVar += 1
                num = symbols.getAddress(sym)
            out.write(format(num, "016b") + "\n")
        else:
            bits = "111" + coder.comp(parser.comp()) + coder.dest(parser.dest()) + coder.jump(parser.jump())
            out.write(bits + "\n")
print("wrote " + outfile)
