(ns sdacs.event-stream
  "Real-time event streaming for drone telemetry — SDACS Phase 574"
  (:require [clojure.core.async :as async]
            [clojure.string :as str]))

(defrecord DroneEvent [type drone-id payload timestamp])

(defn event
  "Create a new drone event"
  [type drone-id payload]
  (->DroneEvent type drone-id payload (System/currentTimeMillis)))

(defn stream
  "Create a new event stream channel"
  ([] (stream 1024))
  ([buf-size] (async/chan buf-size)))

(defn publish!
  "Publish an event to a stream"
  [ch ev]
  (async/>!! ch ev))

(defn subscribe
  "Subscribe to events with a handler function"
  [ch handler]
  (async/go-loop []
    (when-let [ev (async/<! ch)]
      (handler ev)
      (recur))))

(defn filter-stream
  "Filter events by type"
  [ch event-type]
  (let [out (stream)]
    (async/go-loop []
      (when-let [ev (async/<! ch)]
        (when (= (:type ev) event-type)
          (async/>! out ev))
        (recur)))
    out))

(defn merge-streams
  "Merge multiple event streams"
  [& streams]
  (async/merge streams))

(comment
  ;; Usage example
  (def ch (stream))
  (publish! ch (event :telemetry "drone-001" {:lat 35.1 :lon 126.8}))
  (subscribe ch println))
