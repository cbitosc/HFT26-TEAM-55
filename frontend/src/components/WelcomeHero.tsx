import React from 'react';

interface WelcomeHeroProps {
  onNavigateToSearch?: () => void;
  onNavigateToRepository?: () => void;
  hasRepository?: boolean;
}

export const WelcomeHero: React.FC<WelcomeHeroProps> = ({
  onNavigateToSearch,
  onNavigateToRepository,
  hasRepository,
}) => {
  return (
    <section className="welcome-hero">
      <div className="hero-eyebrow">
        <span className="eyebrow-spark">✦</span>
        <span className="eyebrow-text">LOCAL-FIRST CODE INTELLIGENCE</span>
        <span className="eyebrow-pill">Zero Repository Leakage</span>
      </div>

      <h1 className="hero-heading">
        Navigate Any Python Codebase <span className="hero-gradient-text">with Precision.</span>
      </h1>

      <p className="hero-subtext">
        CodeCompass parses syntax trees in memory and indexes symbols into SQLite FTS5 with BM25 ranking.
        Explore functions, classes, and call structures in sub-milliseconds—then consult Featherless AI
        for grounded architectural explanations with zero secret exposure.
      </p>

      <div className="hero-actions-row">
        {hasRepository ? (
          <button
            type="button"
            className="hero-primary-btn"
            onClick={onNavigateToSearch}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <span>Search Active Codebase</span>
          </button>
        ) : (
          <button
            type="button"
            className="hero-primary-btn"
            onClick={onNavigateToRepository}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>Upload Repository Archive</span>
          </button>
        )}

        {hasRepository && (
          <button
            type="button"
            className="hero-secondary-btn"
            onClick={onNavigateToRepository}
          >
            <span>Manage Repository</span>
            <span className="btn-arrow">→</span>
          </button>
        )}
      </div>

      <div className="hero-tags-row">
        <div className="hero-tag">
          <span className="tag-dot cyan" />
          <span>SQLite FTS5 Full-Text Search</span>
        </div>
        <div className="hero-tag">
          <span className="tag-dot violet" />
          <span>AST Scope & Line Parsing</span>
        </div>
        <div className="hero-tag">
          <span className="tag-dot blue" />
          <span>Qwen 2.5 • Featherless AI</span>
        </div>
        <div className="hero-tag">
          <span className="tag-dot emerald" />
          <span>100% In-Memory Validation</span>
        </div>
      </div>
    </section>
  );
};
