import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 100000,
  headers: {
    'Content-Type': 'application/json'
  }
});

export const sendChatMessage = async (sessionId, query, model = 'deepseek-chat') => {
  const response = await api.post('/chat', {
    session_id: sessionId,
    query: query,
    model: model
  });
  return response.data;
};

export const fetchTools = async () => {
  const response = await api.get('/tools');
  return response.data.tools; // [{ name, description }, ...]
};
