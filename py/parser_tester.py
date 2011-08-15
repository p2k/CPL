#!/usr/bin/env python

#
#  Copyright (C) 2011  Patrick "p2k" Schneider <patrick.p2k.schneider@gmail.com>
#
#  This file is part of :cpl.
#
#  :cpl is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  :cpl is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with :cpl.  If not, see <http://www.gnu.org/licenses/>.
#

import cpl.compiler

import sys, readline, traceback

if len(sys.argv) > 1:
    print cpl.compiler.parse(open(sys.argv[1], "r").read())
else:
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
