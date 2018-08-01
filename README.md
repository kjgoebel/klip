# Klip
Klip is a lexically scoped Lisp inspired by Arc.

Klip is currently compiled into Python. Why would anyone do this? Well, I thought it would be fun, and all the Lisp dialects I know of annoy me in some way.

It's nowhere near finished. This paragraph, for example, ends before it's really begun.

Some major features of Klip:
* Klip doesn't use cons cells. Lists are implemented as arrays, and they are accessed with indices. (E.g. `(a 1)` is the second element in the list `a`.)
* The language itself is very small. Most of what makes Klip Klip is in the core library, `klip.k`.

### Special Symbols
Klip differs from other Lisps in the usage of some symbols. In particular, the shorthand for quote is "~", the shorthand for unquotesplicing is ";", comments are begun with "\#", and strings can be single-quoted. All special symbols are described below.

|character(s)|use|
|---|:---|
|`( )`|a list|
|`[ ]`|`[1 2 3]` is shorthand for `(list 1 2 3)`|
|`{ }`|literal hash table|
|`~`|`~x` is shorthand for `(quote x)`|
|``` ` ```|``` `x ``` is shorthand for `(quasiquote x)`|
|`,`|`,x` is shorthand for `(unquote x)`|
|`;`|`;x` is shorthand for `(unquotesplicing x)`|
|`'`|`'blah'` is a literal string|
|`"`|`"can't"` is a literal string|
|`#`|begins a rest-of-line comment|

### Special Forms
#### ```(branch <conditional> <consequent> [<alternative>])```
The branch form is used exactly nine times in Klip. That's how many it takes to write the vastly more powerful ```if``` macro (see below).

#### ```(fn <parameter list> <body of zero or more expressions>)```
Lambda is spelled ```fn``` in Klip.

Parameter lists can contain lists:

```(fn (n (acc 1)) ...)``` -> `acc` will be given a default value of 1 if the function is called with fewer than two arguments.

```(fn (x (args)) ...)``` -> `x` will be given the value of the first argument and `args` will be given the values of all the remaining arguments, as a list.

The entire parameter list can be a symbol:

```(fn args ...)``` -> The name `args` will be a list of all the arguments.

#### ```(assign <symbol> <expression>)```
Assigns the value of the given expression to the given symbol. The value of the `assign` form is `nil`.

#### ```(get-safe <symbol>)```
Evaluates to the current value of the given symbol, or `nil` if the symbol is undefined.

#### ```(ccc <function of one parameter>)```
Stands for Call with Current Continuation. It calls the function, passing it the current continuation. This is a first-order continuation that can be called more than once and from outside the `ccc` form. The value of the `ccc` form is either the return value of the given function or the value passed to the continuation when it's called.

#### ```(include <file name>)```
Behaves as if all the expressions in the specified file were inserted in this file here. Only valid at the toplevel.

#### ```(halt <any object>)```
Stops the program and returns the object given to the waiting shell.

#### `(quote x)`, `(quasiquote x)`, `(unquote x)`, `(unquotesplicing x)`
These all work the way you'd expect.

### Other Key Features of Klip
#### Containers
Lists and hash tables are containers. Lists are not made of cons cells in Klip. They are arrays, and their contents are accessed with indices and slices. Hash tables are fundamental objects in Klip, and as such they can be contained in programs.

A literal hash table looks like this:

```{a b c d ...}```

In this example, the key `a` is associated with the value `b`, `c` with `d`, etc. There must be an even number of expressions between the braces.

Brackets are used as a shorthand to create literal lists:

```[a b c ...]``` -> Equivalent to ```(list a b c ...)```

*Empty containers are false in Klip!*

The contents of a container are accessed by calling it:

```(a 4)``` -> Returns the fifth element in the list `a`.

```(h 'fish')``` -> Returns the value in `h` associated with the key `'fish'`.

Container lookups are recursive:

```(a 4 2)``` -> ```((a 4) 2)```

The contents of a container can be changed with `set`:

```(set h 'three' 3)``` -> Associates the key 'three' with the value 3 in the hash table `h`. Any previous value of `(h 'three')` is overwritten.

Hash tables cannot contain `nil`, either as a key or a value. Looking up a key that is not present in a hash table produces the value `nil`:

```({'one' 1 'two' 2} 'three')``` -> `nil`

Basic list indices are consecutive integers starting with zero. List indices can be more interesting. Klip supports negative list indices, as in Python:

```(a -1)``` -> Returns the last element in `a`.

List slices can be specified by using a list as an index:

