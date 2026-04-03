import api from './api';

export const configEmbedding = async (
    filename,
    provider,
    modelName,
    embeddingMode = 'dense',
    vectorDimension = null
) => {
    const response = await api.post(`/knowledge/embedding/${filename}`, {
        embedding_provider: provider,
        embedding_model: modelName,
        embedding_mode: embeddingMode,
        vector_dimension: vectorDimension
    }, {
        timeout: 300000
    });
    return response.data;
};

export const getEmbeddingState = async (filename) => {
    const response = await api.get(`/knowledge/process/state/${filename}/embedding`);
    return response.data;
};

export const getEmbeddingPreview = async (filename) => {
    const response = await api.get(`/knowledge/embedding/preview/${filename}`);
    return response.data;
};
