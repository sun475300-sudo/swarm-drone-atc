;;; Phase 619 — Scheme Rule Engine for SDACS airspace constraints
;;; Forward-chaining rule engine for airspace conflict resolution

(define-record-type <rule>
  (make-rule name condition action priority)
  rule?
  (name      rule-name)
  (condition rule-condition)
  (action    rule-action)
  (priority  rule-priority))

(define-record-type <drone-fact>
  (make-drone-fact id x y z battery phase)
  drone-fact?
  (id      fact-id)
  (x       fact-x)
  (y       fact-y)
  (z       fact-z)
  (battery fact-battery)
  (phase   fact-phase))

;;; Create default airspace rules
(define (make-default-rules)
  (list
    (make-rule
      'low-battery
      (lambda (drone) (< (fact-battery drone) 20.0))
      (lambda (drone) (list 'rtl (fact-id drone)))
      10)
    (make-rule
      'altitude-violation
      (lambda (drone) (> (fact-z drone) 400.0))
      (lambda (drone) (list 'descend (fact-id drone)))
      9)
    (make-rule
      'geofence-violation
      (lambda (drone)
        (or (> (abs (fact-x drone)) 1000.0)
            (> (abs (fact-y drone)) 1000.0)))
      (lambda (drone) (list 'return-to-base (fact-id drone)))
      8)))

;;; Fire rules against a list of drone facts
(define (fire-rules rules facts)
  (apply append
    (map (lambda (fact)
           (filter-map
             (lambda (rule)
               (and ((rule-condition rule) fact)
                    ((rule-action rule) fact)))
             (sort rules (lambda (a b) (> (rule-priority a) (rule-priority b))))))
         facts)))

;;; Helper: filter-map
(define (filter-map f lst)
  (let loop ((lst lst) (acc '()))
    (if (null? lst)
        (reverse acc)
        (let ((result (f (car lst))))
          (loop (cdr lst) (if result (cons result acc) acc))))))
