'''
N2T VM Translator, Project 7, Parser
stough F26

Parser class and the CommandType constants
follow the API specified in N2T Ch 7.
'''

from enum import Enum


class CommandType(Enum):
    C_ARITMETIC = 0
    C_PUSH      = 1
    C_POP       = 2
    C_LABEL     = 3
    C_GOTO      = 4
    C_IF        = 5
    C_FUNCTION  = 6
    C_RETURN    = 7
    C_CALL      = 8
    C_NONE      = 9

arithmetic_all = [ 'add', 'sub', 'neg', 'eq', 'gt', 'lt', 'and', 'or', 'not' ]
arithmetic_comp = [ 'eq', 'gt', 'lt' ]
arithmetic_unary = [ 'neg', 'not' ]
arithmetic_binary = [ 'add', 'sub', 'and', 'or' ]

class Parser:
    def __init__(self, inputfile):
        self._inputfile = inputfile
        self._lines = []
        self._preprocessFile()
        self._cur = -1
        self._ctype = CommandType.C_NONE
        self._carg1 = None
        self._carg2 = None

    def hasMoreLines(self):
        return self._cur + 1 < len(self._lines)

    def advance(self) -> None:
        # if there are more lines, then advance and interpret
        if self.hasMoreLines():
            self._cur += 1
            self._interpretLine()

    def curLine(self):
        assert self._cur >= 0, 'Parser error curLine: no current line.\n'
        return self._lines[self._cur]

    def commandType(self):
        assert self._ctype != CommandType.C_NONE, \
            f'Parser Error: no current line at #{self._cur}.\n'
        return self._ctype

    def arg1(self):
        assert self._ctype != CommandType.C_RETURN, \
            f'Parser Error: no arg1 for {self._lines[self._cur]}.\n'
        return self._carg1

    def arg2(self):
        assert self._ctype in [CommandType.C_PUSH, CommandType.C_POP, \
                               CommandType.C_FUNCTION, CommandType.C_CALL], \
                                f'Parser Error: no arg2 for {self._lines[self._cur]}.\n'
        return self._carg2

    def _interpretLine(self) -> None:
        line = self._lines[self._cur]
        tokens = [x for x in line.split(' ') if len(x)>0]

        assert len(tokens) > 0, 'Parser Error: could not tokenize {line}.\n'\

        # Read the first token and select among push/pop/arithmetic
        cmd = tokens[0]
        if cmd in arithmetic_all:
            # arithmetic: arg1 is the command itself, no arg2.
            self._ctype = CommandType.C_ARITMETIC
            self._carg1 = cmd
            self._carg2 = None
        elif cmd in ('push', 'pop'):
            # push/pop segment index
            self._ctype = CommandType.C_PUSH if cmd == 'push' else CommandType.C_POP
            self._carg1 = tokens[1]
            self._carg2 = int(tokens[2])
        else:
            print(f'Parser: this parser does not process {line}, will force C_LABEL.\n')
            self._ctype = CommandType.C_LABEL
            self._carg1 = None
            self._carg2 = None


    def _preprocessFile(self) -> None:
        '''
        Preprocess the input file, removing comments and whitespace, and storing
        the lines in self.lines.
        '''
        try:
            with open(self._inputfile, 'r') as f:
                all_lines = f.read().split('\n')
        except FileNotFoundError:
            print(f'Read Error: could not read {self._inputfile}.')
        except OSError as e:
            print(f'Unexpected Error: {e}')
        # filter the lines for comments and blanks:
        for line in all_lines:
            line = line.lstrip().rstrip()
            if line == '' or line[0] == '/':
                continue
            self._lines.append(line)


