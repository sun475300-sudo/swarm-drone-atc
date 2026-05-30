(ns sdacs.event-stream
  "SDACS event streaming subsystem.
   Manages drone telemetry event pipelines."
  (:require [clojure.core.async :as async]
            [clojure.string :as str]))

;; Event types
(def event-types
  #{:telemetry :conflict :geofence-breach :waypoint-reached
    :battery-low :motor-fault :wind-alert :mission-complete})

;; Event record constructor
(defn make-event
  "Create a new event map with timestamp."
  [event-type drone-id payload]
  {:type      event-type
   :drone-id  drone-id
   :payload   payload
   :timestamp (System/currentTimeMillis)
   :id        (str (java.util.UUID/randomUUID))})

;; Event validation
(defn valid-event?
  "Check whether an event map has required fields."
  [event]
  (and (map? event)
       (contains? event-types (:type event))
       (some? (:drone-id event))
       (some? (:timestamp event))))

;; In-memory event store
(def event-store (atom []))

(defn publish-event!
  "Publish an event to the event store and notify listeners."
  [event]
  (when (valid-event? event)
    (swap! event-store conj event)
    event))

(defn subscribe-events
  "Return a filtered sequence of events matching the given type."
  [event-type]
  (filter #(= (:type %) event-type) @event-store))

;; Event channel for async processing
(def event-channel (async/chan 1024))

(defn stream-event!
  "Put an event onto the async channel."
  [event]
  (async/go
    (async/>! event-channel event)))

(defn consume-events!
  "Consume events from the channel and apply f to each."
  [f]
  (async/go-loop []
    (when-let [event (async/<! event-channel)]
      (f event)
      (recur))))

;; Telemetry event helpers
(defn telemetry-event
  "Create a telemetry event for a drone."
  [drone-id position velocity battery]
  (make-event :telemetry drone-id
              {:position position
               :velocity velocity
               :battery  battery}))

(defn conflict-event
  "Create a conflict detection event."
  [drone-a drone-b distance]
  (make-event :conflict drone-a
              {:other-drone drone-b
               :distance    distance}))

(defn geofence-event
  "Create a geofence breach event."
  [drone-id zone-id]
  (make-event :geofence-breach drone-id
              {:zone zone-id}))

;; Event aggregation
(defn aggregate-by-drone
  "Group events by drone-id."
  []
  (group-by :drone-id @event-store))

(defn event-count-by-type
  "Return a frequency map of events by type."
  []
  (frequencies (map :type @event-store)))

(defn clear-events!
  "Clear all stored events (for testing)."
  []
  (reset! event-store []))
