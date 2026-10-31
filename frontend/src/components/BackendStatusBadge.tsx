import React from 'react';
import { HealthData } from '../types/navigation';

interface BackendStatusBadgeProps {
  health: HealthData | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const BackendStatusBadge: React.FC<BackendStatusBadgeProps> = ({
  health,
  loading,
  error,
  onRefresh,
}) => {
  return (
    <div className="backend-status-card" title={error || (health ? `Service: ${health.service} (${health.environment})` : 'Connecting...')}>
      <div className="backend-status-info">
        <span className={`status-dot ${loading ? 'dot-checking' : health ? 'dot-online' : 'dot-offline'}`} />
        <div className="status-text-group">
          <span className="status-label">FastAPI Backend</span>
          <span className="status-sub">
            {loading ? 'Connecting...' : health ? 'Online (Port 8000)' : 'Offline'}
          </span>
        </div>
      </div>
      <button
        className="refresh-btn"
        onClick={onRefresh}
        disabled={loading}
        aria-label="Refresh backend status"
        title="Check backend health"
      >
        <svg
          className={`refresh-icon ${loading ? 'spinning' : ''}`}
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
        </svg>
      </button>
    </div>
  );
};
