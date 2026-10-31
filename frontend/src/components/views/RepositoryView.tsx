import React from 'react';
import { RepoUploadZone } from '../RepoUploadZone';
import { RepositoryMetadata } from '../../types/navigation';

interface RepositoryViewProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onGitUrlSubmit?: (url: string) => void;
  repoStatus: RepositoryMetadata | null;
  loadingRepo: boolean;
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
  uploadError: string | null;
  uploadSuccess: string | null;
  onNavigateToSearch: () => void;
}

export const RepositoryView: React.FC<RepositoryViewProps> = ({
  selectedFile,
  onFileSelect,
  onGitUrlSubmit,
  repoStatus,
  loadingRepo,
  onUpload,
  isUploading,
  uploadError,
  uploadSuccess,
  onNavigateToSearch,
}) => {
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (isoString: string): string => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="tab-pane view-repository">
      <div className="section-intro">
        <h2 className="section-title">Repository Ingestion</h2>
        <p className="section-subtitle">
          Upload a ZIP archive or connect a Git repository to generate the local SQLite FTS5 database index.
        </p>
      </div>

      {/* Active Indexed Repository Display */}
      {loadingRepo ? (
        <div className="active-repo-banner" style={{ opacity: 0.75 }}>
          <div className="active-repo-info">
            <span className="active-repo-badge">Checking Status</span>
            <span style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
              Querying local SQLite repository index...
            </span>
          </div>
        </div>
      ) : repoStatus ? (
        <div className="active-repo-banner">
          <div className="active-repo-info">
            <span className="active-repo-badge">Active In SQLite FTS5</span>
            <h3 className="active-repo-title">{repoStatus.name}</h3>
            <div className="active-repo-stats">
              <span><strong>{repoStatus.total_files}</strong> files</span>
              <span>•</span>
              <span><strong>{repoStatus.total_symbols}</strong> symbols</span>
              <span>•</span>
              <span><strong>{repoStatus.total_lines.toLocaleString()}</strong> lines of code</span>
              <span>•</span>
              <span>Indexed {formatDate(repoStatus.uploaded_at)}</span>
            </div>
          </div>

          <button
            type="button"
            className="action-primary-btn"
            onClick={onNavigateToSearch}
          >
            Search Codebase →
          </button>
        </div>
      ) : null}

      {/* Upload/Drop Zone */}
      <RepoUploadZone
        selectedFile={selectedFile}
        onFileSelect={onFileSelect}
        onGitUrlSubmit={onGitUrlSubmit}
      />

      {/* Alerts for upload feedback */}
      {uploadError && (
        <div className="alert-box alert-box-error">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{uploadError}</span>
        </div>
      )}

      {uploadSuccess && (
        <div className="alert-box alert-box-success">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          <span>{uploadSuccess}</span>
        </div>
      )}

      {/* Selected File Details & Trigger */}
      {selectedFile ? (
        <div className="repo-status-card">
          <div className="repo-status-header">
            <div className="repo-title-group">
              <span className="repo-badge-ready">Local File Ready For Ingestion</span>
              <h3 className="repo-file-heading">{selectedFile.name}</h3>
            </div>
            <button
              type="button"
              className="action-ghost-btn"
              onClick={() => onFileSelect(null)}
              disabled={isUploading}
            >
              Clear Selection
            </button>
          </div>

          <div className="repo-meta-grid">
            <div className="repo-meta-item">
              <span className="meta-label">Archive Size</span>
              <span className="meta-value">{formatFileSize(selectedFile.size)}</span>
            </div>
            <div className="repo-meta-item">
              <span className="meta-label">Target Engine</span>
              <span className="meta-value highlight-cyan">SQLite FTS5</span>
            </div>
            <div className="repo-meta-item">
              <span className="meta-label">Processing State</span>
              <span className={`meta-value ${isUploading ? 'highlight-cyan' : 'highlight-amber'}`}>
                {isUploading ? 'Extracting AST & Indexing FTS5...' : 'Ready to Upload & Index'}
              </span>
            </div>
          </div>

          <div className="upload-action-panel">
            <button
              type="button"
              className="upload-trigger-btn"
              onClick={() => onUpload(selectedFile)}
              disabled={isUploading}
            >
              {isUploading ? (
                <>
                  <span className="engine-pulse" style={{ width: 12, height: 12 }} />
                  <span>Validating & Indexing Archive...</span>
                </>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  <span>Upload & Index Codebase</span>
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        <div className="repo-info-card">
          <div className="info-card-header">
            <span className="info-card-badge">INSPECTION PIPELINE</span>
            <h3 className="info-card-title">Defensive In-Memory Parsing & Indexing</h3>
          </div>
          <p className="info-card-desc">
            When a repository archive is processed, CodeCompass unpacks it strictly in memory, executes security traversal checks, excludes build artifacts, extracts AST symbols with line spans, and commits to SQLite FTS5 in an atomic transaction.
          </p>
          <div className="pipeline-steps-row">
            <div className="pipeline-step">
              <span className="step-num">1</span>
              <span className="step-text">ZIP Security & Exclusion</span>
              <span className="step-sub">Filters node_modules, dist, .venv</span>
            </div>
            <div className="pipeline-step-arrow">→</div>
            <div className="pipeline-step">
              <span className="step-num">2</span>
              <span className="step-text">AST Symbol Visitor</span>
              <span className="step-sub">Classes, functions, line ranges</span>
            </div>
            <div className="pipeline-step-arrow">→</div>
            <div className="pipeline-step">
              <span className="step-num">3</span>
              <span className="step-text">SQLite FTS5 BM25</span>
              <span className="step-sub">Atomic virtual table commit</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
