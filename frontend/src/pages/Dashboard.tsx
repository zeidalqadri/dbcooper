import { useEffect } from 'react';
import useSWR from 'swr';
import { getMigrationStatus, getAppliedMigrations } from '../services/api';
import type { MigrationStatus, AppliedMigration } from '../types';
import wsService from '../services/websocket';

export default function Dashboard() {
  const { data: status, mutate } = useSWR<MigrationStatus>(
    '/migrations/status',
    () => getMigrationStatus().then((res) => res.data)
  );

  const { data: recentMigrations } = useSWR<AppliedMigration[]>(
    '/migrations/applied',
    () => getAppliedMigrations(5).then((res) => res.data)
  );

  useEffect(() => {
    // Listen for WebSocket updates
    const handleStatusUpdate = (_data: any) => {
      mutate();
    };

    wsService.on('status_update', handleStatusUpdate);

    return () => {
      wsService.off('status_update', handleStatusUpdate);
    };
  }, [mutate]);

  if (!status) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status Hero Card */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">System Status</h2>
            <p className="text-sm text-gray-500 mt-1">
              Last updated: {new Date().toLocaleTimeString()}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            {status.is_compliant ? (
              <span className="badge badge-success text-lg px-4 py-2">
                ✓ Compliant
              </span>
            ) : (
              <span className="badge badge-error text-lg px-4 py-2">
                ✗ Violations Detected
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-6">
          <MetricCard
            label="Applied"
            value={status.applied_count}
            color="green"
          />
          <MetricCard
            label="Pending"
            value={status.pending_count}
            color={status.pending_count > 0 ? 'amber' : 'gray'}
          />
          <MetricCard
            label="Failed"
            value={status.failed_count}
            color={status.failed_count > 0 ? 'red' : 'gray'}
          />
          <MetricCard
            label="Total"
            value={status.applied_count + status.pending_count}
            color="blue"
          />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button className="btn-primary" disabled={status.pending_count === 0}>
            Apply Pending Migrations ({status.pending_count})
          </button>
          <button className="btn-secondary">Create New Migration</button>
          <button className="btn-secondary">Validate Compliance</button>
        </div>
      </div>

      {/* Recent Migrations */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Recent Migrations
        </h3>
        {recentMigrations && recentMigrations.length > 0 ? (
          <div className="space-y-3">
            {recentMigrations.map((migration) => (
              <MigrationItem key={migration.version} migration={migration} />
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No migrations applied yet</p>
        )}
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  const colorClasses: Record<string, string> = {
    green: 'bg-green-50 border-green-200 text-green-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
    red: 'bg-red-50 border-red-200 text-red-700',
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    gray: 'bg-gray-50 border-gray-200 text-gray-700',
  };

  return (
    <div className={`rounded-lg border p-4 ${colorClasses[color]}`}>
      <p className="text-sm font-medium opacity-75">{label}</p>
      <p className="text-3xl font-bold mt-2">{value}</p>
    </div>
  );
}

function MigrationItem({ migration }: { migration: AppliedMigration }) {
  return (
    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
      <div className="flex items-center space-x-4">
        <span className="text-2xl">
          {migration.status === 'success' ? '✓' : '✗'}
        </span>
        <div>
          <p className="font-medium text-gray-900">{migration.description}</p>
          <p className="text-sm text-gray-500">
            {migration.version} • Applied:{' '}
            {new Date(migration.applied_at).toLocaleString()} •{' '}
            {migration.execution_time?.toFixed(2)}s
          </p>
        </div>
      </div>
      <button className="text-primary-600 hover:text-primary-700 text-sm font-medium">
        View Details
      </button>
    </div>
  );
}
