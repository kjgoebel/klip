import Prefix
from Internal import Halt, Func, GlobalEnv		#Maybe this stuff should all be in Prefix.
import operator, time, random


class DefaultError(Exception):
	pass



def _no(k, arg):
	raise TailCall(k, t if klipFalse(arg) else nil)

def _prn(k, *args):
	print(*args)
	raise TailCall(k, nil)

def _prnr(k, *args):
	print(*map(repr, args))
	raise TailCall(k, nil)

def _apply(k, f, args):
	raise TailCall(f, k, *args)

def _list(k, *args):
	raise TailCall(k, KlipList(args))

_typeDict = {k : Sym(v) for k, v in {
	int : 'int',
	float : 'float',
	KlipStr : 'str',
	KlipList : 'list',
	KlipHash : 'hash',
	Sym : 'sym',
}.items()}

def _typeq(k, arg):
	try:
		raise TailCall(k, _typeDict[type(arg)])
	except KeyError:
		if callable(arg):
			raise TailCall(k, Sym('func'))
		raise DefaultError('Unknown object type %s (%s).' % (arg, type(arg)))


def _items(k, con):
	if isa(con, KlipList):
		raise TailCall(k, KlipList(con[:]))
	elif isa(con, KlipHash):
		raise TailCall(k, KlipList([KlipList([k, v]) for k, v in con.items()]))
	elif isa(con, KlipStr):
		raise TailCall(k, KlipList([x for x in con]))
	else:
		raise ValueError("Can't get items from %s." % con)

def _len(k, con):
	raise TailCall(k, len(con))

def _set(k, con, ix, value):
	raise TailCall(k, con.set(ix, value))

def _insert(k, con, ix, value):
	raise TailCall(k, con.insert(ix, value))

def _pop(k, con, ix = -1):
	raise TailCall(k, con.pop(ix))

def _append(k, con, value):
	raise TailCall(k, con.append(value))


_uniqCounter = 0
def _uniq(k, sym = None):
	global _uniqCounter
	_uniqCounter += 1
	raise TailCall(k, Sym(' gs%d%s' % (_uniqCounter, sym.pyx() if sym else '')))


def _bnot(k, arg):
	if not isa(arg, int):
		raise DefaultError("Can't use bnot on an object of type %s." % type(arg))
	raise TailCall(k, ~arg)

def _time(k):
	raise TailCall(k, time.time())

def _rand(k, *args):
	raise TailCall(k, random.randrange(*args))

def _randf(k):
	raise TaiLCall(k, random.random())


genv = GlobalEnv({
	'nil' : nil,
	't' : t,
	
	'no' : _no,
	
	'prn' : _prn,
	'prnr' : _prnr,
	
	'apply' : _apply,
	
	'list' : _list,
	'type?' : _typeq,
	
	'items' : _items,
	'len' : _len,
	'set' : _set,
	'insert' : _insert,
	'pop' : _pop,
	'append' : _append,
	
	'uniq' : _uniq,
	
	'bnot' : _bnot,
	
	'time' : _time,
	
	'rand' : _rand,
	'randf' : _randf,
})


def _binOp(name, op, allowedTypes):
	def temp(k, *args):
		if len(args) != 2:
			raise DefaultError('Operator %s takes exactly two arguments.' % (name))
		for arg in args:
			if not type(arg) in allowedTypes:
				raise DefaultError("Can't use operator %s on an object of type %s." % (name, type(arg)))
		raise TailCall(k, op(*args))
	genv.set(name, temp)

def _accOp(name, op, default, allowedTypes):
	def temp(k, *args):
		ret = default
		for arg in args:
			if not type(arg) in allowedTypes:
				raise DefaultError("Can't use operator %s on an object of type %s." % (name, type(arg)))
			ret = op(ret, arg)
		raise TailCall(k, ret)
	genv.set(name, temp)

def _antiAccOp(name, op, default, allowedTypes):
	def temp(k, *args):
		n = len(args)
		
		for arg in args:
			if not type(arg) in allowedTypes:
				raise DefaultError("Can't apply operator %s to an object of type %s." % (name, type(arg)))
		
		if n < 1:
			raise DefaultError("Can't apply operator %s to zero objects." % name)
		
		if n == 1:
			raise TailCall(k, op(default, args[0]))
		
		ret = args[0]
		for arg in args[1:]:
			ret = op(ret, arg)
		raise TailCall(k, ret)
	genv.set(name, temp)

def _compOp(name, op):
	def temp(k, *args):
		for i in range(len(args) - 1):
			if not op(args[i], args[i+1]):
				raise TailCall(k, nil)
		raise TailCall(k, t)
	genv.set(name, temp)


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



