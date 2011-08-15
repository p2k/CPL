
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

import inspect
from types import FunctionType
from functools import wraps
from cStringIO import StringIO

class Token(object):
    """
    Represents elements in the parse tree.
    
    You need to declare a class-attribute "Attributes" which should hold a list
    of attribute names in your subclasses. That way the `__init__` method will
    pick up the right attributes and store them.
    
    :param loc: an optional location within a source. Should be passed as named
      argument.
    
    .. automethod:: __str__
    .. automethod:: __repr__
    """
    
    Attributes = []
    
    def __init__(self, *args, **kwargs):
        self.loc = kwargs.get("loc")
        got = len(args)
        need = len(self.Attributes)
        if got != need:
            raise TypeError("%s() takes exactly %d argument%s (%d given)" % (self.__class__.__name__, need, "s" if need > 1 else "", got))
        for i in xrange(got):
            name = self.Attributes[i]
            value = args[i]
            setattr(self, name, value)
    
    def tokenName(self):
        """Returns the token's class name."""
        return self.__class__.__name__
    
    def iter(self):
        """
        Returns an iterator over all attributes and their names.
        The iterator yields `(name, value)` tuples.
        """
        for name in self.Attributes:
            yield name, getattr(self, name)
    
    def __pp(self, out, level):
        indent = "    " * (level + 1)
        if len(self.Attributes) == 0:
            out.write("%s {}\n" % (self.tokenName()))
            return
        out.write("%s {\n" % (self.tokenName()))
        for name, attr in self.iter():
            if isinstance(attr, list):
                if len(attr) == 0:
                    out.write("%s%s = []\n" % (indent, name))
                else:
                    out.write("%s%s = [\n" % (indent, name))
                    for entry in attr:
                        if isinstance(entry, Token):
                            out.write("%s    " % (indent))
                            entry.__pp(out, level + 2)
                        else:
                            out.write("%s    %s\n" % (indent, repr(entry)))
                    out.write("%s]\n" % (indent))
            elif isinstance(attr, Token):
                out.write("%s%s = " % (indent, name))
                attr.__pp(out, level + 1)
            else:
                out.write("%s%s = %s\n" % (indent, name, repr(attr)))
        out.write("%s}\n" % ("    " * (level)))
    
    def __str__(self):
        """Pretty-print the token."""
        out = StringIO()
        self.__pp(out, 0)
        return out.getvalue()
    
    def __repr__(self):
        """
        Returns a formal representation of the token, which can be used
        to instantiate a parse tree.
        """
        attrs = [repr(getattr(self, name)) for name in self.Attributes]
        return '%s(%s)' % (self.tokenName(), ",".join(attrs))
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        """
        Subclasses are to override this class method and return a new instance
        of the class initialized with the parser output.
        """
        raise NotImplementedError

class Instruction(object):
    """
    Represents an arbitrary instruction for arbitrary virtual machines.
    
    :param name: the name of the instruction
    :param label: an optional label for the instruction, useful in branching
    
    All other arguments will be kept in `args`.
    """
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.args = args
        self.label = kwargs.get("label", None)
    
    def clone(self):
        """Creates an exact copy of this instruction."""
        if self.label != None:
            return Instruction(self.name, *self.args, label=self.label)
        else:
            return Instruction(self.name, *self.args)
    
    def __repr__(self):
        sargs = "".join(["," + repr(arg) for arg in self.args])
        if self.label != None:
            return 'Instruction(%s%s,label=%s)' % (repr(self.name), sargs, repr(self.label))
        else:
            return 'Instruction(%s%s)' % (repr(self.name), sargs)
    
    def __str__(self):
        sargs = "".join([" " + str(arg) for arg in self.args])
        if self.label != None:
            return '%s: %s%s' % (self.label, self.name, sargs)
        else:
            return '%s%s' % (self.name, sargs)

def makeInstructionConstructor(f):
    args = inspect.getargspec(f).args
    argc = len(args)
    name = f.__name__.replace("_", "")
    @wraps(f)
    def wrapper(*args, **kwargs):
        if len(args) != argc:
            raise TypeError("%s() takes exactly %d argument%s (%d given)" % (f.__name__, argc, "s" if argc > 1 else "", len(args)))
        return Instruction(name, *args, **kwargs)
    wrapper.args = args # For documentation purposes
    return staticmethod(wrapper)

