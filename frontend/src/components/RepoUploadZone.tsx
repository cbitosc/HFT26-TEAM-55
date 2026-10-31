import React, { useState, useRef } from 'react';

interface RepoUploadZoneProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onGitUrlSubmit?: (url: string) => void;
}

export const RepoUploadZone: React.FC<RepoUploadZoneProps> = ({
  selectedFile,
  onFileSelect,
  onGitUrlSubmit,
}) => {
  const [activeMode, setActiveMode] = useState<'zip' | 'git'>('zip');
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [gitUrl, setGitUrl] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      onFileSelect(file);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      onFileSelect(file);
    }
  };

  const handleGitSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (gitUrl.trim() && onGitUrlSubmit) {
      onGitUrlSubmit(gitUrl.trim());
    }
  };

  const handleClearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    onFileSelect(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="upload-section-card">
      {/* Upload Header with Mode Selector */}
      <div className="upload-header">
        <div className="upload-header-titles">
          <div className="upload-title-row">
            <span className="upload-title-icon">⚡</span>
            <h2 className="upload-title">Connect Repository Archive</h2>
          </div>
          <p className="upload-subtitle">
            Upload a Python repository ZIP to parse AST symbols, extract exact line ranges, and index full-text search into local SQLite FTS5.
          </p>
        </div>

        <div className="upload-mode-toggle">
          <button
            type="button"
            className={`mode-btn ${activeMode === 'zip' ? 'mode-btn-active' : ''}`}
            onClick={() => setActiveMode('zip')}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>ZIP Archive</span>
          </button>
          <button
            type="button"
            className={`mode-btn ${activeMode === 'git' ? 'mode-btn-active' : ''}`}
            onClick={() => setActiveMode('git')}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <circle cx="12" cy="12" r="4" />
              <line x1="1.05" y1="12" x2="7" y2="12" />
              <line x1="17.01" y1="12" x2="22.96" y2="12" />
            </svg>
            <span>Git URL</span>
          </button>
        </div>
      </div>

      {activeMode === 'zip' ? (
        <>
          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,.tar.gz,.tar"
            className="visually-hidden-input"
            onChange={handleFileChange}
            id="repo-archive-input"
          />

          {/* Interactive Drop / Upload Zone */}
          <div
            className={`drop-zone-interactive ${isDragging ? 'drop-zone-active' : ''} ${selectedFile ? 'drop-zone-selected' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                fileInputRef.current?.click();
              }
            }}
          >
            <div className="drop-zone-glow" />

            {selectedFile ? (
              <div className="drop-zone-content selected-state">
                <div className="file-icon-box file-selected-icon">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="9" y1="15" x2="15" y2="15" />
                  </svg>
                </div>
                <div className="file-details-text">
                  <div className="file-name-row">
                    <span className="selected-filename">{selectedFile.name}</span>
                    <button
                      type="button"
                      className="clear-file-btn"
                      onClick={handleClearFile}
                      aria-label="Remove selected file"
                    >
                      ✕
                    </button>
                  </div>
                  <span className="selected-filesize">
                    {formatFileSize(selectedFile.size)} • Ready for in-memory AST extraction & FTS5 indexing
                  </span>
                </div>
              </div>
            ) : (
              <div className="drop-zone-content idle-state">
                <div className="upload-icon-ring">
                  <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <div className="upload-prompt-text">
                  <span className="upload-primary-text">
                    Drag & drop your repository archive, or <span className="highlight-text">browse files</span>
                  </span>
                  <span className="upload-secondary-text">
                    Supports .ZIP format up to 20 MiB • Up to 1,000 Python source files
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Security & Intelligent Exclusion Information Banner */}
          <div className="upload-safeguards-strip">
            <div className="safeguard-item">
              <span className="safeguard-icon">🛡️</span>
              <span><strong>Intelligent Exclusion:</strong> Automatically ignores node_modules/, dist/, build/, .venv/, and build bundles</span>
            </div>
            <div className="safeguard-item">
              <span className="safeguard-icon">🔒</span>
              <span><strong>Local & Air-Gapped:</strong> All parsing happens 100% in memory; zero disk traversal risks</span>
            </div>
          </div>
        </>
      ) : (
        /* Git URL Mode */
        <form onSubmit={handleGitSubmit} className="git-connect-form">
          <div className="git-input-wrap">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="git-url-icon">
              <circle cx="12" cy="12" r="4" />
              <line x1="1.05" y1="12" x2="7" y2="12" />
              <line x1="17.01" y1="12" x2="22.96" y2="12" />
            </svg>
            <input
              type="url"
              className="git-url-input"
              placeholder="https://github.com/organization/python-repository.git"
              value={gitUrl}
              onChange={(e) => setGitUrl(e.target.value)}
            />
            <button type="submit" className="git-submit-btn" disabled={!gitUrl.trim()}>
              Ingest Repo
            </button>
          </div>
          <span className="git-helper-text">
            For local-first operation, export a ZIP archive from your Git repository and upload via the ZIP tab.
          </span>
        </form>
      )}
    </div>
  );
};
