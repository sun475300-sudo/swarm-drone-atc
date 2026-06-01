;; Phase 637 — Clojure CQRS Event Sourcing v2 for SDACS audit trail
(ns sdacs.event-sourcing-v2
  (:require [clojure.core.async :as async]))

(defrecord DroneEvent [drone-id event-type payload timestamp-ms])

(defn make-event-store []
  (atom {:events [] :subscribers []}))

(defn append-event!
  "Append an event to the store and notify subscribers."
  [store event]
  (swap! store update :events conj event)
  (doseq [sub (:subscribers @store)]
    (async/put! sub event))
  event)

(defn subscribe!
  "Add a core.async channel to receive future events."
  [store ch]
  (swap! store update :subscribers conj ch)
  ch)

(defn replay
  "Replay all events through a reducing function to rebuild state."
  [store reducer init-state]
  (reduce reducer init-state (:events @store)))

(defn aggregate-by-drone
  "Return a map of drone-id -> vector of events."
  [store]
  (group-by :drone-id (:events @store)))
