(include 'klip.k')



(eachpairs (x y [1 2 3 4 5] z w ['a' 'b' 'c' 'd'])
	(prn x y z w))



# (defmemo binco (n k)
	# (if
		# (< k 0) 0
		# (> k n) 0
		# (== k 0) 1
		# (== k n) 1
		# (+
			# (binco (- n 1) k)
			# (binco (- n 1) (- k 1)))))

# (prn (binco 16 8))

# (prn (anofs (2 3 3) (rand 5)))

# (prn (amap
	# (fn (x1 y1 x2 y2)
		# (+ (* x1 x2) (* y1 y2)))
	# (list [1 2 3] [2 3 4])
	# (list [9 8 7] [6 5 4])))

# (prn (amap
	# (fn (x y z)
		# (+ x y z))
	# (list [1 2 3] [4 5 6])
	# [7 8 9]))


# (let temp (rcopy [[2 3 4] 6])
	# (prn temp))

# (wcc return
	# (let it (iterator {1 2 3 4} return)
		# (while t
			# (prn (it)))))








