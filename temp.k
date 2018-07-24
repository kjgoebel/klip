(include 'klip.k')

(def second (a) (a 1))
(def-place second xprs (luq temp
	(prn xprs (xprs 0))
	[
		[temp `(,(xprs 0) 1)]
		temp
		`(fn (value) (set ,(xprs 0) 1 value))]))

(let test [1 2 3 4]
	(prn test)
	(prn (second test))
	(= (second test) 77)
	(prn test))








