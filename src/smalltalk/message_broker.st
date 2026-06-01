"MessageBroker — Smalltalk for SDACS pub/sub messaging"
"Phase 596"

Object subclass: #MessageBroker
    instanceVariableNames: 'subscriptions messageQueue'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Messaging'!

!MessageBroker methodsFor: 'initialize-release'!
initialize
    subscriptions := Dictionary new.
    messageQueue  := OrderedCollection new.
! !

!MessageBroker methodsFor: 'subscription'!
subscribe: aTopic handler: aBlock
    | handlers |
    handlers := subscriptions at: aTopic ifAbsent: [OrderedCollection new].
    handlers add: aBlock.
    subscriptions at: aTopic put: handlers.
    ^self
!

unsubscribe: aTopic handler: aBlock
    | handlers |
    handlers := subscriptions at: aTopic ifAbsent: [^self].
    handlers remove: aBlock ifAbsent: [].
! !

!MessageBroker methodsFor: 'publishing'!
publish: aTopic payload: aPayload
    | msg handlers |
    msg := Association key: aTopic value: aPayload.
    messageQueue addLast: msg.
    ^self dispatch: msg
!

dispatch: aMessage
    | handlers |
    handlers := subscriptions at: aMessage key ifAbsent: [^self].
    handlers do: [:handler | handler value: aMessage value].
! !

!MessageBroker methodsFor: 'status'!
pendingCount
    ^messageQueue size
!

topicCount
    ^subscriptions size
! !

MessageBroker class extend [
    new [^super new initialize]
]
