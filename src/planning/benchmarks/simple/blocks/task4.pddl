(define (problem BLOCKS-4-2)
(:domain BLOCKS)
(:objects B D C A - block)
(:INIT (CLEAR A)
(CLEAR C)
(ONTABLE A)
(ONTABLE D)
 (ON C B)
 (ON B D)
 (HANDEMPTY)
 )
(:goal (AND
(CLEAR A)
(ON A B)
(ON B C)
(ON C D)
(ONTABLE D)
(HANDEMPTY)
))
)