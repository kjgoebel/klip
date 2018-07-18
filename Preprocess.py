

def preprocess(s):
	lines = s.split('\n')
	lines = [x.split('#')[0] for x in lines]
	s = '\n'.join(lines)
	return s

