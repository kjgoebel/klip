import builtins

if not hasattr(builtins, '_prefix'):
	builtins._prefix = True
	
	builtins.isa = isinstance
	
	
	
	import string
	_allowed = set(string.ascii_letters + string.digits)
	
	class Sym(object):
		def __init__(self, name):
			self.name = name
		
		def __str__(self):
			return self.name
		def __repr__(self):
			return 'Sym("%s")' % self.name
		
		def __hash__(self):
			return hash(self.name)
		def __eq__(self, other):
			if not isa(other, Sym):
				return False
			return self.name == other.name
		def __neq__(self, other):
			if type(other) != Sym:
				return True
			return self.name != other.name
		
		def pyx(self):
			return '_' + ''.join([c if c in _allowed else '_%d_' % ord(c) for c in self.name])
	builtins.Sym = Sym
	
	nil = Sym('nil')
	builtins.nil = nil
	t = Sym('t')
	builtins.t = t
	
	class KlipCollection(object):
		def __call__(self, k, *args):
			try:
				item = self[args[0]]
			except IndexError:
				return k, nil
			except KeyError:
				return k, nil
			
			if len(args) > 1:
				return tuple((item, k, *args[1:]))
			return k, item
	
	def _makeIx(ix):
		if isa(ix, KlipList):
			return slice(*[None if x == t else x for x in ix])
		return ix
	
	class KlipList(KlipCollection, list):
		def __init__(self, *args, **kwargs):
			list.__init__(self, *args, **kwargs)
			self._hash = None
		
		def __getitem__(self, index):
			ret = list.__getitem__(self, _makeIx(index))
			if type(ret) == list:
				return KlipList(ret)			#I'm not happy about constructing another list here.
			return ret
		
		def set(self, index, value):
			self._hash = None
			ix = _makeIx(index)
			ret = self[ix]
			list.__setitem__(self, ix, value)
			return ret
		
		def insert(self, index, value):
			self._hash = None
			list.insert(self, index, value)
			return nil
		
		def append(self, value):
			self._hash = None
			list.append(self, value)
			return nil
		
		def __str__(self):
			return '(%s)' % ' '.join([str(x) for x in self])
		def __repr__(self):
			return 'KlipList([%s])' % ', '.join([repr(x) for x in self])
		
		def __hash__(self):
			if self._hash is None:
				self._hash = sum(map(hash, self))			#****This is horrifically slow!
			return self._hash
	
	#Redefine all other methods of list that might change the hash value, so 
	#that they invalidate _hash.
	#reverse and sort don't actually change the hash value.
	
	#We have to do an absurd dance to get around the static binding of 
	#funcName in the loop below:
	def _makeWrapperFunc(cls, name):
		def temp(self, *args, **kwargs):
			self._hash = None
			ret = getattr(cls, name)(self, *args, **kwargs)
			return nil if ret is None else ret
		return temp
	
	for funcName in ['clear', 'extend', 'remove']:
		setattr(KlipList, funcName, (lambda cls = list, name = funcName: _makeWrapperFunc(cls, name))())
	
	builtins.KlipList = KlipList
	
	class KlipHash(KlipCollection, dict):
		def __init__(self, *args, **kwargs):
			dict.__init__(self, *args, **kwargs)
			self._hash = None
			for k, v in self.items():
				if k == nil:
					raise ValueError('nil cannot be a key in a hash.')
				if v == nil:
					raise ValueError('nil cannot be a value in a hash.')
		
		def set(self, index, value):
			if index == nil:
				raise ValueError('nil cannot be a key in a hash.')
			
			self._hash = None
			
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
			return 'KlipHash({%s})' % ', '.join(['%s : %s' % (repr(k), repr(v)) for k, v in self.items()])
		
		def __hash__(self):
			if self._hash is None:
				self._hash = sum(map(hash, self.keys())) + sum(map(hash, self.values()))		#****This is even more horrifically slow!
			return self._hash
	
	#Redefine all other methods of dict that might change the hash value, so 
	#that they invalidate _hash.
	for funcName in ['clear', 'pop', 'popitem', 'update']:
		#We have to do an absurd dance to deal with the static binding of funcName:
		setattr(KlipHash, funcName, (lambda cls = dict, name = funcName: _makeWrapperFunc(cls, name))())
	
	builtins.KlipHash = KlipHash
	
	class KlipStr(str):
		def __call__(self, k, *args):
			return k, KlipStr(self % args)
		def __repr__(self):
			return 'KlipStr("%s")' % self
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
	
	builtins.dcompile = False
	builtins.dxprs = False

