;; Phase 574: Event Stream — Clojure Reactive Processing
;; SDACS real-time event streaming for drone telemetry

(ns sdacs.event-stream
  (:require [clojure.core.async :as async :refer [chan go go-loop >! <! close! put!]]
            [clojure.spec.alpha :as s]))

;; Event schema specification
(s/def ::event-type #{:telemetry :alert :command :status :conflict :battery})
(s/def ::drone-id string?)
(s/def ::timestamp number?)
(s/def ::payload map?)

(s/def ::event
  (s/keys :req-un [::event-type ::drone-id ::timestamp ::payload]))

;; Event stream state
(defonce ^:private stream-state
  (atom {:channels {}
         :subscribers {}
         :event-count 0
         :running false}))

(defn create-stream
  "Create a new event channel for a topic"
  [topic buffer-size]
  (let [ch (chan buffer-size)]
    (swap! stream-state assoc-in [:channels topic] ch)
    ch))

(defn publish-event
  "Publish an event to the appropriate stream topic"
  [topic event]
  (when-not (s/valid? ::event event)
    (throw (ex-info "Invalid event" {:event event :spec-error (s/explain-str ::event event)})))
  (let [ch (get-in @stream-state [:channels topic])]
    (when ch
      (put! ch event)
      (swap! stream-state update :event-count inc))))

(defn subscribe
  "Subscribe a handler function to a topic"
  [topic handler-fn]
  (let [sub-id (str (java.util.UUID/randomUUID))
        ch (get-in @stream-state [:channels topic])]
    (when ch
      (go-loop []
        (when-let [event (<! ch)]
          (handler-fn event)
          (recur))))
    (swap! stream-state assoc-in [:subscribers sub-id] {:topic topic :handler handler-fn})
    sub-id))

(defn make-event
  "Construct a validated event map"
  [event-type drone-id payload]
  {:event-type event-type
   :drone-id   drone-id
   :timestamp  (System/currentTimeMillis)
   :payload    payload})

(defn telemetry-event
  "Create telemetry event from drone state"
  [drone-id {:keys [lat lng alt speed battery heading]}]
  (make-event :telemetry drone-id
              {:lat lat :lng lng :alt alt
               :speed speed :battery battery
               :heading heading}))

(defn alert-event
  "Create alert event"
  [drone-id alert-type message]
  (make-event :alert drone-id
              {:alert-type alert-type :message message :severity :high}))

(defn conflict-event
  "Create conflict detection event"
  [drone-id other-drone-id distance]
  (make-event :conflict drone-id
              {:other-drone other-drone-id
               :separation-m distance
               :action-required true}))

(defn battery-event
  "Create battery status event"
  [drone-id pct remaining-s]
  (make-event :battery drone-id
              {:pct pct :remaining-seconds remaining-s
               :rtl-required (< pct 20)}))

(defn filter-stream
  "Filter events by predicate, returns new filtered channel"
  [source-ch pred-fn buffer-size]
  (let [out-ch (chan buffer-size)]
    (go-loop []
      (when-let [event (<! source-ch)]
        (when (pred-fn event)
          (>! out-ch event))
        (recur)))
    out-ch))

(defn merge-streams
  "Merge multiple event channels into one"
  [channels]
  (let [out (chan 1024)]
    (doseq [ch channels]
      (go-loop []
        (when-let [event (<! ch)]
          (>! out event)
          (recur))))
    out))

(defn transform-stream
  "Apply transform function to each event in channel"
  [source-ch transform-fn buffer-size]
  (let [out-ch (chan buffer-size)]
    (go-loop []
      (when-let [event (<! source-ch)]
        (>! out-ch (transform-fn event))
        (recur)))
    out-ch))

(defn start-stream-processor
  "Start the main event stream processor"
  []
  (swap! stream-state assoc :running true)
  (doseq [topic [:telemetry :alert :command :status :conflict :battery]]
    (create-stream topic 1024))
  :started)

(defn stop-stream-processor
  "Shutdown all event streams"
  []
  (doseq [[_topic ch] (:channels @stream-state)]
    (close! ch))
  (swap! stream-state assoc :running false :channels {})
  :stopped)

(defn stream-stats
  "Return current stream statistics"
  []
  {:event-count    (:event-count @stream-state)
   :active-topics  (count (:channels @stream-state))
   :subscriber-count (count (:subscribers @stream-state))
   :running        (:running @stream-state)})
