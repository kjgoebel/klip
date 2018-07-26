from Internal import TailCall, Halt, Func, GlobalEnv
import operator


class DefaultError(Exception):
	pass



def _prn(k, *args):
	print(*args)
	raise TailCall(k, nil)

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


class MacEx(Func):
	def __init__(self):
		Func.__init__(self, genv, 0)
	def __call__(self, k, xpr):
		raise Halt(xpr)



genv = GlobalEnv({
	'nil' : nil,
	't' : t,
	
	'prn' : _prn,
	
	'list' : _list,
	'type?' : _typeq,
	
	'macex' : MacEx,
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



