"message_broker.st - Message broker for SDACS drone swarm"
"Smalltalk implementation of publish-subscribe message routing"

Object subclass: #MessageBroker
    instanceVariableNames: 'subscriptions messageQueue droneRegistry'
    classVariableNames: 'Instance'
    poolDictionaries: ''
    category: 'SDACS-Comms'!

!MessageBroker class methodsFor: 'instance creation'!
new
    Instance isNil ifTrue: [Instance := super new initialize].
    ^Instance
! !

!MessageBroker methodsFor: 'initialization'!
initialize
    subscriptions := Dictionary new.
    messageQueue := OrderedCollection new.
    droneRegistry := Dictionary new.
    ^self
! !

!MessageBroker methodsFor: 'subscription management'!
subscribe: aTopic handler: aBlock
    (subscriptions includesKey: aTopic)
        ifFalse: [subscriptions at: aTopic put: OrderedCollection new].
    (subscriptions at: aTopic) add: aBlock.
    ^self
!

unsubscribe: aTopic
    subscriptions removeKey: aTopic ifAbsent: [].
    ^self
! !

!MessageBroker methodsFor: 'publishing'!
publish: aTopic message: aMessage
    | handlers |
    messageQueue add: (Array with: aTopic with: aMessage).
    handlers := subscriptions at: aTopic ifAbsent: [^self].
    handlers do: [:handler | handler value: aMessage].
    ^self
!

publishTelemetry: droneId position: aPosition battery: aBattery
    self publish: 'telemetry' message: (Dictionary new
        at: 'drone_id' put: droneId;
        at: 'position' put: aPosition;
        at: 'battery' put: aBattery;
        yourself).
    ^self
! !

!MessageBroker methodsFor: 'drone registry'!
registerDrone: droneId
    droneRegistry at: droneId put: (Dictionary new
        at: 'status' put: 'active';
        at: 'registered' put: Time now;
        yourself).
    ^self
!

droneCount
    ^droneRegistry size
! !
