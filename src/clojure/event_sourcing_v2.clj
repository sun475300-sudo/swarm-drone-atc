;; Phase 637 — CQRS Event Sourcing v2 in Clojure
(ns sdacs.event-sourcing
  (:require [clojure.core.async :as async]))

(defprotocol EventStore
  (append! [store stream-id events])
  (load-stream [store stream-id]))

(defrecord InMemoryEventStore [state]
  EventStore
  (append! [_ stream-id events]
    (swap! state update stream-id (fnil concat []) events))
  (load-stream [_ stream-id]
    (get @state stream-id [])))

(defn make-store [] (->InMemoryEventStore (atom {})))

(defmulti apply-event (fn [_ event] (:type event)))

(defmethod apply-event :drone-registered [state event]
  (assoc-in state [:drones (:drone-id event)] {:status :active :pos (:pos event)}))

(defmethod apply-event :conflict-detected [state event]
  (update state :conflicts conj event))

(defn rebuild [events]
  (reduce apply-event {} events))
