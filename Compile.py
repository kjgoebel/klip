import Prefix
import Internal
from Defaults import genv


class CompileError(Exception):
	pass

_uniqueCounter = 0
def nextUnique():
	global _uniqueCounter
	ret = _uniqueCounter
	_uniqueCounter += 1
	return ret



class CompCtx(object):
	def __init__(self, prev = None, **kwargs):
		if prev:
			self.__dict__.update(prev.__dict__)
		self.__dict__.update(kwargs)
	
	def __getattr__(self, name):
		return None
	
	def derive(self, **kwargs):
		return CompCtx(self, **kwargs)



class Temp(object):
	def __init__(self):
		self.maxTemps = 0
		self._curTempKey = 0
		self.unsaved = {}
		self.saved = {}
		self.usedTemps = set()
	
	def set(self, pyx):
		key = self._curTempKey
		self._curTempKey += 1
		self.unsaved[key] = pyx
		#print('************TEMP CREATED', key)
		return key
	
	def _findOpenTemp(self):
		ret = 0
		while ret in self.usedTemps:
			ret += 1
		self.maxTemps = max(self.maxTemps, ret + 1)
		return ret
	
	def push(self, c, indent):
		for key, pyx in self.unsaved.items():
			tempIndex = self._findOpenTemp()
			self.usedTemps.add(tempIndex)
			c.line(indent, '%s = %s' % ('self.temps[%d]' % tempIndex, pyx))
			self.saved[key] = tempIndex
		self.unsaved = {}
	
	def getPyx(self, key):
		if key in self.unsaved:
			return self.unsaved[key]
		if key in self.saved:
			return 'self.temps[%d]' % self.saved[key]
		raise ValueError("Can't find temp key %d." % key)
	
	def rem(self, key):
		#print('************TEMP REMOVING', key)
		if key in self.unsaved:
			del self.unsaved[key]
		elif key in self.saved:
			self.usedTemps.remove(self.saved[key])
			del self.saved[key]
		else:
			raise ValueError("Can't find temp key %d." % key)



class CompInfo(object):
	def __init__(self, pyx, needsTemp):
		self.pyx = pyx
		self.needsTemp = needsTemp



#Possible optimization: Don't slice the function unless something actually 
#exists that will see the continuation. This would require the ability to shift 
#rapidly between CPS and non-CPS. The Func class would need callCPS and 
#callNCPS methods. Builtins would need different versions, too.



