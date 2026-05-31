;; event_sourcing_v2.clj - Event sourcing v2 for SDACS drone telemetry
(ns sdacs.event-sourcing-v2
  (:require [clojure.spec.alpha :as s]))

(s/def ::event-type keyword?)
(s/def ::drone-id string?)
(s/def ::timestamp pos-int?)
(s/def ::event (s/keys :req [::event-type ::drone-id ::timestamp]))

(defn make-event [event-type drone-id data]
  {::event-type event-type
   ::drone-id   drone-id
   ::timestamp  (System/currentTimeMillis)
   ::data       data})

(defprotocol EventStore
  (append! [store event])
  (read-events [store drone-id])
  (get-snapshot [store drone-id]))

(defrecord InMemoryEventStore [events-atom]
  EventStore
  (append! [_ event]
    (swap! events-atom conj event))
  (read-events [_ drone-id]
    (filter #(= (::drone-id %) drone-id) @events-atom))
  (get-snapshot [_ drone-id]
    (last (filter #(= (::drone-id %) drone-id) @events-atom))))

(defn create-store [] (->InMemoryEventStore (atom [])))

(defn apply-event [state event]
  (case (::event-type event)
    :telemetry  (merge state (::data event))
    :command    (assoc state :last-command (::data event))
    :conflict   (update state :conflicts (fnil conj []) (::data event))
    state))

(defn reconstruct-state [events]
  (reduce apply-event {} events))
