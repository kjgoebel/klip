import Prefix
import Internal
import Asm
from Defaults import genv
import dis

class CompileError(Exception):
	pass



uniqueCounter = 0
def getUnique():
	global uniqueCounter
	uniqueCounter += 1
	return uniqueCounter



def r_macroExpand(xpr, macex):
	xpr = Internal.wrap(macex, Internal.justHalt, xpr)
	for i, sub in enumerate(xpr):
		xpr[i] = r_macroExpand(sub, macex)
	return xpr

def macroExpand(xpr):
	try:
		macex = genv.get('macex')
	except KeyError:
		return xpr
	return r_macroExpand(xpr, macex)

#This can be turned into a dispatch dict: 'fn' : c_fn, etc.
_specialForms = dict.fromkeys(map(lambda x: Sym(x), [
	'branch', 'fn', 'ccc', 'quote', 'quasiquote', 'unquote', 'unquotesplicing', 'include', 'assign', 'get-safe', 'halt',
]))



def getNodeType(xpr):
	try:
		return xpr.nodeType
	except AttributeError:
		if isa(xpr, KlipList):
			if len(xpr):
				if xpr[0] in _specialForms:
					return xpr[0].name
				return 'combination'
			else:
				return '()'
		elif isa(xpr, Sym):
			return 'sym'
		elif isa(xpr, KlipHash):
			return 'hash'
		else:
			return 'datum'


def activeChildren(xpr):
	nt = getNodeType(xpr)
	if nt == 'parmlist':
		if isa(xpr, Sym):
			raise StopIteration
		for parm in xpr:
			if isa(parm, KlipList):
				yield from parm[1:]
	elif nt == 'combination':
		yield from xpr
	elif isa(xpr, KlipList):
		yield from xpr[1:]
	elif isa(xpr, KlipHash):
		for k, v in xpr.items():
			yield k
			yield v
		raise StopIteration
	else:
		raise StopIteration


def analyzeNodeTypes(xpr):
	if isa(xpr, KlipList):
		xpr.nodeType = getNodeType(xpr)
		if xpr.nodeType == 'fn':
			xpr[1].nodeType = 'parmlist'
	for sub in activeChildren(xpr):
		analyzeNodeTypes(sub)


def getParmNames(parmList):
	ret = set()
	if isa(parmList, Sym):
		ret.add(parmList)
	else:
		for parm in parmList:
			if isa(parm, KlipList):
				ret.add(parm[0])
			else:
				ret.add(parm)
	return ret


def analyzeEnvs(xpr, env):
	nt = getNodeType(xpr)
	if nt == 'fn':
		xpr.parms = getParmNames(xpr[1])
		xpr.inherited = env - xpr.parms
		xpr.heritable = {}
		
		subenv = env | xpr.parms
		
		for i, sub in enumerate(xpr[1:]):
			for var in analyzeEnvs(sub, subenv):
				if var in xpr.parms:
					xpr.heritable[var] = i
		
		return xpr.inherited
	
	ret = set()
	for sub in activeChildren(xpr):
		ret |= analyzeEnvs(sub, env)
	return ret


def analyzeContinuations(xpr, heritable = set()):
	nt = getNodeType(xpr)
	if nt == 'fn':
		for i, sub in enumerate(xpr[1:]):
			subherit = heritable | {var for var, lastIndex in xpr.heritable.items() if lastIndex >= i}
			analyzeContinuations(sub, subherit)
		return
	
	if nt == 'combination':
		xpr.knum = getUnique()
		xpr.kvars = heritable
	
	for sub in activeChildren(xpr):
		analyzeContinuations(sub, heritable)


def c_datum(xpr, a, waiting):
	if waiting:
		a.const(xpr)
	return a

def c_sym(xpr, a, waiting):
	if waiting:
		a.load(xpr.pyx())
	return a


_c_Table = {
	'datum' : c_datum,
	'sym' : c_sym,
	#'combination' : c_combo,
}



def c_xpr(xpr, a, waiting):
	nt = getNodeType(xpr)
	
	f = _c_Table.get(nt, None)
	
	if f:
		return f(xpr, a, waiting)
	
	raise CompileError('not implemented %s' % nt)



def compFunc(node):
	parms = [parm.pyx() for parm in node.parms]
	inherited = [var.pyx() for var in node.inherited]
	heritable = [var.pyx() for var in node.heritable.keys()]
	body = node[2:]
	
	a = Asm.Asm(
		parms,
		None,
		inherited,
		heritable,
		str(node)
	)
	
	aa = a
	for xpr in body[:-1]:
		aa = c_xpr(xpr, aa, False)
	c_xpr(body[-1], aa, True)
	
	a.add('RETURN_VALUE')
	
	return a




def run(xpr):
	xpr = macroExpand(xpr)
	analyzeNodeTypes(xpr)
	analyzeEnvs(xpr, set())
	analyzeContinuations(xpr)
	
	def r_show(xpr, indent = ''):
		nt = getNodeType(xpr)
		print('%s%s:' % (indent, nt))
		
		items = []
		if hasattr(xpr, 'freeVars'):
			items.append('freeVars = %s' % xpr.freeVars)
		
		if hasattr(xpr, 'knum'):
			items.append('knum = %d' % xpr.knum)
			items.append('kvars = %s' % xpr.kvars)
		
		if nt == 'parmlist':
			items.append(str(xpr))
		elif nt == 'fn':
			items.append('parms = %s' % xpr.parms)
			items.append('inherited = %s' % xpr.inherited)
			items.append('heritable = %s' % xpr.heritable)
		elif not isa(xpr, KlipList):
			items.append(repr(xpr))
		
		indent += '\t'
		for item in items:
			print(indent + item)
		
		if isa(xpr, KlipList) and nt != 'parmlist':
			for sub in xpr:
				r_show(sub, indent + '\t')
		
		# if nt == 'fn':
			# a = compFunc(xpr)
			# f = a.makeF('func%d' % getUnique(), globals(), None, None)
			# dis.dis(f)
			# print(f(2, 1))
			# return f
		
	r_show(xpr)



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
	
	print(tree)
	
	for xpr in tree:
		run(xpr)
	
	# s = '''
		# (fn (x y) 3 x)
	# '''
	# tree = parse(tokenize(preprocess(s), 'string'), 'string')
	# print(tree)
	# run(tree)

	


