;; Phase 637 — Clojure CQRS Event Sourcing v2 for SDACS
(ns sdacs.cqrs.event-sourcing)

(defprotocol EventStore
  (append! [store aggregate-id events])
  (load-events [store aggregate-id]))

(defrecord InMemoryEventStore [state]
  EventStore
  (append! [_ aggregate-id events]
    (swap! state update aggregate-id (fnil into []) events))
  (load-events [_ aggregate-id]
    (get @state aggregate-id [])))

(defn create-store [] (->InMemoryEventStore (atom {})))

(defn apply-event [state {:keys [type payload]}]
  (case type
    :drone-registered (assoc-in state [:drones (:id payload)] payload)
    :conflict-detected (update state :conflicts conj payload)
    state))

(defn rebuild-state [events]
  (reduce apply-event {} events))
