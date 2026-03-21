import React from 'react';
import { Crosshair, Shield, AlertTriangle } from 'lucide-react';

export default function StatsPanel({ stats }) {
  // Si los datos aún no cargan desde el backend, mostramos un mensaje
  if (!stats) {
    return (
      <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 animate-pulse">
        <p className="text-slate-500 text-center">Cargando métricas de la base de datos...</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
      <h2 className="text-xl font-bold text-slate-200 mb-6">Métricas Históricas</h2>
      
      <div className="space-y-4">
        {/* Total de Disparos */}
        <div className="flex items-center justify-between p-3 bg-slate-900 rounded-lg border border-slate-700">
          <div className="flex items-center gap-3">
            <Crosshair className="text-blue-400" size={20} />
            <span className="text-slate-300">Total Disparos</span>
          </div>
          <span className="text-xl font-bold text-white">{stats.totalDisparos || 0}</span>
        </div>
        
        {/* Tiempo de Camuflaje */}
        <div className="flex items-center justify-between p-3 bg-slate-900 rounded-lg border border-slate-700">
          <div className="flex items-center gap-3">
            <Shield className="text-indigo-400" size={20} />
            <span className="text-slate-300">Tiempo Camuflaje (seg)</span>
          </div>
          <span className="text-xl font-bold text-white">{stats.tiempoCamuflaje || 0}</span>
        </div>

        {/* Alertas Críticas */}
        <div className="flex items-center justify-between p-3 bg-red-950/30 rounded-lg border border-red-900/50">
          <div className="flex items-center gap-3">
            <AlertTriangle className="text-red-500" size={20} />
            <span className="text-red-200">Alertas Críticas</span>
          </div>
          <span className="text-xl font-bold text-red-500">{stats.alertasCriticas || 0}</span>
        </div>
      </div>
    </div>
  );
}