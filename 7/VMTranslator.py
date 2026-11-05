'''
N2T Project 7 Virtual Machine 1, VM Translater
stough F26

The VM Translator takes .vm already compiled to the 
virtual machine spec, and translates those codes 
(push/pop different segments, compute stack ops) into
the associated Hack assembly mnemonics (@var, AM=M-1,...). 
(Proj 6 Assembler was the one traslates that to binary 
that runs on the Hack architecture.)

So here the script's job is to mindlessly use the Parser
and CodeWriter to perform the translation.

This version does not have to account for function, call,
return, if, goto, label. That's a lot of action that 
we can worry about in Ch. 8 :-{
'''


import sys

from vm_codewriter import CodeWriter
from vm_parser import CommandType, Parser


def vm_translate(inputfile):
    outputfile = inputfile.replace('.vm', '.asm')
    parser = Parser(inputfile=inputfile)
    coder = CodeWriter(outputfile)

    while (parser.hasMoreLines()):
        parser.advance()
        ctype = parser.commandType()

        coder.writeComment(parser.curLine())  # the VM command, as a comment in the .asm

        if ctype == CommandType.C_ARITMETIC:
            coder.writeArithmetic(parser.arg1())
        elif ctype in (CommandType.C_PUSH, CommandType.C_POP):
            coder.writePushPop(ctype, parser.arg1(), parser.arg2())
        # function/call/return/label/goto/if-goto are not handled until Project 8.

    coder.close()
    coder.writeComment('VMTranslator: finished translation.')


if __name__ == '__main__':
    vm_translate(sys.argv[1])