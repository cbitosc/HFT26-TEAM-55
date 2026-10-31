import React from 'react';
import { TabType, HealthData } from '../types/navigation';
import { BackendStatusBadge } from './BackendStatusBadge';

interface SidebarProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  health: HealthData | null;
  loadingHealth: boolean;
  healthError: string | null;
  onRefreshHealth: () => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  health,
  loadingHealth,
  healthError,
  onRefreshHealth,
  isOpen,
  onToggle,
}) => {
  const navSections = [
    {
      group: 'NAVIGATION',
      items: [
        {
          id: 'overview' as TabType,
          label: 'Overview',
          badge: 'Hub',
          icon: (
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" rx="2" />
              <rect x="14" y="3" width="7" height="7" rx="2" />
              <rect x="14" y="14" width="7" height="7" rx="2" />
              <rect x="3" y="14" width="7" height="7" rx="2" />
            </svg>
          ),
        },
        {
          id: 'repository' as TabType,
          label: 'Repository',
          badge: 'ZIP / AST',
          icon: (
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              <line x1="12" y1="11" x2="12" y2="17" />
              <line x1="9" y1="14" x2="15" y2="14" />
            </svg>
          ),
        },
        {
          id: 'search' as TabType,
          label: 'Code Search',
          badge: 'FTS5 BM25',
          icon: (
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
              <path d="M11 8v6M8 11h6" opacity="0.6" />
            </svg>
          ),
        },
        {
          id: 'settings' as TabType,
          label: 'Settings',
          badge: 'Config',
          icon: (
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          ),
        },
      ],
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && <div className="sidebar-backdrop" onClick={onToggle} aria-hidden="true" />}

      <aside className={`sidebar-container ${isOpen ? 'sidebar-open' : ''}`}>
        {/* Brand Header */}
        <div className="sidebar-header">
          <div className="brand-lockup">
            <div className="brand-compass-emblem">
              <div className="compass-outer-ring" />
              <div className="compass-inner-core">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                  {/* Glowing 4-point compass needle */}
                  <polygon points="12,2 14.5,10 22,12 14.5,14 12,22 9.5,14 2,12 9.5,10" fill="url(#brandCompassGrad)" />
                  <circle cx="12" cy="12" r="2.5" fill="#f8fafc" />
                  <defs>
                    <linearGradient id="brandCompassGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#22d3ee" />
                      <stop offset="50%" stopColor="#60a5fa" />
                      <stop offset="100%" stopColor="#c084fc" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
            </div>

            <div className="brand-text-block">
              <span className="brand-title">CodeCompass</span>
              <span className="brand-subtitle-tag">LOCAL ARCHITECTURE</span>
            </div>
          </div>

          <button className="sidebar-close-btn" onClick={onToggle} aria-label="Close sidebar">
            ✕
          </button>
        </div>

        {/* Navigation Section */}
        <nav className="sidebar-nav">
          {navSections.map((sec, idx) => (
            <div key={idx} className="nav-group">
              <span className="nav-group-heading">{sec.group}</span>
              <div className="nav-items-stack">
                {sec.items.map((item) => {
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      className={`nav-item-btn ${isActive ? 'nav-item-active' : ''}`}
                      onClick={() => {
                        onTabChange(item.id);
                        if (isOpen) onToggle();
                      }}
                    >
                      <span className="nav-active-pill" />
                      <span className="nav-icon-wrap">{item.icon}</span>
                      <span className="nav-label">{item.label}</span>
                      {item.badge && (
                        <span className={`nav-micro-badge ${isActive ? 'badge-active' : ''}`}>
                          {item.badge}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* System Diagnostics & Backend Status Footer */}
        <div className="sidebar-footer">
          <div className="engine-status-card">
            <div className="engine-status-row">
              <div className="engine-indicator">
                <span className="engine-pulse" />
                <span className="engine-label">SQLite FTS5 Local</span>
              </div>
              <span className="engine-shield-icon" title="Zero repository cloud transmission">🛡️</span>
            </div>
            <p className="engine-subtext">Local-First • Privacy Conscious</p>
          </div>

          <BackendStatusBadge
            health={health}
            loading={loadingHealth}
            error={healthError}
            onRefresh={onRefreshHealth}
          />
        </div>
      </aside>
    </>
  );
};
