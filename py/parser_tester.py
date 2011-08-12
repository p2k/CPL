#!/usr/bin/env python

from cpl import compiler

import readline

print "Enter a blank line or hit Ctrl+D to leave.\n"

while True:
    try:
        s = raw_input("> ")
    except EOFError:
        print ""
        break
    if s == "":
        break
    
    print compiler.parse(s)
