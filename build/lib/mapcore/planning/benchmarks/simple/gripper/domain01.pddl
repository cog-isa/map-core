(define (domain gripper-strips)
   (:types place orb arm)
   (:predicates (room ?r - place)
		(ball ?b - orb)
		(gripper ?g - arm)
		(at-robby ?r - place)
		(at ?b - orb ?r - place)
		(free ?g - arm)
		(carry ?o - orb ?g - arm))

   (:action move
       :parameters  (?from - place ?to - place)
       :precondition (and  (room ?from) (room ?to) (at-robby ?from))
       :effect (and  (at-robby ?to) (room ?from) (room ?to)
		     (not (at-robby ?from))))



   (:action pick
       :parameters (?obj - orb ?room - place ?gripper - arm)
       :precondition  (and  (ball ?obj) (room ?room) (gripper ?gripper)
			    (at ?obj ?room) (at-robby ?room) (free ?gripper))
       :effect (and (ball ?obj) (room ?room) (gripper ?gripper)
            (carry ?obj ?gripper) (at-robby ?room)
		    (not (at ?obj ?room))
		    (not (free ?gripper))))


   (:action drop
       :parameters  (?obj - orb ?room - place ?gripper - arm)
       :precondition  (and  (ball ?obj) (room ?room) (gripper ?gripper)
			    (carry ?obj ?gripper) (at-robby ?room))
       :effect (and (ball ?obj) (room ?room) (gripper ?gripper)
            (at ?obj ?room) (at-robby ?room)
		    (free ?gripper)
		    (not (carry ?obj ?gripper)))))

