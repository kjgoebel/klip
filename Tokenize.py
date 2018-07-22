

class Token(object):
	def __init__(self, value, fname, line):
		self.value = value
		self.fname = fname
		self.line = line
	
	def __repr__(self):
		return 'Node(%s, %s, %d)' % (repr(self.value), repr(self.fname), self.line)
	
	def __str__(self):
		return str(self.value)


class TokenizeError(Exception):
	pass


gSingleCharTokens = {'(', ')', '{', '}', '~', '`', ',', ';', ':'}




class Tokenizer(object):
	def endWord(self):
		if self.curWord:
			self.tokens.append(Token(self.curWord, self.fname, self.line))
			self.curWord = None
	
	def contWord(self, c):
		if self.curWord:
			self.curWord += c
		else:
			self.curWord = c
	
	def readString(self, quote):
		startLine = self.line
		self.contWord(self.input[self.i])
		self.i += 1
		escaping = False
		
		while self.i < len(self.input):
			c = self.input[self.i]
			self.contWord(c)
			if c == quote and self.curWord[-2] != '\\':
				self.endWord()
				return
			
			self.i += 1
		
		raise TokenizeError('End of input before end of string. %s line %d' % (self.fname, startLine))
	
	def __call__(self, s, fname = ''):
		self.fname = fname
		self.input = s
		self.line = 1
		
		self.tokens = []
		self.curWord = None
		self.i = 0
		
		while self.i < len(self.input):
			c = self.input[self.i]
			if c == '\n':
				self.line += 1
			
			if c == "'":
				self.endWord()
				self.readString("'")
			elif c == '"':
				self.endWord()
				self.readString('"')
			elif c in gSingleCharTokens:
				self.endWord()
				self.tokens.append(Token(c, self.fname, self.line))
			elif c.isspace():
				self.endWord()
			else:
				self.contWord(c)
			
			self.i += 1
		self.endWord()
		
		return self.tokens

tokenize = Tokenizer()
		

if __name__ == '__main__':
	import Preprocess
	import sys, pprint
	fin = open(sys.argv[1], 'r')
	pprint.pprint(tokenize(Preprocess.preprocess(fin.read()), sys.argv[1]))
	fin.close()