class Compiler(object):
	def __init__(self, parmList, body):
		self.lines = []
		self.name = 'func%d' % nextUnique()
		
		self.curMethod = 1
		
		self.temp = Temp()
		
		self.line(0, 'class %s(Func):' % self.name)
		
		self.parms = {}				#Sym : <str that is a legal python identifier>
		
		parmCleanup = {}
		defaultDummies = []
		
		pyParms = ['self', 'k']
		if isa(parmList, Sym):
			legal = parmList.pyx()
			self.parms[parmList] = legal
			pyParms.append('*%s' % legal)
			parmCleanup[parmList] = 'KlipList(%s)' % legal
		else:
			for parm in parmList:
				if isa(parm, KlipList):
					if len(parm) == 1:
						legal = parm[0].pyx()
						self.parms[parm[0]] = legal
						pyParms.append('*%s' % legal)
						parmCleanup[parm[0]] = 'KlipList(%s)' % legal
					else:
						legal = parm[0].pyx()
						self.parms[parm[0]] = legal
						dummyName = 'defParm%d__' % nextUnique()
						pyParms.append('%s = %s' % (legal, dummyName))
						defaultDummies.append((legal, dummyName, parm[0], parm[1]))
				else:
					legal = parm.pyx()
					self.parms[parm] = legal
					pyParms.append(legal)
		
		ctx = CompCtx(tail = False)
		
		for legal, dummyName, parm, xpr in defaultDummies:
			self.line(1, '%s = object()' % dummyName)
		
		self.line(1, 'def __call__(%s):' % ', '.join(pyParms))
		self.comment('%s, %s' % (parmList, body))
		self.line(2, 'self.setLocal(" cont", k)')
		for parm, legal in self.parms.items():
			if parm in parmCleanup:
				self.line(2, '%s = %s' % (legal, parmCleanup[parm]))
			self.line(2, 'self.setLocal("%s", %s)' % (parm, legal))			#Parms could be temped, and then some/most of these wouldn't have to be done. But that would require thought.
		
		try:
			for legal, dummyName, parm, xpr in defaultDummies:
				afterMeth = self.nextMethName()
				defMeth = self.nextMethName()
				
				self.line(2, 'if self.get("%s") is self.%s:' % (parm, dummyName))
				self.line(3, 'return self.%s, None' % defMeth)
				self.line(2, 'else:')
				self.line(3, 'return self.%s, None' % afterMeth)
				
				self.line(1, 'def %s(self, dummy):' % (defMeth))
				ci = self.c_xpr(xpr, ctx)
				#ci can't be None
				self.line(2, 'self.setLocal("%s", %s)' % (parm, ci.pyx))
				self.line(2, 'return self.%s, None' % afterMeth)
				
				self.line(1, 'def %s(self, dummy):' % (afterMeth))
			
			for xpr in body[:-1]:
				self.c_xpr(xpr, ctx)
			self.c_xpr(body[-1], ctx.derive(tail = True))
		except Exception as e:
			print('PARTIAL COMPILER DUMP:')
			print(str(self))
			raise e
		
		self.line(1, 'def __init__(self):')
		self.line(2, 'Func.__init__(self, self._parent, %d)' % self.temp.maxTemps)
		
		if dcompile:
			print(str(self))
	
	def nextMethName(self):
		temp = self.curMethod
		self.curMethod += 1
		return '_%d' % temp
	
	def c_fn(self, rest, ctx):
		parmList = rest[0]
		body = rest[1:]
		
		self.temp.push(self, 2)
		
		#This is a gruesome hack.
		fnName = 'fn%d' % nextUnique()
		Internal.internals[fnName] = (parmList, body)
		
		methName = self.nextMethName()
		k = 'self.%s' % methName
		
		self.comment('%s, %s' % (parmList, body))
		self.line(2, 'return tuple((compFunc, %s, self, *%s))' % (k, fnName))
		
		self.line(1, 'def %s(self, ret):' % methName)
		return self.finish('ret', ctx, True)
	
	def c_branch(self, rest, ctx):
		cond = rest[0]
		result = rest[1]
		alternative = len(rest) > 2 and rest[2]
		
		ci = self.c_xpr(cond, ctx.derive(tail = False))
		self.line(2, 'if klipFalse(%s):' % ci.pyx)
		
		if ctx.tail:
			cont = 'self.get(" cont")'
		else:
			finalMeth = self.nextMethName()
			cont = 'self.%s' % finalMeth
		
		if alternative:
			alternativeMeth = self.nextMethName()
			self.line(3, 'return self.%s, None' % (alternativeMeth))
		else:
			self.line(3, 'return %s, nil' % cont)
		self.line(2, 'else:')
		resultMeth = self.nextMethName()
		self.line(3, 'return self.%s, None' % (resultMeth))
		
		self.line(1, 'def %s(self, k):' % resultMeth)
		ci = self.c_xpr(result, ctx)
		if ci:
			self.line(2, 'return %s, %s' % (cont, ci.pyx))
		
		if alternative:
			self.line(1, 'def %s(self, k):' % alternativeMeth)
			ci = self.c_xpr(alternative, ctx)
			if ci:
				self.line(2, 'return %s, %s' % (cont, ci.pyx))
		
		if ctx.tail:
			return None
		
		self.line(1, 'def %s(self, ret):' % finalMeth)
		return self.finish('ret', ctx, True)
	
	def c_ccc(self, rest, ctx):
		ci = self.c_xpr(rest[0], ctx.derive(tail = False))
		#ci cannot be None
		cont = self.nextMethName()
		self.line(2, 'return %s, self.%s, self.makeExplicitCont(self.%s)' % (ci.pyx, cont, cont))
		
		self.line(1, 'def %s(self, ret):' % cont)
		return self.finish('ret', ctx, True)
	
	def c_getSafe(self, rest, ctx):
		sym = rest[0]
		if not isa(sym, Sym):
			raise CompileError('Argument to get-safe must be a sym.')
		
		return self.finish('self.getSafe("%s")' % sym, ctx, False)
	
	def c_assign(self, rest, ctx):
		sym = rest[0]
		if not isa(sym, Sym):
			raise CompileError('First argument to assign must be a sym.')
		
		pyx = self.c_xpr(rest[1], ctx.derive(tail = False)).pyx
		self.line(2, 'self.set("%s", %s)' % (sym, pyx))
		return self.finish('nil', ctx, False)
	
	def c_halt(self, rest, ctx):
		pyx = self.c_xpr(rest[0], ctx.derive(tail = False)).pyx
		self.line(2, 'raise Halt(%s)' % pyx)
		return self.finish('None', ctx, False)
	
	def c_quote(self, rest, ctx):
		return self.finish(repr(rest[0]), ctx, True)
	
	def c_quasiquote(self, rest, ctx):
		return self.c_xpr(rest[0], ctx.derive(qq = 1))
	
	def c_unquote(self, rest, ctx):
		raise CompileError('unquote is undefined outside of a quasiquote.')
	
	def c_unquotesplicing(self, rest, ctx):
		raise CompileError('unquotesplicing is undefined outside of a quasiquote.')
	
	_specialTable = {
		'fn' : c_fn,
		'branch' : c_branch,
		'ccc' : c_ccc,
		'get-safe' : c_getSafe,
		'assign' : c_assign,
		'halt' : c_halt,
		
		'quote' : c_quote,
		'quasiquote' : c_quasiquote,
		'unquote' : c_unquote,
		'unquotesplicing' : c_unquotesplicing,
	}
	
	def c_list(self, xpr, ctx):
		if len(xpr) == 0:
			return self.finish('KlipList()', ctx, True)
		
		head = xpr[0]
		if isa(head, Sym) and head.name in Compiler._specialTable:
			return Compiler._specialTable[head.name](self, xpr[1:], ctx)
		
		methName = self.nextMethName()
		subctx = ctx.derive(tail = False)
		
		#Create a list of arguments, carefully keeping track of which ones might be temped during the execution of the subsequent ones:
		pyArgs = []
		temps = []
		for sub in xpr:
			self.temp.push(self, 2)
			ci = self.c_xpr(sub, subctx)
			#ci cannot be None.
			if ci.needsTemp:
				key = self.temp.set(ci.pyx)
				temps.append((key, len(pyArgs)))		#Record the temp key and the position in the arg list so we can go back and fix them up.
			pyArgs.append(ci.pyx)
		
		#And now replace all the ones that were temped:
		for key, ix in temps:
			pyArgs[ix] = self.temp.getPyx(key)
		
		if ctx.tail:
			pyArgs.insert(1, 'self.get(" cont")')
		else:
			pyArgs.insert(1, 'self.%s' % methName)
		self.doCall(pyArgs, ctx)
		[self.temp.rem(key) for key, ix in temps]			#Deleting all temps is only correct because parms aren't temped. If parms are temped, we need to know the last time a parm is used in the function.
		
		if ctx.tail:
			return None
		self.line(1, 'def %s(self, ret):' % methName)
		return self.finish('ret', ctx, True)
	
	def c_hash(self, xpr, ctx):
		subctx = ctx.derive(tail = False)
		pyKeys = []
		pyValues = []
		keyTemps = []
		valueTemps = []
		for subK, subV in xpr.items():
			self.temp.push(self, 2)
			ci = self.c_xpr(subK, subctx)
			if ci.needsTemp:
				tk = self.temp.set(ci.pyx)
				keyTemps.append((tk, len(pyKeys)))
			pyKeys.append(ci.pyx)
			
			self.temp.push(self, 2)
			ci = self.c_xpr(subV, subctx)
			if ci.needsTemp:
				tk = self.temp.set(ci.pyx)
				valueTemps.append((tk, len(pyValues)))
			pyValues.append(ci.pyx)
		
		for tk, ix in keyTemps:
			pyKeys[ix] = self.temp.getPyx(tk)
		for tk, ix in valueTemps:
			pyValues[ix] = self.temp.getPyx(tk)
		
		s = 'KlipHash({%s})' % ', '.join([
			'%s : %s' % (pyKeys[i], pyValues[i])
			for i in range(len(xpr))
		])
		[self.temp.rem(tk) for tk, ix in keyTemps]
		[self.temp.rem(tk) for tk, ix in valueTemps]
		return self.finish(s, ctx, True)
	
	def c_qq(self, xpr, ctx):
		if isa(xpr, KlipList):
			if not len(xpr):
				return self.finish('KlipList()', ctx, True)
			
			head = xpr[0]
			
			qq = ctx.qq
			
			if head == Sym('unquote'):
				qq -= 1
				if qq == 0:
					return self.c_xpr(xpr[1], ctx.derive(qq = qq, tail = False))
			elif head == Sym('unquotesplicing'):
				qq -= 1
				if qq == 0:
					inner = self.c_xpr(xpr[1], ctx.derive(qq = qq, tail = False))
					return self.finish('SpliceWrapper(%s)' % inner.pyx, ctx, True)
			elif head == Sym('quasiquote'):
				qq += 1
			
			subctx = ctx.derive(qq = qq, tail = False)
			methName = self.nextMethName()
			
			#Pretty much copied from c_list. Is there a way to generalize this, and the one in c_hash?
			pyArgs = ['self.get("list")']
			temps = []
			for sub in xpr:
				#self.comment(str(self.temp.unsaved) + str(self.temp.saved))
				self.temp.push(self, 2)
				ci = self.c_xpr(sub, subctx)
				if ci.needsTemp:
					key = self.temp.set(ci.pyx)
					temps.append((key, len(pyArgs)))
				pyArgs.append(ci.pyx)
			
			for key, ix in temps:
				pyArgs[ix] = self.temp.getPyx(key)
			
			# if ctx.tail:
				# pyArgs.insert(1, 'self.get(" cont")')
			# else:
				# pyArgs.insert(1, 'self.%s' % methName)
			
			pyArgs.insert(1, 'self.%s' % methName)
			self.doCall(pyArgs, ctx)
			[self.temp.rem(key) for key, ix in temps]
			
			# if ctx.tail:
				# return None
			self.line(1, 'def %s(self, ret):' % methName)
			return self.finish('KlipList(flatten(ret))', ctx, True)
		
		if isa(xpr, KlipHash):
			return self.c_hash(xpr, ctx)
		
		return self.finish(repr(xpr), ctx, True)
	
	_atomicTypes = set([int, float, KlipStr])
	
	def x_atom(self, xpr, ctx):
		if isa(xpr, Sym):
			return 'self.get("%s")' % xpr
		if type(xpr) in Compiler._atomicTypes:
			return repr(xpr)
		raise ValueError('Unknown atom type %s. (%s)' % (type(xpr), xpr))
	
	def c_xpr(self, xpr, ctx):
		if ctx.qq:
			return self.c_qq(xpr, ctx)
		
		try:
			macex = genv.get('macex')
		except KeyError:
			pass
		else:
			#self.comment('expanding %s' % xpr)
			xpr = Internal.wrap(macex, Internal.doHalt, xpr)
			#self.comment('expanded to %s' % xpr)
		
		if dxprs:
			self.comment(str(xpr))
		
		if isa(xpr, KlipList):
			return self.c_list(xpr, ctx)
		if isa(xpr, KlipHash):
			return self.c_hash(xpr, ctx)
		return self.finish(self.x_atom(xpr, ctx), ctx, False)
	
	def finish(self, pyx, ctx, needTemp):
		if ctx.tail:
			self.line(2, 'return self.get(" cont"), %s' % pyx)
			return None
		return CompInfo(pyx, needTemp)
	
	def doCall(self, args, ctx):
		self.line(2, 'return %s' % ', '.join(args))
	
	def line(self, indent, s):
		self.lines.append(indent * '\t' + s)
	
	def comment(self, s):
		self.lines.append('#' + s)
	
	def __str__(self):
		return '\n'.join(self.lines)
	
	def make(self):
		code = compile(str(self), 'Compiler %s' % self.name, 'exec')
		loc = {}
		exec(code, Internal.internals, loc)
		return loc[self.name]


