;; Event sourcing v2 for SDACS audit trail — Clojure stub
(ns sdacs.event-sourcing-v2)

(defrecord Event [id timestamp actor action payload])

(defn create-event [actor action payload]
  (->Event (random-uuid) (System/currentTimeMillis) actor action payload))

(defn apply-events [initial-state events reducer]
  (reduce reducer initial-state events))

(defn replay [store entity-id]
  (filter #(= (:entity-id %) entity-id) @store))
