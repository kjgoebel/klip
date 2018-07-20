
(mac do body
	`((fn () ;body)))

(mac def (name args [body])
	`(assign ,name (fn ,args ;body)))

#The _ is because _let isn't intended to be used directly. See let, below.
(mac _let (s v [body])
	`((fn (,s) ;body) ,v))


#ELEMENTARY LIST STUFF
(def no (x) (== x nil))				#Following my usual convention, this should be called nil?. But no is really nice.

(def caar (l) (car (car l)))
(def cadr (l) (car (cdr l)))
(def cdar (l) (cdr (car l)))
(def cddr (l) (cdr (cdr l)))



(mac if args
	(branch args
		(branch (cdr args)
			(branch (cddr args)
				`(branch ,(car args)
					,(cadr args)
					(if ;(cddr args)))
				`(branch ,(car args)
					,(cadr args)))
			(_let temp (uniq)
				`(_let ,temp ,(car args)
					(branch ,temp
						,temp))))
		nil))
#And now we never have to write out branch again.


(def map1 (f l)
	(if l
		(cons (f (car l)) (map1 f (cdr l)))
		nil))

(def pairs (l)
	(if l
		(if (cdr l)
			(cons (cons (car l) (cadr l)) (pairs (cddr l)))
			(cons (cons (car l) nil) nil))
		nil))

#The _ is because _with isn't supposed to be used directly. See let, below.
(mac _with (parms [body])
	(_let temp (pairs parms)
		`(
			(fn ,(map1 car temp)
				;body)
			;(map1 cdr temp))))

(def cons? (x)
	(== (type? x) ~cons))

(def atom? (x)
	(!= (type? x) ~cons))

#let can be used in three forms: (let s v ...) creates a single variable. 
#(let (s1 v1 s2 v2 ...) ...) creates several variables, without the possibility 
#of values later in the list depending on variables earlier in the list. 
#(let ((s1 v1 ...) (s2 v2 ...)) ...) creates several variables, in multiple 
#stages, so that values in later stages can depend on variables in earlier 
#stages. In other words, it's a nested _with without having to write with or 
#let multiple times.
(mac let xprs
	(if 
		(no (car xprs))
		`(do ;(cdr xprs))
		
		(cons? (car xprs))
		(if (cons? (caar xprs))
			`(_with ,(caar xprs) (let ;(cdar xprs) ;(cdr xprs)))
			`(_with ;xprs))
		
		`(_with (,(car xprs) ,(cadr xprs)) ;(cddr xprs))))

#Short for let-unique. First arg is a symbol or a list of symbols.
(mac luq xprs
	(if (cons? (car xprs))
		`(
			(fn ,(car xprs) ;(cdr xprs))
			;(map1 (fn (temp) ~(uniq)) (car xprs)))
		`(
			(fn (,(car xprs)) ;(cdr xprs))
			(uniq))))

(mac iflet (s v [rest])
	`(let ,s ,v (if ,s ;rest)))

(mac when (cond [body])
	`(if ,cond (do ;body)))

(def idfn (x) x)

(mac ++ (x (delta 1))
	`(assign ,x (+ ,x ,delta)))
(mac -- (x (delta 1))
	`(assign ,x (- ,x ,delta)))



#AND and OR

#or returns the first argument that is non-nil, or nil if there is no such 
#argument. and returns nil if any argument is nil. Otherwise, it returns the 
#last argument, or t if there are no arguments. The symmetry of the Lisp-style 
#and and or can be seen thusly:

#ret = init
#for arg in args:
#	ret = arg
#	if test(ret):
#		return ret
#return ret

#For or, test is identity. For and, test is not. The value of init is selected 
#so that it will fail test.

(mac or args
	(if args
		(luq temp
			`(iflet ,temp ,(car args)
				,temp
				(or ;(cdr args))))))

