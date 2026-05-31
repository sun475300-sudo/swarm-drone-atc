;; Phase 637 — Event Sourcing v2 (Clojure)
;; 드론 이벤트 소싱 / CQRS 패턴 구현

(ns sdacs.event-sourcing-v2
  (:require [clojure.spec.alpha :as s]))

;; ── 이벤트 스펙 ───────────────────────────────────────────────
(s/def ::event-type keyword?)
(s/def ::drone-id   string?)
(s/def ::timestamp  double?)
(s/def ::payload    map?)

(s/def ::event
  (s/keys :req-un [::event-type ::drone-id ::timestamp ::payload]))

;; ── 이벤트 스토어 ─────────────────────────────────────────────
(defn make-store []
  (atom {:events [] :snapshots {}}))

(defn append-event! [store event]
  {:pre [(s/valid? ::event event)]}
  (swap! store update :events conj event)
  event)

(defn events-for [store drone-id]
  (->> (:events @store)
       (filter #(= (:drone-id %) drone-id))
       (sort-by :timestamp)))

;; ── 집계 함수 ─────────────────────────────────────────────────
(defmulti apply-event (fn [_state event] (:event-type event)))

(defmethod apply-event :drone/spawned [_state {:keys [payload]}]
  {:pos     (:pos payload [0.0 0.0 100.0])
   :vel     (:vel payload [0.0 0.0 0.0])
   :battery (:battery payload 100.0)
   :phase   :grounded})

(defmethod apply-event :drone/moved [state {:keys [payload]}]
  (merge state {:pos (:pos payload) :vel (:vel payload)}))

(defmethod apply-event :drone/battery-updated [state {:keys [payload]}]
  (assoc state :battery (:battery payload)))

(defmethod apply-event :default [state _event] state)

(defn rebuild-state [store drone-id]
  (reduce apply-event {} (events-for store drone-id)))

;; ── 스냅샷 ────────────────────────────────────────────────────
(defn save-snapshot! [store drone-id]
  (let [state (rebuild-state store drone-id)]
    (swap! store assoc-in [:snapshots drone-id] state)
    state))