class InstructionSetMetaClass(type):
    """Metaclass for instruction sets. See :class:`InstructionSet`."""
    
    def __new__(meta, classname, bases, classDict):
        for name, obj in classDict.iteritems():
            if isinstance(obj, FunctionType):
                classDict[name] = makeInstructionConstructor(obj)
        return type.__new__(meta, classname, bases, classDict)

class InstructionSet(object):
    """
    This convenience class will decorate all its methods in a way so they are
    static methods, can accept an optional argument `label` and return
    :class:`Instruction` objects initialzed with the returned tuple. This is
    implemented via metaclasses.
    
    It is used to create named instruction constructors more quickly. Subclasses
    are usually called `instrs` for each machine's instruction set.
    """
    
    __metaclass__ = InstructionSetMetaClass

class InstructionLabel(object):
    """
    Instances of this class provide a simple mechanism to create unique labels
    for one compiling pass. Usually the class is instantiated once per compiler
    module.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Resets the internal label counter."""
        self.label_counter = -1
    
    def new(self):
        """Returns a new label of the form 'lX' where X is a serial number."""
        self.label_counter += 1
        return 'l%d' % (self.label_counter)

def putLabel(label, instrs):
    """
    Helper function which puts a label onto the first instruction in the list
    `instrs` or inserts a `nop` instruction with the label if the list is empty.
    """
    if len(instrs) == 0:
        instrs.append(Instruction("nop"))
    instrs[0].label = label
    return instrs

class AbstractOptimizer(object):
    """
    Abstract base class for optimizers.
    
    Note: Please do not inherit from this class directly, instead inherit from a
    set-up subclass of this class which gets returned by :func:`newOptimizerBase`.
    """
    
    min_instrs = 2
    """
    Denotes the minimum instructions needed for this optimizer to work. This can
    then be used as an assertion for the `optimize` method.
    """
    
    @classmethod
    def optimize(cls, instructions):
        """
        Subclasses must overwrite this method.
        
        This method should return None if no optimization could be done or
        a tuple (`n`, `new_instrs`) where `n` is the number of instructions that
        should be consumed and `new_instrs` is a list of new instructions.
        
        The base implementation provides the common `nop` remover. It removes
        `nop` instructions which might have been produced by if-statements
        or loops. If the instruction has a label it will be carried over to the
        next instruction, if that one doesn't already have a label.
        """
        
        if instructions[0].name == "nop":
            if instructions[0].label != None and instructions[1].label == None:
                new_instr = instructions[1].clone()
                new_instr.label = instructions[0].label
                return (2, [new_instr])
            elif instructions[0].label == None:
                return (1, [])
        return None
    
    @classmethod
    def run_optimizers(cls, instructions):
        """
        Optimizes a set of instructions.
        
        Runs all instructions subsequently through all defined optimizers by
        calling `run_first_optimizer`.
        """
        
        srcinstrs = list(instructions)
        optinstrs = []
        
        while len(srcinstrs) > 0:
            result = cls.run_first_optimizer(srcinstrs)
            
            if result != None:
                n, new_instrs = result
                del srcinstrs[:n]
                srcinstrs[0:0] = new_instrs
            else:
                optinstrs.append(srcinstrs.pop(0))
        
        return optinstrs
    
    @classmethod
    def run_first_optimizer(cls, instructions):
        """
        Returns the results of the first optimizer which yields a success or
        None, if no optimzier worked for the given instruction stack.
        """
        for optimizer in cls.__metaclass__.all_optimizers:
            if len(instructions) < optimizer.min_instrs:
                continue
            
            result = optimizer.optimize(instructions)
            if result != None:
                return result
        
        return None

def newOptimizerBase():
    """
    Dynamically creates a new base class for optimizers. Inheriting from the
    returned class will automatically register it to be run on a call to
    `run_optimizers` which is a special class method.
    """
    
    class OptimizerMetaClass(type):
        all_optimizers = []
        
        def __new__(meta, classname, bases, classDict):
            if bases != (AbstractOptimizer,):
                if not classDict.has_key("optimize"):
                    raise ValueError("The optimize method must be overridden by subclasses!")
            optimizer_class = type.__new__(meta, classname, bases, classDict)
            meta.all_optimizers.append(optimizer_class)
            return optimizer_class
    
    class Optimizer(AbstractOptimizer):
        __metaclass__ = OptimizerMetaClass
    
    return Optimizer
