;; P574: EventStream - Clojure event streaming for drone telemetry
;; Phase 574: Event-driven telemetry processing pipeline

(ns sdacs.event-stream
  (:require [clojure.core.async :as async]
            [clojure.string :as str]))

;; Event types
(def event-types #{:telemetry :command :alert :conflict :status})

;; Create a drone telemetry event
(defn make-telemetry-event [drone-id pos vel battery]
  {:type        :telemetry
   :drone-id    drone-id
   :timestamp   (System/currentTimeMillis)
   :position    pos
   :velocity    vel
   :battery     battery})

;; Create a command event
(defn make-command-event [drone-id command params]
  {:type     :command
   :drone-id drone-id
   :timestamp (System/currentTimeMillis)
   :command  command
   :params   params})

;; Create an alert event
(defn make-alert-event [drone-id alert-type severity message]
  {:type      :alert
   :drone-id  drone-id
   :timestamp (System/currentTimeMillis)
   :alert     alert-type
   :severity  severity
   :message   message})

;; Event stream processor
(defrecord EventStream [channel buffer-size filters subscribers])

(defn create-stream [buffer-size]
  (->EventStream
    (async/chan buffer-size)
    buffer-size
    (atom [])
    (atom [])))

(defn publish! [stream event]
  (when (event-types (:type event))
    (async/>!! (:channel stream) event)))

(defn subscribe! [stream handler]
  (swap! (:subscribers stream) conj handler)
  (let [sub-chan (async/chan 100)]
    (async/go-loop []
      (when-let [event (async/<! (:channel stream))]
        (doseq [f @(:filters stream)]
          (when (f event) (handler event)))
        (recur)))
    sub-chan))

(defn add-filter! [stream predicate]
  (swap! (:filters stream) conj predicate))

;; defn pipeline: chain of transformations
(defn pipeline [stream transformers]
  (reduce
    (fn [events xf]
      (sequence xf events))
    []
    transformers))

;; Filter by drone ID
(defn filter-by-drone [drone-id]
  (filter #(= (:drone-id %) drone-id)))

;; Filter by event type
(defn filter-by-type [event-type]
  (filter #(= (:type %) event-type)))

;; Aggregate telemetry events
(defn aggregate-telemetry [events window-ms]
  (let [now (System/currentTimeMillis)
        cutoff (- now window-ms)
        recent (filter #(> (:timestamp %) cutoff) events)]
    {:count        (count recent)
     :avg-battery  (when (seq recent)
                     (/ (apply + (map :battery recent))
                        (count recent)))
     :window-ms    window-ms}))

;; Process event batch
(defn process-batch [events]
  (group-by :type events))

;; Telemetry stream stats
(defn compute-stats [telemetry-events]
  {:total      (count telemetry-events)
   :by-drone   (frequencies (map :drone-id telemetry-events))
   :alerts     (count (filter #(= (:type %) :alert) telemetry-events))})
