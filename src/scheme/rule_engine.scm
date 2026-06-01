;; Rule Engine — Scheme module for Phase 619
;; Functional rule-based inference engine for drone swarm behavior control.

;; ===== Rule Representation =====

;; A rule is a list: (rule-id condition-thunk action-thunk priority description)
;; Using association lists for the rule database

(define (make-rule id condition action priority description)
  (list id condition action priority description))

(define (rule-id r) (car r))
(define (rule-condition r) (cadr r))
(define (rule-action r) (caddr r))
(define (rule-priority r) (cadddr r))
(define (rule-description r) (car (cddddr r)))

;; ===== Fact Base =====

;; The fact base is a simple association list: ((key . value) ...)
(define (make-fact-base) '())

(define (assert-fact fb key value)
  (cons (cons key value) (remove-fact fb key)))

(define (retract-fact fb key)
  (remove-fact fb key))

(define (remove-fact fb key)
  (filter (lambda (pair) (not (equal? (car pair) key))) fb))

(define (get-fact fb key . default)
  (let ((found (assoc key fb)))
    (if found
        (cdr found)
        (if (null? default) #f (car default)))))

(define (fact-true? fb key)
  (let ((val (get-fact fb key)))
    (and val (not (equal? val #f)) (not (equal? val 0)))))

;; ===== Rule Engine Core =====

(define (make-engine)
  (list '() (make-fact-base) '()))  ; (rules, facts, fired-log)

(define (engine-rules eng) (car eng))
(define (engine-facts eng) (cadr eng))
(define (engine-log eng) (caddr eng))

(define (add-rule eng rule)
  (list (append (engine-rules eng) (list rule))
        (engine-facts eng)
        (engine-log eng)))

(define (update-facts eng new-facts)
  (list (engine-rules eng) new-facts (engine-log eng)))

(define (log-fired eng rule-id)
  (list (engine-rules eng)
        (engine-facts eng)
        (append (engine-log eng) (list rule-id))))

;; Sort rules by priority (descending)
(define (sort-by-priority rules)
  (sort rules (lambda (a b) (> (rule-priority a) (rule-priority b)))))

;; Run one inference cycle: evaluate all rules against current facts
(define (inference-cycle eng)
  (let* ((rules (sort-by-priority (engine-rules eng)))
         (facts (engine-facts eng))
         (result
           (fold-left
             (lambda (acc-eng rule)
               (let ((cond-fn (rule-condition rule)))
                 (if (cond-fn (engine-facts acc-eng))
                     (let* ((action-fn (rule-action rule))
                            (new-facts (action-fn (engine-facts acc-eng))))
                       (log-fired (update-facts acc-eng new-facts) (rule-id rule)))
                     acc-eng)))
             eng
             rules)))
    result))

;; Run N inference cycles
(define (run-engine eng n-cycles)
  (let loop ((e eng) (i 0))
    (if (>= i n-cycles)
        e
        (loop (inference-cycle e) (+ i 1)))))

;; ===== Drone Safety Rules =====

;; Rule: Low battery → request return to launch
(define rule-low-battery
  (make-rule
    'LOW-BATTERY-RTL
    (lambda (facts)
      (let ((bat (get-fact facts 'battery 100)))
        (< bat 20)))
    (lambda (facts)
      (display "  [RULE] Low battery: RTL commanded\n")
      (assert-fact facts 'command 'RTL))
    10
    "Return to launch when battery < 20%"))

;; Rule: Geofence violation → hold position
(define rule-geofence
  (make-rule
    'GEOFENCE-HOLD
    (lambda (facts)
      (let ((alt (get-fact facts 'altitude 0)))
        (> alt 120)))
    (lambda (facts)
      (display "  [RULE] Altitude exceeded: HOLD commanded\n")
      (assert-fact (assert-fact facts 'command 'HOLD) 'violation 'geofence))
    9
    "Hold when altitude > 120m"))

;; Rule: Collision risk → reduce speed
(define rule-collision-risk
  (make-rule
    'COLLISION-DECELERATE
    (lambda (facts)
      (fact-true? facts 'collision-risk))
    (lambda (facts)
      (display "  [RULE] Collision risk: reducing speed\n")
      (assert-fact facts 'target-speed 2.0))
    8
    "Reduce speed on collision risk"))

;; Rule: Signal loss → switch to autonomous mode
(define rule-signal-loss
  (make-rule
    'SIGNAL-LOSS-AUTONOMOUS
    (lambda (facts)
      (let ((rssi (get-fact facts 'rssi -40)))
        (< rssi -90)))
    (lambda (facts)
      (display "  [RULE] Signal lost: autonomous mode\n")
      (assert-fact facts 'mode 'autonomous))
    7
    "Autonomous mode on signal loss"))

;; Rule: All safe → normal operation
(define rule-nominal
  (make-rule
    'NOMINAL-OPERATION
    (lambda (facts)
      (and (> (get-fact facts 'battery 100) 30)
           (< (get-fact facts 'altitude 0) 100)
           (not (fact-true? facts 'collision-risk))
           (> (get-fact facts 'rssi -40) -80)))
    (lambda (facts)
      (assert-fact facts 'mode 'nominal))
    1
    "Nominal operation when all conditions safe"))

;; ===== fold-left (R7RS compatible) =====
(define (fold-left f init lst)
  (if (null? lst)
      init
      (fold-left f (f init (car lst)) (cdr lst))))

;; ===== Main =====

(display "Phase 619: Rule Engine — Drone Safety Inference\n")

;; Build engine with all rules
(define engine
  (fold-left add-rule (make-engine)
    (list rule-low-battery rule-geofence rule-collision-risk
          rule-signal-loss rule-nominal)))

;; Test Scenario 1: Low battery drone
(display "\n[Scenario 1: Low battery (15%)]\n")
(define facts-1
  (assert-fact
    (assert-fact
      (assert-fact (make-fact-base) 'battery 15)
      'altitude 60)
    'rssi -70))

(define eng-1 (run-engine (update-facts engine facts-1) 3))
(display "  Command: ")
(display (get-fact (engine-facts eng-1) 'command "NONE"))
(newline)

;; Test Scenario 2: Geofence breach
(display "\n[Scenario 2: High altitude (135m)]\n")
(define facts-2
  (assert-fact
    (assert-fact
      (assert-fact (make-fact-base) 'battery 80)
      'altitude 135)
    'rssi -65))

(define eng-2 (run-engine (update-facts engine facts-2) 3))
(display "  Command: ")
(display (get-fact (engine-facts eng-2) 'command "NONE"))
(newline)

;; Test Scenario 3: Normal operation
(display "\n[Scenario 3: Normal conditions]\n")
(define facts-3
  (assert-fact
    (assert-fact
      (assert-fact (make-fact-base) 'battery 85)
      'altitude 70)
    'rssi -60))

(define eng-3 (run-engine (update-facts engine facts-3) 3))
(display "  Mode: ")
(display (get-fact (engine-facts eng-3) 'mode "UNKNOWN"))
(newline)

(display "\nRules fired (scenario 1): ")
(display (engine-log eng-1))
(newline)
(display "Rule engine complete.\n")
