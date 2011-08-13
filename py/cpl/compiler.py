
__all__ = ["compile", "parse", "optimize", "instrs", "compile_options"]

from cStringIO import StringIO
from time import time
import operator

from pyparsing import Literal, Suppress, Keyword, Regex, Combine, Group, Forward, Word, OneOrMore, ZeroOrMore, Optional, White, NotAny
from pyparsing import alphas, nums, oneOf, delimitedList

from compiler_base import Token, Instruction, InstructionSet, InstructionLabel
from compiler_base import putLabel, newOptimizerBase

#=============================================================================#
#                               Token objects                                 #
#=============================================================================#

class Integer(Token):
    Attributes = ["value"]

class Float(Token):
    Attributes = ["value"]

def numberFromParser(s, loc, toks):
    if len(toks) == 2:
        return Float(float(toks[0]+toks[1]), loc=loc)
    else:
        return Integer(int(toks[0]), loc=loc)

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

class FunName(Token):
    Attributes = ["module", "name"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(str(toks[0]), str(toks[1]), loc=loc)

class Tuple(Token):
    Attributes = ["elements"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks.asList(), loc=loc)

class EmptyList(Token):
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(loc=loc)

class List(Token):
    Attributes = ["head", "tail"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        tail = toks[-1]
        if tail is None:
            obj = EmptyList()
        else:
            obj = tail
        
        for i in xrange(len(toks)-2,-1,-1):
            obj = cls(toks[i], obj)
        
        return obj

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

class Assignment(Token):
    Attributes = ["pattern", "expr"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks[0], toks[1], loc=loc)

class FunApplExpression(Token):
    Attributes = ["fun", "args"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks[0], toks[1:], loc=loc)

class FunExpressionClause(Token):
    Attributes = ["args", "body"]
    
    @property
    def arity(self):
        return len(self.args)
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks[:-1], toks[-1].asList(), loc=loc)

class FunExpression(Token):
    Attributes = ["clauses"]
    
    @property
    def arity(self):
        return len(self.args)
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks.asList(), loc=loc)

class CaseExpressionClause(Token):
    Attributes = ["pattern", "body"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks[0], toks[1].asList(), loc=loc)

class CaseExpression(Token):
    Attributes = ["expr", "clauses"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks[0], toks[1:], loc=loc)

class FunDeclClause(Token):
    Attributes = ["name", "args", "body"]
    
    @property
    def arity(self):
        return len(self.args)
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks[0], toks[1:-1], toks[-1].asList(), loc=loc)

class FunDeclaration(Token):
    Attributes = ["clauses"]
    
    @property
    def name(self):
        return self.clauses[0].name
    
    @property
    def arity(self):
        return self.clauses[0].arity
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks.asList(), loc=loc)