```(a [2 4])``` -> ```[(a 2) (a 3)]``` a list of the elements of `a`, from 2 (inclusive) to 4 (exclusive).

```(set a [2 3] ['fish' 'chips'])``` -> Sets the third and fourth elements of `a` to `'fish'` and `'chips'`, respetively.

Missing ends of a slice are represented with `t`:

```(a [2 t])``` -> The elements of `a`, from 2 (inclusive) to the end of the array.

As in Python, slice specifiers can have one, two or three elements. The three signatures are `[stop]`, `[start, stop]` and `[start, stop, step]`.

```(a [t t -1])``` -> All the elements of `a` in reverse order.

There are several built-in functions that operate on containers.

```(len a)``` -> Returns the length of `a`. The length of a hash table is the number of key/value pairs.

```(items h)``` -> Returns a list of the items in `h`. For a hash table, the items are lists of length 2, representing key/value pairs. For a list, `items` returns a copy of the list.

```(pop a 3)``` -> Removes and returns `(a 3)`. If `a` is a list, the elements after the fourth move down to fill the newly vacated space. 

The argument to `pop` defaults to -1:

```(pop a)``` -> Removes and returns the last element of `a`, if `a` is a list. If `a` is a hash table, this will attempt to remove and return the value associated with the key -1, which is likely not what you want to do.

The following functions only operate on lists.

```(append a 'fish')``` -> Adds `'fish'` to the end of the list.

```(insert a 4 'chips')``` -> Moves the fifth and later elements up, and inserts `'chips'` into the newly vacated space.

#### The `mac` Macro

Klip uses good, old-fashioned unhygienic macros.

```(mac <name> <argument list> <body>)``` -> Defines a macro.

A function is created with the given arugment list and body. From now on, when the compiler finds an expression whose head is equal to `name`, it will call this function on the rest of the expression, and compile the return value of that function instead of the original expression.

Actually, the system is slightly more general. The compiler doesn't interact with specific macros. For _every_ expression it encounters, it checks for a variable called `macex` in the global environment. If if finds such a variable, it calls it on the expression and compiles the result. The core library binds `macex` to a function that implements the system described above. `mac` is itself a macro registered using this scheme.

#### The `if` Macro
This is similar to the `cond` form in some Lisp dialects and the `if` macro in Arc.

```(if)``` -> `nil`

```(if a)``` -> `a` if `a` is true, otherwise `nil`

```(if a b ...)``` -> `b` if `a` is true, otherwise `(if ...)`

#### The `=` Macro
This is similar to the `=` macro in Arc. It is used to assign values to "places", which are generalized variables.

```(= place val)``` -> Evaluating `place` should now yield the value `val`.

The `=` macro deconstructs `place` to determine what it needs to do to make `place` evaluate to `val`. `place` can be a simple symbol:

```(= x 1)``` -> Assigns `x` the value 1.

But place can be more complicated:

```(= (a 0) 2)``` -> Assigns the value 1 to the first element of the list `a`.

A very important feature of the `=` macro is that, unlike assignment in most programming languages, *the value of the `=` form itself is the original value of `place`, not the new value.* So,

```
(= x 1)
(prn (= x 2))
```

prints 1, not 2. Variables that haven't been created yet have a "previous value" of `nil`.

```(prn (= y 1))``` -> Prints `nil`, assuming that `y` doesn't exist previously.

The `=` form can have more than two argument expressions.

```(= x y z)``` -> Assigns `x` the value of `y`, `y` the value of `z`, and returns the original value of `x`.

This means that swapping and rotating of values can be accomplished with the `=` macro:

```(= x y x)``` -> Swaps the values of `x` and `y`.

#### The `let` Macro
Klip's `let` macro is very general. It can be used to create a single variable:

```(let x 5 (prn x))``` -> Prints 5.

With an additional set of parentheses, it can be used to create several variables at once:

```(let (x 5 y 10) (prn (* x y)))``` -> Prints 50.

And with yet another set of parentheses, it can create variables in multiple stages, so that values assigned in later stages can depend on the variables created in earlier stages:

```
(let
	(
		(x 5)
		(y 6 z (* 2 x)))
	(prn x y z))
```
prints 5 6 10. This is just a nested `let` form without having to write `let` multiple times.

#### String Formatting
This is accomplished by calling the string:

```('We have %05d fish on hand.' 33)``` -> `'We have 00033 fish on hand.'`

Klip uses (through Python) the C string format specifiers, because no superior method for string formatting has yet been devised by man.
