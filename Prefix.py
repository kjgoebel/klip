import builtins

if not hasattr(builtins, '_prefix'):
	builtins._prefix = True
	
	builtins.isa = isinstance
	
	class Sym(object):
		def __init__(self, name):
			self.name = name
		
		def __str__(self):
			return self.name
		def __repr__(self):
			return self.name
		
		def __hash__(self):
			return hash(self.name)
		def __eq__(self, other):
			# if type(other) != Sym:			#Don't use isa because GenSyms are also Sym instances.
				# return False
			if not isa(other, Sym):
				return False
			return self.name == other.name
		def __neq__(self, other):
			if type(other) != Sym:
				return True
			return self.name != other.name
	builtins.Sym = Sym
	
	# class GenSym(Sym):
		# def __repr__(self):
			# return '(%s:%d)' % (self.name, id(self))
			
		# def __hash__(self):
			# return hash(id(self))
		# def __eq__(self, other):
			# return self is other
		# def __neq__(self, other):
			# return not self is other
	# builtins.GenSym = GenSym
	
	nil = Sym('nil')
	builtins.nil = nil
	t = Sym('t')
	builtins.t = t
	
	class KlipList(list):
		def __call__(self, env, *args):
			if isa(args[0], KlipList):
				ix = slice(*args[0])
			else:
				ix = args[0]
			ret = self[ix]
			if isa(ret, KlipList):
				return ret(env, args[1:])
			return ret
		
		def __getitem__(self, index):
			ret = list.__getitem__(self, index)
			if type(ret) == list:
				return KlipList(ret)			#I'm not happy about constructing another list here.
			return ret
		
		def __hash__(self):
			return id(self)
		
		def __str__(self):
			return '(%s)' % ' '.join([str(x) for x in self])
		def __repr__(self):
			return str(self)
	builtins.KlipList = KlipList
	
	class KlipHash(dict):
		def __call__(self, env, *args):
			if len(args) == 0:
				return len(self)
			
			if len(args) == 1:
				try:
					return self[args[0]]
				except KeyError:
					return nil
			
			if len(args) == 2:
				if args[1] == nil:
					try:
						return self.pop(args[0])
					except KeyError:
						return nil
				if args[0] == nil:
					raise ValueError('nil cannot be a key in a hash.')
				self[args[0]] = args[1]
				return nil
			
			raise ValueError('hash object called with more than two arguments.')
		
		def __str__(self):
			return '{%s}' % ' '.join(['%s %s' % (k, v) for k, v in self.items()])
		def __repr__(self):
			return 'KlipHash({%s})' % ', '.join(['%s: %s' % (repr(k), repr(v)) for k, v in self.items()])
	builtins.KlipHash = KlipHash
	
	class KlipStr(str):
		def __call__(self, env, *args):
			if len(args) == 0:
				return len(self)
			
			if len(args) == 1:
				return KlipStr(self[args[0]])
			
			if args[0] != nil:
				raise ValueError('For string formatting, the first argument must be nil.')
			return KlipStr(self % args[1:])		#This is a gruesome, heinous hack. But man, I really want to be able to format strings by calling them.
	builtins.KlipStr = KlipStr
	
	class SpliceWrapper(list):
		pass
	builtins.SpliceWrapper = SpliceWrapper
	
	def flatten(args):
		for arg in args:
			if isa(arg, SpliceWrapper):
				yield from flatten(arg)
			else:
				yield arg
	builtins.flatten = flatten
	
	
	builtins.debugTrace = False
	builtins.debugCompile = False
	builtins.debugEnv = False

