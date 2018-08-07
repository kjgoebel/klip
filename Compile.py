import Prefix
import Internal
from Defaults import genv

class CompileError(Exception):
	pass



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



# def analyzeFreeVars(xpr):
	# if hasattr(xpr, 'freeVars'):
		# return xpr.freeVars
	
	# ret = set()
	# for sub in activeChildren(xpr):
		# ret |= analyzeFreeVars(sub)
	
	# nt = getNodeType(xpr)
	
	# if nt == 'fn':
		# xpr.parms = getParmNames(xpr[1])
		# ret -= xpr.parms
	
	# if nt == 'sym':
		# ret.add(xpr)
	
	# if nt != 'datum':
		# xpr.freeVars = ret
	
	# return ret


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
					xpr.heritable[var] = i - 1
		
		return xpr.inherited
	
	ret = set()
	for sub in activeChildren(xpr):
		ret |= analyzeEnvs(sub, env)
	return ret



def run(xpr):
	xpr = macroExpand(xpr)
	analyzeNodeTypes(xpr)
	# analyzeFreeVars(xpr)
	analyzeEnvs(xpr, set())
	
	def r_show(xpr, indent = ''):
		nt = getNodeType(xpr)
		print('%s%s:' % (indent, nt))
		
		items = []
		if hasattr(xpr, 'freeVars'):
			items.append('freeVars = %s' % xpr.freeVars)
		
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

	


