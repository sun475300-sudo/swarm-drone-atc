;; Phase 637: Event Sourcing v2 — Clojure
;; SDACS event-sourced drone state management with CQRS pattern

(ns sdacs.event-sourcing-v2
  (:require [clojure.spec.alpha :as s]))

(s/def ::event-type keyword?)
(s/def ::drone-id string?)
(s/def ::timestamp number?)
(s/def ::payload map?)
(s/def ::event (s/keys :req-un [::event-type ::drone-id ::timestamp ::payload]))

(defprotocol EventStore
  (append! [store drone-id event])
  (load-events [store drone-id])
  (snapshot [store drone-id]))

(defrecord InMemoryEventStore [store-atom]
  EventStore
  (append! [_ drone-id event]
    (swap! store-atom update drone-id (fnil conj []) event))
  (load-events [_ drone-id]
    (get @store-atom drone-id []))
  (snapshot [_ drone-id]
    (get @store-atom drone-id [])))

(defn new-store [] (->InMemoryEventStore (atom {})))

(defmulti apply-event (fn [state event] (:event-type event)))
(defmethod apply-event :takeoff [state event]  (assoc state :mode :flying :alt (get-in event [:payload :alt] 60)))
(defmethod apply-event :land    [state event]  (assoc state :mode :idle :alt 0))
(defmethod apply-event :telemetry [state event](merge state (:payload event)))
(defmethod apply-event :default [state _]      state)

(defn rebuild-state [events]
  (reduce apply-event {:mode :idle :alt 0 :battery 100} events))

(defn record-event! [store drone-id event-type payload]
  (let [event {:event-type event-type :drone-id drone-id
               :timestamp (System/currentTimeMillis) :payload payload}]
    (append! store drone-id event)
    event))

(comment
  (def store (new-store))
  (record-event! store "D001" :takeoff {:alt 60})
  (record-event! store "D001" :telemetry {:battery 85 :speed 10})
  (println "Phase 637:" (rebuild-state (load-events store "D001"))))
