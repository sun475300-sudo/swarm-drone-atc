"Phase 596: message_broker — Smalltalk 기반 메시지 브로커"
"SDACS MessageBroker for Drone Inter-Process Communication"

Object subclass: #MessageBroker
    instanceVariableNames: 'subscribers topics messageQueue droppedCount deliveredCount'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Communication'.

!MessageBroker class methodsFor: 'instance creation'!
new
    ^super new initialize
! !

!MessageBroker methodsFor: 'initialization'!
initialize
    subscribers     := Dictionary new.
    topics          := Set new.
    messageQueue    := OrderedCollection new.
    droppedCount    := 0.
    deliveredCount  := 0.
    ^self
! !

!MessageBroker methodsFor: 'topic management'!
createTopic: aTopicName
    topics add: aTopicName.
    subscribers at: aTopicName ifAbsent: [
        subscribers at: aTopicName put: OrderedCollection new].
    ^aTopicName
!

topicExists: aTopicName
    ^topics includes: aTopicName
! !

!MessageBroker methodsFor: 'subscription'!
subscribe: aHandler toTopic: aTopicName
    self createTopic: aTopicName.
    (subscribers at: aTopicName) add: aHandler.
    ^aHandler
!

unsubscribe: aHandler fromTopic: aTopicName
    (topics includes: aTopicName) ifTrue: [
        (subscribers at: aTopicName) remove: aHandler ifAbsent: []].
! !

!MessageBroker methodsFor: 'publishing'!
publish: aMessage toTopic: aTopicName
    | handlers |
    (topics includes: aTopicName) ifFalse: [
        droppedCount := droppedCount + 1.
        ^self].
    handlers := subscribers at: aTopicName ifAbsent: [OrderedCollection new].
    handlers do: [:handler |
        handler value: aMessage.
        deliveredCount := deliveredCount + 1].
!

publishAsync: aMessage toTopic: aTopicName
    messageQueue add: (Association key: aTopicName value: aMessage).
!

flushQueue
    | pending |
    pending := messageQueue copy.
    messageQueue := OrderedCollection new.
    pending do: [:assoc |
        self publish: assoc value toTopic: assoc key].
! !

!MessageBroker methodsFor: 'statistics'!
deliveredCount
    ^deliveredCount
!

droppedCount
    ^droppedCount
!

subscriberCountForTopic: aTopicName
    ^(subscribers at: aTopicName ifAbsent: [OrderedCollection new]) size
!

printStats
    Transcript show: 'MessageBroker 통계:'; nl.
    Transcript show: '  토픽 수: ', topics size printString; nl.
    Transcript show: '  전달: ',    deliveredCount printString; nl.
    Transcript show: '  드롭: ',    droppedCount printString; nl.
! !

"드론 텔레메트리 메시지"
Object subclass: #DroneMessage
    instanceVariableNames: 'droneId payload timestamp topic'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Communication'.

!DroneMessage class methodsFor: 'instance creation'!
drone: anId payload: aPayload topic: aTopic
    ^self new initDrone: anId payload: aPayload topic: aTopic
! !

!DroneMessage methodsFor: 'initialization'!
initDrone: anId payload: aPayload topic: aTopic
    droneId   := anId.
    payload   := aPayload.
    topic     := aTopic.
    timestamp := DateAndTime now.
    ^self
! !

!DroneMessage methodsFor: 'accessing'!
droneId   ^droneId
payload   ^payload
topic     ^topic
timestamp ^timestamp

printOn: aStream
    aStream
        nextPutAll: 'DroneMessage[';
        nextPutAll: topic;
        nextPutAll: ':D';
        print: droneId;
        nextPutAll: ']'.
! !

"메인 실행"
| broker telemetry_handler alert_handler |

Transcript show: 'SDACS MessageBroker — Phase 596'; nl; nl.

broker := MessageBroker new.
broker createTopic: 'telemetry'.
broker createTopic: 'alerts'.
broker createTopic: 'commands'.

telemetry_handler := [:msg |
    Transcript show: '  [Telemetry] 드론', msg droneId printString,
        ': ', msg payload printString; nl].

alert_handler := [:msg |
    Transcript show: '  [ALERT] 드론', msg droneId printString,
        ': ', msg payload printString; nl].

broker subscribe: telemetry_handler toTopic: 'telemetry'.
broker subscribe: alert_handler     toTopic: 'alerts'.

"메시지 발행"
0 to: 4 do: [:droneId |
    broker publish:
        (DroneMessage drone: droneId
            payload: (Dictionary new
                at: 'alt' put: 50 + droneId;
                at: 'bat' put: 95 - (droneId * 5);
                yourself)
            topic: 'telemetry')
        toTopic: 'telemetry'].

broker publish:
    (DroneMessage drone: 2 payload: 'BATTERY_LOW' topic: 'alerts')
    toTopic: 'alerts'.

broker printStats.
Transcript show: '메시지 브로커 처리 완료.'; nl.
