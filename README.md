KLIP

Klip is a lexically scoped Lisp inspired by Arc.

Klip currently runs on a virtual machine implemented in Python. Why would anyone want to do this? Well, I thought it would be fun, and all the Lisp dialects I know of annoy me in some way.

It's nowhere near finished. This paragraph, for example, ends before it's really begun.


Special Symbols:

Klip differs slightly from other Lisps in the usage of some symbols. In particular, the shorthand for quote is ~, the shorthand for unquotesplicing is ;, comments are begun with #, and strings can be single-quoted. All special symbols are described below:
( )			literal cons
[ ]			literal array
{ }			literal hash
~			~x is shorthand for (quote x)
`			`x is shorthand for (quasiquote x)
,			,x is shorthand for (unquote x)
;			;x is shorthand for (unquotesplicing x)
.			(1 2 . 3) is an improper list whose last cons has a cdr of 3 rather than nil.
'			'blah' is a literal string
"			"can't" is a literal string
#			begins a rest-of-line comment


Special Forms:

(branch <conditional> <consequent> [<alternative>])
The branch form is used exactly six times in Klip. That's how many it takes to write the vastly more powerful if macro.

(fn <parameter list> <zero or more expressions>)
Lambda is spelled fn in Klip.

Parameter lists can be improper:
(fn (x . rest) ...) -> The name x will refer to the first argument passed to the function, and rest will refer to a cons list of all the remaining arguments.
(fn args ...) -> The name args will refer to a cons list of all the arguments passed to this function.

Parameter lists can contain conses:
(fn (n (acc . 1)) ...) -> acc will be given a default value of 1 if the function is called with fewer than two arguments. ****At the moment, default arguments are copied literally by the compiler, so only numbers, strings and unquoted symbols will work.

(assign <symbol> <expression>)
My intention is to implement something like Arc's = macro. That's why I chose the name assign instead of something shorter and better.

(ccc <function of one argument>)
Stands for Call with Current Continuation. It calls the function given and passes it the current continuation. This is a first-order continuation that can be called more than once and from outside the ccc form.

(mac <name> <argument list> <zero or more expressions>)
Creates a macro. Klip uses good, old-fashioned unhygienic macros. This form defines a function with the given arugment list and body. From now on, when the compiler finds an expression whose head is equal to name, it will call this function on the rest of the expression, and compile the return value of that function instead of the original expression.

(apply <function> <argument list>)
Applies the given function to the given arguments. The argument list can be a cons list or an array.

(include <file name>)
Behaves as if all the expressions in the specified file were inserted in this file here. Only valid at the toplevel.

(halt)
Stops the virtual machine.

(quote x)
(quasiquote x)
(unquote x)
(unquotesplicing x)
all work the way you'd expect.


Containers:

Conses, strings, ints, floats, symbols and functions are immutable.

There are two container types, array and hash. Both are mutable. They can be part of a Klip program, just like other types. A literal array is written like this:
[a b c ...]
and a literal hash like this:
{a b c d ...}
When a literal container is evaluated, its contents are evaluated, so [(+ 3 4) 5 6] evaluates to [7 5 6]. The expressions in a hash are key/value pairs. In the given example, a is associated with b, c with d, etc. There must be an even number of expressions. unquotesplicing works with arrays but not hashes.

Both arrays and hashes are considered atoms by all the traditional Lisp stuff.

There is a gotcha concerning containers. Conses have to be immutable (and hashable, in the Python sense) so that they can be put in hashes. Conses also have to be able to contain arrays and hashes, so that arrays and hashes can be part of programs. So, despite being immutable, conses can contain mutable objects. In a certain sense, the value of a cons can change (if the array it contains is changed) but it's still considered immutable. The equality test for conses uses the identity, rather than the value, of any mutable objects it contains. Thus,
(assign x (list [2 3]))
(assign y (list [2 3]))
(prn
	(== (car x) (car y))
	(== (cdr x) (cdr y))
	(== x y))
prints t t nil, not t t t. Both arrays have the value [2 3], and they are thus equal. But they are different arrays, so the conses containing them are not equal. Two conses are not equal unless they have the same value and are guaranteed to always have the same value. For less surprising comparison, use iso.

The contents of containers are accessed by indices. The indices of an array are consecutive integers starting with zero. The indices of a hash can be any immutable object. The contents of a container can be any object except nil. (****At the moment, there is not very much enforcement of this fact.)

Containers can be treated as functions. If a container is called with zero arguments,
(a) -> len(a)
the number of items in the container is returned. The number of items in a hash is the number of key/value pairs. If the container is called with one argument,
(a 1) -> a[1]
the item associated with that index is returned. If the function is called with two arguments,
(a 3 'fish') -> a[3] = 'fish'
the contents of the container are updated. If the second argument is nil,
(a 2 nil) -> a.pop(2)
the item at the given index is removed from the array and returned. If the container is an array, there are two more possibilities. If the second argument is nil and there is a third argument,
(a 4 nil 'bird') -> a.insert(4, 'bird')
the third argument is inserted into the array at the given index, and the contents of the array at that position and beyond are pushed forward. Also with an array, the first argument can be nil,
(a nil 5) -> a.append(5)
In this case, the second argument is appended to the end of the array.

Getting or setting an item in a container is O(1). Removing an item from an array and inserting an item into an array are O(n), where n is the number of items in the array after the one removed/inserted. Appending an item to an array is O(1), unless many items are appended, in which case it's probably O((log n) / m) where n is the total number of items in the array and m is the number appended (Python presumably has to reallocate the block of memory holding the array from time to time).

Array indices can be more interesting. Klip supports negative indices, as in Python.
(a -1) -> a[-1] (the last item in a)
(a -2 3) -> a[-2] = 3
Slices can also be specified by using a literal array.
(a [2 4]) -> a[2:4]
Slices can be used in assignment.
(a [2 4] ['x' 'y']) -> a[2:4] = ['x', 'y']
Missing ends of a slice are represented with t.
(a [2 t]) -> a[2:]
As in Python, slices can have one, two or three parameters. The three signatures are [stop], [start stop] and [start stop step].

Strings can also be considered containers. The items contained in a string are characters, which are themselves strings of length 1, as in Python. They are immutable, so they don't support item assignment.
(s) -> len(s)
(s 3) -> s[3]
(s [t -1]) -> s[:-1]
String formatting is accomplished by calling a string and passing nil for the first parameter.
(s nil a b c) -> s % (a, b, c)
Klip uses the C format specifiers, because no superior method for string formatting has yet been devised by man.
