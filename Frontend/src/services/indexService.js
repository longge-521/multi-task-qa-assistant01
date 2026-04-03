import api from './api';

export const indexFile = async (filename, dbType, dbName) => {
    const response = await api.post(`/knowledge/index/${filename}`, {
        db_type: dbType,
        db_name: dbName
    }, {
        timeout: 300000
    });
    return response.data;
};

export const getStageStats = async () => {
    const response = await api.get('/knowledge/stages/stats');
    return response.data;
};

export const getChunks = async (filename) => {
    const response = await api.get(`/knowledge/files/${filename}/chunks`);
    return response.data;
};

export const getParsedState = async (filename) => {
    const response = await api.get(`/knowledge/process/state/${filename}/parsed`);
    return response.data;
};

export const searchKnowledge = async ({
    query,
    k = 5,
    dbType = 'FAISS',
    dbName = 'default',
    filenames = null,
    scoreThreshold = null,
    hybridAlpha = 0.7
}) => {
    const response = await api.post('/knowledge/search', {
        query,
        k,
        db_type: dbType,
        db_name: dbName,
        filenames,
        score_threshold: scoreThreshold,
        hybrid_alpha: hybridAlpha
    });
    return response.data;
};
