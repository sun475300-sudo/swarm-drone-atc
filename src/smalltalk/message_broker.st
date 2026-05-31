"Phase 596 — Smalltalk MessageBroker class"
"SDACS inter-process message broker for drone event distribution"

Object subclass: #MessageBroker
    instanceVariableNames: 'name subscribers queues messageCount droppedCount'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Messaging'!

!MessageBroker class methodsFor: 'instance creation'!
new: aName
    "Create and return a new MessageBroker with the given name."
    | broker |
    broker := super new.
    broker initializeWithName: aName.
    ^broker
! !

!MessageBroker methodsFor: 'initialization'!
initializeWithName: aName
    "Initialise internal state."
    name := aName.
    subscribers := Dictionary new.
    queues := Dictionary new.
    messageCount := 0.
    droppedCount := 0.
! !

!MessageBroker methodsFor: 'subscription'!
subscribe: aBlock toTopic: aTopic
    "Register a handler block for messages on the given topic."
    | list |
    list := subscribers at: aTopic ifAbsent: [ OrderedCollection new ].
    list add: aBlock.
    subscribers at: aTopic put: list.
    Transcript showCr: 'MessageBroker [', name, ']: subscribed to topic: ', aTopic.
!

unsubscribeFromTopic: aTopic
    "Remove all subscribers for the given topic."
    subscribers removeKey: aTopic ifAbsent: [].
    Transcript showCr: 'MessageBroker [', name, ']: unsubscribed from topic: ', aTopic.
! !

!MessageBroker methodsFor: 'publishing'!
publish: aMessage toTopic: aTopic
    "Dispatch aMessage to all subscribers on aTopic."
    | list delivered |
    messageCount := messageCount + 1.
    list := subscribers at: aTopic ifAbsent: [ nil ].
    list isNil ifTrue: [
        "Queue messages for topics with no current subscribers."
        self enqueue: aMessage forTopic: aTopic.
        droppedCount := droppedCount + 1.
        ^self
    ].
    delivered := 0.
    list do: [ :handler |
        [ handler value: aMessage.
          delivered := delivered + 1. ]
        on: Error do: [ :e |
            Transcript showCr: 'MessageBroker handler error: ', e messageText.
        ].
    ].
    Transcript showCr: 'MessageBroker [', name, '] published to ', aTopic,
               ' — ', delivered printString, ' handler(s)'.
!

enqueue: aMessage forTopic: aTopic
    "Buffer a message for a topic that has no active subscriber."
    | queue |
    queue := queues at: aTopic ifAbsent: [ OrderedCollection new ].
    queue addLast: aMessage.
    queues at: aTopic put: queue.
! !

!MessageBroker methodsFor: 'draining'!
drainTopic: aTopic
    "Deliver all buffered messages for aTopic to current subscribers."
    | queue msg |
    queue := queues at: aTopic ifAbsent: [ ^self ].
    [ queue isEmpty ] whileFalse: [
        msg := queue removeFirst.
        self publish: msg toTopic: aTopic.
    ].
    queues removeKey: aTopic.
! !

!MessageBroker methodsFor: 'reporting'!
printStats
    "Print broker statistics to the Transcript."
    Transcript showCr: '=== MessageBroker Stats: ', name, ' ==='.
    Transcript showCr: '  Topics subscribed : ', subscribers size printString.
    Transcript showCr: '  Messages published: ', messageCount printString.
    Transcript showCr: '  Messages queued   : ', droppedCount printString.
!

name
    ^name
!

messageCount
    ^messageCount
!

droppedCount
    ^droppedCount
! !

"--- Example usage ---"
| broker |
broker := MessageBroker new: 'SDACS-Primary'.
broker subscribe: [ :msg | Transcript showCr: 'Telemetry received: ', msg printString ] toTopic: 'telemetry'.
broker subscribe: [ :msg | Transcript showCr: 'Conflict alert: ', msg printString ] toTopic: 'conflict'.
broker publish: 'drone-1 alt=80m bat=85%' toTopic: 'telemetry'.
broker publish: 'drone-2 alt=79m bat=90%' toTopic: 'telemetry'.
broker publish: 'drone-1 vs drone-3 dist=4.2m' toTopic: 'conflict'.
broker printStats.
