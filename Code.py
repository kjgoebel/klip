import Prefix
import copy


class MachineError(Exception):
	pass


class Env(object):
	def __init__(self, parent, name = None, init = None):
		self.name = name
		if debugEnv:
			s = 'NEW ENV %d(%s)' % (id(self), self.name)
			this = parent
			while this:
				s += ' -> %d(%s)' % (id(this), this.name)
				this = this.parent
			print(s)
		self.parent = parent
		self.vars = {}
		
		self.args = []
		self.argPos = 0
		
		if init:
			for k, v in init.items():
				self.vars[Sym(k)] = v
	
	def arg(self):
		ret = self.args[self.argPos]
		self.argPos += 1
		return ret
	
	def defArg(self):
		if self.argPos < len(self.args):
			ret = self.args[self.argPos]
			self.argPos += 1
			return ret
		return None
	
	def restArg(self):
		ret = KlipList(self.args[self.argPos:])
		self.argPos = len(self.args)
		return ret
	
	def setArgs(self, args):
		self.args = args
		self.argPos = 0
	
	def get(self, name):
		if name in self.vars:
			ret = self.vars[name]
			if isa(ret, Func) and ret.name is None:
				ret.name = name
			return ret
		if self.parent == None:
			raise NameError('Name %s not found.' % name)
		return self.parent.get(name)
	
	def setLocal(self, name, value):
		self.vars[name] = value
	
	def set(self, name, value):
		if name in self.vars or self.parent == None:
			self.vars[name] = value
		else:
			self.parent.set(name, value)
	
	def __str__(self):
		return str(id(self))
	def __repr__(self):
		return str(id(self))
	
	def dump(self, ignore = {}):
		print(
			'\t',
			id(self),
			self.args,
			{k : v for k, v in self.vars.items() if not (k in ignore or isa(k, Sym) and k.name in ignore)}
		)
		if self.parent:
			self.parent.dump(ignore)



import sys

class Inst(object):
	pass

def makeInstClass(name, *fieldNames, **defaults):
	def _init(self, *args, **kwargs):
		self.__dict__.update(defaults)
		for i in range(len(args)):
			setattr(self, fieldNames[i], args[i])
		self.__dict__.update(kwargs)
	def _repr(self):
		ret = '%s<<%s>>' % (
			name,
			', '.join([
				repr(getattr(self, fieldNames[i]))
				for i in range(len(fieldNames))
			])
		)
		if hasattr(self, 'notes'):
			ret += '\t%s' % self.notes
		return ret
	sys.modules[__name__].__dict__[name] = type(name, (Inst, ), dict(
		__init__ = _init,
		__repr__ = _repr
	))

makeInstClass('Lit', 'value')
makeInstClass('Ld', 'sym')
makeInstClass('St', 'sym')
makeInstClass('Jmp', 'skip')
makeInstClass('Br', 'skip')
makeInstClass('LitFunc', 'func', 'env', 'parmList', 'pos', 'stack', stack = None)		#It's just the evaluation stack! There's no control stack!
makeInstClass('Cont', 'parmList', 'pos', 'poppage', poppage = None)
makeInstClass('Call', 'nargs')
makeInstClass('Pop')
makeInstClass('Fn', 'parmList', 'body')
makeInstClass('Halt')

makeInstClass('Arg', 'message')
makeInstClass('DefArg', 'pos')
makeInstClass('RestArg')
makeInstClass('NoArgsLeft', 'message')
makeInstClass('StLocal', 'sym')

#Really?
makeInstClass('Splice')


def dumpCode(code):
	for i in range(len(code)):
		inst = code[i]
		print('\t%d\t%s' % (i, repr(inst)))

class Func(object):
	def __init__(self, env, code):
		self.env = env
		self.code = code
		self.name = None
	
	def __repr__(self):
		if self.name:
			return '%d (%s)' % (id(self.env), self.name)
		return str(id(self.env))
