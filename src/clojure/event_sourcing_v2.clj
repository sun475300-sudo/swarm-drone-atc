;; P637: Event Sourcing v2 - Clojure stub
;; Event-sourced state management for drone airspace

(ns sdacs.event-sourcing-v2
  (:require [clojure.core.async :as async]))

(defrecord DroneEvent [id type payload timestamp])

(defn create-event [drone-id type payload]
  (->DroneEvent drone-id type payload (System/currentTimeMillis)))

(defprotocol EventStore
  (append! [store event])
  (get-events [store drone-id])
  (get-all-events [store]))

(defrecord InMemoryEventStore [events-atom]
  EventStore
  (append! [_ event]
    (swap! events-atom conj event))
  (get-events [_ drone-id]
    (filter #(= (:id %) drone-id) @events-atom))
  (get-all-events [_]
    @events-atom))

(defn make-store []
  (->InMemoryEventStore (atom [])))

(defmulti apply-event (fn [state event] (:type event)))

(defmethod apply-event :drone/moved [state {:keys [id payload]}]
  (assoc-in state [:drones id :position] (:position payload)))

(defmethod apply-event :drone/battery-updated [state {:keys [id payload]}]
  (assoc-in state [:drones id :battery] (:level payload)))

(defmethod apply-event :default [state _] state)

(defn rebuild-state [events]
  (reduce apply-event {:drones {}} events))
