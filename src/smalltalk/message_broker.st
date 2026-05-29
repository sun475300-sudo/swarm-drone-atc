"Phase 596: Message Broker — Smalltalk"
"드론 간 메시지 브로커: 발행-구독 패턴, 토픽 라우팅, 큐 관리."

"─── 메시지 클래스 ───"
Object subclass: #DroneMessage
    instanceVariableNames: 'senderId topic payload timestamp priority'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Broker'.

DroneMessage >> senderId
    ^ senderId.

DroneMessage >> topic
    ^ topic.

DroneMessage >> payload
    ^ payload.

DroneMessage >> timestamp
    ^ timestamp.

DroneMessage >> priority
    ^ priority.

DroneMessage >> senderId: anId topic: aTopic payload: aPayload priority: aPriority
    senderId := anId.
    topic := aTopic.
    payload := aPayload.
    timestamp := DateAndTime now.
    priority := aPriority.
    ^ self.

DroneMessage >> printString
    ^ 'Message[', senderId asString, ' -> ', topic, ': ', payload asString, ']'.

"─── 구독자 클래스 ───"
Object subclass: #Subscriber
    instanceVariableNames: 'subscriberId topics messageQueue maxQueueSize'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Broker'.

Subscriber >> initialize: anId
    subscriberId := anId.
    topics := OrderedCollection new.
    messageQueue := OrderedCollection new.
    maxQueueSize := 100.
    ^ self.

Subscriber >> subscribeTo: aTopic
    (topics includes: aTopic) ifFalse: [
        topics add: aTopic
    ].

Subscriber >> unsubscribeFrom: aTopic
    topics remove: aTopic ifAbsent: [].

Subscriber >> receive: aMessage
    messageQueue size >= maxQueueSize ifTrue: [
        messageQueue removeFirst.  "버퍼 오버플로 시 오래된 메시지 제거"
    ].
    messageQueue add: aMessage.

Subscriber >> pendingMessages
    ^ messageQueue size.

Subscriber >> consumeAll
    | messages |
    messages := messageQueue copy.
    messageQueue removeAll.
    ^ messages.

Subscriber >> isSubscribedTo: aTopic
    ^ topics includes: aTopic.

"─── 메시지 브로커 ───"
Object subclass: #MessageBroker
    instanceVariableNames: 'subscribers topicQueues publishedCount deliveredCount deadLetterQueue'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Broker'.

MessageBroker >> initialize
    subscribers := Dictionary new.
    topicQueues := Dictionary new.
    publishedCount := 0.
    deliveredCount := 0.
    deadLetterQueue := OrderedCollection new.
    ^ self.

MessageBroker >> register: aSubscriberId
    | sub |
    sub := Subscriber new initialize: aSubscriberId.
    subscribers at: aSubscriberId put: sub.
    ^ sub.

MessageBroker >> subscribe: aSubscriberId to: aTopic
    | sub |
    sub := subscribers at: aSubscriberId ifAbsent: [^ nil].
    sub subscribeTo: aTopic.

MessageBroker >> publish: aMessage
    | delivered |
    publishedCount := publishedCount + 1.
    delivered := false.

    "토픽 큐에 저장"
    (topicQueues includesKey: aMessage topic) ifFalse: [
        topicQueues at: aMessage topic put: OrderedCollection new.
    ].
    (topicQueues at: aMessage topic) add: aMessage.

    "구독자에게 라우팅"
    subscribers valuesDo: [:sub |
        (sub isSubscribedTo: aMessage topic) ifTrue: [
            sub receive: aMessage.
            deliveredCount := deliveredCount + 1.
            delivered := true.
        ].
    ].

    "배달 불가 메시지"
    delivered ifFalse: [
        deadLetterQueue add: aMessage.
    ].

MessageBroker >> stats
    ^ Dictionary new
        at: 'published' put: publishedCount;
        at: 'delivered' put: deliveredCount;
        at: 'subscribers' put: subscribers size;
        at: 'topics' put: topicQueues size;
        at: 'dead_letters' put: deadLetterQueue size;
        yourself.

"─── 시뮬레이션 실행 ───"
| broker drones topics msg |
broker := MessageBroker new initialize.

"드론 등록 및 구독"
drones := #('DRONE_001' 'DRONE_002' 'DRONE_003' 'DRONE_004' 'DRONE_005').
topics := #('position' 'conflict' 'advisory' 'battery' 'mission').

drones do: [:id |
    broker register: id.
    topics do: [:t |
        broker subscribe: id to: t.
    ].
].

"메시지 발행"
1 to: 50 do: [:i |
    msg := DroneMessage new
        senderId: (drones atRandom)
        topic: (topics atRandom)
        payload: ('data_', i printString)
        priority: (i \\ 3).
    broker publish: msg.
].

"통계 출력"
Transcript show: '=== SDACS Message Broker ==='; cr.
broker stats keysAndValuesDo: [:k :v |
    Transcript show: '  ', k, ': ', v printString; cr.
].
