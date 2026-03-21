import axios from 'axios';

// Cuando Aaron tenga el backend, solo cambian esta URL si es necesario
const API_URL = 'http://localhost:3000/api';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

export const naveAPI = {
  // Obtener historial para las gráficas
  getHistorialSensores: async () => {
    try {
      const response = await apiClient.get('/sensores/historial');
      return response.data;
    } catch (error) {
      console.error("Error al obtener historial:", error);
      return []; // Retorna arreglo vacío para que no explote el frontend
    }
  },

  // Obtener métricas para el panel de estadísticas
  getEstadisticas: async () => {
    try {
      const response = await apiClient.get('/estadisticas');
      return response.data;
    } catch (error) {
      console.error("Error al obtener estadísticas:", error);
      return null;
    }
  },

  // Enviar comando a la torreta, compuertas o LCD
  enviarComando: async (comando, valor) => {
    try {
      const response = await apiClient.post('/comandos', { comando, valor });
      return response.data;
    } catch (error) {
      console.error(`Error al enviar comando ${comando}:`, error);
      throw error;
    }
  }
};