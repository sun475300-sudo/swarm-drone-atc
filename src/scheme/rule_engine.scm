;;; Rule Engine — Scheme for SDACS declarative conflict resolution
;;; Phase 619

(define-module (sdacs rule-engine)
  :export (make-rule apply-rule apply-rules match-pattern
           make-fact-base assert-fact retract-fact query-facts))

;;; ── Fact Base ────────────────────────────────────────────────────

(define (make-fact-base)
  (list))

(define (assert-fact db fact)
  (if (member fact db)
      db
      (cons fact db)))

(define (retract-fact db fact)
  (filter (lambda (f) (not (equal? f fact))) db))

(define (query-facts db pattern)
  (filter (lambda (f) (match-pattern pattern f)) db))

;;; ── Pattern Matching ─────────────────────────────────────────────

(define (match-pattern pattern fact)
  (cond
    ((eq? pattern '?) #t)                        ; wildcard
    ((pair? pattern)
     (and (pair? fact)
          (match-pattern (car pattern) (car fact))
          (match-pattern (cdr pattern) (cdr fact))))
    (else (equal? pattern fact))))

;;; ── Rules ────────────────────────────────────────────────────────

(define (make-rule name condition action)
  (list 'rule name condition action))

(define (rule-name r)      (cadr r))
(define (rule-condition r) (caddr r))
(define (rule-action r)    (cadddr r))

(define (apply-rule rule db)
  (let ((matches (query-facts db (rule-condition rule))))
    (if (null? matches)
        db
        ((rule-action rule) db matches))))

(define (apply-rules rules db)
  (fold-left apply-rule db rules))

;;; ── SDACS Domain Rules ───────────────────────────────────────────

;;; Separation violation rule: if two drones are within 50m, issue advisory
(define separation-rule
  (make-rule
    'separation-violation
    '(conflict ? ? separation_violation)
    (lambda (db conflicts)
      (fold-left
        (lambda (db+ conflict)
          (let ((d1 (cadr conflict))
                (d2 (caddr conflict)))
            (assert-fact db+ (list 'advisory d1 'ascend 50))))
        db conflicts))))

;;; NFZ violation rule
(define nfz-rule
  (make-rule
    'nfz-violation
    '(conflict ? ? nfz_violation)
    (lambda (db violations)
      (fold-left
        (lambda (db+ violation)
          (let ((drone (cadr violation)))
            (assert-fact db+ (list 'advisory drone 'return-to-launch 0))))
        db violations))))

;;; Low battery rule
(define low-battery-rule
  (make-rule
    'low-battery
    '(drone-state ? battery-critical)
    (lambda (db states)
      (fold-left
        (lambda (db+ state)
          (assert-fact db+ (list 'advisory (cadr state) 'land-immediately 0)))
        db states))))

(define sdacs-rules
  (list separation-rule nfz-rule low-battery-rule))

;;; ── Inference Engine ─────────────────────────────────────────────

(define (run-inference db . max-cycles)
  (let ((limit (if (null? max-cycles) 10 (car max-cycles))))
    (let loop ((db db) (cycle 0))
      (if (>= cycle limit)
          db
          (let ((db* (apply-rules sdacs-rules db)))
            (if (equal? db db*)
                db              ; fixed point reached
                (loop db* (+ cycle 1))))))))
