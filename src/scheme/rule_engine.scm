;; SDACS Phase 619 — Scheme rule engine for airspace logic
(define (safe-altitude? alt) (and (>= alt 30) (<= alt 200)))
(define (conflict? pos-a pos-b threshold)
  (let ((dist (sqrt (+ (expt (- (car pos-a) (car pos-b)) 2)
                       (expt (- (cadr pos-a) (cadr pos-b)) 2)
                       (expt (- (caddr pos-a) (caddr pos-b)) 2)))))
    (< dist threshold)))
(define (apply-rules drone rules) (filter (lambda (r) (r drone)) rules))
