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



#Next improvements:
#1. Compiler will know parms, locals, inherited and willBeInherited. So Asm can 
#just take those as arguments. Asm can then figure out what kind of load/store 
#needs to be done. load x -> LOAD_FAST index(self.locals, 'x') if x is not in 
#willBeInherited, and that sort of thing. The question is whether this is Asm's 
#job or the compiler's. Either way, the code that translates names into 
#indices should be in the same class as the code that chooses between 
#LOAD_FAST, LOAD_DEREF, etc.
#2. add and adda are dumb. There should be a dict {opname : how to calculate 
#what it does to the stack} in Asm.

class Asm(object):
	def __init__(self, parms, inherited, willBeInherited, doc = ''):
		self.parms = parms
		self.locals = parms + []		#Vars local to this function.
		self.inherited = inherited		#Vars inherited from outer functions.
		self.globals = []				#Includes attribute names.
		self.constants = [doc]			#Constants
		self.willBeInherited = willBeInherited	#Vars that will be inherited by nested functions.
		
		self.labels = {}
		self.instrs = []
		
		self.stackHeight = 0
		self.maxStack = 0
	
	def add(self, opname, delta):
		self.adda(opname, None, delta)
	
	def adda(self, opname, arg, delta):
		f = self._opVarMap.get(opname, lambda self, x: x)
		arg = f(self, arg)
		
		self.instrs.append(Inst(opname, arg))
		
		self.stackHeight += delta
		if self.stackHeight > self.maxStack:
			self.maxStack = self.stackHeight
	
	def label(self, name):
		self.labels[len(self.instrs)] = name
	
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
			tuple(self.globals),
			tuple(self.locals),
			'<string>',
			'f',
			1,
			b'',
			tuple(self.inherited),
			tuple(self.willBeInherited)
		)
	
	def makeF(self, globals, closure):
		return types.FunctionType(
			self.makeC(),
			globals,
			'f',
			None,
			closure
		)
	
	def _getVar(self, arg, varList):
		try:
			return varList.index(arg)
		except ValueError:
			ret = len(varList)
			varList.append(arg)
			return ret
	
	def _getConst(self, arg):
		return self._getVar(arg, self.constants)
	
	def _getLocal(self, arg):
		return self._getVar(arg, self.locals)
	
	def _getGlobal(self, arg):
		return self._getVar(arg, self.globals)
	
	def _getCell(self, arg):
		if arg in self.inherited:
			return self._getVar(arg, self.inherited)
		if arg in self.willBeInherited:
			return self._getVar(arg, self.willBeInherited)
		raise ValueError("%s doesn't seem to be a cell var." % arg)
	
	_opVarMap = {
		'LOAD_CONST' : _getConst,
		'LOAD_FAST' : _getLocal,
		'STORE_FAST' : _getLocal,
		'LOAD_DEREF' : _getCell,
		'STORE_DEREF' : _getCell,
		'LOAD_CLOSURE' : _getCell,
		'LOAD_GLOBAL' : _getGlobal,
		'STORE_GLOBAL' : _getGlobal,
		'LOAD_NAME' : _getGlobal,
		'LOAD_ATTR' : _getGlobal,
		'STORE_ATTR' : _getGlobal,
	}


if __name__ == '__main__':
	# a = Asm(['x'])
	
	# a.adda('LOAD_GLOBAL', 'len', 1)
	# a.adda('LOAD_FAST', 'x', 1)
	# a.adda('CALL_FUNCTION', 1, -2)
	# a.add('RETURN_VALUE', -1)
	
	# print(a.maxStack)
	
	# b = a.make()
	# print(b)
	# dis.dis(b)
	
	# f = a.makeF({'len' : len}, None)
	
	# print(f([1, 2, 3]))
	
	gAsm = Asm(['y'], ['x'], [])
	
	gAsm.adda('LOAD_GLOBAL', 'print', 1)
	gAsm.adda('LOAD_DEREF', 'x', 1)
	gAsm.adda('LOAD_FAST', 'y', 1)
	gAsm.adda('CALL_FUNCTION', 2, -3)
	gAsm.add('RETURN_VALUE', -1)
	
	gCode = gAsm.makeC()
	print(dis.dis(gCode))
	
	fAsm = Asm(['x'], [], ['x'])
	
	fAsm.adda('LOAD_CLOSURE', 'x', 1)
	fAsm.adda('BUILD_TUPLE', 1, 0)
	fAsm.adda('LOAD_CONST', gCode, 1)
	fAsm.adda('LOAD_CONST', 'f.g', 1)
	fAsm.adda('MAKE_FUNCTION', 0x8, -3)
	fAsm.add('DUP_TOP', 1)		#Note that g isn't stored anywhere. This is fine only because it's not inherited.
	fAsm.adda('LOAD_CONST', 5, 1)
	fAsm.adda('CALL_FUNCTION', 1, -2)
	fAsm.add('POP_TOP', -1)
	fAsm.adda('LOAD_CONST', 7, 1)
	fAsm.adda('CALL_FUNCTION', 1, -2)
	fAsm.add('RETURN_VALUE', -1)
	
	f = fAsm.makeF(
		{'print' : print},
		None
	)
	print(dis.dis(f))
	
	print(f(9))
	
	



