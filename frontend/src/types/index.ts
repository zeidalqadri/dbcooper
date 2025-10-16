export interface MigrationStatus {
  applied_count: number;
  pending_count: number;
  failed_count: number;
  last_applied_version: string | null;
  last_applied_timestamp: string | null;
  is_compliant: boolean;
}

export interface AppliedMigration {
  version: string;
  description: string;
  applied_at: string;
  checksum: string;
  status: 'success' | 'failed' | 'pending';
  execution_time: number | null;
  error_message: string | null;
}

export interface PendingMigration {
  version: string;
  description: string;
  file_path: string;
  checksum: string;
  file_type: 'sql' | 'py';
}

export interface ComplianceViolation {
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  message: string;
  details: Record<string, any>;
}

export interface ComplianceReport {
  is_compliant: boolean;
  timestamp: string;
  violation_count: number;
  violations: ComplianceViolation[];
  recommendations: string[];
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  database_connected: boolean;
  message?: string;
}

export interface WebSocketMessage {
  type: string;
  data: any;
}
