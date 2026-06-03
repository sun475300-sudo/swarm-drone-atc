"Phase 586: Message Broker — Smalltalk
 SDACS pub/sub message broker for drone communication"

Object subclass: #MessageBroker
    instanceVariableNames: 'subscriptions messageQueue droneRegistry messageCount'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Communication'!

!MessageBroker class methodsFor: 'instance creation'!
new
    ^super new initialize! !

!MessageBroker methodsFor: 'initialization'!
initialize
    subscriptions := Dictionary new.
    messageQueue  := OrderedCollection new.
    droneRegistry := Dictionary new.
    messageCount  := 0.
    ^self! !

!MessageBroker methodsFor: 'subscription management'!
subscribe: aTopic handler: aBlock
    | topicSubs |
    topicSubs := subscriptions at: aTopic ifAbsent: [OrderedCollection new].
    topicSubs add: aBlock.
    subscriptions at: aTopic put: topicSubs.
    ^self!

unsubscribe: aTopic handler: aBlock
    | topicSubs |
    topicSubs := subscriptions at: aTopic ifAbsent: [^self].
    topicSubs remove: aBlock ifAbsent: [].
    ^self!

unsubscribeAll: aTopic
    subscriptions removeKey: aTopic ifAbsent: []! !

!MessageBroker methodsFor: 'publishing'!
publish: aMessage topic: aTopic
    | handlers |
    messageCount := messageCount + 1.
    messageQueue addLast: (Association key: aTopic value: aMessage).
    handlers := subscriptions at: aTopic ifAbsent: [^self].
    handlers do: [:handler | handler value: aMessage].
    ^self!

broadcast: aMessage
    subscriptions keysDo: [:topic |
        self publish: aMessage topic: topic].
    ^self! !

!MessageBroker methodsFor: 'drone registry'!
registerDrone: aDroneId state: aState
    droneRegistry at: aDroneId put: aState.
    self publish: aState topic: 'drone.registered'.
    ^self!

updateDrone: aDroneId state: aState
    droneRegistry at: aDroneId put: aState.
    self publish: aState topic: 'drone.telemetry'.
    ^self!

removeDrone: aDroneId
    droneRegistry removeKey: aDroneId ifAbsent: [].
    self publish: aDroneId topic: 'drone.removed'.
    ^self!

dronesCount
    ^droneRegistry size! !

!MessageBroker methodsFor: 'querying'!
messageCount
    ^messageCount!

queueSize
    ^messageQueue size!

topics
    ^subscriptions keys asArray!

subscriberCount: aTopic
    ^(subscriptions at: aTopic ifAbsent: [#()]) size!

stats
    ^Dictionary new
        at: 'messageCount'   put: messageCount;
        at: 'queueSize'      put: messageQueue size;
        at: 'topicCount'     put: subscriptions size;
        at: 'droneCount'     put: droneRegistry size;
        yourself! !

"Test / demo"
| broker count |
broker := MessageBroker new.
count := 0.
broker subscribe: 'drone.telemetry' handler: [:msg | count := count + 1].
broker publish: 'hello' topic: 'drone.telemetry'.
broker publish: 'world' topic: 'drone.telemetry'.
Transcript show: 'Messages received: ', count printString; nl.
Transcript show: 'Stats: ', broker stats printString; nl.
