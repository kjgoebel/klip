import Prefix, Internal
from Code import Env

_global = Env(None, 'Global', Internal.klipDefaults)

from Preprocess import preprocess
from Tokenize import tokenize
from Parse import parse
import sys

fin = open(sys.argv[1], 'r')
tree = parse(tokenize(preprocess(fin.read()), sys.argv[1]), sys.argv[1])
fin.close()

import builtins

builtins.debugTrace = ('dtrace' in sys.argv[1:])
builtins.debugCompile = ('dcompile' in sys.argv[1:])
builtins.debugEnv = ('denv' in sys.argv[1:])

from Compile import compFile
from Code import Func
from Compute import Computer
builtins.Computer = Computer			#This is a shitty hack to give Compile._macex access to Computer.

func = Func(_global, compFile(_global, tree))

computer = Computer(func)
while True:
	try:
		computer.step()
	except StopIteration:
		break
print('*****FINISHED EXECUTION*****')
print(computer.stack)




