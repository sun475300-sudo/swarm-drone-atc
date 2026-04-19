;; Phase 574: Event Stream Processor — Clojure
;; 드론 이벤트 스트림 처리: CQRS 패턴, 이벤트 소싱, 상태 복원.

(ns sdacs.event-stream
  (:require [clojure.string :as str]))

;; ─── 이벤트 정의 ───
(defrecord DroneEvent [event-id drone-id event-type timestamp payload])

(defrecord SystemState [drones conflicts alerts event-count])

;; ─── 이벤트 저장소 ───
(def event-store (atom []))

(defn append-event!
  "이벤트 저장소에 이벤트 추가."
  [event]
  (swap! event-store conj event))

(defn get-events
  "드론별 이벤트 조회."
  [drone-id]
  (filter #(= (:drone-id %) drone-id) @event-store))

;; ─── 이벤트 생성 ───
(defn create-event
  [drone-id event-type payload]
  (->DroneEvent
    (str (java.util.UUID/randomUUID))
    drone-id
    event-type
    (System/currentTimeMillis)
    payload))

(defn position-update [drone-id x y z]
  (create-event drone-id :position-update {:x x :y y :z z}))

(defn conflict-detected [drone-id other-id distance]
  (create-event drone-id :conflict-detected
    {:other-drone other-id :distance distance}))

(defn advisory-issued [drone-id advisory-type action]
  (create-event drone-id :advisory-issued
    {:type advisory-type :action action}))

(defn mission-status [drone-id status]
  (create-event drone-id :mission-status {:status status}))

;; ─── 이벤트 핸들러 (Reducer) ───
(defmulti handle-event
  "이벤트 유형별 상태 업데이트."
  (fn [state event] (:event-type event)))

(defmethod handle-event :position-update
  [state event]
  (let [drone-id (:drone-id event)
        pos (:payload event)]
    (-> state
        (assoc-in [:drones drone-id :position] pos)
        (update :event-count inc))))

(defmethod handle-event :conflict-detected
  [state event]
  (let [conflict {:drone (:drone-id event)
                  :other (get-in event [:payload :other-drone])
                  :distance (get-in event [:payload :distance])
                  :time (:timestamp event)}]
    (-> state
        (update :conflicts conj conflict)
        (update :event-count inc))))

(defmethod handle-event :advisory-issued
  [state event]
  (let [alert {:drone (:drone-id event)
               :advisory (:payload event)
               :time (:timestamp event)}]
    (-> state
        (update :alerts conj alert)
        (update :event-count inc))))

(defmethod handle-event :mission-status
  [state event]
  (let [drone-id (:drone-id event)
        status (get-in event [:payload :status])]
    (-> state
        (assoc-in [:drones drone-id :status] status)
        (update :event-count inc))))

(defmethod handle-event :default
  [state _]
  (update state :event-count inc))

;; ─── 상태 복원 (이벤트 소싱) ───
(defn empty-state []
  (->SystemState {} [] [] 0))

(defn rebuild-state
  "이벤트 스트림에서 현재 상태 재구축."
  [events]
  (reduce handle-event (empty-state) events))

(defn current-state []
  (rebuild-state @event-store))

;; ─── 스트림 처리 파이프라인 ───
(defn filter-by-type
  "이벤트 유형별 필터링."
  [events event-type]
  (filter #(= (:event-type %) event-type) events))

(defn aggregate-by-drone
  "드론별 이벤트 집계."
  [events]
  (group-by :drone-id events))

(defn conflict-summary
  "충돌 이벤트 요약 통계."
  [events]
  (let [conflicts (filter-by-type events :conflict-detected)
        by-drone (aggregate-by-drone conflicts)]
    {:total-conflicts (count conflicts)
     :drones-involved (count by-drone)
     :avg-distance (if (seq conflicts)
                     (/ (reduce + (map #(get-in % [:payload :distance]) conflicts))
                        (count conflicts))
                     0)}))

;; ─── 윈도우 처리 ───
(defn time-window
  "시간 윈도우 내 이벤트 필터."
  [events window-ms]
  (let [now (System/currentTimeMillis)
        cutoff (- now window-ms)]
    (filter #(>= (:timestamp %) cutoff) events)))

(defn sliding-window-count
  "슬라이딩 윈도우 이벤트 카운트."
  [events window-ms step-ms]
  (let [sorted-events (sort-by :timestamp events)
        start (if (seq sorted-events) (:timestamp (first sorted-events)) 0)
        end (if (seq sorted-events) (:timestamp (last sorted-events)) 0)]
    (for [t (range start end step-ms)]
      {:window-start t
       :count (count (filter #(and (>= (:timestamp %) t)
                                   (< (:timestamp %) (+ t window-ms)))
                             sorted-events))})))

;; ─── 시뮬레이션 실행 ───
(defn simulate-event-stream
  "테스트 이벤트 스트림 생성 및 처리."
  [n-drones n-events]
  (reset! event-store [])
  (let [drone-ids (map #(str "DRONE_" (format "%03d" %)) (range n-drones))]
    ;; 이벤트 생성
    (doseq [_ (range n-events)]
      (let [drone-id (rand-nth drone-ids)
            event-type (rand-nth [:position-update :conflict-detected
                                  :advisory-issued :mission-status])]
        (case event-type
          :position-update
            (append-event! (position-update drone-id
              (rand-int 1000) (rand-int 1000) (rand-int 400)))
          :conflict-detected
            (append-event! (conflict-detected drone-id
              (rand-nth drone-ids) (+ 10 (rand-int 90))))
          :advisory-issued
            (append-event! (advisory-issued drone-id
              (rand-nth ["climb" "descend" "turn"]) (rand-nth ["execute" "pending"])))
          :mission-status
            (append-event! (mission-status drone-id
              (rand-nth ["active" "completed" "aborted"]))))))
    ;; 상태 재구축 & 요약
    (let [state (current-state)
          summary (conflict-summary @event-store)]
      {:state state
       :conflict-summary summary
       :total-events (count @event-store)})))

;; ─── 메인 ───
(defn -main [& args]
  (println "=== SDACS Event Stream Processor ===")
  (let [result (simulate-event-stream 10 100)]
    (println "Events processed:" (:total-events result))
    (println "Drones tracked:" (count (get-in result [:state :drones])))
    (println "Conflicts:" (get-in result [:conflict-summary :total-conflicts]))
    (println "Alerts:" (count (get-in result [:state :alerts])))))
