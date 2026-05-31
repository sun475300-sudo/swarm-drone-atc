;;; Rule Engine — SDACS Phase 619
(define (make-rule condition action)
  (list condition action))

(define (rule-condition r) (car r))
(define (rule-action r) (cadr r))

(define (apply-rules rules state)
  (filter (lambda (r) ((rule-condition r) state)) rules))

(define airspace-rules
  (list (make-rule (lambda (s) (> (car s) 100)) 'reroute)))
