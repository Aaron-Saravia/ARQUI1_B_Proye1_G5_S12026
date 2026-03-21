import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function HistoryChart({ data }) {
  // data será un arreglo real que vendrá del endpoint GET /api/sensores/historial
  // Ejemplo de lo que esperará: [{ hora: '10:00', gas: 45, meteorito: 120 }]

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center bg-slate-800 rounded-xl border border-slate-700">
        <p className="text-slate-500">Esperando datos históricos de la base de datos...</p>
      </div>
    );
  }

  return (
    <div className="h-64 w-full bg-slate-800 p-4 rounded-xl border border-slate-700">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="hora" stroke="#94a3b8" fontSize={12} />
          <YAxis stroke="#94a3b8" fontSize={12} />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569', color: '#f8fafc' }}
          />
          <Line type="monotone" dataKey="gas" stroke="#f59e0b" strokeWidth={2} name="Gas (ppm)" />
          <Line type="monotone" dataKey="meteorito" stroke="#3b82f6" strokeWidth={2} name="Distancia (cm)" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}