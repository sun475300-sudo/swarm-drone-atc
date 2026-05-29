; Phase 619: Rule Engine — Scheme Airspace Rule Inference
; LISP 계열 공역 규칙 추론 엔진

;; ── Knowledge Base ──

(define *rules* '())
(define *facts* '())

;; ── Fact Management ──

(define (assert-fact fact)
  (if (not (member fact *facts*))
      (set! *facts* (cons fact *facts*))))

(define (retract-fact fact)
  (set! *facts* (remove (lambda (f) (equal? f fact)) *facts*)))

(define (fact-exists? fact)
  (member fact *facts*))

;; ── Rule Definition ──
;; Rule format: (rule name (conditions ...) (actions ...))

(define (add-rule name conditions actions)
  (set! *rules*
        (cons (list 'rule name conditions actions) *rules*)))

;; ── Airspace Rules ──

(define (init-airspace-rules)
  ;; 최소 분리 규칙
  (add-rule 'min-separation
    '((drone ?d1) (drone ?d2) (distance ?d1 ?d2 ?dist) (< ?dist 50))
    '((alert conflict ?d1 ?d2)))

  ;; 고도 제한 규칙
  (add-rule 'max-altitude
    '((drone ?d) (altitude ?d ?alt) (> ?alt 120))
    '((alert altitude-violation ?d)))

  ;; 배터리 부족 규칙
  (add-rule 'low-battery
    '((drone ?d) (battery ?d ?bat) (< ?bat 15))
    '((advisory return-to-base ?d)))

  ;; 지오펜스 규칙
  (add-rule 'geofence-breach
    '((drone ?d) (position ?d ?x ?y) (outside-fence ?x ?y))
    '((advisory return-to-fence ?d) (alert geofence ?d)))

  ;; 강풍 규칙
  (add-rule 'high-wind
    '((wind-speed ?ws) (> ?ws 15) (drone ?d) (altitude ?d ?alt) (> ?alt 50))
    '((advisory descend ?d) (set-separation-factor 1.6))))

;; ── Pattern Matching ──

(define (match-pattern pattern fact bindings)
  (cond
    ((null? pattern)
     (if (null? fact) bindings #f))
    ((null? fact) #f)
    ((and (symbol? (car pattern))
          (char=? (string-ref (symbol->string (car pattern)) 0) #\?))
     (let ((var (car pattern))
           (val (car fact)))
       (let ((existing (assoc var bindings)))
         (if existing
             (if (equal? (cdr existing) val)
                 (match-pattern (cdr pattern) (cdr fact) bindings)
                 #f)
             (match-pattern (cdr pattern) (cdr fact)
                           (cons (cons var val) bindings))))))
    ((equal? (car pattern) (car fact))
     (match-pattern (cdr pattern) (cdr fact) bindings))
    (else #f)))

;; ── Inference Engine ──

(define (evaluate-condition cond bindings)
  (cond
    ((and (list? cond) (= (length cond) 3)
          (memq (car cond) '(< > = <=  >=)))
     (let ((op (car cond))
           (a (cadr cond))
           (b (caddr cond)))
       (let ((va (if (and (symbol? a) (assoc a bindings)) (cdr (assoc a bindings)) a))
             (vb (if (and (symbol? b) (assoc b bindings)) (cdr (assoc b bindings)) b)))
         (if (and (number? va) (number? vb))
             (case op
               ((< ) (< va vb))
               ((> ) (> va vb))
               ((= ) (= va vb))
               ((<= ) (<= va vb))
               ((>= ) (>= va vb)))
             #f))))
    (else
     (let loop ((facts *facts*))
       (if (null? facts)
           #f
           (let ((result (match-pattern cond (car facts) bindings)))
             (if result result
                 (loop (cdr facts)))))))))

;; ── Engine Summary ──

(define (engine-summary)
  (list
    (cons 'rules (length *rules*))
    (cons 'facts (length *facts*))))

;; Initialize
(init-airspace-rules)
