// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/4/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel. When no key is pressed,
// the screen should be cleared.

(LOOP)
    @KBD
    D=M
    @BLACK
    D;JNE      // if keyboard != 0, go blacken
    @WHITE
    0;JMP      // else clear

(BLACK)
    @color
    M=-1       // -1 = all 1s = black
    @FILL
    0;JMP

(WHITE)
    @color
    M=0        // 0 = all 0s = white
    @FILL
    0;JMP

(FILL)
    @SCREEN
    D=A
    @addr
    M=D        // addr = base of screen memory map

    @8192
    D=A
    @n
    M=D        // n = 8192 words to fill (256 rows * 32 words/row)

(FILLLOOP)
    @n
    D=M
    @LOOP
    D;JEQ      // done filling, go recheck keyboard

    @color
    D=M
    @addr
    A=M
    M=D        // RAM[addr] = color

    @addr
    M=M+1      // addr++

    @n
    M=M-1      // n--

    @FILLLOOP
    0;JMP
