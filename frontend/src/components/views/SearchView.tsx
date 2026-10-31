import React, { useState } from 'react';
import { SearchBar } from '../SearchBar';
import { AIExplanationPanel } from '../AIExplanationPanel';
import { SafeHighlight } from '../SafeHighlight';
import { SearchResultItem, RepositoryMetadata, ExplainCodeResponse } from '../../types/navigation';

interface SearchViewProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSearchSubmit: (q: string) => void;
  repoStatus: RepositoryMetadata | null;
  searchResults: SearchResultItem[];
  totalMatches: number;
  isSearching: boolean;
  searchError: string | null;
  hasSearched: boolean;
  onNavigateToRepository: () => void;
}

interface SymbolAIState {
  state: 'idle' | 'loading' | 'success' | 'error';
  explanation: string | null;
  error: string | null;
  tokensUsed: { prompt_tokens: number; completion_tokens: number; total_tokens: number } | null;
  isOpen: boolean;
}

export const SearchView: React.FC<SearchViewProps> = ({
  searchQuery,
  onSearchChange,
  onSearchSubmit,
  repoStatus,
  searchResults,
  totalMatches,
  isSearching,
  searchError,
  hasSearched,
  onNavigateToRepository,
}) => {
  // Independent per-card AI explanation state
  const [aiStates, setAiStates] = useState<Record<number, SymbolAIState>>({});
  // Optional client-side symbol kind filter: 'all' | 'function' | 'class' | 'method'
  const [kindFilter, setKindFilter] = useState<'all' | 'function' | 'class' | 'method'>('all');

  const filteredResults = searchResults.filter((item) => {
    if (kindFilter === 'all') return true;
    if (kindFilter === 'function') return item.kind.includes('function') && !item.kind.includes('method');
    if (kindFilter === 'class') return item.kind.includes('class');
    if (kindFilter === 'method') return item.kind.includes('method');
    return true;
  });

  const handleRequestExplanation = async (symbolId: number) => {
    // Explicit user action: start loading
    setAiStates((prev) => ({
      ...prev,
      [symbolId]: {
        state: 'loading',
        explanation: null,
        error: null,
        tokensUsed: null,
        isOpen: true,
      },
    }));

    try {
      // Authoritative requirement: Send ONLY symbol_id and optional query_context
      const res = await fetch('/api/ai/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol_id: symbolId,
          query_context: searchQuery.trim() || undefined,
        }),
      });

      if (!res.ok) {
        let errMessage = `HTTP ${res.status}`;
        try {
          const errData = await res.json();
          if (errData.detail) errMessage = errData.detail;
        } catch {
          // fallback
        }
        throw new Error(errMessage);
      }

      const data: ExplainCodeResponse = await res.json();
      setAiStates((prev) => ({
        ...prev,
        [symbolId]: {
          state: 'success',
          explanation: data.explanation,
          error: null,
          tokensUsed: data.tokens_used || null,
          isOpen: true,
        },
      }));
    } catch (err) {
      setAiStates((prev) => ({
        ...prev,
        [symbolId]: {
          state: 'error',
          explanation: null,
          error: err instanceof Error ? err.message : 'Failed to generate explanation.',
          tokensUsed: null,
          isOpen: true,
        },
      }));
    }
  };

  const handleCollapseExplanation = (symbolId: number) => {
    setAiStates((prev) => ({
      ...prev,
      [symbolId]: {
        ...prev[symbolId],
        isOpen: false,
      },
    }));
  };

  return (
    <div className="tab-pane view-search">
      <div className="section-intro">
        <h2 className="section-title">Code Search & Retrieval</h2>
        <p className="section-subtitle">
          Query code semantics or structural symbols ranked via SQLite FTS5 BM25.
        </p>
      </div>

      <SearchBar
        value={searchQuery}
        onChange={onSearchChange}
        onSubmit={onSearchSubmit}
      />

      {/* 1. No repository indexed yet */}
      {!repoStatus ? (
        <div className="search-empty-card">
          <div className="empty-icon-box">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
              <line x1="11" y1="8" x2="11" y2="14" strokeDasharray="2 2" />
            </svg>
          </div>
          <h3 className="empty-title">No Repository Connected</h3>
          <p className="empty-desc">
            To perform full-text code search and symbol extraction, connect a repository in the Repository tab.
            Once ingested into SQLite FTS5, live search results and line ranges will appear here.
          </p>
          <button
            type="button"
            className="action-primary-btn"
            onClick={onNavigateToRepository}
          >
            Connect a Repository
          </button>
        </div>
      ) : isSearching ? (
        /* 2. Loading State */
        <div className="search-loading-card">
          <div className="engine-pulse" style={{ width: 14, height: 14 }} />
          <p>Querying SQLite FTS5 virtual tables with BM25 ranking...</p>
        </div>
      ) : searchError ? (
        /* 3. Search Error State */
        <div className="alert-box alert-box-error">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{searchError}</span>
        </div>
      ) : hasSearched && searchResults.length === 0 ? (
        /* 4. Zero matches state */
        <div className="search-empty-card">
          <div className="empty-icon-box" style={{ borderColor: 'rgba(245, 158, 11, 0.4)', color: 'var(--color-amber-400)' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
              <line x1="8" y1="11" x2="14" y2="11" />
            </svg>
          </div>
          <h3 className="empty-title">No Matches Found</h3>
          <p className="empty-desc">
            No indexed code symbols matched your query <strong>"{searchQuery}"</strong> in repository <strong>{repoStatus.name}</strong>.
            Try searching for another function, class, or keyword.
          </p>
        </div>
      ) : hasSearched && searchResults.length > 0 ? (
        /* 5. Real Search Results List */
        <div className="search-results-section">
          <div className="search-results-summary">
            <div className="summary-text-group">
              <span>
                Found <strong className="summary-highlight">{totalMatches}</strong> matching {totalMatches === 1 ? 'symbol' : 'symbols'} in{' '}
                <strong className="summary-highlight">{repoStatus.name}</strong>
              </span>
              <span className="summary-engine">Ranked via SQLite FTS5 BM25</span>
            </div>

            {/* Quick Kind Filter Pills */}
            <div className="kind-filter-tabs">
              <button
                type="button"
                className={`kind-filter-pill ${kindFilter === 'all' ? 'active' : ''}`}
                onClick={() => setKindFilter('all')}
              >
                All ({searchResults.length})
              </button>
              <button
                type="button"
                className={`kind-filter-pill ${kindFilter === 'function' ? 'active' : ''}`}
                onClick={() => setKindFilter('function')}
              >
                Functions
              </button>
              <button
                type="button"
                className={`kind-filter-pill ${kindFilter === 'class' ? 'active' : ''}`}
                onClick={() => setKindFilter('class')}
              >
                Classes
              </button>
              <button
                type="button"
                className={`kind-filter-pill ${kindFilter === 'method' ? 'active' : ''}`}
                onClick={() => setKindFilter('method')}
              >
                Methods
              </button>
            </div>
          </div>

          <div className="search-results-list">
            {filteredResults.map((item) => {
              const kindClass = item.kind.includes('class')
                ? 'kind-class'
                : item.kind.includes('method')
                ? 'kind-method'
                : 'kind-function';

              const aiState = aiStates[item.symbol_id] || {
                state: 'idle',
                explanation: null,
                error: null,
                tokensUsed: null,
                isOpen: false,
              };

              return (
                <div key={`${item.file_id}-${item.symbol_id}`} className="search-result-card">
                  <div className="search-result-header">
                    <div className="symbol-identity">
                      <span className={`kind-badge ${kindClass}`}>{item.kind.replace('_', ' ')}</span>
                      <span className="symbol-name-text">{item.name}</span>
                      {item.parent_scope && (
                        <span className="symbol-parent-scope">(in {item.parent_scope})</span>
                      )}
                    </div>

                    <div className="result-meta-badges">
                      <span className="range-badge">
                        {item.file_path}:{item.start_line}–{item.end_line}
                      </span>
                      <span className="rank-badge" title="FTS5 BM25 relevance score">
                        BM25: {item.rank}
                      </span>
                    </div>
                  </div>

                  {item.docstring && (
                    <div className="result-docstring-box">
                      {item.docstring}
                    </div>
                  )}

                  <div className="result-snippet-box">
                    <pre className="result-snippet-code">
                      <SafeHighlight text={item.highlight || item.snippet} />
                    </pre>
                  </div>

                  {/* AI Explanation Section (Triggered Only on User Click) */}
                  <AIExplanationPanel
                    symbolId={item.symbol_id}
                    symbolName={item.name}
                    filePath={item.file_path}
                    startLine={item.start_line}
                    endLine={item.end_line}
                    state={aiState.state}
                    explanation={aiState.explanation}
                    error={aiState.error}
                    tokensUsed={aiState.tokensUsed}
                    isOpen={aiState.isOpen}
                    onExplainClick={() => handleRequestExplanation(item.symbol_id)}
                    onCollapseClick={() => handleCollapseExplanation(item.symbol_id)}
                  />
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* 6. Initial Prompt State when repository is connected */
        <div className="search-empty-card">
          <div className="empty-icon-box">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h3 className="empty-title">Ready to Search Codebase</h3>
          <p className="empty-desc">
            Active repository <strong>{repoStatus.name}</strong> is indexed ({repoStatus.total_symbols} symbols across {repoStatus.total_files} files).
            Enter a query above or click a suggested query to inspect symbols, line ranges, and request AI onboarding explanations.
          </p>
        </div>
      )}
    </div>
  );
};
