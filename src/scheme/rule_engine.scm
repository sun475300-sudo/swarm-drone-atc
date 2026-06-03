;;; Phase 619: Rule Engine — Scheme
;;; SDACS declarative rule engine for drone flight policy enforcement

(define-record-type <rule>
  (make-rule id condition action priority)
  rule?
  (id        rule-id)
  (condition rule-condition)
  (action    rule-action)
  (priority  rule-priority))

(define-record-type <drone-state>
  (make-drone-state id battery altitude speed mode)
  drone-state?
  (id       drone-state-id)
  (battery  drone-state-battery)
  (altitude drone-state-altitude)
  (speed    drone-state-speed)
  (mode     drone-state-mode))

;; Rule evaluation
(define (evaluate-rule rule state)
  (and (rule? rule)
       ((rule-condition rule) state)))

(define (apply-rule rule state)
  (when (evaluate-rule rule state)
    ((rule-action rule) state)))

;; Sort rules by priority (lower = higher priority)
(define (sort-rules rules)
  (sort rules (lambda (a b) (< (rule-priority a) (rule-priority b)))))

;; Run all matching rules
(define (run-rules rules state)
  (let ((sorted (sort-rules rules)))
    (filter (lambda (r) (evaluate-rule r state)) sorted)))

;; Built-in rules
(define rtl-rule
  (make-rule 'rtl-battery
    (lambda (s) (< (drone-state-battery s) 20))
    (lambda (s) (display (string-append "RTL: " (drone-state-id s) "\n")))
    1))

(define altitude-rule
  (make-rule 'altitude-limit
    (lambda (s) (> (drone-state-altitude s) 120))
    (lambda (s) (display (string-append "DESCEND: " (drone-state-id s) "\n")))
    2))

;; Demo
(let* ((state (make-drone-state "D001" 15.0 65.0 10.0 "flying"))
       (rules (list rtl-rule altitude-rule))
       (matched (run-rules rules state)))
  (display (string-append "Phase 619: Rule Engine — " (number->string (length matched)) " rules matched\n"))
  (for-each (lambda (r) (apply-rule r state)) matched))
