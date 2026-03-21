import React, { useEffect, useState } from 'react';
import { Flame, Activity, Palette, Wind } from 'lucide-react';
import { Toaster } from 'react-hot-toast'; // Importamos las notificaciones
import SensorCard from './components/SensorCard';
import ControlPanel from './components/ControlPanel';
import HistoryChart from './components/HistoryChart';
import StatsPanel from './components/StatsPanel'; // Importamos el nuevo panel
import { useDashboardSocket } from './hooks/useDashboardSocket';
import { naveAPI } from './api/client';

function App() {
  const { sensoresEnTiempoReal, isConnected } = useDashboardSocket();
  const [datosHistorial, setDatosHistorial] = useState([]);
  const [estadisticas, setEstadisticas] = useState(null);

  // Carga de datos iniciales reales desde la API
  useEffect(() => {
    const cargarDatos = async () => {
      const historial = await naveAPI.getHistorialSensores();
      const stats = await naveAPI.getEstadisticas();
      setDatosHistorial(historial);
      setEstadisticas(stats);
    };
    cargarDatos();
  }, []);

  // Lógica real del estado de la nave basada en los sensores
  const determinarEstadoNave = () => {
    if (!isConnected) return { texto: 'DESCONECTADA', clases: 'bg-slate-500/10 border-slate-500/20 text-slate-400' };
    
    // Si hay mucho gas o un meteorito muy cerca
    if (sensoresEnTiempoReal.gas > 80 || sensoresEnTiempoReal.distanciaMeteorito < 20) {
      return { texto: 'EMERGENCIA', clases: 'bg-red-600/20 border-red-500/50 text-red-500 animate-pulse' };
    }
    // Si los niveles están subiendo pero aún no son críticos
    if (sensoresEnTiempoReal.gas > 50 || sensoresEnTiempoReal.distanciaMeteorito < 50) {
      return { texto: 'ALERTA', clases: 'bg-yellow-500/20 border-yellow-500/50 text-yellow-500' };
    }
    // Todo normal
    return { texto: 'OPERATIVA', clases: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' };
  };

  const estadoActual = determinarEstadoNave();

  return (
    <div className="min-h-screen p-8">
      {/* Componente que renderiza las notificaciones visuales en la esquina */}
      <Toaster position="top-right" toastOptions={{ style: { background: '#1e293b', color: '#fff', border: '1px solid #334155' } }} />

      <header className="mb-10 flex justify-between items-center border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-500">
            Nave Espacial
          </h1>
          <p className="text-slate-400 mt-2">Estación de Control</p>
        </div>
        
        <div className={`px-6 py-2 rounded-full font-bold border ${estadoActual.clases}`}>
          ESTADO: {estadoActual.texto}
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <section className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-bold text-slate-200">Lecturas en Tiempo Real</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SensorCard title="Gas (MQ-2)" value={sensoresEnTiempoReal.gas} unit="ppm" icon={<Flame className="text-slate-400" />} isCritical={sensoresEnTiempoReal.gas > 80} />
            <SensorCard title="Meteoritos" value={sensoresEnTiempoReal.distanciaMeteorito} unit="cm" icon={<Activity className="text-slate-400" />} isCritical={sensoresEnTiempoReal.distanciaMeteorito < 20 && sensoresEnTiempoReal.distanciaMeteorito > 0} />
            <SensorCard title="Camuflaje RGB" value={sensoresEnTiempoReal.colorCamuflaje} unit="" icon={<Palette className="text-slate-400" />} isCritical={false} />
            <SensorCard title="Compuerta" value={sensoresEnTiempoReal.estadoCompuerta} unit="" icon={<Wind className="text-slate-400" />} isCritical={false} />
          </div>

          <h2 className="text-xl font-bold text-slate-200 mt-8 mb-4">Historial 24H</h2>
          <HistoryChart data={datosHistorial} />
        </section>

        {/* Panel lateral con Controles y Estadísticas */}
        <aside className="space-y-6">
          <ControlPanel />
          <StatsPanel stats={estadisticas} />
        </aside>
      </main>
    </div>
  );
}

export default App;