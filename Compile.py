import Prefix
import Internal

class CompileError(Exception):
	pass


def _print(k, *args):
	print(*args)
	raise Internal.TailCall(k, nil)

def _add(k, *args):
	raise Internal.TailCall(k, sum(args))


genv = Internal.GlobalEnv({
	'nil' : nil,
	't' : t,
	'prn' : _print,
	'+' : _add,
	'macex' : lambda x: x,
})



class CompCtx(object):
	def __init__(self, prev = None, **kwargs):
		if prev:
			self.__dict__.update(prev.__dict__)
		self.__dict__.update(kwargs)
	
	def __getattr__(self, name):
		return None

_uniqueCounter = 0
def nextUnique():
	global _uniqueCounter
	ret = _uniqueCounter
	_uniqueCounter += 1
	return ret


class Temp(object):
	def __init__(self):
		self.maxTemps = 0
		self._curTempKey = 0
		self.unsaved = {}
		self.saved = {}
	
	def set(self, pyx):
		key = self._curTempKey
		self._curTempKey += 1
		self.unsaved[key] = pyx
		return key
	
	def _findOpenTemp(self):
		ret = 0
		while ret in self.saved:
			ret += 1
		self.maxTemps = max(self.maxTemps, ret + 1)
		return ret
	
	def push(self, c, indent):
		for key, pyx in self.unsaved.items():
			newPyx = 'self.temps[%d]' % self._findOpenTemp()
			c.line(indent, '%s = %s' % (newPyx, pyx))
			self.saved[key] = newPyx
		self.unsaved = {}
	
	def getPyx(self, key):
		if key in self.unsaved:
			return self.unsaved[key]
		if key in self.saved:
			return self.saved[key]
		raise ValueError("Can't find temp key %d." % key)
	
	def rem(self, key):
		if key in self.unsaved:
			del self.unsaved[key]
		elif key in self.saved:
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
	def __init__(self, parmList, body, name = 'f'):
		self.lines = []
		self.name = name
		
		self.curMethod = 1
		
		self.temp = Temp()
		
		self.line(0, 'class %s(Func):' % self.name)
		
		pyParms = ['self', 'k']
		for parm in parmList:
			if isa(parm, KlipList):
				if len(parm) == 1:
					pyParms.append('%s*' % parm[0])
				else:
					pyParms.append('%s = %s' % (parm[0], parm[1]))			#Doesn't work yet. And won't ever work, because Python default parameters are only evaluated once. Need to create special values in the class body that are the defaults, and then check for them and generate default code.
			else:
				pyParms.append(str(parm))
		
		self.line(1, 'def __call__(%s):' % ', '.join(pyParms))
		self.line(2, 'self.setLocal(" cont", k)')
		for arg in pyParms[2:]:
			self.line(2, 'self.setLocal("%s", %s)' % (arg, arg))		#Ugh.
		
		try:
			ctx = CompCtx(tail = False)
			for xpr in body[:-1]:
				self.c_xpr(xpr, ctx)
			self.c_xpr(body[-1], CompCtx(ctx, tail = True))
		except Exception as e:
			print('PARTIAL COMPILER DUMP:')
			print(str(self))
			raise e
		
		self.line(1, 'def __init__(self, parent):')
		self.line(2, 'Func.__init__(self, parent, %d)' % self.temp.maxTemps)
		
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
		
		if ctx.tail:
			k = 'self.get(" cont")'
		else:
			methName = self.nextMethName()
			k = 'self.makeCont(self.%s)' % methName
		
		self.line(2, 'raise TailCall(compFunc, %s, *%s)' % (k, fnName))
		
		if ctx.tail:
			return None
		self.line(1, 'def %s(self, ret):' % methName)
		self.line(2, 'ret = ret(self)')
		return self.finish('ret', ctx, True)
	
	def c_branch(self, rest, ctx):
		cond = rest[0]
		result = rest[1]
		alternative = len(rest) > 2 and rest[2]
		
		ci = self.c_xpr(cond, CompCtx(ctx, tail = False))
		self.line(2, 'if (%s != nil):' % ci.pyx)
		
		if ctx.tail:
			cont = 'self.get(" cont")'
		else:
			finalMeth = self.nextMethName()
			cont = 'self.makeCont(self.%s)' % finalMeth
		
		resultMeth = self.nextMethName()
		self.line(3, 'raise TailCall(self.%s, None)' % (resultMeth))
		self.line(2, 'else:')
		if alternative:
			alternativeMeth = self.nextMethName()
			self.line(3, 'raise TailCall(self.%s, None)' % (alternativeMeth))
		else:
			self.line(3, 'raise TailCall(%s, nil)' % cont)
		
		self.line(1, 'def %s(self, k):' % resultMeth)
		ci = self.c_xpr(result, ctx)
		if ci:
			self.line(2, 'raise TailCall(%s, %s)' % (cont, ci.pyx))
		
		if alternative:
			self.line(1, 'def %s(self, k):' % alternativeMeth)
			ci = self.c_xpr(alternative, ctx)
			if ci:
				self.line(2, 'raise TailCall(%s, %s)' % (cont, ci.pyx))
		
		if ctx.tail:
			return None
		
		self.line(1, 'def %s(self, ret):' % finalMeth)
		return self.finish('ret', ctx, True)
	
	_specialTable = {
		'fn' : c_fn,
		'branch' : c_branch,
	}
	
	def c_list(self, xpr, ctx):
		if len(xpr) == 0:
			return self.finish('KlipList()', ctx, True)
		
		head = xpr[0]
		if isa(head, Sym) and head.name in Compiler._specialTable:
			return Compiler._specialTable[head.name](self, xpr[1:], ctx)
		
		methName = self.nextMethName()
		subctx = CompCtx(ctx, tail = False)
		
		#Create a list of arguments, carefully keeping track of which ones might be temped during the execution of the subsequent ones:
		pyArgs = []
		temps = []
		for sub in xpr:
			self.temp.push(self, 2)
			ci = self.c_xpr(sub, subctx)
			if ci.needsTemp:
				key = self.temp.set(ci.pyx)
				temps.append((key, len(pyArgs)))		#Record the temp key and the position in the arg list so we can go back and fix them up.
			pyArgs.append(ci.pyx)
		
		#And now replace all the ones that were temped:
		for record in temps:
			key, ix = record
			pyArgs[ix] = self.temp.getPyx(key)
		
		if ctx.tail:
			pyArgs.insert(1, 'self.get(" cont")')
		else:
			pyArgs.insert(1, 'self.makeCont(self.%s)' % methName)
		self.doCall(pyArgs, ctx)
		[self.temp.rem(key) for key, ix in temps]			#Deleting all temps is only correct because parms aren't temped. If parms are temped, we need to know the last time a parm is used in the function.
		
		if ctx.tail:
			return None
		self.line(1, 'def %s(self, ret):' % methName)
		return self.finish('ret', ctx, True)
	
	def c_xpr(self, xpr, ctx):
		#self.comment(str(xpr))
		if isa(xpr, KlipList):
			return self.c_list(xpr, ctx)
		return self.finish(self.x_atom(xpr, ctx), ctx, False)
	
	def x_atom(self, xpr, ctx):
		if isa(xpr, Sym):
			return 'self.get("%s")' % xpr
		if isa(xpr, int) or isa(xpr, float):
			return str(xpr)
		if isa(xpr, KlipStr):
			return '"%s"' % xpr
		raise ValueError('Unknown atom type %s. (%s)' % (type(xpr), xpr))
	
	def finish(self, pyx, ctx, needTemp):
		if ctx.tail:
			self.line(2, 'raise TailCall(self.get(" cont"), %s)' % pyx)
			return None
		return CompInfo(pyx, needTemp)
	
	def doCall(self, args, ctx):
		self.line(2, 'raise TailCall(')
		for arg in args:
			self.line(3, '%s,' % arg)
		self.line(2, ')')
	
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


def compFunc(k, parmList, body):
	c = Compiler(parmList, body)
	raise Internal.TailCall(k, c.make())

Internal.internals['compFunc'] = compFunc


if __name__ == '__main__':
	import sys, traceback
	from Preprocess import preprocess
	from Tokenize import tokenize
	from Parse import parse
	
	fin = open(sys.argv[1], 'r')
	tree = parse(tokenize(preprocess(fin.read()), sys.argv[1]), sys.argv[1])
	fin.close()
	
	print(tree)
	
	c = Compiler(KlipList(), tree)
	f = c.make()

	def disp(x):
		print(len(traceback.extract_stack()), x)
		raise Internal.Halt()
	
	Internal.wrap(f(genv), disp)


