
(mac do body
	`((fn () ;body)))

(mac assign (name value)
	`(set-var ~,name ,value))

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
				(_let temp (uniq)
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
	~list (fn (s break)
		(_let i 0 (fn ((value nil))
			(if (>= i (len s))
				(break value))
			(_let ret (s i)
				(assign i (+ i 1))
				ret))))
})

(def iterator (s break)
	((iterators (type? s)) s break))

(set iterators ~hash (fn (s break)
	(iterator (items s) break)))


(mac rfn (name args (body))				#I don't like the fact that you have to specify a name. But I really don't like anaphora.
	`(_let ,name nil				#This is to keep the binding of name local.
		(assign ,name (fn ,args ;body))
		,name))

(mac forever body
	(_let temp (uniq)
		`((rfn ,temp ()
			;body
			(,temp)))))

(mac wcc (sym (body))
	`(ccc (fn (,sym) ;body)))


#This definition would be cleaner if let was already defined, but we need it to define let.
(mac _with (args (body))
	(
		(fn (syms vals)
			(wcc done
				(_let it (iterator args done)
					(forever
						(append syms (it))
						(append vals (it)))))
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
		
		`(_with (,(xprs 0) ,(xprs 1)) ;(xprs [2 t]))))

(def map1 (f l)
	(_let ret []			#So, this == the ugliest thing in consless Lisp. It's not functional code. But something like (+ [(f (l 0))] (map1 (l [1 t]))) would be slow.
		(wcc return
			(_let it (iterator l return)
				(forever
					(append ret (f (it ret))))))))


#Short for let-unique. First arg == a symbol or a list of symbols.
(mac luq xprs
	(if (list? (xprs 0))
		`(
			(fn ,(xprs 0) ;(xprs [1 t]))
			;(map1 (fn (x) ~(uniq)) (xprs 0)))
		`(
			(fn (,(xprs 0)) ;(xprs [1 t]))
			(uniq))))



