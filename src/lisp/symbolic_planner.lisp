;;; Phase 599: Symbolic Mission Planner — Common Lisp
;;; 기호적 미션 계획기: STRIPS 계획, 상태 공간 탐색,
;;; 목표 지향 행동 계획.

;;; ─── 상태 표현 ───
(defstruct world-state
  "세계 상태: 참인 명제들의 집합."
  (facts nil :type list))

(defstruct action
  "STRIPS 행동: 전제조건, 추가 효과, 삭제 효과."
  (name nil :type symbol)
  (params nil :type list)
  (preconditions nil :type list)
  (add-effects nil :type list)
  (del-effects nil :type list))

(defstruct plan
  "계획: 행동 시퀀스."
  (actions nil :type list)
  (cost 0 :type number))

;;; ─── 상태 연산 ───
(defun state-contains-p (state fact)
  "상태에 명제가 포함되어 있는지 확인."
  (member fact (world-state-facts state) :test #'equal))

(defun applicable-p (state action)
  "행동이 현재 상태에서 적용 가능한지 확인."
  (every (lambda (pre) (state-contains-p state pre))
         (action-preconditions action)))

(defun apply-action (state action)
  "행동을 적용하여 새 상태 반환."
  (let* ((facts (world-state-facts state))
         (new-facts (union (action-add-effects action)
                          (set-difference facts
                                        (action-del-effects action)
                                        :test #'equal)
                          :test #'equal)))
    (make-world-state :facts new-facts)))

(defun goal-satisfied-p (state goals)
  "모든 목표가 현재 상태에서 만족되는지 확인."
  (every (lambda (g) (state-contains-p state g)) goals))

;;; ─── 드론 미션 도메인 ───
(defun make-drone-domain ()
  "드론 미션 행동 정의."
  (list
    ;; 이륙
    (make-action
      :name 'takeoff
      :params '(?drone ?loc)
      :preconditions '((at ?drone ?loc) (on-ground ?drone) (charged ?drone))
      :add-effects '((flying ?drone) (at-altitude ?drone))
      :del-effects '((on-ground ?drone)))

    ;; 착륙
    (make-action
      :name 'land
      :params '(?drone ?loc)
      :preconditions '((flying ?drone) (at ?drone ?loc))
      :add-effects '((on-ground ?drone))
      :del-effects '((flying ?drone) (at-altitude ?drone)))

    ;; 이동
    (make-action
      :name 'move-to
      :params '(?drone ?from ?to)
      :preconditions '((flying ?drone) (at ?drone ?from) (path-clear ?from ?to))
      :add-effects '((at ?drone ?to))
      :del-effects '((at ?drone ?from)))

    ;; 스캔
    (make-action
      :name 'scan-area
      :params '(?drone ?loc)
      :preconditions '((flying ?drone) (at ?drone ?loc) (has-sensor ?drone))
      :add-effects '((scanned ?loc))
      :del-effects '())

    ;; 통신 중계
    (make-action
      :name 'relay-data
      :params '(?drone ?loc)
      :preconditions '((flying ?drone) (at ?drone ?loc) (scanned ?loc))
      :add-effects '((data-relayed ?loc))
      :del-effects '())

    ;; 충전
    (make-action
      :name 'charge
      :params '(?drone ?loc)
      :preconditions '((at ?drone ?loc) (on-ground ?drone) (charging-station ?loc))
      :add-effects '((charged ?drone))
      :del-effects '((low-battery ?drone)))))

;;; ─── 전방 탐색 계획기 ───
(defun instantiate-action (action bindings)
  "행동 인스턴스 생성 (변수 바인딩 적용)."
  (labels ((subst-vars (expr)
             (cond
               ((null expr) nil)
               ((symbolp expr)
                (let ((binding (assoc expr bindings)))
                  (if binding (cdr binding) expr)))
               ((listp expr)
                (mapcar #'subst-vars expr))
               (t expr))))
    (make-action
      :name (action-name action)
      :params (subst-vars (action-params action))
      :preconditions (subst-vars (action-preconditions action))
      :add-effects (subst-vars (action-add-effects action))
      :del-effects (subst-vars (action-del-effects action)))))

(defun forward-search (initial-state goals actions max-depth)
  "전방 상태 공간 탐색 (BFS)."
  (let ((queue (list (list initial-state nil 0)))
        (visited nil))
    (loop while queue do
      (let* ((entry (pop queue))
             (state (first entry))
             (plan-so-far (second entry))
             (depth (third entry)))

        ;; 목표 달성 확인
        (when (goal-satisfied-p state goals)
          (return-from forward-search
            (make-plan :actions (reverse plan-so-far)
                      :cost depth)))

        ;; 깊이 제한
        (when (>= depth max-depth)
          (go continue-loop))

        ;; 적용 가능한 행동 탐색
        (dolist (action actions)
          (when (applicable-p state action)
            (let* ((new-state (apply-action state action))
                   (state-key (world-state-facts new-state)))
              (unless (member state-key visited :test #'equal)
                (push state-key visited)
                (setf queue
                      (append queue
                              (list (list new-state
                                        (cons (action-name action) plan-so-far)
                                        (1+ depth)))))))))
        continue-loop))
    ;; 계획 실패
    (make-plan :actions '(:no-plan-found) :cost -1)))

;;; ─── 테스트 시나리오 ───
(defun run-demo ()
  "미션 계획 데모 실행."
  (format t "=== SDACS Symbolic Planner ===~%~%")

  ;; 초기 상태
  (let* ((initial (make-world-state
                    :facts '((at drone-1 base)
                            (on-ground drone-1)
                            (charged drone-1)
                            (has-sensor drone-1)
                            (charging-station base)
                            (path-clear base alpha)
                            (path-clear alpha bravo)
                            (path-clear bravo base)
                            (path-clear alpha base))))

         ;; 목표: alpha를 스캔하고 데이터 중계 후 기지 복귀
         (goals '((scanned alpha)
                  (data-relayed alpha)
                  (at drone-1 base)
                  (on-ground drone-1)))

         ;; 그라운드 행동 (변수 바인딩 완료)
         (actions (list
                    (make-action :name 'takeoff-at-base
                      :preconditions '((at drone-1 base) (on-ground drone-1) (charged drone-1))
                      :add-effects '((flying drone-1) (at-altitude drone-1))
                      :del-effects '((on-ground drone-1)))
                    (make-action :name 'move-base-to-alpha
                      :preconditions '((flying drone-1) (at drone-1 base) (path-clear base alpha))
                      :add-effects '((at drone-1 alpha))
                      :del-effects '((at drone-1 base)))
                    (make-action :name 'scan-alpha
                      :preconditions '((flying drone-1) (at drone-1 alpha) (has-sensor drone-1))
                      :add-effects '((scanned alpha))
                      :del-effects '())
                    (make-action :name 'relay-alpha
                      :preconditions '((flying drone-1) (at drone-1 alpha) (scanned alpha))
                      :add-effects '((data-relayed alpha))
                      :del-effects '())
                    (make-action :name 'move-alpha-to-base
                      :preconditions '((flying drone-1) (at drone-1 alpha) (path-clear alpha base))
                      :add-effects '((at drone-1 base))
                      :del-effects '((at drone-1 alpha)))
                    (make-action :name 'land-at-base
                      :preconditions '((flying drone-1) (at drone-1 base))
                      :add-effects '((on-ground drone-1))
                      :del-effects '((flying drone-1) (at-altitude drone-1))))))

    ;; 계획 실행
    (let ((result (forward-search initial goals actions 10)))
      (format t "Plan found (cost=~d):~%" (plan-cost result))
      (dolist (action (plan-actions result))
        (format t "  ~d. ~a~%" (1+ (position action (plan-actions result))) action))
      (format t "~%Total actions: ~d~%" (length (plan-actions result))))))

;;; 실행
(run-demo)