(mac and args
	(if args
		(if (cdr args)
			`(if ,(car args) (and ;(cdr args)))
			(car args))
		t))



#LIST STUFF
(def list? (x)
	(or (== (type? x) ~cons) (no x)))

(mac push! (x c)
	`(assign ,c (cons ,x ,c)))
(mac pop! (c)
	(luq ret
		`(let ,ret (car ,c)
			(assign ,c (cdr ,c))
			,ret)))

(def iso (x y)
	(or
		(== x y)
		(and
			(cons? x)
			(cons? y)
			(iso (car x) (car y))
			(iso (cdr x) (cdr y)))))



#ITERATION ON CONTAINERS

(assign iterators {
	~sym (fn (s break)			#This is so that the empty list can be iterated over.
		(fn ((value nil)) (break value)))
	~cons (fn (s break)
		(fn ((value nil))
			(if s
				(pop! s)
				(break value))))
	~array (fn (s break)
		(let i 0 (fn ((value nil))
			(if (>= i (s))
				(break value))
			(let ret (s i)
				(++ i)
				ret))))
})

(def iterator (s break)
	((iterators (type? s)) s break))

(iterators ~hash (fn (s break)
	(iterator (items s) break)))



#NAUGHTY LIST STUFF
#I think this stuff is unnecessary. Use arrays for anything you would want to 
#do this with. If you really need an array to be backwards, use (a [t t -1]).


# (def reverse (c)
	# (let ret nil
		# (while c (push! (pop! c) ret))
		# ret))

# (def count (c (n . 0))
	# (if c
		# (count (cdr c) (+ n 1))
		# n))


#CONTROL STUFF

(mac rfn (name args [body])
	`(let ,name nil				#This is to keep the binding of name local.
		(assign ,name (fn ,args ;body))))

(mac wcc (sym [body])
	`(ccc (fn (,sym) ;body)))

(mac while (cond [body])
	(luq temp
		`(
			(rfn ,temp ()
				(when ,cond
					;body
					(,temp))))))

(mac dowhile (cond [body])
	(luq temp
		`(
			(rfn ,temp ()
				;body
				(if ,cond (,temp))))))

#A dowhile that captures the value of the (last expression of the) body. The 
#given symbol x is bound to that value for the evaluation of the condition. 
#That value is returned when the condition returns false. (This is for 
#rejection method randomization.)
(mac xwhile (x cond [body])
	(luq temp
		`(
			(rfn ,temp ()
				(let ,x (do ;body)
					(if ,cond
						(,temp)
						,x))))))




(mac each (x seq [body])
	(luq (it return _seq)
		`(let ,_seq ,seq
			(wcc ,return
				(let ,it (iterator ,_seq ,return)
					(while t
						(let ,x (,it)
							;body)))))))

(mac eachpair (x y seq [body])
	(luq (it return _seq)
		`(let ,_seq ,seq
			(if
				(wcc ,return
					(let ,it (iterator ,_seq ,return)
						(while t
							(let (,x (,it nil) ,y (,it t))
								;body))))
				(prn 'WARNING: eachpair invoked on a sequence with an odd number of elements.')))))





(def even? (n)
	(if (== 0 (band n 1))))

(def odd? (n)
	(if (!= 0 (band n 1))))



#This stores fns in a literal hash, rather than the horror of if elif elif 
#elif ... else. So all cases take the same (short) amount of time to run.
(mac case (var [rest])
	(luq choice
		(let (xpdict {} default (if (odd? (rest)) (rest -1 nil) nil))
			(eachpair val result rest
				(xpdict val `(fn () ,result)))
			`(let ,choice (,xpdict ,var)
				(if ,choice
					(,choice)
					,default)))))

(mac typecase (var [rest])
	`(case (type? ,var) ;rest))

#Now this is a real loop macro. Accepts both (for <symbol> <evaluates to 
#number> ...) and (for <slice specifier> ...) forms. That is,
#(for i 3 ...) -> 0, 1, 2
#(for i [3] ...) -> 0, 1, 2
#(for i [1 3] ...) -> 1, 2
#(for i [1 10 2] ...) -> 1, 3, 5, 7, 9
(mac for (i r [body])
	(if (== (type? r) ~array)
		(let forfunc
			(fn (i start stop step body)
				(luq (_start _stop _step op)
					`(let
						(
							(,_start ,start ,_stop ,stop ,_step ,step)
							(,op (if (<= ,_start ,_stop) < >=) ,i ,_start))			#Yup, this is why I wanted let to be as general as it is.
						(while (,op ,i ,_stop)
							;body
							(++ ,i ,_step)))))
			(case (r)
				1 (forfunc i 0 (r 0) 1 body)
				2 (forfunc i (r 0) (r 1) 1 body)
				3 (forfunc i (r 0) (r 1) (r 2) body)))
		`(for ,i [,r] ;body)))

#PLURALIZE
#A tool for compounding the effects of macros.
#old is an existing macro, function or keyword that takes zero or more 
#parameters. pluralize n creates a macro called new which takes a parameter 
#array and a body. The new macro peels parameters off the array n at a time 
#and feeds them to the old macro. The invocations of the old macro are nested, 
#so the eachs macro (below) treats each sequence as a dimension.
#(eaches [i [1 2] j [3 4]] (prn i j))
#print out
#1 3
#1 4
#2 3
#2 4


(mac pluralize (n old new)
	(let old-args []
		(for i n
			(old-args nil (list ~args i)))
		`(mac ,new (args [body])
			(if (!= 0 (args))					#This right here? This is why we need consless lisp with no nil and empty list evals to false!
				`(,~,old ;(list ;old-args)
					(,~,new ,(args [,n t]) ;body))
				`(do ;body)))))


