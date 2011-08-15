
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

import inspect, sys
from weakref import WeakKeyDictionary
from functools import wraps
from types import FunctionType

from kvo.broker import KVOBroker, ROBroker

def makeInterpreterMethodWrapper(method_name, method):
    @wraps(method)
    def wrapper(self, *args):
        return self.__iglobals__[method_name](*args)
    return wrapper

class InterpreterMetaClass(type):
    """Metaclass for interpreters. See :class:`Interpreter`."""
    
    def __new__(meta, classname, bases, classDict):
        if len(bases) > 1:
            raise ValueError("Multiple inheritance is not supported")
        base = bases[0]
        
        cglobals = sys._getframe(1).f_globals
        if base is object:
            nmethods = []
            imethods = {}
        elif base is Interpreter:
            nmethods = base.__cglobals__["__nmethods__"]
            imethods = base.__cglobals__["__imethods__"]
        else:
            raise ValueError("Interpreters cannot inherit from other interpreters.")
        
        replace = {}
        for name, obj in classDict.iteritems():
            if isinstance(obj, FunctionType):
                args = inspect.getargspec(obj).args
                if len(args) == 0 or args[0] != "self":
                    if name.endswith("_"):
                        replace[name] = name[:-1]
                        name = name[:-1]
                    else:
                        classDict[name] = makeInterpreterMethodWrapper(name, obj)
                    imethods[name] = obj.func_code
                elif not name.startswith("__"): # Igonre special methods
                    nmethods.append(name)
        
        for oldname, newname in replace.iteritems():
            obj = classDict[oldname]
            del classDict[oldname]
            classDict[newname] = makeInterpreterMethodWrapper(newname, obj)
        
        cglobals["__nmethods__"] = nmethods
        cglobals["__imethods__"] = imethods
        classDict["__cglobals__"] = cglobals
        
        return type.__new__(meta, classname, bases, classDict)

class Interpreter(object):
    """
    This class is the base class of all interpreters. It will decorate methods
    that don't have `self` as their first argument in a way so they can access
    instance attributes like they were global variables. This is implemented via
    metaclasses.
    
    Like this, interpreters can be written faster and more readable. Note,
    however that setting attributes requires the python "global" statement, as
    a set operation normally creates a local variable instead. In the scope of
    interpreters (stack/heap objects or pointer objects) the setting of
    attributes is avoided by using special operators or methods instead.
    
    This base class provides the program storeage `PS`, the program counter `PC`
    and the instructions `nop` and `halt` which are common among all virtual
    machines.
    """
    
    __metaclass__ = InterpreterMetaClass
    
    #: A list of attribute names which form the registers of the interpreter. Make sure to add the program counter `PC`.
    registerNames = ["PC"]
    
    def __init__(self):
        iglobals = self.__cglobals__.copy()
        for name in iglobals["__nmethods__"]:
            iglobals[name] = getattr(self, name)
        for name, code in iglobals["__imethods__"].iteritems():
            iglobals[name] = FunctionType(code, iglobals)
        del iglobals["__nmethods__"]
        del iglobals["__imethods__"]
        self.__iglobals__ = iglobals
        
        self.PS = ProgramStorage()
        self.PC = Pointer(self.PS)
        
        self.__breakpointHit = False
        self.__breakpoints = set()
    
    def __getattr__(self, name):
        if name == "__iglobals__":
            return object.__getattr__(self, name)
        else:
            return self.__iglobals__[name]
    
    def __setattr__(self, name, value):
        if name == "__iglobals__":
            object.__setattr__(self, name, value)
        else:
            self.__iglobals__[name] = value
    
    # ------------------------------------------------------------------------ #
    
    def resetVM(self):
        """
        Resets the interpreters state. Should be overriden and called by
        subclasses.
        """
        self.PC.setTo(0)
        self.__breakpointHit = False
    
    def loadVM(self, instructions):
        """Loads a program into the program storage."""
        self.PS.load(instructions)
    
    def runVM(self):
        """
        Runs the loaded program by calling `stepVM()` until `InterpreterHalt` or
        `InterpreterBreakpoint` is raised. Returns `True` on halt and `False` on
        a breakpoint.
        """
        try:
            while True:
                self.stepVM()
        except InterpreterHalt:
            return True
        except InterpreterBreakpoint:
            return False
    
    def stepVM(self):
        """Performs one computation step."""
        if not self.__breakpointHit and int(self.PC) in self.__breakpoints:
            self.__breakpointHit = True
            raise InterpreterBreakpoint
        
        self.__breakpointHit = False
        
        IR = self.nextVMInstruction()
        self.PC >> 1
        
        f = getattr(self, IR.name)
        f(*IR.args)
    
    def nextVMInstruction(self):
        """Returns the next instruction to execute."""
        return self.PS[self.PC]
    
    def setVMBreakpoint(self, index):
        """
        Sets a breakpoint at the instruction specified by `index`.
        
        Running `stepVM` will raise `InterpreterBreakpoint` on that instruction.
        A second call to `stepVM` continues normally.
        """
        self.__breakpoints.add(index)
        if self.PC == index:
            self.__breakpointHit = True
    
    def setVMBreakpoints(self, indexes):
        """
        Sets multiple breakpoints given as an iterable of integers.
        
        Replaces the existing set of breakpoints.
        """
        self.__breakpoints = set(indexes)
        if self.PC.v in indexes:
            self.__breakpointHit = True
    
    def resetVMBreakpoint(self, index):
        """Removes a breakpoint at the instruction specified by `index`."""
        self.__breakpoints.remove(index)
    
    def hasVMBreakpoint(self, index):
        """
        Returns `True` if a breakpoint is set at the instruction specified by
        `index`.
        """
        return index in self.__breakpoints
    
    def allVMBreakpoints(self):
        """Returns a list of the indexes of instructions with breakpoints."""
        return list(self.__breakpoints)
    
    def clearVMBreakpoints(self):
        """Removes all breakpoints."""
        self.__breakpoints.remove()
    
    # ------------------------------------------------------------------------ #
    
    def nop(self):
        """Generic instruction. Does nothing."""
        pass
    
    def halt(self):
        """Generic instruction. Raises `InterpreterHalt`."""
        raise InterpreterHalt

