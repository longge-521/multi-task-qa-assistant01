import api from './api';

export const fetchTools = async () => {
    const response = await api.get('/tools');
    return response.data.tools;
};

export const sendChatMessage = async (sessionId, query, model = 'deepseek-chat') => {
    const response = await api.post('/chat', {
        session_id: sessionId,
        query: query,
        model: model
    });
    return response.data;
};
