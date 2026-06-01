"Phase 596: Message Broker — 드론 메시지 브로커 (Smalltalk)
 Publish-subscribe message broker for swarm drone event distribution."

Object subclass: #MessageBroker
    instanceVariableNames: 'topics subscribers messageLog phase'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Comms'!

!MessageBroker methodsFor: 'initialization'!
initialize
    topics     := Dictionary new.
    subscribers := Dictionary new.
    messageLog := OrderedCollection new.
    phase      := 596! !

!MessageBroker methodsFor: 'publishing'!
publish: aMessage onTopic: aTopic
    "Publish a message to all subscribers of topic."
    | entry handlers |
    entry := Association key: aTopic value: aMessage.
    messageLog add: entry.
    handlers := subscribers at: aTopic ifAbsent: [#()].
    handlers do: [:handler | handler value: aMessage].
    ^aMessage!

subscribe: aHandler toTopic: aTopic
    "Register handler block for a topic."
    | current |
    current := subscribers at: aTopic ifAbsent: [OrderedCollection new].
    current add: aHandler.
    subscribers at: aTopic put: current! !

!MessageBroker methodsFor: 'querying'!
messageCount
    ^messageLog size!

topicCount
    ^subscribers size!

phase
    ^phase!

summary
    ^Dictionary new
        at: 'phase'     put: phase;
        at: 'messages'  put: messageLog size;
        at: 'topics'    put: subscribers size;
        yourself! !

Object subclass: #DroneMessageRouter
    instanceVariableNames: 'broker droneId receivedMessages'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Comms'!

!DroneMessageRouter methodsFor: 'initialization'!
initWithBroker: aBroker droneId: anId
    broker          := aBroker.
    droneId         := anId.
    receivedMessages := OrderedCollection new.
    broker subscribe: [:msg | receivedMessages add: msg] toTopic: 'telemetry'.
    broker subscribe: [:msg | receivedMessages add: msg] toTopic: ('cmd_drone_', anId printString)! !

!DroneMessageRouter methodsFor: 'messaging'!
sendTelemetry: aDictionary
    broker publish: aDictionary onTopic: 'telemetry'!

sendAlert: aString
    broker publish: aString onTopic: 'alerts'! !

"── Entry point ──────────────────────────────────────────────────"

| broker router1 router2 summary |
Transcript showCr: 'Phase 596: Message Broker — 드론 메시지 브로커'.
broker  := MessageBroker new initialize.
router1 := DroneMessageRouter new initWithBroker: broker droneId: 1.
router2 := DroneMessageRouter new initWithBroker: broker droneId: 2.

router1 sendTelemetry: (Dictionary new at: 'x' put: 100; at: 'battery' put: 80; yourself).
router2 sendTelemetry: (Dictionary new at: 'x' put: 200; at: 'battery' put: 65; yourself).
router1 sendAlert: 'low_battery_warning'.

summary := broker summary.
Transcript showCr: 'Messages: ', (summary at: 'messages') printString.
Transcript showCr: 'Topics: ',   (summary at: 'topics') printString.
