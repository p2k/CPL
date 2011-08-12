
__all__ = ["compile", "parse", "optimize", "instrs", "compile_options"]

from cStringIO import StringIO
from time import time
import operator

from pyparsing import Literal, Suppress, Keyword, Regex, Combine, Forward, Word, OneOrMore, ZeroOrMore, Optional, White, NotAny
from pyparsing import alphas, nums, oneOf, delimitedList

from compiler_base import Token, Instruction, InstructionSet, InstructionLabel
from compiler_base import putLabel, newOptimizerBase

#=============================================================================#
#                               Token objects                                 #
#=============================================================================#

class Integer(Token):
    Attributes = ["value"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(int(toks[0]), loc=loc)

class Variable(Token):
    Attributes = ["name"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(str(toks[0]), loc=loc)

class Atom(Token):
    Attributes = ["name"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(str(toks[0]), loc=loc)

class UnaryOp(Token):
    Attributes = ["op", "expr"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(str(toks[0]), toks[1], loc=loc)

class BinaryOp(Token):
    Attributes = ["lexpr", "op", "rexpr"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        """
        Creates a tree of BinaryOp tokens from a set of operators and operands
        of the same level from left to right. Single operands are left untouched.
        """
        sumExpr = toks[0]
        for i in xrange(1, len(toks), 2):
            sumExpr = cls(sumExpr, str(toks[i]), toks[i+1], loc=loc)
        return sumExpr

class FunApplExpression(Token):
    Attributes = ["fun", "args"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks[0], toks[1:], loc=loc)

class FunExpression(Token):
    Attributes = ["args", "body_expr"]
    
    @property
    def arity(self):
        return len(self.args)
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks[:-1], toks[-1], loc=loc)

class FunDeclaration(Token):
    Attributes = ["name", "args", "body"]
    
    @property
    def arity(self):
        return len(self.args)
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks[0], toks[1:-1], toks[-1], loc=loc)

#=============================================================================#
#                               Instruction set                               #
#=============================================================================#

class instrs(InstructionSet):
    def nop():
        """
        Does not do anything. This is needed temporarily to add labels to
        following instructions on branching operations.
        """

#=============================================================================#
#                        Helper objects for compiling                         #
#=============================================================================#

#=============================================================================#
#                              Code functions                                 #
#=============================================================================#

instructionLabel = InstructionLabel()

#=============================================================================#
#                               Optimization                                  #
#=============================================================================#

Optimizer = newOptimizerBase()

#=============================================================================#
#                                  Parser                                     #
#=============================================================================#

lparen = Suppress("(")
rparen = Suppress(")")
reserved = "and andalso band bnot bor bsl bsr bxor case div end fun if not of or orelse when xor".split()
reserved = reduce(operator.or_, map(Keyword, reserved))

simple_atom = (NotAny(reserved).suppress() + Regex(r'[a-z][a-zA-Z0-9_]*'))
quoted_atom = (Suppress("'") + Regex(r'[a-zA-Z0-9_ ]+') + Suppress("'"))

atom = (quoted_atom | simple_atom).setParseAction(Atom.fromParser).setName("atom")

integer = Regex(r'-?([1-9][0-9]*|0)').setParseAction(Integer.fromParser).setName("integer")

var = Regex(r'[A-Z][a-zA-Z0-9_]*').setParseAction(Variable.fromParser).setName("variable")

expr = Forward().setName("expr")

atomic_expr = ((lparen + expr + rparen) | integer | var | atom).setName("atomic_expr")

unaryop = oneOf("+ - not")
arith_multop = oneOf("* / div mod")
arith_addop = oneOf("+ -")
bool_gtlt = oneOf("< > <= >=")
bool_eq = oneOf("== <>")
bool_and = Keyword("and")
bool_or = Keyword("or")

def nextBinOpPrecLevelRAssoc(prev_pl, ops):
    return (prev_pl + ZeroOrMore(ops + prev_pl)).setParseAction(BinaryOp.fromParser)

prec_expr = atomic_expr | (unaryop + atomic_expr).setParseAction(UnaryOp.fromParser)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, arith_multop)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, arith_addop)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, bool_gtlt)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, bool_eq)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, bool_and)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, bool_or)

expr << (prec_expr)

fun_decl = (atom + lparen + delimitedList(var) + rparen + Suppress("->") + expr + Suppress(".")).setParseAction(FunDeclaration.fromParser)

#=============================================================================#
#                            Exported Functions                               #
#=============================================================================#

def parse(source):
    #t = time()
    parse_tree = expr.parseString(source)[0]
    #t = time() - t
    #print "Parse time: %dms" % (int(t*1000))
    return parse_tree

def compile(source, options = {}):
    """
    
    This compiler accepts the `optimize` option (`True` by default).
    """
    if isinstance(source, basestring):
        parse_tree = parse(source)
    else:
        parse_tree = source
    
    instructionLabel.reset()
    t = time()
    compiled_instructions = code_P(parse_tree)
    t = time() - t
    print "Compile time: %dms" % (int(t*1000))
    if options.get("optimize", True):
        return optimize(compiled_instructions)
    else:
        return compiled_instructions

compile_options = [
    ("optimize", "Optimize", "Runs the instructions through the optimizer on compiling.", 'bool', True),
]

def optimize(instructions):
    t = time()
    optinstrs = Optimizer.run_optimizers(instructions)
    t = time() - t
    print "Optimize time: %dms" % (int(t*1000))
    
    return optinstrs
