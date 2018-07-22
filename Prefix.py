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
	
	class KlipCollection(object):
		def __call__(self, env, *args):
			try:
				item = self[args[0]]
			except IndexError:
				return nil
			
			if len(args) > 1:
				return item(env, args[1:])
			return item
		
		def __hash__(self):
			return id(self)
		def __eq__(self, other):
			return id(self) == id(other)
		def __neq__(self, other):
			return id(self) != id(other)
	
	def _makeIx(ix):
		if isa(ix, KlipList):
			return slice(*[None if x == t else x for x in ix])
		return ix
	
	class KlipList(KlipCollection, list):
		def __getitem__(self, index):
			ret = list.__getitem__(self, _makeIx(index))
			if type(ret) == list:
				return KlipList(ret)			#I'm not happy about constructing another list here.
			return ret
		
		def set(self, index, value):
			ix = _makeIx(index)
			ret = self[ix]
			if value == nil:
				del self[ix]
			else:
				list.__setitem__(self, ix, value)
			return ret
		
		def insert(self, index, value):
			list.insert(self, index, value)
			return nil
		
		def append(self, value):
			list.append(self, value)
			return nil
		
		def __str__(self):
			return '(%s)' % ' '.join([str(x) for x in self])
		def __repr__(self):
			return '(%s)' % ' '.join([repr(x) for x in self])
	builtins.KlipList = KlipList
	
	class KlipHash(KlipCollection, dict):
		def set(self, index, value):
			try:
				ret = self[index]
			except KeyError:
				ret = nil
			
			if value == nil:
				del self[index]
			else:
				dict.__setitem__(self, index, value)
			
			return ret
		
		def __str__(self):
			return '{%s}' % ' '.join(['%s %s' % (k, v) for k, v in self.items()])
		def __repr__(self):
			return '{%s}' % ', '.join(['%s: %s' % (repr(k), repr(v)) for k, v in self.items()])
	builtins.KlipHash = KlipHash
	
	class KlipStr(str):
		def __call__(self, env, *args):
			return KlipStr(self % args)
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
	
	
	def klipFalse(x):
		try:
			return len(x) == 0
		except TypeError:
			return x == nil
	builtins.klipFalse = klipFalse
	
	
	builtins.debugTrace = False
	builtins.debugCompile = False
	builtins.debugEnv = False

