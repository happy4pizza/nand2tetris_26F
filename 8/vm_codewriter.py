'''
N2T VM Translator, Project 7, CodeWriter class
stough F26

Example processes in a comment at the bottom. Some of these
ops are going to lead to a lot of assembly instructions.

Notes:
    - Following the API specified in N2T Ch 7
'''

import os

from vm_parser import (
    CommandType,
    arithmetic_all,
    arithmetic_binary,
    arithmetic_comp,
    arithmetic_unary,
)

# Would be a good idea to put together some standard snippets of code that are used over and over again.
# I'm thinking:
# push_d, pop_d: either take D and push it to the stack, or pop the stack into D.
# deref_push, deref_pop: take a segment and index, compute the address, then push or pop to that address.
#                       this is one is for local, argument, this, that. Those are ones where you do addr
#                       arithmetic.
# direct push and pop, for pointer and temp
standard_pushd = '@SP\nA=M\nM=D\n@SP\nM=M+1\n' # done in class but there's a more efficient version.
standard_popd = '@SP\nAM=M-1\nD=M\n'  # the reverse: SP down one, D = the value that was on top


class CodeWriter:
    '''
    I put a bunch of dictionaries here to simplify some processing.
    python has string-formatting capabilities, see my video. For example
    s = '@{}\nD=M\nA=M...{}...'
    s.format('LCL', index)
    '''

    '''
    comparison ops are harder. They involve making a computation on
    x and y, optimistically assuming true (M=-1), then skipping ahead
    if it was true, or else setting the value to false and falling through.
    The skip ahead has to be unique in the code, so we must keep track.
    I'll keep that in the init, since it changes versus these others that
    are read only.
    I made a comp_boiler kind of static string that could be used for any
    of the logic ops, which require executing a comparison in assembly,
    really hard to think about
    s = 'some string {} but also {{}}'
    s.format('first') -> s is now 'some string first but also {}'
    s.format('second') -> s is now 'some string first but also second'
    '''

    # the dictionaries: the virtual segments whose base address is held in a register
    segment_symbols = {  # noqa: RUF012
        'local': 'LCL',
        'argument': 'ARG',
        'this': 'THIS',
        'that': 'THAT'
    }
    # jump mnemonic to test D = x - y for each comparison op
    comp_jumps = {  # noqa: RUF012
        'eq': 'JEQ',
        'gt': 'JGT',
        'lt': 'JLT'
    }
    # comp_boiler: with x in M and y in D (after gettwo), compute x-y, optimistically
    # store true (-1), and skip the "store false" if the relation held.
    # Use as comp_boiler.format(unique_label, jump_mnemonic).
    comp_boiler = ('D=M-D\nM=-1\n@{0}\nD;{1}\n'
                   '@SP\nA=M-1\nM=0\n({0})\n')

    def __init__(self, outfile=None):
        if outfile is None:
            outfile = './Garbage.asm'
            print(f'CodeWriter: default outfile {outfile}.')
        self._outfile = outfile
        with open(self._outfile, 'w') as f:
            f.write(f'// CodeWriter Hack assembly output file {outfile}\n\n')
        # You'll have to keep track of comparison counts for the logic ops lt, gt, eq
        self.comp_counts = {
            'lt': 0,
            'eq': 0,
            'gt': 0
        }
        self.static_count = 0
        self.static_name = self.extract_static_name(self._outfile)
        # ch 8: current function for function$label names, and a count for unique return labels
        self.cur_function = 'bootstrap'
        self.call_count = 0

    def writeArithmetic(self, command: str):
        '''
        Write asm for the arithmetic op. all of these ops require
        one or two stack operands, perform an op, then push the result
        back on the stack. Could use the temp registers R13-15.
        '''
        assert command in arithmetic_all, \
            f'CodeWriter writeArithmetic: unknown command {command}'
        if command in arithmetic_binary:
            # pop two elements off, do the math, push the result:
            # gettwo leaves y in D and x in M (x's slot is where the result goes).
            ops = {'add': 'M=D+M', 'sub': 'M=M-D', 'and': 'M=D&M', 'or': 'M=D|M'}
            s = self.gettwo() + ops[command] + '\n'
        elif command in arithmetic_unary:
            # operate on just the top element in place.
            ops = {'neg': 'M=-M', 'not': 'M=!M'}
            s = self.getone() + ops[command] + '\n'
        else: # comparison command. by elimination, must be in arithmetic_comp
            assert command in arithmetic_comp, \
                f'CodeWriter writeArithmetic: unhandled command {command}'
            label = f'{command.upper()}_{self.comp_counts[command]}'
            self.comp_counts[command] += 1
            s = self.gettwo() + self.comp_boiler.format(label, self.comp_jumps[command])
        with open(self._outfile, 'a') as f:
            f.write(s)

    def writePushPop(self, command: CommandType, segment: str, index: int):
        '''
        Write asm for the push or pop command. So, compute segement+index addr, then
        either push to sp and update sp, or copy *sp-1 and decrement sp.
        push:
        // compute segment offset
        @SEGMENT
        '''
        assert command in [CommandType.C_PUSH, CommandType.C_POP], \
            f'CodeWriter writePushPop: unknown command {command}'
        push = command == CommandType.C_PUSH

        if segment == 'static':
            self.staticPushPop(command, index)
            return
        if segment == 'constant':
            # purely virtual: the "value" is the index itself.
            s = f'@{index}\nD=A\n' + standard_pushd
        elif segment in self.segment_symbols:
            # local, argument, this, that: address is RAM[base] + index
            base = self.segment_symbols[segment]
            if push:
                s = f'@{index}\nD=A\n@{base}\nA=D+M\nD=M\n' + standard_pushd
            else:
                # no A+index in Hack: record base+index in R13, then pop through it
                s = (f'@{index}\nD=A\n@{base}\nD=D+M\n@R13\nM=D\n'
                     + standard_popd + '@R13\nA=M\nM=D\n')
        elif segment in ['pointer', 'temp']:
            # fixed spots in RAM: pointer 0/1 is THIS/THAT (RAM 3,4), temp i is RAM 5+i
            if segment == 'pointer':
                addr = 'THIS' if index == 0 else 'THAT'
            else:
                addr = 5 + index
            if push:
                s = f'@{addr}\nD=M\n' + standard_pushd
            else:
                s = standard_popd + f'@{addr}\nM=D\n'
        else:
            raise ValueError(f'CodeWriter writePushPop: unknown segment {segment}')
        with open(self._outfile, 'a') as f:
            f.write(s)

    def staticPushPop(self, command, index):
        '''
        The vm notes something like 'push static i' and needs to be a variable
        of the @x form.
        '''
        varname = f'{self.static_name}.{index}'
        # push at least: write to the file f'@{varname}\nD=M\n' + standard_pushd
        if command == CommandType.C_PUSH:
            s = f'@{varname}\nD=M\n' + standard_pushd
        else:
            s = standard_popd + f'@{varname}\nM=D\n'
        with open(self._outfile, 'a') as f:
            f.write(s)

    def setFileName(self, filename):
        '''
        New .vm file: statics are named after it, and so are labels
        that aren't inside a function (like in BasicLoop).
        '''
        self.static_name = self.extract_static_name(filename)
        self.cur_function = self.static_name

    def writeInit(self):
        '''
        Bootstrap code from 8.3.1, goes at the top of the .asm.
        SP=256 then call Sys.init
        '''
        with open(self._outfile, 'a') as f:
            f.write('@256\nD=A\n@SP\nM=D\n')
        self.writeCall('Sys.init', 0)

    def writeLabel(self, label):
        with open(self._outfile, 'a') as f:
            f.write(f'({self.cur_function}${label})\n')

    def writeGoto(self, label):
        with open(self._outfile, 'a') as f:
            f.write(f'@{self.cur_function}${label}\n0;JMP\n')

    def writeIf(self, label):
        # pop the top of the stack and jump if it isn't 0 (false is 0)
        s = standard_popd + f'@{self.cur_function}${label}\nD;JNE\n'
        with open(self._outfile, 'a') as f:
            f.write(s)

    def writeFunction(self, functionName, numLocals):
        # (functionName), then push 0 for every local. pushd doesn't change D, so set D=0 once

        self.cur_function = functionName
        s = f'({functionName})\nD=0\n' + standard_pushd * numLocals
        with open(self._outfile, 'a') as f:
            f.write(s)

    def writeCall(self, functionName, numArgs):
        # follows fig 8.5
        ret = f'{self.cur_function}$ret.{self.call_count}'
        self.call_count += 1
        # push the return address, then save the caller's LCL, ARG, THIS, THAT
        s = f'@{ret}\nD=A\n' + standard_pushd
        for symbol in ['LCL', 'ARG', 'THIS', 'THAT']:
            s += f'@{symbol}\nD=M\n' + standard_pushd
        # ARG = SP-n-5
        s += f'@SP\nD=M\n@{numArgs + 5}\nD=D-A\n@ARG\nM=D\n'
        # LCL = SP
        s += '@SP\nD=M\n@LCL\nM=D\n'
        # goto the function, and the return label goes right after
        s += f'@{functionName}\n0;JMP\n({ret})\n'
        with open(self._outfile, 'a') as f:
            f.write(s)

    def writeReturn(self):
        '''
        Follows fig 8.5, with FRAME in R13 and RET in R14. RET has to be saved
        before *ARG = pop(): with 0 args, ARG points right at where RET is stored.
        '''
        # FRAME = LCL
        s = '@LCL\nD=M\n@R13\nM=D\n'
        # RET = *(FRAME-5)
        s += '@5\nA=D-A\nD=M\n@R14\nM=D\n'
        # *ARG = pop()
        s += standard_popd + '@ARG\nA=M\nM=D\n'
        # SP = ARG+1
        s += '@ARG\nD=M+1\n@SP\nM=D\n'
        # THAT = *(FRAME-1), THIS = *(FRAME-2), ARG = *(FRAME-3), LCL = *(FRAME-4)
        # R13 counts down by one each time through
        for symbol in ['THAT', 'THIS', 'ARG', 'LCL']:
            s += f'@R13\nAM=M-1\nD=M\n@{symbol}\nM=D\n'
        # goto RET
        s += '@R14\nA=M\n0;JMP\n'
        with open(self._outfile, 'a') as f:
            f.write(s)

    def gettwo(self):
        '''
        gettwo: pops the stack once, leaving D and M with y and x respectively,
        while sp points to (y or) the new stack top. This is the common first step for all binary ops.
        Returns the asm string.
        '''
        return standard_popd + 'A=A-1\n'

    def getone(self):
        '''
        Like gettwo, leaving M with x but without decrementing the stack pointer. common first step
        for not/neg
        Returns the asm string.
        '''
        return '@SP\nA=M-1\n'

    def extract_static_name(self, filename):
        # doing some file path algorithm to the get name without the extension...
        _, file = os.path.split(filename)
        name, _ = os.path.splitext(file)
        return name

    def close(self):
        # finish with an infinite loop.
        with open(self._outfile, 'a') as f:
            f.write('(END)\n@END\n0;JMP\n')

    def writeComment(self, comment):
        # Writes the comment into the file, for debugging.
        with open(self._outfile, 'a') as f:
            f.write(f'\n//{comment}\n')

