import React, { useEffect, useState } from 'react';
import { Flame, Activity, Palette, Wind } from 'lucide-react';
import SensorCard from './components/SensorCard';
import ControlPanel from './components/ControlPanel';
import HistoryChart from './components/HistoryChart';
import { useDashboardSocket } from './hooks/useDashboardSocket';
import { naveAPI } from './api/client';

function App() {
  // 1. Hook que trae la telemetría en tiempo real (ahora mismo intentará conectar y no hallará el servidor, pero ya está listo)
  const { sensoresEnTiempoReal, isConnected } = useDashboardSocket();
  
  // 2. Estado para guardar el historial de la gráfica
  const [datosHistorial, setDatosHistorial] = useState([]);

  // 3. Petición real a la API al cargar la página
  useEffect(() => {
    const cargarDatos = async () => {
      const historial = await naveAPI.getHistorialSensores();
      setDatosHistorial(historial);
    };
    cargarDatos();
  }, []);

  return (
    <div className="min-h-screen p-8">
      <header className="mb-10 flex justify-between items-center border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500">
            Nave Espacial CYS
          </h1>
          <p className="text-slate-400 mt-2">Estación de Telemetría y Defensa</p>
        </div>
        
        {/* Indicador de conexión real */}
        <div className={`px-6 py-2 rounded-full font-bold animate-pulse border ${isConnected ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-red-500/10 border-red-500/20 text-red-400'}`}>
          {isConnected ? 'ESTADO: OPERATIVA' : 'DESCONECTADA DEL SERVIDOR'}
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <section className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-bold text-slate-200">Lecturas en Tiempo Real</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Pasamos los valores reales que vienen del Socket */}
            <SensorCard 
              title="Gas (MQ-2)" 
              value={sensoresEnTiempoReal.gas} 
              unit="ppm" 
              icon={<Flame className="text-slate-400" />} 
              isCritical={sensoresEnTiempoReal.gas > 80} 
            />
            <SensorCard 
              title="Meteoritos" 
              value={sensoresEnTiempoReal.distanciaMeteorito} 
              unit="cm" 
              icon={<Activity className="text-slate-400" />} 
              isCritical={sensoresEnTiempoReal.distanciaMeteorito < 20} 
            />
            <SensorCard 
              title="Camuflaje RGB" 
              value={sensoresEnTiempoReal.colorCamuflaje} 
              unit="Detectado" 
              icon={<Palette className="text-slate-400" />} 
              isCritical={false} 
            />
            <SensorCard 
              title="Compuerta" 
              value={sensoresEnTiempoReal.estadoCompuerta} 
              unit="" 
              icon={<Wind className="text-slate-400" />} 
              isCritical={false} 
            />
          </div>

          <h2 className="text-xl font-bold text-slate-200 mt-8 mb-4">Historial 24H</h2>
          <HistoryChart data={datosHistorial} />

        </section>

        <aside>
          <ControlPanel />
        </aside>
      </main>
    </div>
  );
}

export default App;