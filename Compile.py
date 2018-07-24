import Prefix
from Code import *
from Preprocess import preprocess
from Tokenize import tokenize
from Parse import parse



class CompileError(Exception):
	pass


_cont = Sym(' cont')
_contList = KlipList([_cont])
_ret = Sym(' ret')
_retList = KlipList([_ret])
_dummy = Sym(' dummy')


def _finish(ret, cap, waiting, tail):
	if tail:
		ret += [
			Ld(_cont),
			cap,
			Call(1, notes = '_finish')
		]
	elif waiting:
		ret.append(cap)
	return ret


def c_branch(env, rest, offset, waiting, tail):
	cond = c_xpr(env, rest[0], offset, True, False)
	consequent = c_xpr(env, rest[1], offset + len(cond) + 1, waiting, tail)
	
	if len(rest) > 2:
		alternative = c_xpr(env, rest[2], offset + len(cond) + len(consequent) + 2, waiting, tail)
		consequent.append(Jmp(len(alternative)))
	else:
		alternative = _finish([], Lit(nil), waiting, tail)
		if alternative:
			consequent.append(Jmp(len(alternative)))
	
	cond.append(Br(len(consequent)))
	
	return cond + consequent + alternative

# def c_assign(env, rest, offset, waiting, tail):
	# ret = c_xpr(env, rest[1], offset, True, False)
	# ret.append(St(rest[0]))
	# return _finish(ret, Ld(rest[0]), waiting, tail)

def c_fn(env, rest, offset, waiting, tail):
	parmList = rest[0]
	if isa(parmList, Sym):
		parmList = KlipList([_cont, KlipList([parmList])])		#Man, this is ugly. And slow.
	else:
		parmList = KlipList([_cont] + parmList)					#This is also ugly and slow.
	return _finish([], Fn(parmList, rest[1:]), waiting, tail)

def c_ccc(env, rest, offset, waiting, tail):
	ret = c_xpr(env, rest[0], offset, True, False)
	
	#This is the continuation that will be invoked by the tail of the user 
	#function if it returns normally.
	normalCont = Cont(_retList, 'Dummy value. See below.')
	ret.append(normalCont)
	
	#This is the continuation that will be invoked if the user function 
	#explicitly calls it. The _dummy is the continuation back to user code 
	#which will never be called.
	userCont = Cont(KlipList([_dummy, _ret]), 'Dummy value. See below.', 2)			#Remove the user function and the normal continuation from the saved stack.
	ret.append(userCont)
	
	ret.append(Call(2))
	
	#Explicit call of cc lands here...
	userCont.pos = offset + len(ret)
	ret += [
		Arg('Missing dummy argument.'),
		Pop(),								#and the user continuation is discarded.
	]
	
	#Regular return of user function lands here.
	normalCont.pos = offset + len(ret)
	return _finish(ret, Arg('Missing return value.'), waiting, tail)

def c_quote(env, rest, offset, waiting, tail):
	return _finish([], Lit(rest[0]), waiting, tail)

def c_quasiquote(env, rest, offset, waiting, tail):
	return c_xpr(env, rest[0], offset, waiting, tail, 1)

def c_unquote(env, rest, offset, waiting, tail):
	raise CompileError('unquote is undefined at quote level 0.')

def c_unquotesplicing(env, rest, offset, waiting, tail):
	raise CompileError('unquotesplicing is undefined at quote level 0.')

def c_mac(env, rest, offset, waiting, tail):
	name = rest[0]
	parmList = rest[1]
	body = rest[2:]
	_allMacros[name] = parmList, compMacro(env, body, parmList)
	return _finish([], Lit(nil), waiting, tail)

def c_apply(env, rest, offset, waiting, tail):
	ret = c_xpr(env, rest[0], offset, True, False)
	temp = Cont(_retList, 'Dummy value. See below.')
	ret.append(temp)
	ret += c_xpr(env, rest[1], offset + len(ret), True, False)
	ret.append(Splice())
	ret.append(Call(2))
	temp.pos = offset + len(ret)
	return _finish(ret, Arg('Missing return value.'), waiting, tail)

