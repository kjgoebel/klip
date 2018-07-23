import Prefix
from Code import LitFunc
#from Compute import Computer, wrangleArgs
from Compile import compMacro
import operator, time, random



class InternalError(Exception):
	pass



def _prn(env, *args):
	print(*args)
	return nil

def _rprn(env, *args):
	print(*list(map(repr, args)))
	return nil


#Note: This assignment nonsense is the only reason why Computer passes environments to literal callables.
def _getSafe(env, name):
	try:
		return env.get(name)
	except:
		return nil

def _setVar(env, name, value):
	env.set(name, value)
	return nil


def _no(env, arg):
	if klipFalse(arg):
		return t
	return nil



def _list(env, *args):
	return KlipList(flatten(args))

def _hash(env, *args):
	allArgs = flatten(args)
	ret = KlipHash()
	while True:
		try:
			k = next(allArgs)
		except StopIteration:
			break
		
		try:
			v = next(allArgs)
		except StopIteration:
			raise ValueError('Odd number of arguments to hash.')
		
		ret[k] = v
	return ret




def _items(env, con):
	if isa(con, KlipList):
		return con[:]
	elif isa(con, KlipHash):
		return KlipList([KlipList([k, v]) for k, v in con.items()])
	elif isa(con, KlipStr):
		return KlipList([x for x in con])
	else:
		raise ValueError("Can't get items from %s." % con)

def _len(env, con):
	return len(con)

def _set(env, con, ix, value):
	return con.set(ix, value)

def _insert(env, con, ix, value):
	return con.insert(ix, value)

def _append(env, con, value):
	return con.append(value)




_typeDict = {k : Sym(v) for k, v in {
	int : 'int',
	float : 'float',
	KlipStr : 'str',
	KlipList : 'list',
	KlipHash : 'hash',
	Sym : 'sym',
	#GenSym : 'sym',
	LitFunc : 'func',
}.items()}

def _typeq(env, *args):
	if len(args) != 1:
		raise InternalError('type? takes exactly one argument.')
	try:
		return _typeDict[type(args[0])]
	except KeyError:
		if callable(args[0]):
			return Sym('func')
		raise InternalError('Unknown object type %s.' % type(args[0]))

#There's nothing particularly magical about gensyms. They just have names that 
#the tokenizer can't possibly produce. If I ever provide a way to translate 
#strings into symbols, this will stop working.
_uniqCounter = 0
def _uniq(env):
	global _uniqCounter
	_uniqCounter += 1
	return Sym('gs %d' % _uniqCounter)


def _bnot(env, arg):
	if not isa(arg, int):
		raise InternalError("Can't use bnot on an object of type %s." % type(arg))
	return ~arg


def _time(env):
	return time.time()


def _rand(env, *args):
	return random.randrange(*args)

def _randf(env):
	return random.random()




klipDefaults = {
	'nil' : nil,			#It pains me that the key nil will not be the same object as the value nil. Oh well.
	't' : t,
	
	'prn' : _prn,
	'rprn' : _rprn,
	
	'get-safe' : _getSafe,
	'set-var' : _setVar,
	
	'no' : _no,
	
	'list' : _list,
	'hash' : _hash,
	
	'items' : _items,
	'len' : _len,
	'set' : _set,
	'insert' : _insert,
	'append' : _append,
	
	'type?' : _typeq,
	
	'uniq' : _uniq,
	
	'bnot' : _bnot,
	
	'time' : _time,
	'rand' : _rand,
	'randf' : _randf,
}


def _binOp(name, op, allowedTypes):
	def temp(env, *args):
		if len(args) != 2:
			raise InternalError('Operator %s takes exactly two arguments.' % (name))
		for arg in args:
			if not type(arg) in allowedTypes:
				raise InternalError("Can't use operator %s on an object of type %s." % (name, type(arg)))
		return op(*args)
	klipDefaults[name] = temp

def _accOp(name, op, default, allowedTypes):
	def temp(env, *args):
		ret = default
		for arg in args:
			if not type(arg) in allowedTypes:
				raise InternalError("Can't use operator %s on an object of type %s." % (name, type(arg)))
			ret = op(ret, arg)
		return ret
	klipDefaults[name] = temp

def _antiAccOp(name, op, default, allowedTypes):
	def temp(env, *args):
		n = len(args)
		
		for arg in args:
			if not type(arg) in allowedTypes:
				raise InternalError("Can't apply operator %s to an object of type %s." % (name, type(arg)))
		
		if n < 1:
			raise InternalError("Can't apply operator %s to zero objects." % name)
		
		if n == 1:
			return op(default, args[0])
		
		ret = args[0]
		for arg in args[1:]:
			ret = op(ret, arg)
		return ret
	klipDefaults[name] = temp

def _compOp(name, op):
	def temp(env, *args):
		for i in range(len(args) - 1):
			if not op(args[i], args[i+1]):
				return nil
		return t
	klipDefaults[name] = temp


_numTypes = {int, float}


_accOp('+', operator.add, 0, _numTypes)
_antiAccOp('-', operator.sub, 0, _numTypes)
_accOp('*', operator.mul, 1, _numTypes)
_antiAccOp('/', operator.truediv, 1, _numTypes)

_antiAccOp('div', operator.floordiv, 1, {int})
_binOp('mod', operator.mod, {int})

_compOp('==', operator.eq)
_compOp('!=', operator.ne)
_compOp('>', operator.gt)
_compOp('<', operator.lt)
_compOp('>=', operator.ge)
_compOp('<=', operator.le)

_accOp('band', operator.and_, -1, {int})
_accOp('bor', operator.or_, 0, {int})


