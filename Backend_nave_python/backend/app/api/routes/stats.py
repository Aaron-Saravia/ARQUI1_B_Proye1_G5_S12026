from __future__ import annotations

from fastapi import APIRouter

from app.db.mongo import mongo

router = APIRouter(tags=['stats'])


@router.get('/api/stats')
@router.get('/api/estadisticas')
def get_stats() -> dict[str, int]:
    if not mongo.is_connected:
        return {
            'totalDisparos': 0,
            'tiempoCamuflaje': 0,
            'alertasCriticas': 0,
            'totalShots': 0,
            'totalCamouflageSeconds': 0,
            'gasAlerts': 0,
            'meteorAlerts': 0,
            'totalMessages': 0,
        }

    commands = mongo.collection('commands')
    events = mongo.collection('events')
    messages = mongo.collection('messages')

    total_shots = commands.count_documents({'actuator': 'torreta', 'action': 'fire'})
    gas_alerts = events.count_documents({'$or': [{'type': 'ALERT_GAS'}, {'payload.category': 'gas'}]})
    meteor_alerts = events.count_documents({'$or': [{'type': 'ALERT_METEOR'}, {'payload.category': 'meteor'}]})
    critical_alerts = events.count_documents({'severity': 'critical'})
    total_messages = messages.count_documents({})
    camouflage_agg = list(
        events.aggregate(
            [
                {'$match': {'$or': [{'type': 'CAMOUFLAGE_SESSION'}, {'payload.durationSeconds': {'$exists': True}}]}},
                {'$group': {'_id': None, 'totalSeconds': {'$sum': '$payload.durationSeconds'}}},
            ]
        )
    )
    total_camouflage_seconds = int(camouflage_agg[0]['totalSeconds']) if camouflage_agg else 0

    return {
        'totalDisparos': int(total_shots),
        'tiempoCamuflaje': total_camouflage_seconds,
        'alertasCriticas': int(critical_alerts),
        'totalShots': int(total_shots),
        'totalCamouflageSeconds': total_camouflage_seconds,
        'gasAlerts': int(gas_alerts),
        'meteorAlerts': int(meteor_alerts),
        'totalMessages': int(total_messages),
    }
