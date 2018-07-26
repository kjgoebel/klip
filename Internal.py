import Prefix
import traceback

class Halt(Exception):
	def __init__(self, value = None):
		self.value = value

def justHalt(value):
	raise Halt(value)


class TailCall(Exception):
	def __init__(self, f, k, *args):
		self.f = f
		self.k = k
		self.args = args


class GlobalEnv(object):
	def __init__(self, vars):
		self.vars = vars
	
	def get(self, name):
		return self.vars[name]
	
	def set(self, name, value):
		self.vars[name] = value



class Func(object):
	def __init__(self, parent, ntemps):
		self.parent = parent
		self.vars = {}
		self.temps = [None for i in range(ntemps)]
	
	def get(self, name):
		#This is slow?
		try:
			return self.vars[name]
		except KeyError:
			return self.parent.get(name)
	
	def getSafe(self, name):
		try:
			return self.get(name)
		except KeyError:
			return nil
	
	def set(self, name, value):
		if name in self.vars:
			self.vars[name] = value
		else:
			self.parent.set(name, value)
	
	def setLocal(self, name, value):
		self.vars[name] = value
	
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
		if isa(f, type):
			f = f()
		try:
			f(k, *args)
		except TailCall as e:
			f, k, args = e.f, e.k, e.args
		except Halt as e:
			return e.value


internals = {
	'__builtins__' : {
		'Halt' : Halt,
		'TailCall' : TailCall,
		'Func' : Func,
		'__name__' : 'Temp',
		'__build_class__' : __build_class__,
		'Sym' : Sym,
		'nil' : nil,
		't' : t,
		'klipFalse' : klipFalse,
		'KlipList' : KlipList,
		'KlipHash' : KlipHash,
		'KlipStr' : KlipStr,
	},
}





