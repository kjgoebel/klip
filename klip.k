
(assign *all-macros* {})

#macex cannot use fn forms (after the first one), because they would be 
#compiled during execution of macex, which would make macex recursive with no 
#stopping condition.
(assign macex (fn (xpr (mac-func nil))
	(branch (!= (type? xpr) ~list)
		(halt xpr))
	(branch (== (len xpr) 0)
		(halt xpr))
	(assign mac-func (*all-macros* (xpr 0)))
	(branch mac-func
		(macex (apply mac-func (xpr [1 t])))
		(halt xpr))))

(set *all-macros* ~mac (fn (name args (body))
	`(set *all-macros* ~,name (fn ,args ;body))))

(mac do body
	`((fn () ;body)))

(mac def (name args (body))
	`(assign ,name (fn ,args ;body)))

#Define a crude version of let, because we don't have the machinery for the general version yet.
#The _ is because this macro isn't intended to be used directly.
(mac _let (s v (body))
	`((fn (,s) ;body) ,v))

(def zero? (x)
	(== x 0))

(mac if args
	(_let n (len args)
		(branch (zero? n)
			nil
			(branch (== n 1)
				(_let temp (uniq ~temp-if)
					`(_let ,temp ,(args 0)
						(branch ,temp ,temp)))
				(branch (== n 2)
					`(branch ,(args 0)
						,(args 1))
					`(branch ,(args 0)
						,(args 1)
						(if ;(args [2 t]))))))))
#And now we never have to write out branch again.



(assign iterators {
	~list (fn (s)
		(_let i 0 (fn (break (value nil))
			(if (>= i (len s))
				(break value))
			(_let ret (s i)
				(assign i (+ i 1))
				ret))))
})

(def iterator (s)
	((iterators (type? s)) s))

(set iterators ~hash (fn (s)
	(iterator (items s))))


(mac rfn (name args (body))				#I don't like the fact that you have to specify a name. But I really don't like anaphora.
	`(_let ,name nil				#This is to keep the binding of name local.
		(assign ,name (fn ,args ;body))
		,name))

(mac forever body
	(_let temp (uniq ~temp-forever)
		`((rfn ,temp ()
			;body
			(,temp)))))

(mac wcc (sym (body))
	`(ccc (fn (,sym) ;body)))


(mac eat (seq it (body))
	(
		(fn (break temp)
			`(wcc ,break
				(_let ,temp (iterator ,seq)
					(_let ,it (fn ((ret nil)) (,temp ,break ret))
						(forever ;body)))))
		(uniq ~break)
		(uniq ~temp-eat)))


(mac _with (args (body))
	(
		(fn (syms vals)
			(eat args it
				(append syms (it))
				(append vals (it)))
			`(
				(fn (;syms)
					;body)
				;vals))
		[]
		[]))

(def list? (x)
	(== (type? x) ~list))

#Finally we can define the fully general let.
(mac let xprs
	(if
		(no (xprs 0))
		`(do ;(xprs [1 t]))
		
		(list? (xprs 0))
		(if (list? (xprs 0 0))
			`(_with ,(xprs 0 0) (let ;(xprs 0 [1 t]) ;(xprs [1 t])))
			`(_with ;xprs))
		
		`(_let ,(xprs 0) ,(xprs 1) ;(xprs [2 t]))))


(def map1 (f l)
	(_let ret []			#So, this is the ugliest thing in consless Lisp. It's not functional code. But something like (+ [(f (l 0))] (map1 (l [1 t]))) would be slow.
		(eat l it
			(append ret (f (it))))
		ret))


#Short for With UniQue. First arg is a symbol or a list of symbols.
(mac wuq xprs
	(if (list? (xprs 0))
		`(
			(fn ,(xprs 0) ;(xprs [1 t]))
			;(map1 (fn (x) `(uniq ~,x)) (xprs 0)))
		`(
			(fn (,(xprs 0)) ;(xprs [1 t]))
			(uniq ~,(xprs 0)))))



(assign place-table {})

(mac def-place (name xpr-name (body))
	(wuq xpr
		`(set place-table ~,name
			(fn (,xpr)
				(let ,xpr-name (,xpr [1 t])
					;body)))))


(def =forms (place)
	(if
		(== (type? place) ~sym)
		(wuq (oldx newx)
			[
				[oldx `(get-safe ,place)]
				oldx
				`(fn (,newx)
					(assign ,place ,newx))])
		
		(== (type? place) ~list)
		(let form-func (place-table (place 0))
			(if form-func
				(form-func place)
				(wuq (oldx newx)
					[
						[oldx place]
						oldx
						`(fn (,newx)
							,(if (> (len place) 2)
								`(set ,(place [t -1]) ,(place -1) ,newx)
								`(set ,(place 0) ,(place 1) ,newx)))])))
		
		(halt ("=forms doesn't know what to do with %s" place))))


(mac bin= (place value)
	(let forms (=forms place)
		`(let (;(forms 0))
			(,(forms 2) ,value)
			,(forms 1))))

(mac = args
	(if (< (len args) 3)
		`(bin= ;args)
		`(bin= ,(args 0) (= ;(args [1 t])))))


(mac ++ (place (delta 1))
	(let forms (=forms place)
		`(let (;(forms 0))
			(,(forms 2) (+ ,(forms 1) ,delta))
			,(forms 1))))

(mac -- (place (delta 1))
	(let forms (=forms place)
		`(let (;(forms 0))
			(,(forms 2) (- ,(forms 1) ,delta))
			,(forms 1))))


(mac iflet (s v (rest))
	`(let ,s ,v (if ,s ;rest)))

(mac when (cond (body))
	`(if ,cond (do ;body)))

(mac while (cond (body))
	(wuq temp
		`(
			(rfn ,temp ()
				(when ,cond
					;body
					(,temp))))))

(mac do-while (cond (body))
	(wuq temp
		`(
			(rfn ,temp ()
				;body
				(if ,cond (,temp))))))

#A dowhile that captures the value of the (last expression of the) body. The 
#given symbol x is bound to that value for the evaluation of the condition. 
#That value is returned when the condition returns false. (This is for 
#rejection method randomization.)
(mac xwhile (x cond (body))
	(wuq temp
		`(
			(rfn ,temp ()
				(let ,x (do ;body)
					(if ,cond
						(,temp)
						,x))))))


(mac or args
	(if args
		(wuq temp
			`(iflet ,temp ,(args 0)
				,temp
				(or ;(args [1 t]))))))

(mac and args
	(if args
		(if (> (len args) 1)
			`(if ,(args 0) (and ;(args [1 t])))
			(args 0))
		t))


#Note that these are considerably slower using the eat macro.
(mac each (x seq (body))
	(wuq it
		`(eat ,seq ,it
			(let ,x (,it)
				;body))))

(mac eachpair (x y seq (body))
	(wuq it
		`(if
			(eat ,seq ,it
				(let (,x (,it) ,y (,it t))
					;body))
			(prn 'WARNING: eachpair invoked on a sequence with an odd number of elements.'))))


(def even? (n)
	(if (== 0 (band n 1))))

(def odd? (n)
	(if (!= 0 (band n 1))))

#This stores fns in a literal hash, rather than the horror of if elif elif 
#elif ... else. So all cases take the same (short) amount of time to run.
(mac case (var (rest))
	(wuq choice
		(let
			(
				xpdict {}
				default (if (odd? (len rest))
					(pop rest)
					nil))
			(eachpair val result rest
				(set xpdict val `(fn () ,result)))
			`(let ,choice (,xpdict ,var)
				(if ,choice
					(,choice)
					,default)))))

(mac typecase (var (rest))
	`(case (type? ,var) ;rest))

#Now this is a real loop macro. Accepts both (for <symbol> <number> ...) and 
#(for <symbol> <slice specifier> ...) forms. That is,
#(for i 3 ...) -> 0, 1, 2
#(for i [3] ...) -> 0, 1, 2
#(for i [1 3] ...) -> 1, 2
#(for i [1 10 2] ...) -> 1, 3, 5, 7, 9
#(for i (+ 1 2) ...) -> 0, 1, 2

(let forfunc
	(fn (i start stop step body)
		(wuq (_start _stop _step op)
			`(let
				(
					(,_start ,start ,_stop ,stop ,_step ,step)
					(,op (if (<= ,_start ,_stop) < >=) ,i ,_start))			#Yup, this is why I wanted let to be as general as it is.
				(while (,op ,i ,_stop)
					;body
					(++ ,i ,_step)))))
	(mac for (i r (body))
		(if (and (list? r) (== (r 0) ~list))
			(case (len r)
				2 (forfunc i 0 (r 1) 1 body)
				3 (forfunc i (r 1) (r 2) 1 body)
				4 (forfunc i (r 1) (r 2) (r 3) body))
			(forfunc i 0 r 1 body))))


(mac forlen (i seq (body))
	`(for ,i (len ,seq) ;body))


#PLURALIZE
#A tool for compounding the effects of macros.
#old is an existing macro, function or keyword that takes zero or more 
#parameters. pluralize n creates a macro called new which takes a parameter 
#array and a body. The new macro peels parameters off the array n at a time 
#and feeds them to the old macro. The invocations of the old macro are nested, 
#so the eaches macro (below) treats each sequence as a dimension.
#(eaches (i [1 2] j [3 4]) (prn i j))
#prints
#1 3
#1 4
#2 3
#2 4

(mac pluralize (n old new)
	(let old-args []
		(for i n
			(append old-args [~args i]))
		`(mac ,new (args (body))
			(if args
				`(,~,old ;[;old-args]
					(,~,new ,(args [,n t]) ;body))
				`(do ;body)))))


(pluralize 2 for fors)
(pluralize 2 forlen forlens)
(pluralize 2 each eaches)
(pluralize 3 eachpair eachpairs)


(mac gen (i r (body))
	(wuq ret
		`(let ,ret []
			(for ,i ,r
				(append ,ret (do ;body)))
			,ret)))

(pluralize 2 gen gens)

(mac nof (r (body))
	(wuq i `(gen ,i ,r ;body)))

(pluralize 1 nof nofs)



(def join args
	(let ret []
		(each arg args
			(each sub arg
				(append ret sub)))
		ret))

(let _flatten
	(rfn self (ret arg)
		(if (list? arg)
			(each sub arg
				(self ret sub))
			(append ret arg)))
	(def flatten args
		(let ret []
			(each arg args
				(_flatten ret arg))
			ret)))



#MAPPING

#Industrial strength mapping function. Each group is a dimension in the final 
#sequence. Each group can be a list, or a list of lists. If it's a list of 
#lists, each one contributes an argument to f. 
#So:
#(map f [1 2 3]) -> [(f 1) (f 2) (f 3)]
#(map f ([1 2 3] [4 5 6])) -> [(f 1 4) (f 2 5) (f 3 6)]
#(map f [1 2 3] [4 5 6]) -> [
#	[(f 1 4) (f 1 5) (f 1 6)]
#	[(f 2 4) (f 2 5) (f 2 6)]
#	[(f 3 4) (f 3 5) (f 3 6)]]

(let _map
	(rfn self (f args groups)
		(if groups
			(let
				(
					ret []
					rest (groups [1 t]))
				(wcc break
					(let
						(
							(group
								(let temp (groups 0)
									(if (list? (temp 0)) temp [temp])))
							(its
								(map1
									(fn (seq) (iterator seq))
									group)))
						(forever
							(append ret (self
								f
								(join (map1 (fn (it) (it break)) its) args)
								rest)))))
				ret)
			(apply f args)))
	(def map (f (groups))
		(_map f [] groups)))



#COPYING

(def idfn (x) x)

(def hmap (f h)
	(let ret {}
		(each pair (items h)
			(let temp (f pair)
				(= (ret (temp 0)) (temp 1))))
		ret))

(def rcopy (x)
	(typecase x
		~list (map1 rcopy x)
		~hash (hmap rcopy x)
		x))
		
(def copy (x)
	(typecase x
		~list (map1 idfn x)
		~hash (hmap idfn x)
		x))



#CONTAINER MEMBERSHIP

(mac among (x (args))
	(let dict {}
		(each arg args
			(set dict arg t))
		`(if (,dict ,x))))

(def in (x seq)
	(wcc return
		(each y seq
			(if (== x y)
				(return t)))
		nil))




#MEMO FUNCTION STUFF

#Yup. Two caches are necessary because hash values can't be nil.
(def memo (f)
	(let (cache {} nilcache {})
		(fn args
			(or (cache args)
				(and (no (nilcache args))
					(let ret (apply f args)
						(if ret
							(set cache args ret)
							(set nilcache args t))
						ret))))))

(mac defmemo (name args (body))
	`(assign ,name (memo (fn ,args ;body))))




#MORE STUFF

(mac time-it body
	(wuq start
		`(let ,start (time)
			;body
			(- (time) ,start))))







