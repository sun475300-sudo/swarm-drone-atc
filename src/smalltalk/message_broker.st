Object subclass: #MessageBroker
    instanceVariableNames: 'subscribers topics'
    classVariableNames: ''
    poolDictionaries: ''
    category: 'SDACS-Messaging'.

MessageBroker class >> new [
    ^super new initialize
]

MessageBroker >> initialize [
    subscribers := Dictionary new.
    topics := OrderedCollection new.
    ^self
]

MessageBroker >> subscribe: topic with: handler [
    | list |
    list := subscribers at: topic ifAbsent: [ OrderedCollection new ].
    list add: handler.
    subscribers at: topic put: list.
]

MessageBroker >> publish: topic message: msg [
    | list |
    list := subscribers at: topic ifAbsent: [ OrderedCollection new ].
    list do: [ :handler | handler value: msg ].
]

MessageBroker >> unsubscribe: topic with: handler [
    | list |
    list := subscribers at: topic ifAbsent: [ ^self ].
    list remove: handler ifAbsent: [ nil ].
]

MessageBroker >> topicCount [
    ^subscribers size
]
