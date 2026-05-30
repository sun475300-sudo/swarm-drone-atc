"SDACS Message Broker — Smalltalk"
"군집드론 메시지 브로커 구현"

Object subclass: #MessageBroker
    instanceVariableNames: 'subscribers topics messageQueue'
    classVariableNames: 'Instance'
    poolDictionaries: ''
    category: 'SDACS-Communication'!

!MessageBroker class methodsFor: 'instance creation'!
new
    ^super new initialize! !

!MessageBroker methodsFor: 'initialization'!
initialize
    subscribers := Dictionary new.
    topics := Set new.
    messageQueue := OrderedCollection new.
    ^self! !

!MessageBroker methodsFor: 'subscription'!
subscribe: aTopic handler: aBlock
    | handlers |
    topics add: aTopic.
    handlers := subscribers at: aTopic ifAbsent: [OrderedCollection new].
    handlers add: aBlock.
    subscribers at: aTopic put: handlers.
    ^self! !

!MessageBroker methodsFor: 'publishing'!
publish: aTopic message: aMessage
    | handlers |
    messageQueue add: aMessage.
    handlers := subscribers at: aTopic ifAbsent: [OrderedCollection new].
    handlers do: [:handler | handler value: aMessage].
    ^self! !

!MessageBroker methodsFor: 'querying'!
topicCount
    ^topics size!

queueSize
    ^messageQueue size! !

"MessageBroker 사용 예시"
| broker |
broker := MessageBroker new.
broker subscribe: 'telemetry' handler: [:msg | Transcript showCr: 'Received: ', msg printString].
broker publish: 'telemetry' message: 'DRONE-001 at 100m'.
