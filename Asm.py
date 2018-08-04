import dis, struct, types


class Inst(object):
	def __init__(self, op, arg):
		self.op = op
		self.arg = arg
	
	def make(self):
		return bytes(struct.pack('BB',
			dis.opmap[self.op],
			0 if self.arg is None else self.arg
		))



def _makeFunctionStack(arg):
	ret = 2
	if arg & 0x01:
		ret += 1
	if arg & 0x02:
		ret += 1
	if arg & 0x04:
		ret += 1
	if arg & 0x08:
		ret += 1
	return ret

class Asm(object):
	_stackDelta = {
		'NOP' : 0,
		'POP_TOP' : -1,
		'ROT_TWO' : 0,
		'ROT_THREE' : 0,
		'DUP_TOP' : 1,
		'LIST_APPENT' : -1,
		'SET_ADD' : -1,
		'MAP_ADD' : -2,
		'RETURN_VALUE' : -1,
		'STORE_GLOBAL' : -1,
		'LOAD_CONST' : 1,
		'LOAD_NAME' : 1,
		'BUILD_TUPLE' : lambda arg: -arg,
		'BUILD_LIST' : lambda arg: -arg,
		'BUILD_MAP' : lambda arg: -2 * arg,
		'BUILD_STRING' : lambda arg: -arg,
		'BUILD_TUPLE_UNPACK_WITH_CALL' : lambda arg: -(arg + 1),
		'BUILD_LIST_UNPACK' : lambda arg: -arg,
		'LOAD_ATTR' : 0,
		'JUMP_FORWARD' : 0,
		'POP_JUMP_IF_TRUE' : -1,
		'POP_JUMP_IF_FALSE' : -1,
		'JUMP_ABSOLUTE' : 0,
		'LOAD_GLOBAL' : 1,
		'LOAD_FAST' : 1,
		'STORE_FAST' : -1,
		'LOAD_CLOSURE' : 1,
		'LOAD_DEREF' : 1,
		'STORE_DEREF' : -1,
		'RAISE_VARARGS' : lambda arg: -arg,
		'CALL_FUNCTION' : lambda arg: -arg,
		'MAKE_FUNCTION' : _makeFunctionStack,
		'BUILD_SLICE' : lambda arg: -(arg - 1),
	}
	
	def __init__(self,
			parms,				#parameters, including those with default values.
			restParm,			#the name of the rest parameter.
			otherLocals,		#other variables local to the function, including those in heritable.
			inherited,			#variables inherited from surrounding functions.
			heritable,			#variables that a nested function will inherit.
			doc = ''
	):
		self.parms = parms
		self.restParm = restParm
		if restParm:
			self.locals = parms + [restParm] + otherLocals
		else:
			self.locals = parms + otherLocals
		self.inherited = inherited
		self.heritable = heritable
		self.names = []
		self.constants = [doc]
		
		self.labels = {}
		self.instrs = []
		
		self.stackHeight = 0
		self.maxStack = 0
	
	def add(self, opname, arg = None):
		self.instrs.append(Inst(opname, arg))
		
		delta = self._stackDelta[opname]
		if callable(delta):
			delta = delta(arg)
		
		self.stackHeight += delta
		if self.stackHeight > self.maxStack:
			self.maxStack = self.stackHeight
	
	def label(self, name):
		self.labels[len(self.instrs)] = name
	
	def _getVar(self, name):
		if name in self.inherited:
			return '_DEREF', self.inherited.index(name)
		if name in self.heritable:
			return '_DEREF', len(self.inherited) + self.heritable.index(name)
		if name in self.locals:
			return '_FAST', self.locals.index(name)
		if name in self.names:
			ix = self.names.index(name)
		else:
			ix = len(self.names)
			self.names.append(name)
		return '_GLOBAL', ix
	
	def load(self, name):
		ending, ix = self._getVar(name)
		self.add('LOAD' + ending, ix)
	
	def store(self, name):
		ending, ix = self._getVar(name)
		self.add('STORE' + ending, ix)
	
	def const(self, value):
		if value in self.constants:
			self.add('LOAD_CONST', self.constants.index(value))
		else:
			ix = len(self.constants)
			self.constants.append(value)
			self.add('LOAD_CONST', ix)
	
	def cell(self, name):
		if name in self.inherited:
			self.add('LOAD_CLOSURE', self.inherited.index(name))
		elif name in self.heritable:
			self.add('LOAD_CLOSURE', len(self.inherited) + self.heritable.index(name))
		else:
			raise ValueError('Cell variable %s not found.' % name)
	
	def make(self):
		size = 0
		labelValues = {}
		
		for i, inst in enumerate(self.instrs):
			if i in self.labels:
				labelValues[self.labels[i]] = size
			
			size += 2
			if not inst.arg is None:
				size += 2
		
		for inst in self.instrs:
			if inst.arg in labelValues:
				inst.arg = labelValues[inst.arg]
		
		return b''.join([inst.make() for inst in self.instrs])
	
	def makeC(self):
		return types.CodeType(
			len(self.parms),
			0,
			len(self.locals),
			self.maxStack,
			0,
			self.make(),
			tuple(self.constants),
			tuple(self.names),
			tuple(self.locals),
			'<string>',
			'f',
			1,
			b'',
			tuple(self.inherited),
			tuple(self.heritable)
		)
	
	def makeF(self, globals, closure):
		return types.FunctionType(
			self.makeC(),
			globals,
			'f',
			None,
			closure
		)


if __name__ == '__main__':
	gAsm = Asm(
		['y'],
		None,
		[],
		['x'],
		[],
	)
	
	gAsm.load('print')
	gAsm.load('x')
	gAsm.load('y')
	gAsm.add('CALL_FUNCTION', 2)
	gAsm.add('RETURN_VALUE')
	
	gCode = gAsm.makeC()
	print(dis.dis(gCode))
	
	fAsm = Asm(
		['x'],
		None,
		[],
		[],
		['x'],
	)
	
	fAsm.cell('x')
	fAsm.add('BUILD_TUPLE', 1)
	fAsm.const(gCode)
	fAsm.const('f.g')
	fAsm.add('MAKE_FUNCTION', 0x8)
	fAsm.add('DUP_TOP')		#Note that g isn't stored anywhere. This is fine only because it's not inherited.
	fAsm.const(5)
	fAsm.add('CALL_FUNCTION', 1)
	fAsm.add('POP_TOP')
	fAsm.const(7)
	fAsm.add('CALL_FUNCTION', 1)
	fAsm.add('RETURN_VALUE')
	
	f = fAsm.makeF(
		{'print' : print},
		None
	)
	print(dis.dis(f))
	
	print(f(9))
	
	



