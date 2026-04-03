import api from './api';

export const parseFile = async (filename, loaderType, useOcr) => {
  const response = await api.post(`/knowledge/parse/${filename}`, {
    loader_type: loaderType,
    use_ocr: useOcr
  });
  return response.data;
};

export const uploadFile = async (formData) => {
  const response = await api.post('/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

export const deleteFile = async (filename) => {
  const response = await api.delete(`/knowledge/files/${filename}`);
  return response.data;
};

export const getFiles = async () => {
    const response = await api.get('/knowledge/files');
    return response.data;
};
