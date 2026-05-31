"P596: MessageBroker - Smalltalk message broker for drone communication"
"Phase 596: Topic-based publish-subscribe MessageBroker"

Object subclass: #MessageBroker
    instanceVariableNames: 'topics subscribers messages'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Communication'

MessageBroker class >> new [
    |broker|
    broker := super new.
    broker init.
    ^broker
]

MessageBroker >> init [
    topics := Dictionary new.
    subscribers := Dictionary new.
    messages := OrderedCollection new.
]

MessageBroker >> subscribe: aTopic handler: aBlock [
    (subscribers includesKey: aTopic)
        ifFalse: [subscribers at: aTopic put: OrderedCollection new].
    (subscribers at: aTopic) add: aBlock.
]

MessageBroker >> publish: aTopic message: aMessage [
    |msg|
    msg := Association key: aTopic value: aMessage.
    messages add: msg.
    (subscribers includesKey: aTopic) ifTrue: [
        (subscribers at: aTopic) do: [:handler |
            handler value: aMessage].
    ].
]

MessageBroker >> messageCount [
    ^messages size
]

MessageBroker >> topics [
    ^topics keys
]

"Drone telemetry topic publisher"
Object subclass: #DronePublisher
    instanceVariableNames: 'broker droneId'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Communication'

DronePublisher >> initWith: aBroker droneId: anId [
    broker := aBroker.
    droneId := anId.
]

DronePublisher >> publishTelemetry: aDict [
    broker publish: ('telemetry/', droneId) message: aDict.
]

DronePublisher >> publishAlert: aString [
    broker publish: ('alert/', droneId) message: aString.
]
