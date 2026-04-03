import api from './api';

export const chunkFile = async (filename, strategy, chunkSize, overlap) => {
    const response = await api.post(`/knowledge/chunk/${filename}`, {
        strategy: strategy,
        chunk_size: chunkSize,
        chunk_overlap: overlap
    });
    return response.data;
};

export const getChunkState = async (filename) => {
    const response = await api.get(`/knowledge/process/state/${filename}/chunked`);
    return response.data;
};
