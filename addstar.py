import io
import os

def get_repo_name(line):
    s = line.index('[')
    e = line.index(']')
    names = line[s+1:e].split('/')
    return names[0].strip() + '/' + names[1].strip()

def addstar(file):
    convert_lines = []
    with io.open(file, 'r', encoding='utf8') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith('* 【'):
                convert_lines.append(line.strip() + ' ![](https://img.shields.io/github/stars/' + get_repo_name(line) + '?style=social)\n')
            else:
                convert_lines.append(line)
    with io.open(file, 'w', encoding='utf8') as f:
        f.writelines(convert_lines)

if __name__ == '__main__':
    addstar('./README.md')
    for root, ds, fs in os.walk('./archived'):
        for f in fs:
            addstar('./archived/' + f)
    