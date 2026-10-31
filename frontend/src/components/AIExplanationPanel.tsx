import React from 'react';
import { SafeMarkdown } from './SafeMarkdown';

interface AIExplanationPanelProps {
  symbolId: number;
  symbolName: string;
  filePath: string;
  startLine: number;
  endLine: number;
  state: 'idle' | 'loading' | 'success' | 'error';
  explanation: string | null;
  error: string | null;
  tokensUsed?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  } | null;
  isOpen: boolean;
  onExplainClick: () => void;
  onCollapseClick: () => void;
}

export const AIExplanationPanel: React.FC<AIExplanationPanelProps> = ({
  symbolName,
  filePath,
  startLine,
  endLine,
  state,
  explanation,
  error,
  tokensUsed,
  isOpen,
  onExplainClick,
  onCollapseClick,
}) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopyExplanation = async () => {
    if (explanation) {
      try {
        await navigator.clipboard.writeText(explanation);
        setCopied(true);
        setTimeout(() => setCopied(false), 2200);
      } catch {
        // fallback
      }
    }
  };
  return (
    <div className="ai-explanation-container">
      {/* Explicit User Action Trigger */}
      {!isOpen && state === 'idle' && (
        <button
          type="button"
          className="ai-trigger-btn"
          onClick={onExplainClick}
          aria-label={`Explain ${symbolName} with Featherless AI`}
        >
          <span className="sparkle-icon">✦</span>
          <span>Explain with AI</span>
        </button>
      )}

      {/* Expanded Panel */}
      {isOpen && (
        <div className="ai-panel">
          {/* Header */}
          <div className="ai-panel-header">
            <div className="ai-panel-title-group">
              <span className="ai-model-badge">
                <span className="ai-badge-pulse" />
                <span>Qwen 2.5 • Featherless AI</span>
              </span>
              <span className="ai-citation-pill">
                {filePath}:{startLine}–{endLine}
              </span>
              {tokensUsed && tokensUsed.total_tokens > 0 && (
                <span className="ai-tokens-pill" title="Token consumption">
                  {tokensUsed.total_tokens} tokens
                </span>
              )}
            </div>

            <div className="ai-panel-actions">
              {state === 'success' && explanation && (
                <button
                  type="button"
                  className={`ai-copy-btn ${copied ? 'copied' : ''}`}
                  onClick={handleCopyExplanation}
                  title="Copy explanation markdown"
                >
                  {copied ? '✓ Copied' : '⧉ Copy'}
                </button>
              )}
              {state === 'success' && (
                <button
                  type="button"
                  className="ai-re-explain-btn"
                  onClick={onExplainClick}
                  title="Re-run explanation"
                >
                  ↻ Re-explain
                </button>
              )}
              <button
                type="button"
                className="ai-close-btn"
                onClick={onCollapseClick}
                aria-label="Collapse AI explanation"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Body based on State */}
          {state === 'loading' && (
            <div className="ai-loading-box">
              <div className="engine-pulse" style={{ width: 14, height: 14 }} />
              <div className="ai-loading-text">
                <strong>Consulting Featherless AI (Qwen 2.5)...</strong>
                <span>Analyzing {filePath}:{startLine}–{endLine} with prompt injection protection.</span>
              </div>
            </div>
          )}

          {state === 'error' && (
            <div className="ai-error-box">
              <div className="ai-error-message">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>{error || 'Failed to generate explanation.'}</span>
              </div>
              <button
                type="button"
                className="ai-retry-btn"
                onClick={onExplainClick}
              >
                Retry
              </button>
            </div>
          )}

          {state === 'success' && explanation && (
            <div className="ai-content-box">
              <SafeMarkdown content={explanation} />
              <div className="ai-footer-note">
                <span className="shield-icon">🛡</span>
                <span>Grounded strictly in authoritative SQLite database metadata for {filePath}.</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