(def =forms (place)
	(if
		(== (type? place) ~sym)
		(luq (oldx newx)
			[
				[oldx `(get-safe ~,place)]
				oldx
				`(fn (,newx)
					(set-var ~,place ,newx))])
		
		(== (type? place) ~list)
		(luq (oldx newx)
			[
				[oldx place]
				oldx
				`(fn (,newx)
					,(if (> (len place) 2)
						`(set ,(place [t -1]) ,(place -1) ,newx)
						`(set ,(place 0) ,(place 1) ,newx)))])))
		

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

(def pop (con (index -1))
	(= (con index) nil))




(mac iflet (s v (rest))
	`(let ,s ,v (if ,s ;rest)))

(mac when (cond (body))
	`(if ,cond (do ;body)))

(mac while (cond (body))
	(luq temp
		`(
			(rfn ,temp ()
				(when ,cond
					;body
					(,temp))))))

(mac dowhile (cond (body))
	(luq temp
		`(
			(rfn ,temp ()
				;body
				(if ,cond (,temp))))))

#A dowhile that captures the value of the (last expression of the) body. The 
#given symbol x == bound to that value for the evaluation of the condition. 
#That value == returned when the condition returns false. (This == for 
#rejection method randomization.)
(mac xwhile (x cond (body))
	(luq temp
		`(
			(rfn ,temp ()
				(let ,x (do ;body)
					(if ,cond
						(,temp)
						,x))))))


(mac or args
	(if args
		(luq temp
			`(iflet ,temp ,(args 0)
				,temp
				(or ;(args [1 t]))))))

(mac and args
	(if args
		(if (> (len args) 1)
			`(if ,(args 0) (and ;(args [1 t])))
			(args 0))
		t))

(mac each (x seq (body))
	(luq (it return _seq)
		`(let ,_seq ,seq
			(wcc ,return
				(let ,it (iterator ,_seq ,return)
					(forever
						(let ,x (,it)
							;body)))))))

(mac eachpair (x y seq (body))
	(luq (it return _seq)
		`(let ,_seq ,seq
			(if
				(wcc ,return
					(let ,it (iterator ,_seq ,return)
						(forever
							(let (,x (,it nil) ,y (,it t))
								;body))))
				(prn 'WARNING: eachpair invoked on a sequence with an odd number of elements.')))))


(def even? (n)
	(if (== 0 (band n 1))))

(def odd? (n)
	(if (!= 0 (band n 1))))

#This stores fns in a literal hash, rather than the horror of if elif elif 
#elif ... else. So all cases take the same (short) amount of time to run.
(mac case (var (rest))
	(luq choice
		(let
			(
				xpdict {}
				default (if (odd? (len rest))
					(set rest -1 nil)
					nil))
			(eachpair val result rest
				(set xpdict val `(fn () ,result)))
			`(let ,choice (,xpdict ,var)
				(if ,choice
					(,choice)
					,default)))))

(mac typecase (var (rest))
	`(case (type? ,var) ;rest))

#Now this == a real loop macro. Accepts both (for <symbol> <evaluates to 
#number> ...) and (for <slice specifier> ...) forms. That ==,
#(for i 3 ...) -> 0, 1, 2
#(for i [3] ...) -> 0, 1, 2
#(for i [1 3] ...) -> 1, 2
#(for i [1 10 2] ...) -> 1, 3, 5, 7, 9
(mac for (i r (body))
	(if (list? r)
		(let forfunc
			(fn (i start stop step body)
				(luq (_start _stop _step op)
					`(let
						(
							(,_start ,start ,_stop ,stop ,_step ,step)
							(,op (if (<= ,_start ,_stop) < >=) ,i ,_start))			#Yup, this == why I wanted let to be as general as it ==.
						(while (,op ,i ,_stop)
							;body
							(++ ,i ,_step)))))
			(case (len r)
				1 (forfunc i 0 (r 0) 1 body)
				2 (forfunc i (r 0) (r 1) 1 body)
				3 (forfunc i (r 0) (r 1) (r 2) body)))
		`(for ,i (,r) ;body)))

#PLURALIZE
#A tool for compounding the effects of macros.
#old == an existing macro, function or keyword that takes zero or more 
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
(pluralize 2 each eaches)
(pluralize 3 eachpair eachpairs)


(mac agen (i r (body))
	(luq ret
		`(let ,ret []
			(for ,i ,r
				(append ,ret (do ;body)))
			,ret)))

(pluralize 2 agen agens)

(mac anof (r (body))
	(luq i `(agen ,i ,r ;body)))

(pluralize 1 anof anofs)



(def ajoin args
	(let ret[]
		(each arg args
			(each sub arg
				(append ret sub)))
		ret))




#MAPPING

(def _map (f args groups)
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
								(fn (seq) (iterator seq break))
								group)))
					(forever
						(append ret (_map
							f
							(ajoin (map1 (fn (it) (it)) its) args)
							rest)))))
			ret)
		(apply f args)))

#Industrial strength mapping functions. Each group == a dimension in the final 
#sequence. Each group can be a list, or a list of lists. If it's a list of 
#lists, each one contributes an argument to f. 
#So:
#(map f [1 2 3]) -> ((f 1) (f 2) (f 3))
#(map f ([1 2 3] [4 5 6])) -> ((f 1 4) (f 2 5) (f 3 6))
#(map f [1 2 3] [4 5 6]) -> (
#	((f 1 4) (f 1 5) (f 1 6))
#	((f 2 4) (f 2 5) (f 2 6))
#	((f 3 4) (f 3 5) (f 3 6)))
(def map (f (groups))
	(_map f [] groups))



#COPYING

(def idfn (x) x)

(def rcopy (x)
	(typecase x
		~list (map rcopy x)
		~hash (let ret {}
			(each pair (items x)
				(= (ret (rcopy (pair 0))) (rcopy (pair 1))))
			ret)
		x))
		
(def copy (x)
	(typecase x
		~list (map idfn x)
		~hash (let ret {}
			(each pair (items x)
				(= (ret (pair 0)) (pair 1)))
			ret)
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
	(luq start
		`(let ,start (time)
			;body
			(- (time) ,start))))







