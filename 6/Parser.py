class Parser:
    def __init__(self, filename):
        self.lines = []
        with open(filename) as file:
            for line in file:
                line = line.split("//")[0]
                line = line.replace(" ", "").strip()
                if line != "":
                    self.lines.append(line)
        self.i = -1
        self.cur = ""

    def hasMoreCommands(self):
        return self.i < len(self.lines) - 1

    def advance(self):
        self.i += 1
        self.cur = self.lines[self.i]

    def reset(self):
        self.i = -1
        self.cur = ""

    def commandType(self):
        if self.cur[0] == "@":
            return "A"
        if self.cur[0] == "(":
            return "L"
        return "C"

    def symbol(self):
        if self.cur[0] == "@":
            return self.cur[1:]
        return self.cur[1:-1]

    def dest(self):
        if "=" not in self.cur:
            return ""
        return self.cur.split("=")[0]

    def comp(self):
        c = self.cur
        if "=" in c:
            c = c.split("=")[1]
        if ";" in c:
            c = c.split(";")[0]
        return c

    def jump(self):
        if ";" not in self.cur:
            return ""
        return self.cur.split(";")[1]
