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



class Asm(object):
	def __init__(self, parms):
		self.parms = parms
		self.names = []
		self.varnames = parms + []
		
		self.labels = {}
		self.instrs = []
		
		self.stackHeight = 0
		self.maxStack = 0
	
	def add(self, opname, delta):
		self.adda(opname, None, delta)
	
	def adda(self, opname, arg, delta):
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
			len(self.varnames),
			self.maxStack,
			0,
			self.make(),
			tuple(),
			tuple(self.names),
			tuple(self.varnames),
			'<string>',
			'f',
			1,
			b'',
			tuple(),
			tuple()
		)
	
	def makeF(self):
		return types.FunctionType(
			self.makeC(),
			{'len' : len},
			'f',
			None,
			None
		)


if __name__ == '__main__':
	a = Asm(['x'])
	
	a.adda('LOAD_GLOBAL', 0, 1)
	a.adda('LOAD_FAST', 0, 1)
	a.adda('CALL_FUNCTION', 1, -2)
	a.add('RETURN_VALUE', -1)
	
	print(a.maxStack)
	
	b = a.make()
	print(b)
	dis.dis(b)
	
	a.names = ['len']
	
	f = a.makeF()
	
	print(f([1, 2, 3]))
	



