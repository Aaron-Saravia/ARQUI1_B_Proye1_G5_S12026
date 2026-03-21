import { useEffect, useState } from 'react';
import { io } from 'socket.io-client';

const SOCKET_URL = 'http://localhost:3000';

export function useDashboardSocket() {
  const [sensoresEnTiempoReal, setSensoresEnTiempoReal] = useState({
    gas: 0,
    distanciaMeteorito: 0,
    colorCamuflaje: 'Ninguno',
    estadoCompuerta: 'Cerrada'
  });
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Inicia la conexión real
    const socket = io(SOCKET_URL);

    socket.on('connect', () => {
      setIsConnected(true);
      console.log('Conectado al servidor de telemetría');
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
      console.log('Desconectado del servidor');
    });

    // Escucha el evento real que emitirá Node.js cuando MQTT reciba algo
    socket.on('telemetria_actualizada', (nuevosDatos) => {
      setSensoresEnTiempoReal(prev => ({ ...prev, ...nuevosDatos }));
    });

    // Limpieza al desmontar
    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('telemetria_actualizada');
      socket.disconnect();
    };
  }, []);

  return { sensoresEnTiempoReal, isConnected };
}