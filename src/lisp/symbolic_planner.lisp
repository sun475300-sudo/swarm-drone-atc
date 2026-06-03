;;; Phase 589: Symbolic Planner — Common Lisp
;;; SDACS AI planning system for drone mission optimization

(defpackage :sdacs.planner
  (:use :cl)
  (:export #:make-state #:make-action #:make-goal
           #:plan #:bfs-plan #:a*-plan
           #:apply-action #:applicable-p
           #:DroneAgent #:make-drone-agent))

(in-package :sdacs.planner)

;;; ============================================================
;;; Domain structures

(defstruct (drone-state (:conc-name state-))
  (drone-id  ""     :type string)
  (position  #(0.0 0.0 0.0) :type vector)
  (battery   100.0  :type float)
  (altitude  0.0    :type float)
  (speed     0.0    :type float)
  (mode      :idle  :type keyword)
  (waypoints '()    :type list)
  (payload   '()    :type list))  ; arbitrary key-value pairs

(defstruct (action (:conc-name action-))
  (name        :noop  :type keyword)
  (preconditions '()  :type list)  ; list of predicate functions
  (effects       '()  :type list)  ; list of state-transform functions
  (cost          1.0  :type float))

(defstruct (goal (:conc-name goal-))
  (conditions '()  :type list)  ; list of predicate functions
  (heuristic  nil))             ; optional heuristic fn for A*

;;; ============================================================
;;; Predicate helpers

(defun at-waypoint-p (state wp-name)
  (equal (car (state-waypoints state)) wp-name))

(defun battery-ok-p (state &optional (threshold 20.0))
  (> (state-battery state) threshold))

(defun is-mode-p (state mode)
  (eq (state-mode state) mode))

(defun above-altitude-p (state min-alt)
  (> (state-altitude state) min-alt))

;;; ============================================================
;;; Action library

(defun make-takeoff-action (target-alt)
  (make-action
   :name :takeoff
   :preconditions (list (lambda (s) (is-mode-p s :idle))
                        (lambda (s) (battery-ok-p s 30.0)))
   :effects (list (lambda (s)
                    (let ((new (copy-structure s)))
                      (setf (state-mode new) :flying
                            (state-altitude new) target-alt)
                      new)))
   :cost 2.0))

(defun make-goto-action (waypoint cost)
  (make-action
   :name :goto
   :preconditions (list (lambda (s) (is-mode-p s :flying))
                        (lambda (s) (battery-ok-p s 15.0)))
   :effects (list (lambda (s)
                    (let ((new (copy-structure s)))
                      (push waypoint (state-waypoints new))
                      (setf (state-battery new)
                            (max 0.0 (- (state-battery new) (* cost 5.0))))
                      new)))
   :cost cost))

(defun make-land-action ()
  (make-action
   :name :land
   :preconditions (list (lambda (s) (is-mode-p s :flying)))
   :effects (list (lambda (s)
                    (let ((new (copy-structure s)))
                      (setf (state-mode new) :idle
                            (state-altitude new) 0.0
                            (state-speed new) 0.0)
                      new)))
   :cost 1.0))

(defun make-rtl-action ()
  (make-action
   :name :rtl
   :preconditions (list)
   :effects (list (lambda (s)
                    (let ((new (copy-structure s)))
                      (setf (state-mode new) :idle
                            (state-altitude new) 0.0
                            (state-waypoints new) '())
                      new)))
   :cost 3.0))

;;; ============================================================
;;; Planner core

(defun applicable-p (action state)
  "Return T if all action preconditions are met in state."
  (every (lambda (pred) (funcall pred state))
         (action-preconditions action)))

(defun apply-action (action state)
  "Apply action effects to state, returning new state."
  (reduce (lambda (s eff) (funcall eff s))
          (action-effects action)
          :initial-value state))

(defun goal-reached-p (goal state)
  "Return T if all goal conditions are satisfied."
  (every (lambda (cond) (funcall cond state))
         (goal-conditions goal)))

(defun bfs-plan (initial-state goal actions &key (max-depth 20))
  "Breadth-first search planner. Returns list of actions or NIL."
  (let ((queue (list (list initial-state '())))
        (visited (make-hash-table :test 'equalp)))
    (loop
      (when (null queue) (return nil))
      (destructuring-bind (state plan) (pop queue)
        (when (goal-reached-p goal state)
          (return (reverse plan)))
        (when (> (length plan) max-depth)
          (next-iteration))
        (unless (gethash state visited)
          (setf (gethash state visited) t)
          (dolist (action actions)
            (when (applicable-p action state)
              (let ((new-state (apply-action action state)))
                (push (list new-state (cons action plan)) queue)))))))))

(defun heuristic-cost (state goal)
  "Simple heuristic: count unsatisfied goal conditions."
  (count-if-not (lambda (cond) (funcall cond state))
                (goal-conditions goal)))

(defun a*-plan (initial-state goal actions &key (max-iter 1000))
  "A* planner with cost + heuristic. Returns plan or NIL."
  (let ((open (list (list 0.0 0.0 initial-state '())))
        (visited (make-hash-table :test 'equalp))
        (iter 0))
    (loop
      (when (or (null open) (> iter max-iter)) (return nil))
      (incr iter)
      ;; Sort by f = g + h
      (setf open (sort open #'< :key #'car))
      (destructuring-bind (f g state plan) (pop open)
        (declare (ignore f))
        (when (goal-reached-p goal state)
          (return (reverse plan)))
        (unless (gethash state visited)
          (setf (gethash state visited) t)
          (dolist (action actions)
            (when (applicable-p action state)
              (let* ((new-state (apply-action action state))
                     (new-g (+ g (action-cost action)))
                     (new-h (heuristic-cost new-state goal))
                     (new-f (+ new-g new-h)))
                (push (list new-f new-g new-state (cons action plan)) open)))))))))

;;; ============================================================
;;; Drone agent using planner

(defstruct (DroneAgent (:conc-name agent-))
  (id      ""  :type string)
  (state   nil)
  (actions '() :type list)
  (plan    '() :type list))

(defun make-drone-agent (id initial-state)
  (let ((agent (make-DroneAgent :id id :state initial-state)))
    (setf (agent-actions agent)
          (list (make-takeoff-action 60.0)
                (make-goto-action :wp1 5.0)
                (make-goto-action :wp2 5.0)
                (make-land-action)
                (make-rtl-action)))
    agent))

(defun plan-mission (agent goal)
  "Plan a mission for the agent using A*."
  (let ((plan (a*-plan (agent-state agent) goal (agent-actions agent))))
    (setf (agent-plan agent) plan)
    plan))

;;; ============================================================
;;; Utility

(defmacro incr (var &optional (delta 1))
  `(setf ,var (+ ,var ,delta)))

(defun copy-structure (s)
  "Shallow copy of a structure (drone-state)."
  (make-drone-state
   :drone-id  (state-drone-id s)
   :position  (copy-seq (state-position s))
   :battery   (state-battery s)
   :altitude  (state-altitude s)
   :speed     (state-speed s)
   :mode      (state-mode s)
   :waypoints (copy-list (state-waypoints s))
   :payload   (copy-list (state-payload s))))