class ModuleAttribute(Token):
    Attributes = ["tag", "value"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        return cls(toks[0], toks[1:], loc=loc)

class Module(Token):
    Attributes = ["attributes", "functions"]
    
    @classmethod
    def fromParser(cls, s, loc, toks):
        attrs = []
        funs = []
        for x in toks:
            if isinstance(x, ModuleAttribute):
                attrs.append(x)
            elif isinstance(x, FunDeclaration):
                funs.append(x)
        return cls(attrs, funs, loc=loc)

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
var = Regex(r'[A-Z][a-zA-Z0-9_]*').setParseAction(Variable.fromParser).setName("variable")
number = (Regex(r'-?([1-9][0-9]*|0)') + Optional(Regex(r'\.[0-9]+'))).setParseAction(numberFromParser).setName("number")

fun_name = (Optional((quoted_atom | simple_atom) + Suppress(":"), default="") + (quoted_atom | simple_atom)).setParseAction(FunName.fromParser).setName("fun_name")

term = Forward().setName("term")

tuple = (Suppress("{") + Optional(delimitedList(term)) + Suppress("}")).setParseAction(Tuple.fromParser).setName("tuple")
list = (Suppress("[") + Optional(delimitedList(term)) + Optional(Suppress("|") + term, default=None) + Suppress("]")).setParseAction(List.fromParser).setName("list")

term << (number | atom | list | tuple)

pattern = Forward().setName("pattern")

p_tuple = (Suppress("{") + Optional(delimitedList(pattern)) + Suppress("}")).setParseAction(Tuple.fromParser).setName("p_tuple")
p_list = (Suppress("[") + Optional(delimitedList(pattern)) + Optional(Suppress("|") + pattern, default=None) + Suppress("]")).setParseAction(List.fromParser).setName("p_list")

pattern << (number | atom | var | p_tuple | p_list)

expr = Forward().setName("expr")

body = Group(delimitedList(expr)).setName("body")

e_tuple = (Suppress("{") + Optional(delimitedList(expr)) + Suppress("}")).setParseAction(Tuple.fromParser).setName("e_tuple")
e_list = (Suppress("[") + Optional(delimitedList(expr)) + Optional(Suppress("|") + expr, default=None) + Suppress("]")).setParseAction(List.fromParser).setName("e_list")

atomic_expr = ((lparen + expr + rparen) | number | atom | var | e_tuple | e_list).setName("atomic_expr")

unaryop = oneOf("+ - not")
arith_multop = oneOf("* / div mod")
arith_addop = oneOf("+ -")
bool_gtlt = oneOf("< > =< >=")
bool_eq = oneOf("== /=")
bool_and = Keyword("and")
bool_or = Keyword("or")

fun_appl_expr = ((fun_name | var) + lparen + Optional(delimitedList(expr)) + rparen).setParseAction(FunApplExpression.fromParser).setName("fun_appl_expr")

assignment_expr = (pattern + Suppress("=") + expr).setParseAction(Assignment.fromParser).setName("assignment_expr")

case_expr_clause = (pattern + Suppress("->") + body).setParseAction(CaseExpressionClause.fromParser)
case_expr = (Keyword("case").suppress() + expr + Keyword("of").suppress() + delimitedList(case_expr_clause, delim=";") + Keyword("end").suppress()).setParseAction(CaseExpression.fromParser).setName("case_expr")

def nextBinOpPrecLevelRAssoc(prev_pl, ops):
    return (prev_pl + ZeroOrMore(ops + prev_pl)).setParseAction(BinaryOp.fromParser)

prec_expr = case_expr | fun_appl_expr | atomic_expr | (unaryop + atomic_expr).setParseAction(UnaryOp.fromParser)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, arith_multop)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, arith_addop)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, bool_gtlt)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, bool_eq)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, bool_and)
prec_expr = nextBinOpPrecLevelRAssoc(prec_expr, bool_or)

fun_expr_clause = (lparen + Optional(delimitedList(pattern)) + rparen + Suppress("->") + body).setParseAction(FunExpressionClause.fromParser)
fun_expr = (Keyword("fun").suppress() + delimitedList(fun_expr_clause, delim=";") + Keyword("end").suppress()).setParseAction(FunExpression.fromParser).setName("fun_expr")

expr << (assignment_expr | fun_expr | prec_expr)

module_attribute = (Suppress("-") + atom + lparen + Optional(delimitedList(expr)) + rparen + Suppress(".")).setParseAction(ModuleAttribute.fromParser)

fun_decl_clause = (fun_name + lparen + Optional(delimitedList(pattern)) + rparen + Suppress("->") + body).setParseAction(FunDeclClause.fromParser)
fun_decl = (delimitedList(fun_decl_clause, delim=";") + Suppress(".")).setParseAction(FunDeclaration.fromParser)

module = ZeroOrMore(module_attribute | fun_decl).setParseAction(Module.fromParser)

#=============================================================================#
#                            Exported Functions                               #
#=============================================================================#

def parse(source):
    #t = time()
    parse_tree = module.parseString(source)[0] #expr.parseString(source)[0]
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