def c_halt(env, rest, offset, waiting, tail):
	return [Halt()]


_specialTable = {
	'branch' : c_branch,
	'fn' : c_fn,
	#'assign' : c_assign,
	'ccc' : c_ccc,
	'quote' : c_quote,
	'quasiquote' : c_quasiquote,
	'unquote' : c_unquote,
	'unquotesplicing' : c_unquotesplicing,
	'mac' : c_mac,
	'apply' : c_apply,
	'halt' : c_halt,
}


_allMacros = {}


def macex(xpr, head = True):
	if isa(xpr, KlipList):
		changed = False
		while isa(xpr, KlipList) and isa(xpr[0], Sym) and xpr[0] in _allMacros:
			parmList, func = _allMacros[xpr[0]]
			c = Computer(func)
			c.env.setArgs(xpr[1:])
			#wrangleArgs(c.env, parmList, args)
			
			while True:
				try:
					c.step()
				except StopIteration:
					break
			xpr = c.stack[0]
			changed = True
		if changed and debugCompile:
			print('EXPANDED TO %s' % xpr)
	return xpr

#This is provided for ExtractNames.
def getAllMacros():
	return _allMacros


def c_hash(env, xpr, offset, waiting, tail, qq = 0):
	ret = [Ld(Sym('hash'))]
	temp = Cont(_retList, 'Dummy value. See below.')
	ret.append(temp)
	for k, v in xpr.items():
		ret += c_xpr(env, k, offset + len(ret), True, False, qq)
		ret += c_xpr(env, v, offset + len(ret), True, False, qq)
	ret.append(Call(2 * len(xpr) + 1))
	temp.pos = offset + len(ret)
	return _finish(ret, Arg('Missing return value.'), waiting, tail)


def c_qq(env, xpr, offset, waiting, tail, qq):
	if isa(xpr, KlipList):
		if not len(xpr):
			return [Lit(xpr)]
		
		head = xpr[0]
		
		if head == Sym('unquote'):
			qq -= 1
			if qq == 0:
				return c_xpr(env, xpr[1], offset, waiting, tail, qq)
		elif head == Sym('unquotesplicing'):
			qq -= 1
			if qq == 0:
				ret = c_xpr(env, xpr[1], offset, waiting, tail, qq)
				ret.append(Splice())
				return ret
		elif head == Sym('quasiquote'):
			qq += 1
		
		ret = [Ld(Sym('list'))]
		temp = Cont(_retList, 'Dummy value. See below.')
		ret.append(temp)
		for sub in xpr:
			ret += c_xpr(env, sub, offset + len(ret), True, False, qq)
		ret.append(Call(len(xpr) + 1))
		temp.pos = offset + len(ret)
		return _finish(ret, Arg('Missing return value.'), waiting, tail)
	
	if isa(xpr, KlipHash):
		return c_hash(env, xpr, offset, waiting, tail, qq)
		
	return [Lit(xpr)]


def c_body(env, xpr, offset, waiting, tail):
	if not xpr:
		return _finish([], Lit(nil), waiting, tail)
	ret = []
	for sub in xpr[:-1]:
		ret += c_xpr(env, sub, offset + len(ret), False, False)
	ret += c_xpr(env, xpr[-1], offset + len(ret), waiting, tail)
	return ret


def c_list(env, xpr, offset, waiting, tail):
	head = xpr[0]
	rest = xpr[1:]
	
	#Special forms:
	if isa(head, Sym):
		f = _specialTable.get(head.name, None)
		if f:
			return f(env, rest, offset, waiting, tail)
	
	#ordinary combination:
	if tail:
		ret = c_xpr(env, head, offset, True, False)
		ret.append(Ld(_cont))
		for sub in xpr[1:]:
			ret += c_xpr(env, sub, offset + len(ret), True, False)
		ret.append(Call(len(xpr)))			#-1 for the fn itself, +1 for the continuation.
	else:
		ret = c_xpr(env, xpr[0], offset, True, False)
		temp = Cont(_retList, 'Dummy value. See below.')
		ret.append(temp)
		for sub in rest:
			ret += c_xpr(env, sub, offset + len(ret), True, False)
		ret.append(Call(len(xpr)))
		temp.pos = offset + len(ret)
		if waiting:
			ret.append(Arg('Missing return value.'))
	return ret


