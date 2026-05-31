;; Phase 574 — Clojure event stream
;; SDACS real-time telemetry event stream processing pipeline.
;; Provides event sourcing, filtering, aggregation, and fan-out
;; for drone telemetry events across the swarm.

(ns sdacs.event-stream
  (:require [clojure.core.async :as async :refer [chan go go-loop >! <! close! mult tap]]
            [clojure.string :as str]))

;; ---------------------------------------------------------------
;; Event schema helpers
;; Each event is an immutable map:
;;   {:event/type keyword  :event/drone-id string
;;    :event/ts   long     :payload map}
;; ---------------------------------------------------------------

(defn make-event
  "Construct a new telemetry event map."
  [event-type drone-id payload]
  {:event/type     event-type
   :event/drone-id drone-id
   :event/ts       (System/currentTimeMillis)
   :payload        payload})

(defn event-type
  "Extract the event type keyword from an event."
  [event]
  (:event/type event))

(defn event-drone
  "Extract the drone-id from an event."
  [event]
  (:event/drone-id event))

;; ---------------------------------------------------------------
;; Event bus — a core.async channel backed pub/sub multiplexer
;; ---------------------------------------------------------------

(defonce ^:private event-bus (chan 1024))
(defonce ^:private event-mult (mult event-bus))

(defn publish-event!
  "Publish an event onto the event bus."
  [event]
  (async/put! event-bus event))

(defn subscribe
  "Return a new channel subscribed to all events on the bus."
  ([]     (subscribe 256))
  ([size] (let [sub-ch (chan size)] (tap event-mult sub-ch) sub-ch)))

;; ---------------------------------------------------------------
;; Event filters and transforms
;; ---------------------------------------------------------------

(defn filter-by-type
  "Return a transducer that passes only events of the given type."
  [event-type-kw]
  (filter #(= (event-type %) event-type-kw)))

(defn filter-by-drone
  "Return a transducer that passes events for a specific drone."
  [drone-id]
  (filter #(= (event-drone %) drone-id)))

(defn enrich-with-latency
  "Transducer: adds :latency-ms to event payload based on ingestion time."
  []
  (map (fn [event]
         (let [now  (System/currentTimeMillis)
               ts   (:event/ts event)
               lat  (- now ts)]
           (assoc-in event [:payload :latency-ms] lat)))))

;; ---------------------------------------------------------------
;; Stream processors
;; ---------------------------------------------------------------

(defn pipeline-processor
  "Start an event processing go-loop reading from `in-ch`,
   applying `xf` transducer, writing results to `out-ch`."
  [in-ch xf out-ch]
  (go-loop []
    (when-let [event (<! in-ch)]
      (let [processed ((xf identity) event)]
        (>! out-ch processed))
      (recur))))

(defn aggregate-telemetry
  "Reduce a seq of telemetry events into a per-drone summary map."
  [events]
  (reduce (fn [acc event]
            (let [did  (event-drone event)
                  data (:payload event)]
              (update acc did (fnil conj []) data)))
          {}
          events))

;; ---------------------------------------------------------------
;; Predefined event type constants
;; ---------------------------------------------------------------

(def EVENT_TELEMETRY   :event/telemetry)
(def EVENT_CONFLICT    :event/conflict)
(def EVENT_GEOFENCE    :event/geofence-violation)
(def EVENT_HEARTBEAT   :event/heartbeat)
(def EVENT_COMMAND     :event/command)

(defn start-heartbeat-emitter!
  "Spawn a go loop that emits a heartbeat event every `interval-ms` ms."
  [drone-id interval-ms]
  (go-loop []
    (async/<! (async/timeout interval-ms))
    (publish-event! (make-event EVENT_HEARTBEAT drone-id {:status :alive}))
    (recur)))