_compCache = {}
def compFunc(k, parent, parmList, body):
	if not (parmList, body) in _compCache:
		c = Compiler(parmList, body)
		_compCache[(parmList, body)] = (c.name, c.make())
	
	name, temp = _compCache[(parmList, body)]
	cls = type(name, temp.__bases__, dict(temp.__dict__))
	cls._parent = parent
	return k, cls

Internal.internals['compFunc'] = compFunc


if __name__ == '__main__':
	import sys, traceback, builtins
	from Preprocess import preprocess
	from Tokenize import tokenize
	from Parse import parse
	
	for parm in sys.argv[1:]:
		setattr(builtins, parm, True)
	
	fin = open(sys.argv[1], 'r')
	tree = parse(tokenize(preprocess(fin.read()), sys.argv[1]), sys.argv[1])
	fin.close()
	
	#print(tree)

	# def disp(x):
		# print(len(traceback.extract_stack()), x)
		# raise Internal.Halt()
	
	#This is dumb.
	newTree = []
	for xpr in tree:
		if isa(xpr, KlipList):
			if len(xpr) and xpr[0] == Sym('include'):
				fin = open(xpr[1], 'r')
				newTree += parse(tokenize(preprocess(fin.read()), xpr[1]), xpr[1])
				fin.close()
			else:
				newTree.append(xpr)
	
	for xpr in newTree:
		c = Compiler(KlipList(), KlipList([xpr]))			#Possibly the call to macex should go here, and macex should take care of recursion.
		#print(c)
		f = c.make()
		f._parent = genv
		
		result = Internal.wrap(f(), Internal.justHalt)
		if result != nil:									#This is a dumb hack to deal with the fact that we're running each toplevel expression in a separate call to wrap. The halt form actually means something now, if you pass a non-nil argument to it.
			print(result)
			break


