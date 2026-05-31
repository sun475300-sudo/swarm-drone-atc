;;; rule_engine.scm
;;; Scheme stub for the SDACS airspace rule engine.
;;; Evaluates conflict-resolution and priority rules over drone state facts.

;; ---------------------------------------------------------------------------
;; Fact representation: drone states as association lists
;; ---------------------------------------------------------------------------

(define (make-drone id x y z vel state)
  (list (cons 'id    id)
        (cons 'x     x)
        (cons 'y     y)
        (cons 'z     z)
        (cons 'vel   vel)
        (cons 'state state)))

(define (drone-get drone key)
  (cdr (assq key drone)))

;; ---------------------------------------------------------------------------
;; Geometry helpers
;; ---------------------------------------------------------------------------

(define (square x) (* x x))

(define (horizontal-distance a b)
  (sqrt (+ (square (- (drone-get a 'x) (drone-get b 'x)))
           (square (- (drone-get a 'y) (drone-get b 'y))))))

;; ---------------------------------------------------------------------------
;; Rules
;; ---------------------------------------------------------------------------

(define MIN-SEP-M 5.0)   ; minimum horizontal separation metres
(define EMERG-SEP-M 2.0) ; emergency threshold metres

(define (rule-separation-violated? a b)
  "True when drones A and B are closer than the minimum separation."
  (< (horizontal-distance a b) MIN-SEP-M))

(define (rule-emergency? a b)
  "True when drones are dangerously close (emergency threshold)."
  (< (horizontal-distance a b) EMERG-SEP-M))

(define (priority-score drone)
  "Higher score means higher conflict resolution priority."
  (let ((state (drone-get drone 'state)))
    (cond ((string=? state "emergency") 100)
          ((string=? state "returning")  50)
          ((string=? state "flying")     10)
          (else                           0))))

;; ---------------------------------------------------------------------------
;; Conflict resolution (stub)
;; ---------------------------------------------------------------------------

(define (resolve-conflict a b)
  "Return the drone that must yield, based on priority."
  (if (>= (priority-score a) (priority-score b)) b a))

;; ---------------------------------------------------------------------------
;; Evaluation loop
;; ---------------------------------------------------------------------------

(define (evaluate-rules drones)
  "Check all pairs of drones for rule violations.
   Returns a list of (type . (drone-a-id . drone-b-id)) pairs."
  (let loop ((pairs '())
             (remaining drones))
    (if (null? (cdr remaining))
        (reverse pairs)
        (let ((a (car remaining)))
          (let inner ((result pairs)
                      (others (cdr remaining)))
            (if (null? others)
                (loop result (cdr remaining))
                (let ((b (car others)))
                  (inner
                    (cond
                      ((rule-emergency?            a b)
                       (cons (cons 'emergency (cons (drone-get a 'id) (drone-get b 'id))) result))
                      ((rule-separation-violated?  a b)
                       (cons (cons 'conflict  (cons (drone-get a 'id) (drone-get b 'id))) result))
                      (else result))
                    (cdr others)))))))))

;; ---------------------------------------------------------------------------
;; Demo
;; ---------------------------------------------------------------------------

(define test-drones
  (list (make-drone "D1"  0.0  0.0 50.0 5.0 "flying")
        (make-drone "D2"  3.0  0.0 50.0 5.0 "flying")   ; within MIN-SEP-M
        (make-drone "D3" 20.0 20.0 50.0 5.0 "returning")))

(display "Rule engine violations: ")
(display (evaluate-rules test-drones))
(newline)
