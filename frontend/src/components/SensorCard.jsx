import React from 'react';

export default function SensorCard({ title, value, unit, icon, isCritical }) {
  return (
    <div className={`p-5 rounded-xl border ${isCritical ? 'bg-red-950/50 border-red-500' : 'bg-slate-800 border-slate-700'}`}>
      <div className="flex items-center gap-3 mb-3">
        {icon}
        <h3 className="text-slate-400 text-sm font-semibold uppercase tracking-wider">{title}</h3>
      </div>
      <div className="flex items-baseline gap-2">
        <span className={`text-4xl font-bold ${isCritical ? 'text-red-500' : 'text-emerald-400'}`}>
          {value}
        </span>
        <span className="text-slate-500 font-medium">{unit}</span>
      </div>
    </div>
  );
}