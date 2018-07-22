import Prefix


class ParseError(Exception):
	pass


def _getInt(s):
	try:
		ret = int(s)
	except ValueError:
		return None
	return ret

def _getFloat(s):
	try:
		ret = float(s)
	except ValueError:
		return None
	return ret

def _getString(s):
	return KlipStr(bytes(s[1:-1], 'utf-8').decode('unicode_escape'))


class Parser(object):
	def inc(self, fail):
		try:
			self.cur = next(self.it)
		except StopIteration:
			if fail:
				raise ParseError(fail)
			else:
				self.cur = None
	
	def parseProclitic(self, procliticName, realName):
		fname = self.cur.fname
		line = self.cur.line
		self.inc('Dangling %s. %s line %d' % (procliticName, fname, line))
		temp = self.parseTerminal()
		return KlipList([Sym(realName), temp])
	
	def parseTerminal(self):
		if self.cur.value == '(':
			complaintParms = self.cur.fname, self.cur.line
			temp = KlipList()
			self.inc('Unmatched open parenthesis. %s line %d' % complaintParms)
			while True:
				if self.cur.value == ')':
					return temp
				temp.append(self.parseTerminal())
				self.inc('Unmatched open parenthesis. %s line %d' % complaintParms)
		
		if self.cur.value == '{':
			complaintParms = self.cur.fname, self.cur.line
			ret = KlipHash()
			self.inc('Unmatched open brace. %s line %d' % complaintParms)
			while True:
				if self.cur.value == '}':
					return ret
				
				k = self.parseTerminal()
				if k == nil:
					k.doRaise(ParseError, "nil can't be a key in a hash.")
				self.inc('Unmatched open brace. %s line %d' % complaintParms)
				
				if self.cur.value == '}':
					raise ParseError('Key with no value in literal hash. %s line %d' % complaintParms)
				
				v = self.parseTerminal()
				if v == nil:
					v.doRaise(ParseError, "hashes can't contain nil.")
				self.inc('Unmatched open brace. %s line %d' % complaintParms)
				
				ret[k] = v
		
		if self.cur.value == '~':
			return self.parseProclitic('~', 'quote')
		if self.cur.value == '`':
			return self.parseProclitic('`', 'quasiquote')
		if self.cur.value == ',':
			return self.parseProclitic(',', 'unquote')
		if self.cur.value == ';':
			return self.parseProclitic(';', 'unquotesplicing')
		
		if self.cur.value.startswith("'") or self.cur.value.startswith('"'):
			return _getString(self.cur.value)
		
		i = _getInt(self.cur.value)
		if i != None:
			return i
		
		f = _getFloat(self.cur.value)
		if f != None:
			return f
		
		return Sym(self.cur.value)
	
	def __call__(self, tokens, fname):
		self.fname = fname
		self.input = tokens
		self.it = iter(tokens)
		self.inc(None)
		
		temp = KlipList()
		
		while self.cur:
			temp.append(self.parseTerminal())
			self.inc(None)
		
		return temp



parse = Parser()


if __name__ == '__main__':
	from Preprocess import preprocess
	from Tokenize import tokenize
	import sys, pprint
	fin = open(sys.argv[1], 'r')
	tree = parse(tokenize(preprocess(fin.read()), sys.argv[1]), sys.argv[1])
	fin.close()
	
	print(tree)

