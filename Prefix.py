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
	
	class Cons(object):
		class _ConsIter(object):
			def __init__(self, cons):
				self.cons = cons
				self.this = None
			def __iter__(self):
				return self
			def __next__(self):
				if self.this == None:
					self.this = self.cons
				else:
					self.this = self.this.cdr
				if not isa(self.this, Cons):
					raise StopIteration
				return self.this.car
		
		def __init__(self, car, cdr):
			self._car = car
			#Conses must be immutable and hashable, so that they can be keys 
			#in KlipHashes. But they must be able to contain unhashable 
			#things (KlipArrays and KlipHashes) so that those objects can be 
			#literals in programs. So, in some sense the value of a Cons can 
			#change, if the array it contains is altered, but it still points 
			#to the same array, so its hash remains the same. Note also that 
			#two Conses which contain different array objects that happen to 
			#have the same values will NOT be considered equal.
			try:
				carHash = hash(car)
			except TypeError:
				carHash = id(car)
				self._carForComp = carHash
			else:
				self._carForComp = car
			
			self._cdr = cdr
			try:
				cdrHash = hash(cdr)
			except TypeError:
				cdrHash = id(cdr)
				self._cdrForComp = cdrHash
			else:
				self._cdrForComp = cdr
			
			self._hash = carHash + cdrHash
		
		def _getCar(self):
			return self._car
		car = property(_getCar)
		
		def _getCdr(self):
			return self._cdr
		cdr = property(_getCdr)
		
		def _subStr(self, func):
			if isa(self.cdr, Cons):
				return func(self.car) + ' ' + self.cdr._subStr(func)
			if self.cdr == nil:
				return func(self.car)
			return func(self.car) + ' . ' + func(self.cdr)
		
		def __str__(self):
			return '(%s)' % self._subStr(str)
		def __repr__(self):
			return '(%s)' % self._subStr(repr)
		
		def __hash__(self):
			return self._hash
		
		def __eq__(self, other):
			if not isa(other, Cons):
				return False
			return self._carForComp == other._carForComp and self._cdrForComp == other._cdrForComp
		def __neq__(self, other):
			if not isa(other, Cons):
				return True
			return self._carForComp != other._carForComp and self._cdrForComp != other._cdrForComp
		
		def __iter__(self):
			return Cons._ConsIter(self)
	builtins.Cons = Cons
	
	class KlipArray(list):
		def __call__(self, env, *args):
			if len(args) == 0:
				return len(self)
			
			if isa(args[0], KlipArray):
				ix = slice(*[None if (x == t) else x for x in args[0]])
			else:
				ix = args[0]
			
			if len(args) == 1:
				if isa(ix, slice):
					return KlipArray(self[ix])
				return self[ix]
			
			if len(args) == 2:
				if args[1] == nil:
					return self.pop(ix)
				if ix == nil:
					self.append(args[1])
					return nil
				self[ix] = args[1]
				return nil
			
			#This.... This should not be. I'm sorry. I had a dream of using 
			#basic Lisp constructs to deal with containers without cluttering 
			#up the built-in namespace with names like array-get, array-set, 
			#etc. But this is.... I'm not happy about it.
			if len(args) == 3:
				if args[1] != nil:
					raise ValueError('If an array is called with three arguments, the second one must be nil.')
				self.insert(args[0], args[2])
				return nil
			
			raise ValueError('array object called with more than three arguments.')
		
		def __str__(self):
			return '[%s]' % ' '.join([str(x) for x in self])
		def __repr__(self):
			return 'KlipArray([%s])' % ', '.join([repr(x) for x in self])
	builtins.KlipArray = KlipArray
	
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
	
	class EndCapWrapper(object):
		def __init__(self, contents):
			self.contents = contents
	builtins.EndCapWrapper = EndCapWrapper
	
	
	def clist(args, i = 0):
		if i >= len(args):
			return nil
		head = args[i]
		if isa(head, EndCapWrapper):
			if i < len(args) - 1:
				raise ValueError('clist: End cap encountered before end of args.')
			return head.contents
		return Cons(head, clist(args, i + 1))
	builtins.clist = clist
	
	def unclist(c):
		ret = []
		while isa(c, Cons):
			ret.append(c.car)
			c = c.cdr
		if c != nil:
			ret.append(EndCapWrapper(c))
		return ret
	builtins.unclist = unclist
	
	builtins.debugTrace = False
	builtins.debugCompile = False
	builtins.debugEnv = False

