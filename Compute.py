from Code import *
from Compile import comp
from Internal import klipDefaults
import copy




def wrangleArgs(env, parmList, args):
	before = []
	restFunc = None
	restName = None
	after = []
	
	parms = parmList
	while True:
		if parms == nil:
			break
		if isa(parms, Cons):
			if isa(parms.car, Cons) and parms.car.cdr == nil:
				restFunc = clist
				restName = parms.car.car
				parms = parms.cdr
				break
			if isa(parms.car, KlipArray):
				restFunc = KlipArray
				restName = parms.car[0]
				parms = parms.cdr
				break
			before.append(parms.car)
			parms = parms.cdr
		elif isa(parms, Sym):
			restFunc = clist
			restName = parms
			parms = nil
			break
		else:
			raise MachineError('Unexpected object found in parameter list: %s. %s %s' % (parms, parmList, args))
	
	while True:
		if parms == nil:
			break
		if not isa(parms, Cons):
			raise MachineError('Improper parameter list. %s %s' % (parmList, args))
		if not isa(parms.car, Sym):
			raise MachineError('Only symbols may follow a rest parameter in a parameter list. %s %s' % (parmList, args))
		after.append(parms.car)
		parms = parms.cdr
	
	pos = 0
	for parm in before:
		if pos >= len(args):
			if isa(parm, Cons):
				env.setLocal(parm.car, parm.cdr.car)
			else:
				raise MachineError('Not enough arguments. %s %s' % (parmList, args))
		else:
			if isa(parm, Cons):
				env.setLocal(parm.car, args[pos])
			else:
				env.setLocal(parm, args[pos])
		pos += 1
	
	if not restFunc is None:
		pos = len(args) - len(after)
		env.setLocal(restName, restFunc(args[len(before) : pos]))
	
	for parm in after:
		if pos >= len(args):
			raise MachineError('Not enough arguments. %s %s' % (parmList, args))
		env.setLocal(parm, args[pos])
		pos += 1




class Computer(object):
	def __init__(self, func):
		self.func = func
		self.code = func.code
		self.pos = 0
		self.stack = []
		self.env = Env(func.env, 'Computer()')
		if debugEnv:
			print('ENV SET')
			self.env.dump(klipDefaults)
		#self.nsteps = 0
	
	def step(self):
		try:
			nxt = self.code[self.pos]
		except IndexError as e:
			dumpCode(self.code)
			print(self.pos)
			raise e
		
		#self.nsteps += 1
		# if self.nsteps > 100:
			# raise ValueError
		
		if debugTrace:
			print('%d\t%s' % (self.pos, repr(nxt)))
		
		try:
			f = Computer._instTable[type(nxt)]
		except KeyError:
			raise ValueError('Unknown instruction type (%s)' % nxt)
		f(self, nxt)
		
		if debugTrace:
			print(self.stack)
	
	def _lit(self, nxt):
		self.stack.append(nxt.value)
		self.pos += 1
	
	def _ld(self, nxt):
		if debugTrace:
			self.env.dump(klipDefaults)
		self.stack.append(self.env.get(nxt.sym))
		self.pos += 1
	
	def _st(self, nxt):
		self.env.set(nxt.sym, self.stack.pop())
		self.pos += 1
	
	def _pop(self, nxt):
		self.stack.pop()
		self.pos += 1
	
	def _jmp(self, nxt):
		self.pos += nxt.skip
		self.pos += 1
	
	def _br(self, nxt):
		cond = self.stack.pop()
		if cond == nil:
			self.pos += nxt.skip
		self.pos += 1
	
	def _litFunc(self, nxt):
		self.stack.append(nxt)
		self.pos += 1
	
	def _cont(self, nxt):
		if nxt.poppage is None:
			temp = None
		else:
			temp = copy.copy(self.stack[:-nxt.poppage])
		self.stack.append(LitFunc(self.func, self.env, nxt.parmList, nxt.pos, temp))
		self.pos += 1
	
	def _call(self, nxt):
		args = self.stack[-nxt.nargs:]		#Note: if a Call(0) instruction is encountered, this will not end well.
		del self.stack[-nxt.nargs:]
		lf = self.stack.pop()
		
		self._doCall(lf, args)
	
	def _doCall(self, lf, args):
		if callable(lf):
			func = lf
			lf = args.pop(0)
			ret = func(self.env, *args)
			self.func = lf.func
			self.code = lf.func.code
			self.env = lf.env
			if debugEnv:
				print('ENV SET')
				self.env.dump(klipDefaults)
			self.env.set(Sym(' ret'), ret)
			self.pos = lf.pos
		elif isa(lf, LitFunc):
			self.func = lf.func
			self.code = lf.func.code
			if lf.env:
				self.env = lf.env
			else:
				self.env = Env(lf.func.env, '_call:normal')
			if not lf.stack is None:
				self.stack = copy.copy(lf.stack)
			if debugEnv:
				print('ENV SET')
				self.env.dump(klipDefaults)
			self.pos = lf.pos
			wrangleArgs(self.env, lf.parmList, args)
		else:
			raise MachineError('Call of non-function. (%s)' % lf)
	
	def _fn(self, nxt):
		self.stack.append(comp(self.env, nxt.parmList, nxt.body))
		self.pos += 1
	
	def _halt(self, nxt):
		raise StopIteration
	
	def _splice(self, nxt):
		tos = self.stack[-1]
		if tos == nil:
			self.stack[-1] = SpliceWrapper()
		else:
			self.stack[-1] = SpliceWrapper(tos)
		self.pos += 1
	
	def _endCap(self, nxt):
		self.stack[-1] = EndCapWrapper(self.stack[-1])
		self.pos += 1
	
	_instTable = {
		Lit : _lit,
		Ld : _ld,
		St : _st,
		Jmp : _jmp,
		Br : _br,
		LitFunc : _litFunc,
		Cont : _cont,
		Call : _call,
		Pop : _pop,
		Fn : _fn,
		Halt : _halt,
		Splice : _splice,
		EndCap : _endCap,
	}





