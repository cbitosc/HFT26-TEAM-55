import React, { useState, useEffect } from 'react';
import { HealthData, AIStatusResponse } from '../../types/navigation';

interface SettingsViewProps {
  health: HealthData | null;
  loadingHealth: boolean;
  healthError: string | null;
  onRefreshHealth: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  health,
  loadingHealth,
  healthError,
  onRefreshHealth,
}) => {
  const [aiStatus, setAiStatus] = useState<AIStatusResponse | null>(null);
  const [loadingAI, setLoadingAI] = useState<boolean>(true);

  const fetchAIStatus = async () => {
    setLoadingAI(true);
    try {
      const res = await fetch('/api/ai/status');
      if (res.ok) {
        const data: AIStatusResponse = await res.json();
        setAiStatus(data);
      }
    } catch {
      setAiStatus(null);
    } finally {
      setLoadingAI(false);
    }
  };

  useEffect(() => {
    fetchAIStatus();
  }, []);

  return (
    <div className="tab-pane view-settings">
      <div className="section-intro">
        <h2 className="section-title">Configuration & Health</h2>
        <p className="section-subtitle">
          Live backend connectivity diagnostics and Stage 5 & 6 system architecture status.
        </p>
      </div>

      <div className="settings-grid">
        {/* 1. Live Verified Backend Connection */}
        <div className="settings-card">
          <div className="card-badge-row">
            <h3 className="settings-card-title">Backend Connection</h3>
            <span className={`live-badge ${health ? 'badge-online' : 'badge-offline'}`}>
              {loadingHealth ? 'Pinging...' : health ? 'Live Verified' : 'Disconnected'}
            </span>
          </div>
          <p className="settings-card-desc">
            Real-time status of the FastAPI backend service connected via Vite development proxy.
          </p>
          <div className="settings-field">
            <span className="field-name">Health Status</span>
            <span className={`field-val ${health ? 'text-success' : 'text-danger'}`}>
              {loadingHealth ? 'Checking...' : health ? 'Healthy (200 OK)' : 'Unreachable'}
            </span>
          </div>
          <div className="settings-field">
            <span className="field-name">Proxy Endpoint</span>
            <span className="field-val">/api/health → 127.0.0.1:8000</span>
          </div>
          <div className="settings-field">
            <span className="field-name">Backend Service</span>
            <span className="field-val">{health?.service || 'unknown'}</span>
          </div>
          <div className="settings-field">
            <span className="field-name">Environment</span>
            <span className="field-val">{health?.environment || 'unknown'}</span>
          </div>
          {healthError && (
            <div className="settings-field">
              <span className="field-name">Connection Error</span>
              <span className="field-val text-danger">{healthError}</span>
            </div>
          )}
          <button
            className="settings-btn"
            onClick={onRefreshHealth}
            disabled={loadingHealth}
          >
            {loadingHealth ? 'Pinging...' : 'Re-test Backend Health'}
          </button>
        </div>

        {/* 2. SQLite FTS5 Storage Architecture (Stage 5 Active) */}
        <div className="settings-card">
          <div className="card-badge-row">
            <h3 className="settings-card-title">Storage Architecture</h3>
            <span className="live-badge badge-online">Stage 5 Active</span>
          </div>
          <p className="settings-card-desc">
            Local relational schema and full-text index with foreign key cascade support.
          </p>
          <div className="settings-field">
            <span className="field-name">Target Engine</span>
            <span className="field-val">SQLite 3 (FTS5 Virtual Tables)</span>
          </div>
          <div className="settings-field">
            <span className="field-name">Database Path</span>
            <span className="field-val">backend/data/codecompass.db</span>
          </div>
          <div className="settings-field">
            <span className="field-name">Ranking Function</span>
            <span className="field-val">BM25(symbols: 5.0, content: 1.5)</span>
          </div>
          <div className="settings-field">
            <span className="field-name">Foreign Keys</span>
            <span className="field-val text-success">PRAGMA foreign_keys = ON</span>
          </div>
        </div>

        {/* 3. Featherless AI Provider (Stage 6 Active) */}
        <div className="settings-card">
          <div className="card-badge-row">
            <h3 className="settings-card-title">AI Provider Architecture</h3>
            <span className={`live-badge ${aiStatus?.configured ? 'badge-online' : 'spec-badge'}`}>
              {loadingAI ? 'Checking...' : aiStatus?.configured ? 'Stage 6 Connected' : 'Unconfigured'}
            </span>
          </div>
          <p className="settings-card-desc">
            Defensive LLM onboarding explanations powered by Featherless AI with prompt injection protection.
          </p>
          <div className="settings-field">
            <span className="field-name">Provider</span>
            <span className="field-val">{aiStatus?.provider || 'Featherless AI'}</span>
          </div>
          <div className="settings-field">
            <span className="field-name">Model</span>
            <span className="field-val">{aiStatus?.model || 'Qwen/Qwen2.5-7B-Instruct'}</span>
          </div>
          <div className="settings-field">
            <span className="field-name">Credential Guard</span>
            <span className="field-val text-success">Backend Only (Zero Frontend Exposure)</span>
          </div>
          <div className="settings-field">
            <span className="field-name">Prompt Grounding</span>
            <span className="field-val text-success">Authoritative DB Line Range Citing</span>
          </div>
          <button
            className="settings-btn"
            onClick={fetchAIStatus}
            disabled={loadingAI}
          >
            {loadingAI ? 'Checking...' : 'Refresh AI Provider Status'}
          </button>
        </div>
      </div>
    </div>
  );
};
