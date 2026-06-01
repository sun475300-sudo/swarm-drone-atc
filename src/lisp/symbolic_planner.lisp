;;; Phase 599: Symbolic Planner — 드론 기호 계획 시스템 (Common Lisp)
;;; STRIPS-style symbolic mission planner for swarm drone operations.

(in-package :cl-user)

(defpackage :sdacs.symbolic-planner
  (:use :cl)
  (:export :make-state :make-action :make-problem :plan
           :*phase* :state-facts :action-name))

(in-package :sdacs.symbolic-planner)

(defvar *phase* 599)

;;; ── State representation ─────────────────────────────────────────

(defstruct state
  "A world state is a list of ground facts."
  (facts '() :type list))

(defun state-holds (state fact)
  "Check if FACT holds in STATE."
  (member fact (state-facts state) :test #'equal))

(defun state-add (state facts-to-add)
  "Return new state with FACTS-TO-ADD."
  (make-state :facts (union (state-facts state) facts-to-add :test #'equal)))

(defun state-remove (state facts-to-del)
  "Return new state with FACTS-TO-DEL removed."
  (make-state :facts (set-difference (state-facts state) facts-to-del :test #'equal)))

;;; ── Action representation ─────────────────────────────────────────

(defstruct action
  "A STRIPS action with preconditions and effects."
  name
  (preconditions '() :type list)  ; list of facts required
  (add-effects   '() :type list)  ; facts added after execution
  (del-effects   '() :type list)  ; facts removed after execution
  cost)

(defun action-applicable-p (action state)
  "Return T if ACTION can be applied to STATE."
  (every (lambda (pre) (state-holds state pre))
         (action-preconditions action)))

(defun apply-action (action state)
  "Apply ACTION to STATE, returning new state."
  (state-add (state-remove state (action-del-effects action))
             (action-add-effects action)))

;;; ── Problem definition ────────────────────────────────────────────

(defstruct problem
  "A planning problem: initial state, goal, and action set."
  name
  initial-state
  goal-facts
  (actions '() :type list))

(defun goal-reached-p (problem state)
  "Return T if all goal facts hold in STATE."
  (every (lambda (g) (state-holds state g))
         (problem-goal-facts problem)))

;;; ── BFS Planner ───────────────────────────────────────────────────

(defun plan (problem &key (max-depth 20))
  "BFS planner: return list of actions or NIL if no plan found."
  (let ((queue (list (list (problem-initial-state problem) nil)))
        (visited (make-hash-table :test #'equal)))
    (loop while queue do
      (destructuring-bind (state action-seq) (pop queue)
        (when (goal-reached-p problem state)
          (return (reverse action-seq)))
        (when (< (length action-seq) max-depth)
          (unless (gethash (state-facts state) visited)
            (setf (gethash (state-facts state) visited) t)
            (dolist (action (problem-actions problem))
              (when (action-applicable-p action state)
                (push (list (apply-action action state)
                            (cons action action-seq))
                      queue)))))))))

;;; ── Drone mission actions ─────────────────────────────────────────

(defvar *drone-actions*
  (list
   (make-action
    :name 'takeoff
    :preconditions '((drone-grounded) (battery-ok))
    :add-effects   '((drone-flying))
    :del-effects   '((drone-grounded))
    :cost 1)
   (make-action
    :name 'navigate-to-zone
    :preconditions '((drone-flying) (mission-assigned))
    :add-effects   '((drone-at-zone) (survey-possible))
    :del-effects   '()
    :cost 2)
   (make-action
    :name 'conduct-survey
    :preconditions '((drone-at-zone) (survey-possible))
    :add-effects   '((survey-complete))
    :del-effects   '()
    :cost 3)
   (make-action
    :name 'return-home
    :preconditions '((drone-flying) (survey-complete))
    :add-effects   '((drone-at-home))
    :del-effects   '((drone-at-zone))
    :cost 2)
   (make-action
    :name 'land
    :preconditions '((drone-at-home))
    :add-effects   '((drone-grounded) (mission-done))
    :del-effects   '((drone-flying))
    :cost 1)))

;;; ── Demo ──────────────────────────────────────────────────────────

(let* ((init (make-state :facts '((drone-grounded) (battery-ok) (mission-assigned))))
       (goal '((mission-done)))
       (problem (make-problem :name "patrol-mission"
                              :initial-state init
                              :goal-facts goal
                              :actions *drone-actions*)))
  (format t "Phase ~A: Symbolic Planner — 드론 기호 계획 시스템~%" *phase*)
  (let ((plan-result (plan problem)))
    (if plan-result
        (progn
          (format t "Plan found (~A steps):~%" (length plan-result))
          (dolist (a plan-result)
            (format t "  ~A~%" (action-name a))))
        (format t "No plan found.~%"))))