_xprTable = {
	KlipList : c_list,
	KlipHash : c_hash
}


def c_xpr(env, xpr, offset, waiting, tail, qq = 0):
	if qq:
		return c_qq(env, xpr, offset, waiting, tail, qq)
	
	xpr = macex(xpr)
	
	f = _xprTable.get(type(xpr), None)
	if f:
		return f(env, xpr, offset, waiting, tail)
	
	if isa(xpr, Sym):
		return _finish([], Ld(xpr), waiting, tail)
	
	return _finish([], Lit(xpr), waiting, tail)


def c_parms(env, parmList):
	ret = []
	if isa(parmList, KlipList):
		for parm in parmList:
			if isa(parm, KlipList):
				if len(parm) == 1:
					ret += [RestArg(), StLocal(parm[0])]
				else:
					temp = DefArg('Dummy value. See below.')
					ret.append(temp)
					ret += c_xpr(env, parm[1], len(ret), True, False, 0)
					temp.pos = len(ret)
					ret.append(StLocal(parm[0]))
			else:
				ret += [Arg('Missing argument. %s' % parmList), StLocal(parm)]
	else:
		ret += [RestArg(), StLocal(parmList)]
	ret.append(NoArgsLeft('Too many arguments. %s' % parmList))
	return ret



_compCache = {}

def _doComp(env, body, parmList):
	if debugCompile:
		print('COMPILING', body)
	try:
		ret = c_parms(env, parmList)
		ret += c_body(env, body, len(ret), True, True)
	except Exception as e:
		print('ERROR WHILE COMPILING:\n', body)
		raise e
	if debugCompile:
		print('COMPILED')
		dumpCode(ret)
	return ret

def comp(env, parmList, body):
	if (parmList, body) in _compCache:
		code = _compCache[(parmList, body)]
	else:
		code = _doComp(env, body, parmList)
		_compCache[(parmList, body)] = code
	
	ret = LitFunc(Func(env, code), None, parmList, 0)
	return ret


def compFile(env, tree, offset = 0, main = True):
	if debugCompile:
		print('COMPILING FILE', tree)
	code = []
	for xpr in tree:
		try:
			if isa(xpr, KlipList) and xpr[0] == Sym('include'):
				fname = xpr[1]
				fin = open(fname, 'r')
				sub = parse(tokenize(preprocess(fin.read()), fname), fname)
				fin.close()
				code += compFile(env, sub, offset + len(code), False)
			else:
				#This seems super inefficient. But I don't see any other way of allowing macros to see earlier function definitions.
				code.append(Fn(_contList, KlipList([xpr])))
				code.append(Cont(_retList, len(code) + 2))
				code.append(Call(1, notes = 'compFile'))
		except Exception as e:
			print('ERROR WHILE COMPILING TOPLEVEL XPR:\n', xpr)
			raise e
	if main:
		code.append(Halt())
		if debugCompile:
			print('COMPILED FILE')
			dumpCode(code)
	return code

def compMacro(env, tree, parmList):
	if debugCompile:
		print('COMPILING MACRO', id(env), tree)
	try:
		code = c_parms(env, parmList)
		code += c_body(env, tree, len(code), True, False)
		code.append(Halt())
	except Exception as e:
		print('ERROR WHILE COMPILING MACRO:\n', tree)
		raise e
	if debugCompile:
		print('COMPILED MACRO')
		dumpCode(code)
	return Func(env, code)


if __name__ == '__main__':
	import sys
	
	fin = open(sys.argv[1], 'r')
	tree = parse(tokenize(preprocess(fin.read()), sys.argv[1]), sys.argv[1])
	fin.close()
	
	print(tree)
	
	lf = comp(None, KlipList(), tree)
	
	dumpCode(lf.func.code)

