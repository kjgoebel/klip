# Klip
Klip is a lexically scoped Lisp inspired by Arc.

Klip currently runs on a virtual machine implemented in Python. Why would anyone want to do this? Well, I thought it would be fun, and all the Lisp dialects I know of annoy me in some way.

It's nowhere near finished. This paragraph, for example, ends before it's really begun.

### Special Symbols
Klip differs from other Lisps in the usage of some symbols. In particular, the shorthand for quote is "~", the shorthand for unquotesplicing is ";", comments are begun with "\#", and strings can be single-quoted. All special symbols are described below.

|character(s)|use|
|---|:---|
|`( )`|literal cons list|
|`[ ]`|literal array|
|`{ }`|literal hash|
|`~`|`~x` is shorthand for (quote x)|
|``` ` ```|``` `x ``` is shorthand for (quasiquote x)|
|`,`|`,x` is shorthand for (unquote x)|
|`;`|`;x` is shorthand for (unquotesplicing x)|
|`.`|`(1 2 . 3)` is an improper list whose last cons has a cdr of 3 rather than nil.|
|`'`|`'blah'` is a literal string|
|`"`|`"can't"` is a literal string|
|`#`|begins a rest-of-line comment|

### Special Forms
#### ```(branch <conditional> <consequent> [<alternative>])```
The branch form is used exactly six times in Klip. That's how many it takes to write the vastly more powerful ```if``` macro.

#### ```(fn <parameter list> <body of zero or more expressions>)```
Lambda is spelled ```fn``` in Klip.

Parameter lists can be improper:

```(fn (x . rest) ...)``` -> The name x will refer to the first argument, and rest will refer to a cons list of the remaining arguments.

```(fn args ...)``` -> The name args will refer to all of the arguments.

Parameter lists can contain conses:

```(fn (n (acc . 1)) ...)``` -> acc will be given a default value of 1 if the function is called with fewer than two arguments. *At the moment, default parameters are copied literally by the compiler, so only numbers, strings and unquoted symbols will work.*

#### ```(assign <symbol> <expression>)```
My intention is to implement something resembling Arc's = macro. That's why I chose the name ```assign``` instead of something shorter and better.

#### ```(ccc <function of one parameter>)```
Stands for Call with Current Continuation. It calls the function, passing it the current continuation. This is a first-order continuation that can be called more than once and from outside the `ccc` form.

#### ```(mac <name> <argument list> <body of zero or more expressions>)```
Creates a macro. Klip uses good, old-fashioned unhygienic macros. This form defines a function with the given arugment list and body. From now on, when the compiler finds an expression whose head is equal to `name`, it will call this function on the rest of the expression, and compile the return value of that function instead of the original expression.

#### ```(apply <function> <argument list>)```
Applies the given function to the given arguments. The argument list can be a cons list or an array.

#### ```(include <file name>)```
Behaves as if all the expressions in the specified file were inserted in this file here. Only valid at the toplevel.

#### ```(halt)```
Stops the virtual machine.

#### `(quote x)`, `(quasiquote x)`, `(unquote x)`, `(unquotesplicing x)`
These all work the way you'd expect.

### Containers
Now it gets a little weird. I wanted to create a Lisp where arrays and hash tables were fundamental objects that could be parts of programs. I wanted to get away from the weird obsession that Lisp programmers have traditionally had with using linked lists as arrays. They're not arrays, and using them as such is a disaster. I also wanted to do this without cluttering up the built-in namespace with garbage like "array-ref", "array-set" etc. So I opted for making arrays and hash tables callable. (This is reminiscent of, but different from what Arc does.)

(It is worth noting that one could create a Lisp without conses at all. The control macros would look really weird, but it would be quite doable.)

There are two container types, `array` and `hash`. Unlike all other types (`cons`, `str`, `int`, `float`, `sym` and `func`), they are mutable. They are considered atoms by functions like `list?`. They can be part of a Klip program like any other type (except `func`). A litteral array is written like this:

`[a b c ...]`

and a literal hash table like this

`{a b c d ...}`

When a literal container is evaluated, its contents are evaluated, so `[(+ 3 4) 5 6]` evaluates to `[7 5 6]`. The expressions in a hash are key/value pairs. In the example above, `a` is associated with `b`, `c` with `d`, etc. There must be an even number of expressions. `unquotesplicing` works with arrays, but not with hashes.

There is a gotcha with containers. Conses have to be immutable (and hashable, in the Python sense) so that they can be keys in hashes. Conses also have to be able to contain arrays and hashes, so that arrays and hashes can be part of programs. So, despite being immutable, conses can contain mutable objects. In a certain sense, the value of a cons can change (if the array it contains is changed) but it's still considered immutable. The equality test for conses uses the identity, rather than the value, of any mutable objects it contains. Thus,
```
(assign x (list [2 3]))
(assign y (list [2 3]))
(prn
	(== (car x) (car y))
	(== (cdr x) (cdr y))
	(== x y))
```
prints `t t nil` NOT `t t t`. Both arrays have the same value `[2 3]`, and they are thus equal. But they are different arrays, so the conses containing them are not equal. Two conses are not equal unless they have the same value and are guaranteed to always have the same value. For less surprising comparison, use `iso`.

The contents of a container are accessed by indices. The indices of an array are consecutive integers starting with zero. The indices of a hash can be any immutable object except `nil`. Containers can contain any object except `nil`. *At the moment, the prohibitions against `nil` are very poorly error-checked, but they will cause your program to explode. Just, like, don't do it man.*

Containers are functions on their contents. If a container is called with zero arguments

`(a)` -> len(a)

the number of items is returned. The number of items in a hash is the number of key/value pairs. If the container is called with one argument,

`(a 1)` -> a[1]

the item associated with that index is returned. If the function is called with two arguments,

`(a 3 'fish')` -> a[3] = 'fish'

the contents of the container are updated. If the second argument is `nil`,

`(a 2 nil)` -> a.pop(2)

the item at the given index is removed and returned. If the container is an array, items after the given index move down to fill the vacated space.

If the container is an array, there are two more possibilities. If the second argument is `nil` and there is a third argument,

`(a 4 nil 'chips')` -> a.insert(4, 'chips')

the third argument is inserted into the array at the given index, and items there and after move up to make room. Finaly, with an array, the first argument can be `nil`:

`(a nil 5)` -> a.append(5)

In this case, the second argument is appended to the end of the array.

Array indices can be more interesting. Klip supports negative indices, as in Python:

`(a -1)` -> a[-1] (the last element in `a`)

`(a -2 3)` -> a[-2] = 3

Slices can also be specified by using a literal array:

`(a [2 4])` -> a[2:4]

`(a [2 3] ['x' 'y'])` -> a[2:4] = ['x', 'y']

Missing ends of the slice are represented with t:

`(a [2 t])` -> a[2:]

As in Python, slice specifiers can have length of one, two or three. The three signatures are [start], [start stop] and [start stop step].

Strings can also be considered functions, similar to containers. The items contained in a string are characters, which are themselves strings of length 1, as in Python. Strings are immutable, so they don't support item assignment. They are indexed by integers starting with zero.

`(s)` -> len(s)

`(s 3)` -> s[3]

`(s [t -1])` -> s[:-1]

String formatting is accomplished by calling a string and passing `nil` for the first parameter.

`(s nil a b c)` -> s % (a, b, c)

Klip uses (through Python) the C format specifiers, because no superior method for string formatting has yet been devised by man.
