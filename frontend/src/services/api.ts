import axios from 'axios';
import type {
  MigrationStatus,
  AppliedMigration,
  PendingMigration,
  ComplianceReport,
  HealthResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health & Status
export const getHealth = () => api.get<HealthResponse>('/health');
export const getMigrationStatus = () => api.get<MigrationStatus>('/migrations/status');

// Migrations
export const getAppliedMigrations = (limit = 100) =>
  api.get<AppliedMigration[]>(`/migrations/applied?limit=${limit}`);

export const getPendingMigrations = () =>
  api.get<PendingMigration[]>('/migrations/pending');

export const getHistory = (limit = 50) =>
  api.get<AppliedMigration[]>(`/migrations/history?limit=${limit}`);

export const applyMigrations = (dryRun = false, verbose = false) =>
  api.post('/migrations/apply', { dry_run: dryRun, verbose });

export const rollbackMigrations = (count = 1, dryRun = false) =>
  api.post('/migrations/rollback', { count, dry_run: dryRun });

export const createMigration = (description: string, fileType: 'sql' | 'py' = 'sql') =>
  api.post('/migrations/create', { description, file_type: fileType });

export const uploadMigration = (file: File, description?: string) => {
  const formData = new FormData();
  formData.append('file', file);
  if (description) {
    formData.append('description', description);
  }
  return api.post('/migrations/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};

// Compliance
export const getComplianceReport = () => api.get<ComplianceReport>('/compliance/report');

export const getViolations = () => api.get('/compliance/violations');

export const validateCompliance = () => api.post<ComplianceReport>('/compliance/validate');

export const enforceCompliance = () => api.post('/compliance/enforce');

// Interceptor
export const enableInterceptor = () => api.post('/interceptor/enable');

export const disableInterceptor = () => api.post('/interceptor/disable');

export default api;
