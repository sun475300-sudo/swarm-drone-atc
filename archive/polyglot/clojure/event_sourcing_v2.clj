;; Phase 637: Event Sourcing v2 — Clojure CQRS Enhanced
;; CQRS 이벤트 소싱 고도화 (트랜잭션 로그)

(ns sdacs.event-sourcing-v2
  (:require [clojure.string :as str]))

;; ── Event Store ──

(def event-store (atom []))
(def snapshots (atom {}))
(def projections (atom {}))

(defn create-event [type aggregate-id data]
  {:event-id (str (java.util.UUID/randomUUID))
   :type type
   :aggregate-id aggregate-id
   :data data
   :timestamp (System/currentTimeMillis)
   :version (inc (count @event-store))})

(defn append-event! [type aggregate-id data]
  (let [event (create-event type aggregate-id data)]
    (swap! event-store conj event)
    event))

;; ── Drone Events ──

(defn drone-launched! [drone-id position]
  (append-event! :drone-launched drone-id {:position position}))

(defn drone-moved! [drone-id from to]
  (append-event! :drone-moved drone-id {:from from :to to}))

(defn conflict-detected! [drone-a drone-b distance]
  (append-event! :conflict-detected
                 (str drone-a "-" drone-b)
                 {:drone-a drone-a
                  :drone-b drone-b
                  :distance distance}))

(defn advisory-issued! [drone-id advisory-type]
  (append-event! :advisory-issued drone-id {:type advisory-type}))

(defn drone-landed! [drone-id]
  (append-event! :drone-landed drone-id {}))

;; ── Projections ──

(defn build-drone-projection [events]
  (reduce
    (fn [state event]
      (case (:type event)
        :drone-launched (assoc state (:aggregate-id event)
                              {:status :flying
                               :position (get-in event [:data :position])})
        :drone-moved (update state (:aggregate-id event)
                            assoc :position (get-in event [:data :to]))
        :drone-landed (update state (:aggregate-id event)
                             assoc :status :landed)
        state))
    {}
    events))

(defn build-conflict-projection [events]
  (let [conflicts (filter #(= (:type %) :conflict-detected) events)]
    {:total-conflicts (count conflicts)
     :unique-pairs (count (distinct (map :aggregate-id conflicts)))
     :avg-distance (if (seq conflicts)
                     (/ (reduce + (map #(get-in % [:data :distance]) conflicts))
                        (count conflicts))
                     0)}))

;; ── Snapshots ──

(defn create-snapshot! [aggregate-id]
  (let [events (filter #(= (:aggregate-id %) aggregate-id) @event-store)
        snapshot {:aggregate-id aggregate-id
                  :version (count events)
                  :state (build-drone-projection events)
                  :timestamp (System/currentTimeMillis)}]
    (swap! snapshots assoc aggregate-id snapshot)
    snapshot))

;; ── Query ──

(defn get-events-since [version]
  (filter #(> (:version %) version) @event-store))

(defn get-aggregate-events [aggregate-id]
  (filter #(= (:aggregate-id %) aggregate-id) @event-store))

(defn summary []
  {:total-events (count @event-store)
   :event-types (frequencies (map :type @event-store))
   :snapshots (count @snapshots)})
