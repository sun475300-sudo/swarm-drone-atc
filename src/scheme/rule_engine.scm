;; SDACS Rule Engine — Scheme (Phase 619)
;; 드론 군집 규칙 기반 추론 엔진

(define-record-type <drone>
  (make-drone id x y z battery state)
  drone?
  (id       drone-id)
  (x        drone-x)
  (y        drone-y)
  (z        drone-z)
  (battery  drone-battery)
  (state    drone-state))

;; 거리 계산
(define (drone-distance a b)
  (let ((dx (- (drone-x a) (drone-x b)))
        (dy (- (drone-y a) (drone-y b)))
        (dz (- (drone-z a) (drone-z b))))
    (sqrt (+ (* dx dx) (* dy dy) (* dz dz)))))

;; 규칙 구조 (rule = (name condition action))
(define-record-type <rule>
  (make-rule name priority condition action)
  rule?
  (name       rule-name)
  (priority   rule-priority)
  (condition  rule-condition)
  (action     rule-action))

;; 내장 규칙들
(define rule-low-battery
  (make-rule
    "low-battery" 10
    (lambda (drone context)
      (< (drone-battery drone) 20.0))
    (lambda (drone context)
      (list 'rtl (drone-id drone)))))

(define rule-altitude-violation
  (make-rule
    "altitude-violation" 20
    (lambda (drone context)
      (> (drone-z drone) 400.0))
    (lambda (drone context)
      (list 'descend (drone-id drone) 400.0))))

(define rule-separation-violation
  (make-rule
    "separation-violation" 30
    (lambda (drone context)
      (let ((others (filter (lambda (d)
                              (and (not (equal? (drone-id d) (drone-id drone)))
                                   (< (drone-distance drone d) 30.0)))
                            (cdr (assoc 'fleet context)))))
        (pair? others)))
    (lambda (drone context)
      (list 'evasive (drone-id drone)))))

;; 규칙 엔진 (전방향 체이닝)
(define (evaluate-rules drone rules context)
  (let loop ((rs (sort rules (lambda (a b) (> (rule-priority a) (rule-priority b)))))
             (actions '()))
    (if (null? rs)
        (reverse actions)
        (let ((r (car rs)))
          (if ((rule-condition r) drone context)
              (loop (cdr rs) (cons ((rule-action r) drone context) actions))
              (loop (cdr rs) actions))))))

;; 함대 전체 규칙 실행
(define (run-fleet-rules drones rules)
  (let ((context (list (cons 'fleet drones))))
    (apply append
           (map (lambda (drone)
                  (evaluate-rules drone rules context))
                drones))))

;; 규칙 추가
(define (extend-ruleset base-rules . new-rules)
  (append base-rules new-rules))

;; 기본 규칙셋
(define default-rules
  (list rule-low-battery rule-altitude-violation rule-separation-violation))

;; 드론 상태 업데이트 (불변 — 새 레코드 반환)
(define (update-drone-state drone field value)
  (cond
    ((eq? field 'z)       (make-drone (drone-id drone) (drone-x drone) (drone-y drone)
                                      value (drone-battery drone) (drone-state drone)))
    ((eq? field 'battery) (make-drone (drone-id drone) (drone-x drone) (drone-y drone)
                                      (drone-z drone) value (drone-state drone)))
    ((eq? field 'state)   (make-drone (drone-id drone) (drone-x drone) (drone-y drone)
                                      (drone-z drone) (drone-battery drone) value))
    (else drone)))

;; 보고서
(define (rules-summary actions)
  (let ((counts (map (lambda (action-type)
                       (cons action-type
                             (length (filter (lambda (a) (eq? (car a) action-type)) actions))))
                     '(rtl descend evasive))))
    counts))
