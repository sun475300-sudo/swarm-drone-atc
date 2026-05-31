(ns sdacs.event-sourcing-v2
  (:require [clojure.core.async :as async]))
(defn event [type payload]
  {:type type :payload payload :ts (System/currentTimeMillis)})
(defn apply-event [state ev] (conj state ev))
