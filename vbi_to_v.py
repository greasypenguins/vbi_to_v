# vbi_to_v.py
# Convert Visiboole to Verilog

from argparse import ArgumentParser
import os.path
import re

class RegWire(object):
    is_reg = False
    name = ""
    start_bit = None
    end_bit = None
    declared = False

    def __init__(self):
        pass

    def __len__(self):
        if (self.start_bit is None) and (self.end_bit is None):
            return 1
        elif (self.start_bit is None) or (self.end_bit is None):
            raise Exception("You need to assign a bit range before getting the length")
        return (self.start_bit - self.end_bit + 1)
    
    def __str__(self):
        if len(self) > 1:
            return "{}[{}..{}]".format(self.name, self.start_bit, self.end_bit)
        else:
            return self.name

    def __lt__(self, other):
        # Used to sort lists of RegWires by length
        return len(self) < len(other)

def main():
    print("Convert Visiboole to Verilog")
    print("Author: Weston Harder")
    print("This is a work in progress."
          " Some features of Visiboole and Verilog are not supported yet."
          " Feel free to help fix that!")

    # Interpret shell arguments
    parser = ArgumentParser()
    parser.add_argument(
        "vbi_file",
        help="Path to input Visiboole file"
        )
    parser.add_argument(
        "-v",
        "--v_file",
        help="Optional output Verilog file. Otherwise uses same name with .v extension."
        )
    parser.add_argument(
        "-i",
        "--input",
        help="Print input Visiboole code to console after categorizing lines.",
        action="store_true"
        )
    parser.add_argument(
        "-o",
        "--output",
        help="Print output Verilog code to console instead of saving to .v file.",
        action="store_true"
        )
    parser.add_argument(
        "-f",
        "--force",
        help="Write the .v file even if it already exists (overwriting the old one).",
        action="store_true"
        )
    args = parser.parse_args()

    vbi_file_path = args.vbi_file
    v_file_path = args.v_file
    if v_file_path is None:
        v_file_path = "{}.v".format(os.path.splitext(vbi_file_path)[0])

    print("Visiboole file: {}".format(vbi_file_path))
    print("Verilog   file: {}".format(v_file_path  ))

    # Read in Visiboole file
    print("Reading Visiboole file")
    raw_lines = []
    with open(vbi_file_path) as vbi_file:
        raw_lines = vbi_file.readlines()

    # Preprocess Visiboole
    print("Preprocessing Visiboole")

    # Split into words
    lines = []
    for raw_line in raw_lines:
        # Fix concatenations
        old = raw_line
        new = None
        while new != old:
            if new is not None:
                old = new
            new = re.sub(r"(\{[^\}]+)(\s)([^\{]+\})", r"\g<1>,\g<3>", old)

        lines.append(new.split())

    # Categorize lines
    print("Categorizing lines")
    comment_lines = []
    dec_lines = []
    wire_lines = []
    reg_lines = []
    
    for line in lines:
        category = "???"

        for word in line:
            if "\"" in word:
                # Lines with " are comment lines
                comment_lines.append(line)
                category = "CMT"
                break

            elif word == "<=":
                # Lines with "<=" are register lines
                reg_lines.append(line)
                category = "REG"
                break

            elif word == "=":
                # Lines with "=" are wire lines
                wire_lines.append(line)
                category = "WIR"
                break

            elif word.endswith(";"):
                # The line has ended but it has a colon so it is a declaration line
                dec_lines.append(line)
                category = "DCL"
                break

            else:
                # Line not categorized yet so keep going
                continue

        # All words have been traversed
        if args.input:
            print("[{}] {}".format(category, " ".join(line)))

    # Perform conversion operations
    print("Performing conversion")
    print("  Convert .. to :")
    for line in lines:
        for i, word in enumerate(line):
            line[i] = word.replace("..", ":")

    print("  Convert comment lines")
    for line in comment_lines:
        line[0] = "//{}".format(line[0])

    print("  Identify registers and wires")
    regwires = {}
    
    for line in reg_lines:
        word = line[0]
        reg = RegWire()
        reg.is_reg = True
        if "[" in word:
            reg.name = word.split("[")[0]
            if ":" in word:
                reg.start_bit = int(word.split("[")[1].split(":")[0])
                reg.end_bit = int(word.split("[")[1].split(":")[1].strip("]"))
        else:
            reg.name = word
        regwires[reg.name] = reg

    for line in wire_lines:
        word = line[0]
        wire = RegWire()
        wire.is_reg = False
        if "[" in word:
            wire.name = word.split("[")[0]
            if ":" in word:
                wire.start_bit = int(word.split("[")[1].split(":")[0])
                wire.end_bit = int(word.split("[")[1].split(":")[1].strip("]"))
        else:
            wire.name = word
        regwires[wire.name] = wire

    for line in dec_lines:
        for word in line:
            if "%" in word:
                continue

            if ":" in word:
                name = word.split("[")[0]
                try:
                    regwire = regwires[name]
                except KeyError:
                    regwire = RegWire()
                    regwire.name = name
                    regwires[name] = regwire

                regwire.start_bit = int(word.split("[")[1].split(":")[0])
                regwire.end_bit = int(word.split("[")[1].split(":")[1].split("]")[0])
            
            else:
                name = word.strip(";")
                if name not in regwires:
                    regwire = RegWire()
                    regwire.name = name
                    regwires[name] = regwire
    
    regs_string = ""
    for regwire in regwires.values():
        if regwire.is_reg:
            regs_string = regs_string + "\n      {}".format(regwire.name)
    if len(regs_string) > 0:
        print("    Found registers:{}".format(regs_string))

    wires_string = ""
    for regwire in regwires.values():
        if not regwire.is_reg:
            wires_string = wires_string + "\n      {}".format(regwire.name)
    if len(wires_string) > 0:
        print("    Found wires:{}".format(wires_string))

    print("  Fix declarations")

    for line in dec_lines:
        declared_regwires = []
        for word in line:
            if "%" in word:
                continue
            name = word.strip(";").split("[")[0]
            regwire = regwires[name]
            declared_regwires.append(regwires[name])
        
        new_line = []

        if len(declared_regwires) == 0:
            line[:] = new_line[:]
            continue

        declared_regwires = sorted(declared_regwires)
        
        start_bit = None
        end_bit = None

        for regwire in declared_regwires:
            if  (regwire.start_bit == start_bit) \
            and (regwire.end_bit   == end_bit  ) \
            and (len(new_line) > 0             ):
                new_line[-1] = new_line[-1] + ","
                new_line.append(regwire.name)
                
            else:
                if len(new_line) > 0:
                    new_line[-1] = new_line[-1] + ";\n"

                if regwire.is_reg:
                    new_line.append("reg")
                else:
                    new_line.append("wire")

                if len(regwire) > 1:
                    new_line.append("[{}:{}]".format(regwire.start_bit, regwire.end_bit))
                
                new_line.append(regwire.name)

            start_bit = regwire.start_bit
            end_bit = regwire.end_bit

            regwire.declared = True
        
        new_line[-1] = new_line[-1] + ";"

        line[:] = new_line[:]

    more_dec_lines = []

    for regwire in regwires.values():
        if not regwire.declared:
            line = []

            if regwire.is_reg:
                line.append("reg")
            else:
                line.append("wire")

            if len(regwire) > 1:
                line.append("[{}:{}]".format(regwire.start_bit, regwire.end_bit))
            
            line.append("{};".format(regwire.name))

            more_dec_lines.append(line)

    for line in more_dec_lines:
        lines.insert(0, line)

    # Wire line conversion
    print("  Fix wire line syntax")
    for line in wire_lines:
        for i, word in enumerate(line):
            line[i] = word.replace("[]", "")  #get rid of []

        changed = True

        while changed:
            changed = False
            for i in range(len(line) - 1):
                if line[i] not in ["=", "<=", "|", "&", "^", "+", "-"] and line[i+1] not in ["=", "<=", "|", "&", "^", "+", "-"]:
                    line.insert(i+1, "&")
                    changed = True

        line.insert(0, "assign")  #add assign before each wire assignment

    print("  Fix register line syntax")
    for line in reg_lines:
        for i, word in enumerate(line):
            line[i] = word.replace("[]", "")  #get rid of []

        changed = True

        while changed:
            changed = False
            for i in range(len(line) - 1):
                if line[i] not in ["=", "<=", "|", "&", "^", "+", "-"] and line[i+1] not in ["=", "<=", "|", "&", "^", "+", "-"]:
                    line.insert(i+1, "&")
                    changed = True

    print("  Fix reg line syntax")
    for line in reg_lines:
        line.insert(0,"always @(posedge S08clk)\n    ")

    # Save as Verilog file
    if args.output:
        print("Final Verilog code:")
        for line in lines:
            print(" ".join(line).replace("\n ", "\n"))
    else:
        print("Saving final Verilog code")
        try:
            if args.force:
                open_mode = "w"
            else:
                open_mode = "x"

            with open(v_file_path, open_mode) as v_file:
                for line in lines:
                    str_line = " ".join(line).replace("\n ", "\n").replace("\n\n", "\n")
                    v_file.write("{}\n".format(str_line))

        except FileExistsError:
            print("Cannot create {} because it already exists!".format(v_file_path))
    
    return

if __name__ == "__main__":
    main()
