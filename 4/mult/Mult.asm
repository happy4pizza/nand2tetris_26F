// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/4/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)
// The algorithm is based on repetitive addition.

@R2
M=0        // R2 = 0 (running product)

@R1
D=M
@END
D;JEQ      // if R1 == 0, result is 0, skip loop

@i
M=D        // i = R1 (loop counter)

(LOOP)
    @R0
    D=M
    @R2
    M=D+M      // R2 += R0

    @i
    M=M-1
    D=M
    @LOOP
    D;JGT      // loop while i > 0

(END)
@END
0;JMP      // infinite loop (halt)
