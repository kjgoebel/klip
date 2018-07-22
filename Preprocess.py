

def preprocess(s):
	s = s.replace('[', '(list ').replace(']', ')')
	lines = s.split('\n')
	lines = [x.split('#')[0] for x in lines]
	s = '\n'.join(lines)
	return s

