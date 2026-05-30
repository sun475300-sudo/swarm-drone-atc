;; Phase 574: event_stream — Clojure 기반 이벤트 스트림 처리
;; SDACS Event Stream Processing for Drone Telemetry

(ns sdacs.event-stream
  (:require [clojure.string :as str]))

;; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
;; 이벤트 스키마 정의
;; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(defn make-event
  "드론 이벤트 생성 (불변 맵)"
  [event-type drone-id payload]
  {:event-type event-type
   :drone-id   drone-id
   :payload    payload
   :timestamp  (System/currentTimeMillis)
   :id         (str (java.util.UUID/randomUUID))})

(defn telemetry-event [drone-id lat lon alt battery]
  (make-event :telemetry drone-id
    {:lat lat :lon lon :alt alt :battery battery}))

(defn alert-event [drone-id alert-type severity message]
  (make-event :alert drone-id
    {:alert-type alert-type :severity severity :message message}))

(defn command-event [drone-id command params]
  (make-event :command drone-id
    {:command command :params params}))

;; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
;; 이벤트 필터 및 변환
;; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(defn filter-by-type
  "특정 타입의 이벤트만 필터링"
  [event-type events]
  (filter #(= (:event-type %) event-type) events))

(defn filter-by-drone
  "특정 드론의 이벤트만 필터링"
  [drone-id events]
  (filter #(= (:drone-id %) drone-id) events))

(defn enrich-event
  "이벤트에 메타데이터 추가"
  [event zone]
  (assoc event :zone zone :processed true))

(defn normalize-telemetry
  "텔레메트리 좌표를 표준 형식으로 변환"
  [event]
  (if (= (:event-type event) :telemetry)
    (update-in event [:payload :alt] #(max 0.0 %))
    event))

;; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
;; 이벤트 스트림 프로세서
;; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(defprotocol EventProcessor
  (process [this event])
  (flush-events [this]))

(defrecord BatchProcessor [batch-size state]
  EventProcessor
  (process [this event]
    (let [new-state (update @state :buffer conj event)]
      (reset! state new-state)
      (when (>= (count (:buffer new-state)) (:batch-size this))
        (flush-events this))))
  (flush-events [this]
    (let [batch (:buffer @state)]
      (swap! state assoc :buffer [] :processed-count
             (+ (:processed-count @state) (count batch)))
      batch)))

(defn make-batch-processor [batch-size]
  (->BatchProcessor batch-size
    (atom {:buffer [] :processed-count 0})))

;; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
;; 이벤트 집계 (Aggregation)
;; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(defn aggregate-telemetry
  "드론별 텔레메트리 평균 집계"
  [events]
  (->> events
       (filter #(= (:event-type %) :telemetry))
       (group-by :drone-id)
       (map (fn [[drone-id drone-events]]
              (let [payloads (map :payload drone-events)
                    n        (count payloads)]
                {:drone-id drone-id
                 :count    n
                 :avg-alt  (/ (reduce + (map :alt payloads)) n)
                 :avg-bat  (/ (reduce + (map :battery payloads)) n)
                 :min-bat  (apply min (map :battery payloads))})))
       (into [])))

(defn detect-low-battery-events
  "배터리 부족 이벤트 감지 (threshold 이하)"
  [events threshold]
  (->> events
       (filter #(= (:event-type %) :telemetry))
       (filter #(< (get-in % [:payload :battery]) threshold))
       (map #(alert-event (:drone-id %) :low-battery :warning
               (str "배터리 부족: " (get-in % [:payload :battery]) "%")))))

;; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
;; 메인 실행
;; ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

(defn -main []
  (println "SDACS Event Stream — Phase 574\n")

  ;; 테스트 이벤트 스트림 생성
  (def events
    [(telemetry-event 0 37.500 127.000 50.0 95.0)
     (telemetry-event 1 37.501 127.001 52.0 15.0)
     (telemetry-event 2 37.502 127.002 130.0 88.0)
     (telemetry-event 0 37.503 127.003 51.0 94.0)
     (alert-event 1 :gps-loss :critical "GPS 신호 손실")
     (command-event 1 :rtl {:reason "low-battery"})])

  (println (str "이벤트 수: " (count events)))

  ;; 텔레메트리 집계
  (let [agg (aggregate-telemetry events)]
    (println "\n드론별 텔레메트리 집계:")
    (doseq [a agg]
      (println (str "  드론 " (:drone-id a)
                    ": count=" (:count a)
                    " avg-alt=" (format "%.1f" (double (:avg-alt a))) "m"
                    " avg-bat=" (format "%.1f" (double (:avg-bat a))) "%"))))

  ;; 배터리 경보 감지
  (let [alerts (detect-low-battery-events events 20.0)]
    (println (str "\n배터리 경보: " (count alerts) "건")))

  ;; 배치 처리기
  (let [proc (make-batch-processor 3)]
    (doseq [e events] (process proc e))
    (let [state @(:state proc)]
      (println (str "\n배치 처리: " (:processed-count state) "건 완료"))))

  (println "\n이벤트 스트림 처리 완료."))

(-main)
