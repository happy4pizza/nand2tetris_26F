import difflib

with open('./pong/Pong.hack', 'r') as file1, open('./pong/Pong1.hack', 'r') as file2:
    file1_lines = file1.readlines()
    file2_lines = file2.readlines()

diff = list(difflib.unified_diff(
    file1_lines,
    file2_lines,
    fromfile='./pong/Pong.hack',
    tofile='./pong/Pong1.hack',
    lineterm=''
))

if not diff:
    print("outputs match")
else:
    for line in diff:
        print(line)