class Pointer(KVOBroker):
    """
    Instances of this class manage a pointer to a list-like object. Their
    primary purpose is to point to stack or heap locations.
    
    The following operators are overridden to provide that functionality:
    
    `+, -`
        Return a new pointer object which is increased/decreased by the given
        value.
    
    `<<, >>`
        Increase/decrease the pointer in-place by the given value.
    
    `(comparison operators)`
        Compares the pointer's location with the given location.
    
    `~`
        Dereference the pointer.
    
    Also, pointer objects can be converted to integers by using the built-in
    `int` function.
    """
    
    def __init__(self, target, initial = 0):
        self.__t = target
        self.__v = int(initial)
    
    @property
    def v(self):
        return self.__v
    
    @v.setter
    def v(self, v):
        """
        Property for getting/setting the pointer's value. Will notify observers
        of changes. You can assign any value that can be converted by int();
        this also includes other pointer objects.
        """
        self.notifyPropertyWillChange("v")
        self.__v = int(v)
        self.notifyPropertyDidChange()
    
    def copy(self):
        """Create a copy of this pointer."""
        return Pointer(self.__t, self.__v)
    
    def __add__(self, other):
        return Pointer(self.__t, self.__v + int(other))
    
    def __sub__(self, other):
        return Pointer(self.__t, self.__v - int(other))
    
    def __lshift__(self, other):
        self.v -= int(other)
        return self
    
    def __rshift__(self, other):
        self.v += int(other)
        return self
    
    def __invert__(self):
        return self.__t[self.__v]
    
    def __int__(self):
        return self.__v
    
    def __lt__(self, other):
        return self.__v < int(other)
    
    def __gt__(self, other):
        return self.__v > int(other)
    
    def __le__(self, other):
        return self.__v <= int(other)
    
    def __ge__(self, other):
        return self.__v >= int(other)
    
    def __eq__(self, other):
        return self.__v == int(other)
    
    def __ne__(self, other):
        return self.__v != int(other)
    
    def __repr__(self):
        return "Pointer(%s, %d)" % (repr(self.__t), self.__v)
    
    def __str__(self):
        return "-> %s[%d]" % (str(self.__t), self.__v)

class ProgramStorage(object):
    """
    Instances of this class hold instructions for virtual machines. On the first
    setup, all labels are resolved to their indexes and stored for faster
    lookup.
    
    Instructions can only be loaded in bulk and are later read-only. Otherwise
    this object behaves like a list.
    """
    
    def __init__(self):
        self.clear()
    
    def clear(self):
        """
        Removes all instructions and clears the label lookup dictionary.
        """
        self.__l = []
        self.__lbl = {}
    
    def load(self, instructions):
        """
        Load instructions into the program storage and do the initial setup.
        Clears the program storage first.
        """
        self.clear()
        
        i = 0
        for instr in instructions:
            self.__l.append(instr)
            if instr.label != None:
                self.__lbl[instr.label] = i
            i += 1
    
    def ptr(self, loc):
        """
        Returns a pointer object pointing to the specified instruction (a.k.a.
        an instruction pointer). If `loc` is a string, it will be run through
        `indexOfLabel` first.
        """
        if isinstance(loc, str):
            loc = self.indexOfLabel(loc)
        return Pointer(self, loc)
    
    def indexOfLabel(self, label):
        """
        Looks up the index of a label within the program storage. Will raise a
        key error if not found.
        """
        return self.__lbl[label]
    
    def __len__(self):
        return len(self.__l)
    
    def __getitem__(self, key):
        return self.__l[int(key)]
    
    def dump(self):
        """
        Prints all instructons in a readable form to stdout.
        """
        i = 0
        for obj in self.__l:
            print "%2d:" % i, obj
            i += 1
    
    def __str__(self):
        return "PS"
    
    def __repr__(self):
        return "ProgramStorage(%s)" % repr(self.__l)

