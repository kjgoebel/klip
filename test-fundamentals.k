

(prn '\tTest 1')
(prn 'Yay! we can call prn!')

(prn '\tTest 2 (3):')
(prn (+ 1 2))

(prn '\tTest 3 (5):')
(prn ((fn (x y) (+ x y)) 2 3))

(prn '\tTest 4 (2, nil, 2, 3):')
(prn (branch 1 2))
(prn (branch nil 2))
(prn (branch 1 2 3))
(prn (branch nil 2 3))

(prn '\tTest 5 (3, 7):')
(
	(fn (f)
		(prn (f 1 2))
		(prn (f 3 4)))
		(fn (x y) (+ x y)))

(prn '\tTest 6 (12):')
(prn
	((fn ()
		(assign x 6)
		(+ x x))))

(prn '\tTest 7 CCC (blorts counting down):')
(
	(fn ()
		(assign n 10)
		(assign cc (ccc (fn (_) _)))
		(prn 'blort' n)
		(assign n (- n 1))
		(branch (> n 0)
			(cc cc))))

(prn '\tTest 8 (5, FISH!, 7):')
(
	(fn (f)
		(prn (f t))
		(prn (f nil)))
	(fn (x)
		(ccc (fn (return)
			(branch x
				(return 5))
			(prn 'FISH!')
			7))))

(prn '\tTest 9 (24, 120):')
(
	(fn ()
		(assign fac1
			(
				(fn ()
					(assign self nil)
					(assign self
						(fn (n (acc 1))
							(branch (< n 2)
								acc
								(self (- n 1) (* acc n))))))))
		(prn (fac1 4))
		(prn (fac1 5))))

(prn '\tTest 10 (24, 120):')
(assign fac2 (fn (n (acc 1))
	(branch (< n 2)
		acc
		(self (- n 1) (* acc n)))))
(prn (fac2 4))
(prn (fac2 5))

(prn '\tTest 11 (4, 9):')
(
	(fn (f)
		(f 0)
		(f 1))
	(fn (n (test11-x 9))
		(branch (== n 0)
			(assign test11-x 4))
		(prn test11-x)
		nil))

(prn '\tTest 12 ARRAYS ((1 2 3), 3, 3, nil, (1 2 3 4), (3 4), 3, (1 2 4)):')
(assign a (list 1 (+ 1 1) 3))
(prn a)
(prn (len a))
(prn (a -1))
(prn (append a 4))
(prn a)
(prn (a (list 2 t)))
(prn (set a 2 nil))
(prn a)

(prn '\tTest 13 HASHES ({one 1 two 2}, 2, 2, nil, 1, {two 2 three 3}:')
(assign h {'one' 1 'two' (+ 1 1)})
(prn h)
(prn (h))
(prn (h 'two'))
(prn (h 'three' 3))
(prn (h 'one' nil))
(prn h)

(prn '\tTEST 14 FUNCTION ARGUMENT LISTS:')
(
	(fn (x y (rest))
		(prn rest))
	1
	2
	3
	4)
(
	(fn (x y (rest) last)
		(prn rest last))
	1
	2
	3
	4
	5)
(
	(fn all
		(prn all))
	'fish'
	'chips')
(
	(fn (x (y 2))
		(prn x y))
	1)
(
	(fn (x (y 2) (rest))
		(prn x y rest))
	1
	3
	5
	7)










