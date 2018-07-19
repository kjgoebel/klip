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
		
		if init:
			for k, v in init.items():
				self.vars[Sym(k)] = v
	
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
			{k : v for k, v in self.vars.items() if not (k in ignore or isa(k, Sym) and k.name in ignore)}
		)
		if self.parent:
			self.parent.dump(ignore)


# class Binding(object):
	# def __init__(self, target):
		# self.target = target

# class Env(object):
	# _globalEnv = None
	
	# def __init__(self, parent, name = None, init = None):
		# self.name = name
		# self.parent = parent
		
		# if not parent:
			# Env._globalEnv = self
		
		# if debugEnv:
			# s = 'NEW ENV %s' % self
			# this = parent
			# while this:
				# s += ' -> %s' % this
				# this = this.parent
			# print(s)
		
		# self.vars = {}
		# if parent:
			# #We copy every entry in parent, unless it's in the global 
			# #environment, or it's a special compiler name. This is supposed to 
			# #be an optimization. Creating a new Env takes longer, but looking 
			# #up a symbol is faster because there are only two places the 
			# #binding could be (self.vars or Env._globalEnv.vars).
			# for k, v in parent.vars.items():
				# if not k in Env._globalEnv.vars:
					# if not k.name.startswith(' '):		#Names begining with space are magically always local. They are (ab)used by the compiler.
						# self.vars[k] = v
						# if debugEnv:
							# print('\t\tINHERITED %s' % k)
		
		# if init:
			# for k, v in init.items():
				# self.vars[Sym(k)] = Binding(v)
	
	# def get(self, sym):
		# try:
			# return self.vars[sym].target
		# except KeyError:
			# try:
				# return Env._globalEnv.vars[sym].target
			# except KeyError:
				# raise NameError('Symbol %s not found.' % sym)
	
	# def setLocal(self, sym, value):
		# try:
			# binding = self.vars[sym]
		# except:
			# self.vars[sym] = Binding(value)
		# else:
			# binding.target = value
	
	# def set(self, sym, value):
		# try:
			# binding = self.vars[sym]
		# except:
			# try:
				# binding = Env._globalEnv.vars[sym]
			# except:
				# binding = Binding(value)
				# Env._globalEnv.vars[sym] = binding
			# else:
				# binding.target = value
		# else:
			# binding.target = value
	
	# def __str__(self):
		# return '%d <%s>' % (id(self), self.name)
	# def __repr__(self):
		# return '%d <%s>' % (id(self), self.name)
	
	# def dump(self, ignore = {}):
		# try:
			# print(
				# '\t',
				# id(self),
				# {k : v.target for k, v in self.vars.items() if not (k in ignore or k.name in ignore)}
			# )
		# except Exception as e:
			# print(self.vars)
			# raise e


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
		ret = '%s((%s))' % (
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

#Really?
makeInstClass('Splice')
makeInstClass('EndCap')


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