(pluralize 2 for fors)
(pluralize 2 each eaches)
(pluralize 3 eachpair eachpairs)




#GENERATION

(mac agen (i r [body])
	(luq ret
		`(let ,ret []
			(for ,i ,r
				(,ret nil (do ;body)))
			,ret)))

(pluralize 2 agen agens)

(mac anof (r [body])
	(luq i `(agen ,i ,r ;body)))

(pluralize 1 anof anofs)




#THE GREAT = MACRO
#Actually, it's not that great. Yet.

(mac = (place value)
	(if
		(== (type? place) ~sym)
		`(assign ,place ,value)
		
		(== (type? place) ~array)
		`(do
			;(agen i (place)
				`(assign ,(place i) (,value ,i))))
		
		(and (cons? place) (cdr place) (no (cddr place)))
		`(,(car place) ,(cadr place) ,value)
		
		`(do
			(prn ("= doesn't know how to handle %s" nil ~,place))
			(halt))))




#CONCATENATION

(def ajoin args
	(let ret[]
		(each arg args
			(each sub arg
				(ret nil sub)))
		ret))




#MAPPING

(def _map (f finish args groups)
	(if groups
		(let
			(
				ret []
				rest (cdr groups))
			(wcc break
				(let
					group (let temp (car groups)
						(if (cons? temp) temp (list temp)))
					(let its (map1 (fn (seq) (iterator seq break)) group)
						(while t
							(ret nil (_map
								f
								finish
								(ajoin (map1 (fn (it) (it)) its) args)
								rest))))))
			(if finish
				(apply finish ret)
				ret))
		(apply f args)))

#Industrial strength mapping functions. Each group is a dimension in the final 
#sequence. Each group can be a sequence (array or cons list), or a cons list of 
#sequences. If it's a list of sequences, each one contributes an argument to f. 
#So:
#(amap f [1 2 3]) -> [(f 1) (f 2) (f 3)]
#(amap f ([1 2 3] [4 5 6])) -> [(f 1 4) (f 2 5) (f 3 6)]
#(amap f [1 2 3] [4 5 6]) -> [
#	[(f 1 4) (f 1 5) (f 1 6)]
#	[(f 2 4) (f 2 5) (f 2 6)]
#	[(f 3 4) (f 3 5) (f 3 6)]]
(def amap (f (groups))
	(_map f nil [] groups))

(def cmap (f (groups))
	(_map f list [] groups))




#COPYING

(def rcopy (x)
	(typecase x
		~cons (cons (rcopy (car x)) (rcopy (cdr x)))
		~array (amap rcopy x)
		~hash (let ret {}
			(each pair (items x)
				(ret (rcopy (car pair)) (rcopy (cdr pair))))
			ret)
		x))
		
(def copy (x)
	(typecase x
		~cons (cons (car x) (copy (cdr x)))
		~array (let ret []
			(each y x
				(ret nil x))
			ret)
		~hash (let ret {}
			(each pair (items x)
				(ret (car pair) (cdr pair)))
			ret)
		x))




#CONTAINER MEMBERSHIP

(mac among (x [args])
	(let dict {}
		(each arg args
			(dict arg t))
		`(if (,dict ,x))))

(def in (x seq)
	(wcc return
		(each y seq
			(if (== x y)
				(return t)))
		nil))




#MEMO FUNCTION STUFF

#memo is the reason why conses need to be hashable.
#Yup. Two caches are necessary because hash values can't be nil.
(def memo (f)
	(let (cache {} nilcache {})
		(fn args
			(or (cache args)
				(and (no (nilcache args))
					(let ret (apply f args)
						(if ret
							(cache args ret)
							(nilcache args t))
						ret))))))

(mac defmemo (name args [body])
	`(assign ,name (memo (fn ,args ;body))))






#MORE STUFF

(mac time-it body
	(luq start
		`(let ,start (time)
			;body
			(- (time) ,start))))






