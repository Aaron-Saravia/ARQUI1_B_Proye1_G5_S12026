import React, { useState } from 'react';
import { Crosshair, Shield, Send } from 'lucide-react';
import { naveAPI } from '../api/client';

export default function ControlPanel() {
  const [angulo, setAngulo] = useState(90);
  const [mensaje, setMensaje] = useState("");
  const [estadoCompuerta, setEstadoCompuerta] = useState("Cerrada");

  // Funciones reales que envían datos al backend
  const moverTorreta = async (nuevoAngulo) => {
    setAngulo(nuevoAngulo);
    console.log(`Enviando ángulo ${nuevoAngulo}° a la API...`);
    await naveAPI.enviarComando('torreta', nuevoAngulo);
  };

  const toggleCompuerta = async () => {
    const accion = estadoCompuerta === "Cerrada" ? "Abrir" : "Cerrar";
    console.log(`Enviando comando ${accion} compuerta a la API...`);
    await naveAPI.enviarComando('compuerta', accion);
    setEstadoCompuerta(accion === "Abrir" ? "Abierta" : "Cerrada");
  };

  const activarCamuflaje = async () => {
    console.log("Activando camuflaje en la API...");
    await naveAPI.enviarComando('camuflaje', 'activar');
    alert("¡Comando de camuflaje enviado a la nave!"); // Pequeño feedback visual
  };

  const enviarMensajeLCD = async () => {
    if (!mensaje.trim()) return;
    console.log(`Enviando mensaje LCD: ${mensaje}`);
    await naveAPI.enviarComando('lcd', mensaje);
    setMensaje(""); // Limpiar el input después de enviar
  };

  return (
    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
      <h2 className="text-xl font-bold text-slate-200 mb-6 flex items-center gap-2">
        <Crosshair className="text-blue-400" /> Control de Actuadores
      </h2>
      
      <div className="space-y-6">
        {/* Control de Torreta */}
        <div>
          <label className="block text-slate-400 text-sm mb-2">Ángulo Torreta: {angulo}°</label>
          <input 
            type="range" min="0" max="360" 
            value={angulo} 
            onChange={(e) => moverTorreta(e.target.value)} 
            className="w-full cursor-pointer accent-blue-500" 
          />
          <div className="flex justify-between text-xs text-slate-500 mt-1">
            <span>0°</span><span>180°</span><span>360°</span>
          </div>
        </div>

        {/* Botones de Compuertas y Camuflaje */}
        <div className="grid grid-cols-2 gap-4">
          <button 
            onClick={toggleCompuerta}
            className={`${estadoCompuerta === 'Cerrada' ? 'bg-slate-700 hover:bg-slate-600' : 'bg-red-600 hover:bg-red-500'} py-3 rounded-lg font-semibold transition text-slate-200`}
          >
            {estadoCompuerta === 'Cerrada' ? 'Abrir Compuerta' : 'Cerrar Compuerta'}
          </button>
          
          <button 
            onClick={activarCamuflaje}
            className="bg-indigo-600 hover:bg-indigo-500 py-3 rounded-lg font-semibold flex items-center justify-center gap-2 transition text-white"
          >
            <Shield size={18} /> Modo Camuflaje
          </button>
        </div>

        {/* Mensajes a LCD */}
        <div className="pt-4 border-t border-slate-700">
          <label className="block text-slate-400 text-sm mb-2">Mensaje a Sala de Control</label>
          <div className="flex gap-2">
            <input 
              type="text" 
              maxLength="64" 
              value={mensaje}
              onChange={(e) => setMensaje(e.target.value)}
              placeholder="Ej. Peligro inminente..." 
              className="flex-1 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500" 
            />
            <button 
              onClick={enviarMensajeLCD}
              className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg transition text-white flex items-center justify-center"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}