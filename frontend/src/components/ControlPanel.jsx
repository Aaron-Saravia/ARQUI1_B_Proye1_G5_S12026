import React, { useState } from 'react';
import { Crosshair, Shield, Send } from 'lucide-react';
import { naveAPI } from '../api/client';
import toast from 'react-hot-toast';

export default function ControlPanel() {
  const [angulo, setAngulo] = useState(90);
  const [mensaje, setMensaje] = useState("");
  const [estadoCompuerta, setEstadoCompuerta] = useState("Cerrada");

  const moverTorreta = async (nuevoAngulo) => {
    setAngulo(nuevoAngulo);
    try {
      await naveAPI.enviarComando('torreta', nuevoAngulo);
      toast.success(`Torreta movida a ${nuevoAngulo}°`, { id: 'torreta' }); // El id evita que se saturen las notificaciones
    } catch (e) {
      toast.error("Error al conectar con la nave");
    }
  };

  const toggleCompuerta = async () => {
    const accion = estadoCompuerta === "Cerrada" ? "Abrir" : "Cerrar";
    try {
      await naveAPI.enviarComando('compuerta', accion);
      setEstadoCompuerta(accion === "Abrir" ? "Abierta" : "Cerrada");
      toast.success(`Compuerta ${accion === "Abrir" ? "abierta" : "cerrada"}`);
    } catch (e) {
      toast.error("Fallo al accionar compuerta");
    }
  };

  const activarCamuflaje = async () => {
    try {
      await naveAPI.enviarComando('camuflaje', 'activar');
      toast.success("¡Modo Camuflaje Activado!", { icon: '🛡️' });
    } catch (e) {
      toast.error("Fallo al activar camuflaje");
    }
  };

  const enviarMensajeLCD = async () => {
    if (!mensaje.trim()) return;
    try {
      await naveAPI.enviarComando('lcd', mensaje);
      toast.success("Mensaje enviado a Sala de Control");
      setMensaje(""); 
    } catch (e) {
      toast.error("Error al enviar mensaje");
    }
  };

  return (
    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700">
      <h2 className="text-xl font-bold text-slate-200 mb-6 flex items-center gap-2">
        <Crosshair className="text-blue-400" /> Control de Actuadores
      </h2>
      
      <div className="space-y-6">
        <div>
          <label className="block text-slate-400 text-sm mb-2">Ángulo Torreta: {angulo}°</label>
          <input 
            type="range" min="0" max="360" 
            value={angulo} 
            onChange={(e) => setAngulo(e.target.value)}
            onMouseUp={(e) => moverTorreta(e.target.value)} 
            onTouchEnd={(e) => moverTorreta(e.target.value)}
            className="w-full cursor-pointer accent-blue-500" 
          />
          <div className="flex justify-between text-xs text-slate-500 mt-1">
            <span>0°</span><span>180°</span><span>360°</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <button onClick={toggleCompuerta} className={`${estadoCompuerta === 'Cerrada' ? 'bg-slate-700 hover:bg-slate-600' : 'bg-red-600 hover:bg-red-500'} py-3 rounded-lg font-semibold transition text-slate-200`}>
            {estadoCompuerta === 'Cerrada' ? 'Abrir Compuerta' : 'Cerrar Compuerta'}
          </button>
          <button onClick={activarCamuflaje} className="bg-indigo-600 hover:bg-indigo-500 py-3 rounded-lg font-semibold flex items-center justify-center gap-2 transition text-white">
            <Shield size={18} /> Camuflaje
          </button>
        </div>

        <div className="pt-4 border-t border-slate-700">
          <label className="block text-slate-400 text-sm mb-2">Mensaje a Sala de Control</label>
          <div className="flex gap-2">
            <input type="text" maxLength="64" value={mensaje} onChange={(e) => setMensaje(e.target.value)} placeholder="Ej. Peligro inminente..." className="flex-1 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500" />
            <button onClick={enviarMensajeLCD} className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded-lg transition text-white flex items-center justify-center">
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}