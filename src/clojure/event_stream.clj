;; Event Stream — Clojure event sourcing for SDACS audit trail
;; Phase 574

(ns sdacs.event-stream
  (:require [clojure.core.async :as async]))

;; ── Event Types ──────────────────────────────────────────────────

(defrecord DroneEvent
  [id timestamp drone-id event-type payload])

(defn create-event [drone-id event-type payload]
  (->DroneEvent
    (str (java.util.UUID/randomUUID))
    (System/currentTimeMillis)
    drone-id
    event-type
    payload))

;; ── Event Store ──────────────────────────────────────────────────

(defonce event-store (atom []))

(defn append-event! [event]
  (swap! event-store conj event))

(defn get-events-for [drone-id]
  (filter #(= (:drone-id %) drone-id) @event-store))

(defn get-all-events []
  @event-store)

;; ── Event Processing ─────────────────────────────────────────────

(defn process-event [state event]
  (case (:event-type event)
    :takeoff   (assoc state :status :airborne)
    :land      (assoc state :status :grounded)
    :conflict  (update state :conflicts inc)
    :advisory  (update state :advisories-received conj (:payload event))
    state))

(defn replay-events [drone-id]
  (let [events (get-events-for drone-id)
        initial-state {:status :grounded :conflicts 0 :advisories-received []}]
    (reduce process-event initial-state events)))

;; ── Streaming Pipeline ───────────────────────────────────────────

(defn create-event-stream []
  (async/chan 1024))

(defn publish-event! [stream event]
  (async/put! stream event))

(defn consume-events [stream handler-fn]
  (async/go-loop []
    (when-let [event (async/<! stream)]
      (handler-fn event)
      (recur))))

;; ── Statistics ───────────────────────────────────────────────────

(defn event-statistics []
  (let [events (get-all-events)
        by-type (group-by :event-type events)]
    {:total (count events)
     :by-type (into {} (map (fn [[k v]] [k (count v)]) by-type))}))

;; ── Projection: Current Fleet State ─────────────────────────────

(defn project-fleet-state []
  (let [all-drones (distinct (map :drone-id (get-all-events)))]
    (into {} (map #(vector % (replay-events %)) all-drones))))
