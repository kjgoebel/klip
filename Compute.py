from Code import *
from Compile import comp
from Internal import klipDefaults
import copy





class Computer(object):
	def __init__(self, func):
		self.func = func
		self.code = func.code
		self.pos = 0
		self.stack = []
		self.args = []
		self.argPos = 0
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
	
	#****This sharing of duty between Computer and Env is not good.
	def _arg(self, nxt):
		if debugTrace:
			self.env.dump(klipDefaults)
		try:
			temp = self.env.arg()
		except IndexError:
			raise MachineError('%s %s' % (nxt.message, self.env.args))
		self.stack.append(temp)
		self.pos += 1
	
	def _defArg(self, nxt):
		if debugTrace:
			self.env.dump(klipDefaults)
		temp = self.env.defArg()
		if temp is None:
			self.pos += 1
		else:
			self.stack.append(temp)
			self.pos = nxt.pos
	
	def _restArg(self, nxt):
		if debugTrace:
			self.env.dump(klipDefaults)
		self.stack.append(self.env.restArg())
		self.pos += 1
	
	def _noArgsLeft(self, nxt):
		if self.env.argPos < len(self.env.args):
			raise MachineError('%s %s' % (nxt.message, self.env.args))
		self.pos += 1
	
	def _stLocal(self, nxt):
		self.env.setLocal(nxt.sym, self.stack.pop())
		self.pos += 1
	
	def _jmp(self, nxt):
		self.pos += nxt.skip
		self.pos += 1
	
	def _br(self, nxt):
		cond = self.stack.pop()
		if klipFalse(cond):
			self.pos += nxt.skip
		self.pos += 1
	
	def _litFunc(self, nxt):
		self.stack.append(nxt)
		self.pos += 1
	
	def _cont(self, nxt):
		if nxt.poppage is None:
			stk = None
		else:
			stk = copy.copy(self.stack[:-nxt.poppage])
		self.stack.append(LitFunc(self.func, self.env, nxt.parmList, nxt.pos, stk))
		self.pos += 1
	
	def _call(self, nxt):
		args = self.stack[-nxt.nargs:]		#Note: if a Call(0) instruction is encountered, this will not end well.
		del self.stack[-nxt.nargs:]
		lf = self.stack.pop()
		
		self._doCall(lf, args)
	
	def _doCall(self, lf, args):
		args = list(flatten(args))
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
			self.env.setArgs([ret])
			self.pos = lf.pos
		elif isa(lf, LitFunc):
			self.func = lf.func
			self.code = lf.func.code
			if lf.env:
				self.env = lf.env
			else:
				self.env = Env(lf.func.env, '_call:normal')
			self.env.setArgs(args)
			if not lf.stack is None:
				self.stack = copy.copy(lf.stack)
			if debugEnv:
				print('ENV SET')
				self.env.dump(klipDefaults)
			self.pos = lf.pos
			#wrangleArgs(self.env, lf.parmList, args)
		else:
			raise MachineError('Call of non-function. (%s)' % lf)
	
	def _fn(self, nxt):
		self.stack.append(comp(self.env, nxt.parmList, nxt.body))
		self.pos += 1
	
	def _halt(self, nxt):
		raise StopIteration
	
	def _splice(self, nxt):
		tos = self.stack[-1]
		self.stack[-1] = SpliceWrapper(tos)
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
		
		Arg : _arg,
		DefArg : _defArg,
		RestArg : _restArg,
		NoArgsLeft : _noArgsLeft,
		StLocal : _stLocal,
		
		Splice : _splice,
	}





