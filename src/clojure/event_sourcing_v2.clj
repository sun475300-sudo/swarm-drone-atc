(ns sdacs.event-sourcing-v2
  "SDACS 이벤트 소싱 v2 — 드론 군집 이벤트 저장소"
  (:require [clojure.string :as str]))

;;; 이벤트 타입
(def event-types
  #{:drone-registered :drone-departed :drone-landed
    :conflict-detected :conflict-resolved :advisory-issued
    :telemetry-received :battery-low :geofence-breach})

;;; 이벤트 생성

(defn make-event [type drone-id payload]
  {:event-type type
   :drone-id   drone-id
   :timestamp  (System/currentTimeMillis)
   :payload    payload
   :id         (str (java.util.UUID/randomUUID))})

;;; 이벤트 저장소 (in-memory atom)

(def event-store (atom []))

(defn append-event! [event]
  (swap! event-store conj event))

(defn get-events
  ([] @event-store)
  ([type] (filter #(= (:event-type %) type) @event-store))
  ([type drone-id]
   (filter #(and (= (:event-type %) type)
                 (= (:drone-id %) drone-id))
           @event-store)))

(defn clear-store! []
  (reset! event-store []))

;;; 프로젝션

(defn current-drone-states []
  (reduce (fn [acc ev]
            (let [id (:drone-id ev)]
              (case (:event-type ev)
                :drone-registered (assoc acc id {:status :registered :id id})
                :drone-departed   (assoc-in acc [id :status] :flying)
                :drone-landed     (assoc-in acc [id :status] :landed)
                :battery-low      (assoc-in acc [id :low-battery] true)
                acc)))
          {}
          @event-store))

(defn conflict-history []
  (let [detected  (count (get-events :conflict-detected))
        resolved  (count (get-events :conflict-resolved))]
    {:detected  detected
     :resolved  resolved
     :pending   (- detected resolved)
     :rate      (if (zero? detected) 1.0
                    (double (/ resolved detected)))}))

;;; 이벤트 스트림 재생

(defn replay-events [events handler-map]
  (reduce (fn [state ev]
            (if-let [handler (get handler-map (:event-type ev))]
              (handler state ev)
              state))
          {}
          events))

;;; 드론 집계

(defn drone-event-count [drone-id]
  (->> @event-store
       (filter #(= (:drone-id %) drone-id))
       count))

(defn recent-events [n]
  (take-last n @event-store))

(defn events-by-type-summary []
  (frequencies (map :event-type @event-store)))
