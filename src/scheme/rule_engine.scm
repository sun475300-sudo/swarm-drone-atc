;;; rule_engine.scm - Rule engine for SDACS drone airspace management
;;; Scheme implementation of forward-chaining rule evaluation

(define-record-type <rule>
  (make-rule name conditions actions priority)
  rule?
  (name       rule-name)
  (conditions rule-conditions)
  (actions    rule-actions)
  (priority   rule-priority))

(define-record-type <drone-fact>
  (make-drone-fact type drone-id value)
  drone-fact?
  (type     fact-type)
  (drone-id fact-drone-id)
  (value    fact-value))

(define (create-rule-engine)
  (let ((rules '())
        (facts '())
        (fired-count 0))
    (define (add-rule! rule)
      (set! rules (cons rule rules)))
    (define (assert-fact! fact)
      (set! facts (cons fact facts)))
    (define (retract-fact! type drone-id)
      (set! facts (filter (lambda (f)
                            (not (and (equal? (fact-type f) type)
                                      (equal? (fact-drone-id f) drone-id))))
                          facts)))
    (define (match-conditions conditions)
      (every (lambda (cond) (any (lambda (f) (equal? (fact-type f) (car cond))) facts))
             conditions))
    (define (fire-rules!)
      (for-each (lambda (rule)
                  (when (match-conditions (rule-conditions rule))
                    (for-each (lambda (action) (action facts)) (rule-actions rule))
                    (set! fired-count (+ fired-count 1))))
                (sort rules (lambda (a b) (> (rule-priority a) (rule-priority b))))))
    (define (get-facts) facts)
    (define (get-fired-count) fired-count)
    (list add-rule! assert-fact! retract-fact! fire-rules! get-facts get-fired-count)))

;; Example rules for drone airspace management
(define conflict-rule
  (make-rule 'conflict-resolution
             '((drone-proximity) (altitude-overlap))
             (list (lambda (facts) (display "Resolving conflict\n")))
             10))

(define battery-rule
  (make-rule 'low-battery-return
             '((battery-low))
             (list (lambda (facts) (display "Drone returning to base\n")))
             9))

(display "SDACS Rule Engine initialized\n")
