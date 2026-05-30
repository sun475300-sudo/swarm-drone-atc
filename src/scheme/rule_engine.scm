;;; Phase 619: rule_engine — Scheme 기반 규칙 엔진
;;; SDACS Rule Engine for Airspace Safety Rules

(define-module (sdacs rule-engine)
  :export (make-rule make-drone-fact apply-rules check-airspace))

;;; 드론 팩트 레코드 정의
(define (make-drone-fact id lat lon alt battery armed mode)
  (list 'drone-fact id lat lon alt battery armed mode))

(define (drone-fact-id    f) (list-ref f 1))
(define (drone-fact-lat   f) (list-ref f 2))
(define (drone-fact-lon   f) (list-ref f 3))
(define (drone-fact-alt   f) (list-ref f 4))
(define (drone-fact-bat   f) (list-ref f 5))
(define (drone-fact-armed f) (list-ref f 6))
(define (drone-fact-mode  f) (list-ref f 7))

;;; 규칙 레코드 정의
(define (make-rule id priority condition action description)
  (list 'rule id priority condition action description))

(define (rule-id          r) (list-ref r 1))
(define (rule-priority    r) (list-ref r 2))
(define (rule-condition   r) (list-ref r 3))
(define (rule-action      r) (list-ref r 4))
(define (rule-description r) (list-ref r 5))

;;; 규칙 매칭 결과
(define (make-match rule fact)
  (list 'match rule fact))

;;; 안전 규칙 정의

;; 규칙 1: 낮은 배터리 → RTL 명령
(define rule-low-battery
  (make-rule
    'low-battery 10
    (lambda (fact)
      (< (drone-fact-bat fact) 20.0))
    (lambda (fact)
      (display (string-append "ACTION: Drone " (number->string (drone-fact-id fact))
                              " → RTL (battery=" (number->string (drone-fact-bat fact)) "%)\n")))
    "배터리 20% 미만 시 자동 귀환"))

;; 규칙 2: 고도 초과 → 하강 명령
(define rule-altitude-limit
  (make-rule
    'altitude-limit 8
    (lambda (fact)
      (> (drone-fact-alt fact) 120.0))
    (lambda (fact)
      (display (string-append "ACTION: Drone " (number->string (drone-fact-id fact))
                              " → DESCEND (alt=" (number->string (drone-fact-alt fact)) "m)\n")))
    "고도 120m 초과 시 하강"))

;; 규칙 3: 지상 무장 상태 → 비상 해제
(define rule-armed-on-ground
  (make-rule
    'armed-on-ground 9
    (lambda (fact)
      (and (drone-fact-armed fact)
           (< (drone-fact-alt fact) 0.5)))
    (lambda (fact)
      (display (string-append "ACTION: Drone " (number->string (drone-fact-id fact))
                              " → DISARM (armed on ground)\n")))
    "지상 무장 상태 시 비상 해제"))

;; 규칙 4: 유효하지 않은 비행 모드
(define valid-modes '("STABILIZE" "GUIDED" "AUTO" "RTL" "LAND" "HOLD"))

(define rule-invalid-mode
  (make-rule
    'invalid-mode 7
    (lambda (fact)
      (not (member (drone-fact-mode fact) valid-modes)))
    (lambda (fact)
      (display (string-append "ACTION: Drone " (number->string (drone-fact-id fact))
                              " → MODE_SAFE (invalid mode: " (drone-fact-mode fact) ")\n")))
    "유효하지 않은 비행 모드 감지"))

;;; 규칙 우선순위 정렬
(define (sort-rules-by-priority rules)
  (sort rules (lambda (a b)
    (> (rule-priority a) (rule-priority b)))))

;;; 단일 팩트에 대한 규칙 적용
(define (apply-rules rules fact)
  (let ((sorted (sort-rules-by-priority rules)))
    (for-each
      (lambda (rule)
        (when ((rule-condition rule) fact)
          ((rule-action rule) fact)))
      sorted)))

;;; 전체 공역 검사
(define (check-airspace rules drone-facts)
  (display "=== 공역 안전 규칙 검사 (Phase 619) ===\n")
  (for-each
    (lambda (fact)
      (display (string-append "드론 " (number->string (drone-fact-id fact)) " 검사 중...\n"))
      (apply-rules rules fact))
    drone-facts)
  (display "검사 완료.\n"))

;;; 거리 계산 유틸리티
(define (haversine-dist lat1 lon1 lat2 lon2)
  (let* ((r 6371000.0)
         (dlat (* (/ (- lat2 lat1) 180.0) (* 4 (atan 1))))
         (dlon (* (/ (- lon2 lon1) 180.0) (* 4 (atan 1))))
         (a (+ (expt (sin (/ dlat 2)) 2)
               (* (cos (* (/ lat1 180.0) (* 4 (atan 1))))
                  (cos (* (/ lat2 180.0) (* 4 (atan 1))))
                  (expt (sin (/ dlon 2)) 2)))))
    (* r 2 (atan (sqrt a) (sqrt (- 1 a))))))

;;; 메인 실행
(define all-rules (list rule-low-battery rule-altitude-limit rule-armed-on-ground rule-invalid-mode))

(define test-drones
  (list
    (make-drone-fact 0 37.50 127.00 50.0 85.0 #t "GUIDED")
    (make-drone-fact 1 37.51 127.01 52.0 15.0 #t "GUIDED")   ;; 낮은 배터리
    (make-drone-fact 2 37.52 127.02 130.0 90.0 #t "AUTO")    ;; 고도 초과
    (make-drone-fact 3 37.53 127.03 0.2 92.0 #t "STABILIZE") ;; 지상 무장
    (make-drone-fact 4 37.54 127.04 55.0 88.0 #t "UNKNOWN")  ;; 유효하지 않은 모드
  ))

(check-airspace all-rules test-drones)