class Stack(ROBroker):
    """
    Instances of this class represent stacks for virtual machines. They act
    mostly like a python list, but you can also assign values to places that
    don't exist yet; in that case the object will simply resize its internal
    list.
    
    Also, stacks work together with pointer objects. To prevent pointers from
    being modified from outside, every pointer object which is set in a stack
    will be copied.
    """
    
    def __init__(self, values = None):
        self.__l = values if values != None else []
    
    def __len__(self):
        return len(self.__l)
    
    def __getitem__(self, key):
        return self.__l[int(key)]
    
    def __setitem__(self, key, value):
        key = int(key)
        resizing = False
        if key >= len(self.__l):
            resizing = True
            self.notifyRangeWillIncrease(len(self.__l), key)
            self.__l += [None] * (key - len(self.__l) + 1)
        else:
            self.notifyRangeWillChange(key, key)
        
        if isinstance(value, Pointer):
            self.__l[key] = value.copy()
        else:
            self.__l[key] = value
        
        if resizing:
            self.notifyRangeDidIncrease()
        else:
            self.notifyRangeDidChange()
    
    def clear(self):
        if len(self.__l) == 0:
            return
        
        self.notifyRangeWillDecrease(0, len(self.__l)-1)
        self.__l = []
        self.notifyRangeDidDecrease()
    
    def append(self, value):
        self.notifyRangeWillIncrease(len(self.__l), len(self.__l))
        self.__l.append(value)
        self.notifyRangeDidIncrease()
    
    def pop(self, index = -1):
        if index < 0:
            index = len(self.__l) + index
        self.notifyRangeWillDecrease(index, index)
        item = self.__l.pop(index)
        self.notifyRangeDidDecrease()
        return item
    
    def ptr(self, loc):
        """Returns a pointer object pointing to the specified location."""
        return Pointer(self, loc)
    
    def dump(self):
        """
        Prints all contents in a readable form to stdout.
        """
        i = 0
        for obj in self.__l:
            print "%2d:" % i, obj
            i += 1
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.__l))
    
    def __str__(self):
        return self.__class__.__name__[0]

class Heap(Stack):
    """
    Instances of this class represent heaps for virtual machines. They work
    similar to stacks, but provide means to simplify heap object creation.
    """
    
    def new(self, value):
        """
        Adds a new heap object to the heap and returns a pointer object to its
        location.
        """
        p = Pointer(self, len(self))
        self.append(value)
        return p

class HeapObjAttr(object):
    """
    Descriptor for heap object attributes. Will be filled by the heap object
    constructor in the order of occurrence within the class declaration.
    
    Note: Heap object attributes are read-only.
    """
    
    def __init__(self):
        frame = sys._getframe(1)
        if not frame.f_locals.has_key("attrs"):
            frame.f_locals["attrs"] = [self]
            self.order = 0
        else:
            self.order = len(frame.f_locals["attrs"])
            frame.f_locals["attrs"].append(self)
    
    def __get__(self, instance, owner):
        if instance == None: return self
        return instance.values[self.order]
    
    def __delete__(self, instance):
        pass

class HeapObject(object):
    """
    This class is the base class for all heap objects. It provides the `tag`
    attribute that will return the class name and an automatic constructor based
    on the attribute descriptors which can be found.
    
    Note: The constructor will create copies of pointer objects, so they can't
    be modified from outside. Also, heap objects are immutable.
    """
    
    def __init__(self, *args):
        if not hasattr(self, "attrs"):
            if len(args) > 0:
                raise TypeError("__init__() takes exactly 1 argument (%d given)" % len(args))
        elif len(args) != len(self.attrs):
            raise TypeError("__init__() takes exactly %d arguments (%d given)" % (len(self.args), len(args)))
        else:
            self.values = []
            for arg in args:
                if isinstance(arg, Pointer):
                    self.values.append(arg.copy())
                else:
                    self.values.append(arg)
    
    @property
    def tag(self):
        return self.__class__.__name__
    
    def __repr__(self):
        return "%s(%s)" % (self.tag, repr(self.values)[1:-1])
    
    def __str__(self):
        svalues = []
        for v in self.values:
            if isinstance(v, list):
                svalues.append("[" + ", ".join(map(str, v)) + "]")
            else:
                svalues.append(str(v))
        return "%s{%s}" % (self.tag, ", ".join(svalues))

class InterpreterError(Exception):
    """
    Marker exception for errors raised by the interpreter.
    """

class InterpreterBreakpoint(Exception):
    """
    Marker exception which occurs on a breakpoint.
    """

class InterpreterHalt(Exception):
    """
    Marker exception which occurs on halt.
    """

def error(descr):
    """
    Small helper function that raises an InterpreterError with the given
    description.
    """
    raise InterpreterError(descr)
