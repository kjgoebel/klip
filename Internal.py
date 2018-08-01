import Prefix
import traceback

class Halt(Exception):
	def __init__(self, value = None):
		self.value = value

def justHalt(value):
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
	
	def makeCont(self, method):
		saved = self.temps[:]
		def cont(*args):
			self.temps[:] = saved
			method(*args)
		return cont
	
	def makeDummyCont(self, method):
		saved = self.temps[:]
		def cont(dummy, *args):
			self.temps[:] = saved
			method(*args)
		return cont


def wrap(f, k, *args):
	while True:
		#print(f, k, args)
		if type(f) == type:
			f = f()
		try:
			f(k, *args)
		except TailCall as e:
			f, k, args = e.f, e.k, e.args
		except Halt as e:
			return e.value
		else:
			raise TailCallError('There was no tail call. (%s, %s, %s)' % (f, k, args))


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
	'TailCall' : TailCall,
}





