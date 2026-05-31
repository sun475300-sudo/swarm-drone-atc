;; event_stream.clj - Event streaming for SDACS drone telemetry
;; Real-time event processing using Clojure channels

(ns sdacs.event-stream
  (:require [clojure.core.async :as async
             :refer [chan go go-loop >! <! close! alts!]]
            [clojure.spec.alpha :as s]))

;; Event type definitions
(s/def ::event-type #{:telemetry :conflict :status :command :geofence-alert})
(s/def ::drone-id string?)
(s/def ::timestamp pos-int?)
(s/def ::payload map?)

(s/def ::event
  (s/keys :req [::event-type ::drone-id ::timestamp ::payload]))

;; Event record constructor
(defn make-event
  "Create a new drone event record"
  [event-type drone-id payload]
  {::event-type event-type
   ::drone-id   drone-id
   ::timestamp  (System/currentTimeMillis)
   ::payload    payload})

;; Telemetry event factory
(defn telemetry-event
  "Create telemetry event from drone position data"
  [drone-id position velocity battery]
  (make-event :telemetry drone-id
              {:position position
               :velocity velocity
               :battery  battery}))

;; Conflict event factory
(defn conflict-event
  "Create conflict detection event between two drones"
  [drone-a drone-b distance]
  (make-event :conflict drone-a
              {:other-drone drone-b
               :distance    distance
               :severity    (cond (< distance 10) :critical
                                  (< distance 30) :warning
                                  :else           :caution)}))

;; Event stream processor
(defn create-stream
  "Create a new event processing stream with buffer size"
  [buffer-size]
  {:channel    (chan buffer-size)
   :processors (atom [])
   :stats      (atom {:processed 0 :errors 0})})

;; Add event processor
(defn add-processor
  "Register an event processor function"
  [stream processor-fn]
  (swap! (:processors stream) conj processor-fn))

;; Process events from stream
(defn start-processing
  "Start consuming events from stream"
  [stream]
  (let [ch (:channel stream)]
    (go-loop []
      (when-let [event (<! ch)]
        (doseq [proc @(:processors stream)]
          (try
            (proc event)
            (swap! (:stats stream) update :processed inc)
            (catch Exception e
              (swap! (:stats stream) update :errors inc))))
        (recur)))))

;; Emit event to stream
(defn emit!
  "Emit an event into the stream"
  [stream event]
  (go (>! (:channel stream) event)))

;; Geofence alert event
(defn geofence-alert-event
  "Create geofence violation alert"
  [drone-id zone-name distance]
  (make-event :geofence-alert drone-id
              {:zone     zone-name
               :distance distance
               :action   :return-to-safe-zone}))

;; Stream statistics
(defn stream-stats
  "Get current stream processing statistics"
  [stream]
  @(:stats stream))

;; Event filter middleware
(defn filter-events
  "Create filtered event stream by type"
  [stream event-type]
  (let [filtered (create-stream 100)]
    (add-processor stream
                   (fn [event]
                     (when (= (::event-type event) event-type)
                       (emit! filtered event))))
    filtered))

;; Batch event aggregator
(defn aggregate-telemetry
  "Aggregate telemetry events by drone ID"
  [events]
  (reduce (fn [acc event]
            (update acc (::drone-id event)
                    (fnil conj []) (::payload event)))
          {}
          events))
