TOPICS = {
    'sensors': {
        'gas': 'nave/sensores/gas',
        'proximity': 'nave/sensores/proximidad',
        'color': 'nave/sensores/color',
        'environment': 'nave/sensores/ambiente',
    },
    'actuators': {
        'turret': 'nave/actuadores/torreta',
        'doors': 'nave/actuadores/compuertas',
        'fans': 'nave/actuadores/ventiladores',
        'camouflage': 'nave/actuadores/camuflaje',
    },
    'control': {
        'messages': 'nave/control/mensajes',
        'emergency': 'nave/control/emergencia',
    },
    'alerts': {
        'critical': 'nave/alertas/criticas',
    },
    'state': {
        'general': 'nave/estado/general',
    },
}

MQTT_SUBSCRIPTIONS = [
    TOPICS['sensors']['gas'],
    TOPICS['sensors']['proximity'],
    TOPICS['sensors']['color'],
    TOPICS['sensors']['environment'],
    TOPICS['alerts']['critical'],
    TOPICS['state']['general'],
]

COMMAND_TOPIC_BY_ACTUATOR = {
    'torreta': TOPICS['actuators']['turret'],
    'compuertas': TOPICS['actuators']['doors'],
    'ventiladores': TOPICS['actuators']['fans'],
    'camuflaje': TOPICS['actuators']['camouflage'],
    'emergencia': TOPICS['control']['emergency'],
}
