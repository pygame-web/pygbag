import sys

final = []
with open(sys.argv[-1], "r") as source:
    ml = False
    for line in source.readlines():
        if line.rstrip().endswith('"""'):
            ml = True
            final.append(line.replace('"""', ""))
            continue

        if ml:
            if line.lstrip().startswith('"""'):
                ml = False
                final.append(line.replace('"""', ""))
                continue
            if line and line[0] != "/":
                escaped = line.rstrip().replace('"', '\\"')
                final.append(f'"{escaped}\\n"\n')
                continue

        final.append(line)

print("".join(final))
