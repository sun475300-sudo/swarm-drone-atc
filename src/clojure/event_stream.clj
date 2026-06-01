;; Phase 574: Event Stream — 드론 이벤트 스트림 처리 (Clojure)
;; Reactive event stream processing for swarm drone telemetry.
(ns sdacs.event-stream
  (:require [clojure.string :as str]))

(def ^:const PHASE 574)

;; ── Event types ────────────────────────────────────────────────────

(defrecord DroneEvent
  [id drone-id event-type payload timestamp])

(defrecord TelemetryEvent
  [drone-id x y z battery velocity ts])

(defrecord CommandEvent
  [drone-id command params ts])

(defrecord AlertEvent
  [drone-id severity message ts])

;; ── Event factory ──────────────────────────────────────────────────

(defn make-event [drone-id event-type payload]
  (->DroneEvent (gensym "evt-") drone-id event-type payload (System/currentTimeMillis)))

(defn make-telemetry [drone-id x y z battery velocity]
  (->TelemetryEvent drone-id x y z battery velocity (System/currentTimeMillis)))

(defn make-alert [drone-id severity message]
  (->AlertEvent drone-id severity message (System/currentTimeMillis)))

;; ── Stream processing ──────────────────────────────────────────────

(defn filter-by-drone [events drone-id]
  (filter #(= (:drone-id %) drone-id) events))

(defn filter-alerts [events]
  (filter #(instance? AlertEvent %) events))

(defn critical-alerts [events]
  (->> events
       filter-alerts
       (filter #(= (:severity %) :critical))))

(defn aggregate-telemetry [telemetry-events]
  (when (seq telemetry-events)
    {:count    (count telemetry-events)
     :avg-x    (/ (reduce + (map :x telemetry-events)) (count telemetry-events))
     :avg-y    (/ (reduce + (map :y telemetry-events)) (count telemetry-events))
     :avg-z    (/ (reduce + (map :z telemetry-events)) (count telemetry-events))
     :avg-bat  (/ (reduce + (map :battery telemetry-events)) (count telemetry-events))}))

;; ── Window operations ─────────────────────────────────────────────

(defn sliding-window [events window-size step]
  (let [n (count events)]
    (loop [start 0 result []]
      (if (> start (- n window-size))
        result
        (recur (+ start step)
               (conj result (subvec (vec events) start (min n (+ start window-size)))))))))

;; ── Event router ─────────────────────────────────────────────────

(def event-handlers (atom {}))

(defn register-handler! [event-type handler]
  (swap! event-handlers assoc event-type handler))

(defn dispatch-event! [event]
  (when-let [handler (get @event-handlers (:event-type event))]
    (handler event)))

;; ── Stream simulator ──────────────────────────────────────────────

(defn generate-telemetry-stream [n-drones n-steps seed]
  (let [rng (java.util.Random. seed)]
    (for [step (range n-steps)
          drone (range n-drones)]
      (make-telemetry
        drone
        (* step (+ 1.0 (.nextDouble rng)))
        (* step (+ 0.5 (.nextDouble rng)))
        (+ 50.0 (* (.nextDouble rng) 10))
        (- 100.0 (* step 0.2))
        (+ 5.0 (* (.nextDouble rng) 10))))))

;; ── Event stream pipeline ─────────────────────────────────────────

(defn run-pipeline [events]
  (let [telem    (filter #(instance? TelemetryEvent %) events)
        alerts   (filter #(instance? AlertEvent %) events)
        low-bat  (filter #(< (:battery %) 30.0) telem)
        agg      (aggregate-telemetry telem)]
    {:total-events  (count events)
     :telemetry     (count telem)
     :alerts        (count alerts)
     :low-battery   (count low-bat)
     :aggregate     agg
     :phase         PHASE}))

;; ── Entry point ────────────────────────────────────────────────────

(defn -main []
  (println (str "Phase " PHASE ": Event Stream — 드론 반응형 이벤트 스트림"))
  (let [stream (generate-telemetry-stream 5 20 42)
        result (run-pipeline stream)]
    (println (str "Events: "    (:total-events result)))
    (println (str "Telemetry: " (:telemetry result)))
    (println (str "Low-bat: "   (:low-battery result)))))
