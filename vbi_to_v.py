# vbi_to_v.py
# Convert Visiboole to Verilog

from argparse import ArgumentParser
import os.path
#import re

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
    # TODO: Fix spaces with regex
    # Split into words
    lines = []
    for raw_line in raw_lines:
        lines.append(raw_line.split())

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
                
    for regwire in regwires.values():
        if regwire.is_reg:
            print("    Found reg {}".format(regwire.name))
    for regwire in regwires.values():
        if not regwire.is_reg:
            print("    Found wire {}".format(regwire.name))

    print("  Fix declaration syntax")
    # WMH: This part sucks, fix it

    for line in dec_lines:
        regs = []
        wires = []
        for word in line:
            if "[" in word:
                try:
                    reg_stuff = word.strip("];").split("[")
                    assert(len(reg_stuff) == 2)
                    reg_name = reg_stuff[0]
                    sizes = reg_stuff[1].split(":")
                    assert(len(sizes) == 2)
                    reg = [reg_name, sizes[0], sizes[1]]
                except AssertionError:
                    print(word)
                    raise

                regs.append(reg)
            else:
                wires.append(word.strip(";"))
        
        new_line = []
        for reg in regs:
            new_line.append("reg [{}:{}] {};\n".format(reg[1], reg[2], reg[0]))

        if len(wires) > 0:
            dec_wires = "wire"
            for wire in wires:
                dec_wires = dec_wires + " " + wire
            dec_wires = dec_wires + ";"
            new_line.append(dec_wires)

        line[:] = []
        
        for new_word in new_line:
            line.append(new_word)

    # TODO: Implement more conversion operations
    # Wire line conversion
    print("  Fix wire line syntax")
    for line in wire_lines:
        #equal = line.find('=')  #save index of first equal
        
        if "[]" not in line:    #if [] present, probably an increment to a register and not an OR operator
            line.replace('+', '|')   #replace OR operators
        line.replace('[]', '')   #get rid of [] from registers
        
        word_list = line.split()   #turn line so far into list of words
        for i in range(len(line) - 1):
            if line[i] != "=" and line[i] != "|" and line[i+1] != "=" and line[i+1] != "|":
                line.insert(i+1, "&")

        line.insert(0, "assign")  #add assign before each wire assignment

    # Save as Verilog file
    if args.output:
        for line in lines:
            print(" ".join(line).replace("\n ", "\n"))
    else:
        try:
            with open(v_file_path, "x") as v_file:
                for line in lines:
                    str_line = " ".join(line).replace("\n ", "\n")
                    v_file.write("{}\n".format(str_line))

        except FileExistsError:
            print("Cannot create {} because it already exists!".format(v_file_path))
    
    return

if __name__ == "__main__":
    main()
