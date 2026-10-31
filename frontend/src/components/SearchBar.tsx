import React, { useRef, useEffect } from 'react';
import { ExampleQuery } from '../types/navigation';

interface SearchBarProps {
  value: string;
  onChange: (val: string) => void;
  onSubmit: (query: string) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({ value, onChange, onSubmit }) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const exampleQueries: ExampleQuery[] = [
    {
      id: 'auth',
      query: 'Where is authentication and session handling defined?',
      tag: 'Auth & Security',
    },
    {
      id: 'entry',
      query: 'Find entrypoints for new contributor good-first-issues',
      tag: 'Onboarding',
    },
    {
      id: 'db',
      query: 'Which modules manage database schemas and SQLite models?',
      tag: 'Database',
    },
    {
      id: 'async',
      query: 'How do background workers and async tasks execute?',
      tag: 'Architecture',
    },
  ];

  // Global keyboard shortcut: Cmd+K / Ctrl+K focuses the search input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim()) {
      onSubmit(value.trim());
    }
  };

  const handleChipClick = (queryText: string) => {
    onChange(queryText);
    inputRef.current?.focus();
  };

  return (
    <div className="search-section">
      <form className="search-form" onSubmit={handleSubmit}>
        <div className="search-input-shell">
          <div className="search-icon-prefix">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>

          <input
            ref={inputRef}
            type="text"
            className="search-input"
            placeholder="Ask anything about the codebase... (e.g. 'Where is routing configured?')"
            value={value}
            onChange={(e) => onChange(e.target.value)}
          />

          {value && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={() => onChange('')}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}

          <div className="search-shortcut-badge">
            <kbd className="kbd-key">⌘</kbd>
            <kbd className="kbd-key">K</kbd>
          </div>

          <button type="submit" className="search-submit-btn">
            <span>Search</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </form>

      {/* Suggested Example Queries */}
      <div className="search-examples">
        <span className="examples-label">Suggested queries:</span>
        <div className="examples-chips">
          {exampleQueries.map((item) => (
            <button
              key={item.id}
              type="button"
              className="query-chip"
              onClick={() => handleChipClick(item.query)}
            >
              <span className="chip-tag">{item.tag}</span>
              <span className="chip-text">"{item.query}"</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
