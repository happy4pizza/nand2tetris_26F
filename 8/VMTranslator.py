'''
N2T Project 8 Virtual Machine 2, VM Translater
stough F26

The VM Translator takes .vm already compiled to the 
virtual machine spec, and translates those codes 
(push/pop different segments, compute stack ops) into
the associated Hack assembly mnemonics (@var, AM=M-1,...). 
(Proj 6 Assembler was the one traslates that to binary 
that runs on the Hack architecture.)

So here the script's job is to mindlessly use the Parser
and CodeWriter to perform the translation.

Project 8 adds label, goto, if-goto, function, call, return.
It can also take a folder of .vm files and make one Folder.asm
out of all of them, with the bootstrap code at the top.
'''


import os
import sys

from vm_codewriter import CodeWriter
from vm_parser import CommandType, Parser


def vm_translate(inputfile):
    # inputfile is either one .vm file or a folder of them
    isfolder = os.path.isdir(inputfile)
    if isfolder:
        folder = os.path.abspath(inputfile)
        vmfiles = [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith('.vm')]
        outputfile = os.path.join(folder, os.path.basename(folder) + '.asm')
    else:
        vmfiles = [inputfile]
        outputfile = inputfile.replace('.vm', '.asm')
    coder = CodeWriter(outputfile)

    if isfolder:
        coder.writeInit()  # whole program, so start with SP=256 and call Sys.init

    for vmfile in vmfiles:
        parser = Parser(inputfile=vmfile)
        coder.setFileName(vmfile)

        while (parser.hasMoreLines()):
            parser.advance()
            ctype = parser.commandType()

            coder.writeComment(parser.curLine())  # the VM command, as a comment in the .asm

            if ctype == CommandType.C_ARITMETIC:
                coder.writeArithmetic(parser.arg1())
            elif ctype in (CommandType.C_PUSH, CommandType.C_POP):
                coder.writePushPop(ctype, parser.arg1(), parser.arg2())
            elif ctype == CommandType.C_LABEL:
                coder.writeLabel(parser.arg1())
            elif ctype == CommandType.C_GOTO:
                coder.writeGoto(parser.arg1())
            elif ctype == CommandType.C_IF:
                coder.writeIf(parser.arg1())
            elif ctype == CommandType.C_FUNCTION:
                coder.writeFunction(parser.arg1(), parser.arg2())
            elif ctype == CommandType.C_CALL:
                coder.writeCall(parser.arg1(), parser.arg2())
            elif ctype == CommandType.C_RETURN:
                coder.writeReturn()

    coder.close()
    coder.writeComment('VMTranslator: finished translation.')


if __name__ == '__main__':
    vm_translate(sys.argv[1])