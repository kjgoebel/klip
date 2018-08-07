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
		start = self.cur
		self.inc('Dangling %s. %s' % (procliticName, start.complaint()))
		return self.parseTerminal()
	
	def parseTerminal(self):
		if self.cur.value == '(':
			start = self.cur
			ret = KlipList()
			ret.parseInfo = start
			self.inc('Unmatched open parenthesis. %s' % start.complaint())
			while True:
				if self.cur.value == ')':
					return ret
				ret.append(self.parseTerminal())
				self.inc('Unmatched open parenthesis. %s' % start.complaint())
		
		if self.cur.value == '{':
			start = self.cur
			ret = KlipHash()
			ret.parseInfo = self.cur
			self.inc('Unmatched open brace. %s' % start.complaint())
			while True:
				if self.cur.value == '}':
					return ret
				
				k = self.parseTerminal()
				if k == nil:
					k.doRaise(ParseError, "nil can't be a key in a hash.")
				self.inc('Unmatched open brace. %s' % start.complaint())
				
				if self.cur.value == '}':
					raise ParseError('Key with no value in literal hash. %s' % start.complaint())
				
				v = self.parseTerminal()
				if v == nil:
					v.doRaise(ParseError, "hashes can't contain nil.")
				self.inc('Unmatched open brace. %s' % start.complaint())
				
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
		
		ret = Sym(self.cur.value)
		ret.parseInfo = self.cur
		return ret
	
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
	
	print(repr(tree))

