#!/usr/bin/env python

import cpl.compiler

import readline, traceback

print "Enter a blank line or hit Ctrl+D to leave.\n"

while True:
    try:
        s = raw_input("> ")
    except EOFError:
        print ""
        break
    if s == "":
        break
    
    try:
        reload(cpl.compiler)
        print cpl.compiler.parse(s)
    except:
        traceback.print_exc()
