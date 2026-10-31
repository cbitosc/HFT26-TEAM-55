import React from 'react';

export const ArchitectureGrid: React.FC = () => {
  const cards = [
    {
      title: 'Local SQLite FTS5 Engine',
      category: 'SEARCH & RETRIEVAL',
      desc: 'Sub-millisecond full-text code search powered by native SQLite virtual tables. Weighted BM25 scoring across symbol names, scopes, and snippets with 100% offline persistence.',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="12 2 2 7 12 12 22 7 12 2" />
          <polyline points="2 17 12 22 22 17" />
          <polyline points="2 12 12 17 22 12" />
        </svg>
      ),
      glowClass: 'glow-cyan',
      badge: 'BM25 Scored',
    },
    {
      title: 'In-Memory Defensive Ingestion',
      category: 'PIPELINE SECURITY',
      desc: 'Enforces strict archive size boundaries and path traversal rejection entirely in memory. Automatically filters build artifacts (dist/, node_modules/, .venv/) before AST extraction.',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M9 12l2 2 4-4" />
        </svg>
      ),
      glowClass: 'glow-emerald',
      badge: 'Air-Gapped Limits',
    },
    {
      title: 'Grounded AI Explanations',
      category: 'INTELLIGENCE',
      desc: 'Featherless AI (Qwen 2.5) generates structured contributor guides. Authoritative database lookup by symbol ID ensures only isolated target snippets are analyzed.',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4M12 8h.01" />
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
        </svg>
      ),
      glowClass: 'glow-violet',
      badge: 'Qwen 2.5',
    },
    {
      title: 'Zero-Trust Markdown & Snippets',
      category: 'INTERFACE HYGIENE',
      desc: 'Custom FTS5 highlight tokenizer and pure React Markdown engine completely eliminate dangerouslySetInnerHTML, neutralizing script injection and XSS vectors.',
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      ),
      glowClass: 'glow-blue',
      badge: 'XSS Immune',
    },
  ];

  return (
    <section className="architecture-grid">
      <div className="grid-header-row">
        <div className="grid-header-title-block">
          <span className="grid-header-eyebrow">SYSTEM ARCHITECTURE</span>
          <h2 className="grid-header-heading">Built for Speed, Privacy, and Precision.</h2>
        </div>
      </div>

      <div className="arch-cards-layout">
        {cards.map((card, idx) => (
          <div key={idx} className={`arch-card ${card.glowClass}`}>
            <div className="arch-card-top">
              <div className="arch-card-icon">{card.icon}</div>
              <span className="arch-card-badge">{card.badge}</span>
            </div>
            <span className="arch-card-category">{card.category}</span>
            <h3 className="arch-title">{card.title}</h3>
            <p className="arch-desc">{card.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
};
