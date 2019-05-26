import Prefix
import traceback

class Halt(Exception):
	def __init__(self, value = None):
		self.value = value

def justHalt(value):
	raise Halt(nil)

def doHalt(value):
	raise Halt(value)

class TailCallError(Exception):
	pass



class Binding(object):
	def __init__(self, target):
		self.target = target



class GlobalEnv(object):
	genv = None
	def __init__(self, vars):
		self.vars = {k : Binding(v) for k, v in vars.items()}
		self.parent = None
		GlobalEnv.genv = self
	
	def get(self, name):
		return self.vars[name].target
	
	def set(self, name, value):
		if name in self.vars:
			self.vars[name].target = value
		else:
			self.vars[name] = Binding(value)




class Func(object):
	def __init__(self, parent, ntemps):
		self.vars = parent.vars.copy() if isa(parent, Func) else {}
		self.temps = [None for i in range(ntemps)]
	
	def get(self, name):
		if name in self.vars:
			return self.vars[name].target
		return GlobalEnv.genv.get(name)
	
	def getSafe(self, name):
		try:
			return self.get(name)
		except KeyError:
			return nil
	
	def set(self, name, value):
		if name in self.vars:
			self.vars[name].target = value
		else:
			GlobalEnv.genv.set(name, value)
	
	def setLocal(self, name, value):
		self.vars[name] = Binding(value)
	
	def makeExplicitCont(self, method):
		return lambda dummy, *args: method(*args)
	
	#This is not necessary, because
	#1. Each invocation of the function is a different instance, so calling the fn surrounding the ccc can't affect the temps in the continuation, and
	#2. The continuation won't set the temps that it's waiting for, so calling the continuation multiple times can't affect the relevant temps.
	#1. is stupid and should be fixed.
	# def makeExplicitCont(self, method):
		# saved = self.temps[:]
		# def cont(dummy, *args):
			# self.temps[:] = saved
			# return method(*args)
		# return cont


def _wrap(f, *args):
	while True:
		#print(f, k, args)
		if type(f) == type:
			f = f()
		f, *args = f(*args)

def wrap(f, *args):
	try:
		_wrap(f, *args)
	except Halt as e:
		return e.value


internals = {
	# '__builtins__' : {
		# 'Halt' : Halt,
		# 'TailCall' : TailCall,
		# 'Func' : Func,
		# '__name__' : 'Temp',
		# '__build_class__' : __build_class__,
		# 'Sym' : Sym,
		# 'nil' : nil,
		# 't' : t,
		# 'klipFalse' : klipFalse,
		# 'KlipList' : KlipList,
		# 'KlipHash' : KlipHash,
		# 'KlipStr' : KlipStr,
		# 'SpliceWrapper' : SpliceWrapper,
		# 'flatten' : flatten,
	# },
	'Func' : Func,
	'Halt' : Halt,
}


if __name__ == '__main__':
	import dis
	
	dis.dis(wrap)
	
	from Asm import Asm
	
	a = Asm(
		['f'],
		'args',
		['e'],
		[], [],
	)
	
	a.load('args')
	a.load('f')
	
	a.label('loop_start')
	a.load('type')
	a.add('DUP_TOP_TWO')
	a.add('ROT_TWO')
	a.add('CALL_FUNCTION', 1)
	a.comp('==')
	a.add('POP_JUMP_IF_FALSE', 'after_function_instantiation')
	
	a.add('CALL_FUNCTION', 0)
	
	a.label('after_function_instantiation')
	
	a.add('ROT_TWO')
	a.add('CALL_FUNCTION_EX', 0)
	a.add('UNPACK_EX', 1)
	a.add('JUMP_ABSOLUTE', 'loop_start')
	
	
	f = a.makeF(
		'_wrap',
		{'Halt' : Halt, 'type' : type, 'print' : print},
		None,
		None
	)
	
	print()
	dis.dis(f)
	
	_wrap = f
	
	import sys, traceback, builtins
	from Preprocess import preprocess
	from Tokenize import tokenize
	from Parse import parse
	from Compile import Compiler
	from Defaults import genv
	
	for parm in sys.argv[1:]:
		setattr(builtins, parm, True)
	
	fin = open(sys.argv[1], 'r')
	tree = parse(tokenize(preprocess(fin.read()), sys.argv[1]), sys.argv[1])
	fin.close()
	
	#This is dumb.
	newTree = []
	for xpr in tree:
		if isa(xpr, KlipList):
			if len(xpr) and xpr[0] == Sym('include'):
				fin = open(xpr[1], 'r')
				newTree += parse(tokenize(preprocess(fin.read()), xpr[1]), xpr[1])
				fin.close()
			else:
				newTree.append(xpr)
	
	for xpr in newTree:
		c = Compiler(KlipList(), KlipList([xpr]))			#Possibly the call to macex should go here, and macex should take care of recursion.
		f = c.make()
		f._parent = genv
		
		result = wrap(f(), justHalt)
		if result != nil:									#This is a dumb hack to deal with the fact that we're running each toplevel expression in a separate call to wrap. The halt form actually means something now, if you pass a non-nil argument to it.
			print(result)
			break





