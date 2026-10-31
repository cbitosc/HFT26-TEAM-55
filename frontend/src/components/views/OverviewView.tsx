import React from 'react';
import { WelcomeHero } from '../WelcomeHero';
import { SearchBar } from '../SearchBar';
import { RepoUploadZone } from '../RepoUploadZone';
import { ArchitectureGrid } from '../ArchitectureGrid';
import { RepositoryMetadata } from '../../types/navigation';

interface OverviewViewProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSearchSubmit: (q: string) => void;
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onGitUrlSubmit?: (url: string) => void;
  repoStatus?: RepositoryMetadata | null;
  onNavigateToRepository?: () => void;
  onNavigateToSearch?: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  searchQuery,
  onSearchChange,
  onSearchSubmit,
  selectedFile,
  onFileSelect,
  onGitUrlSubmit,
  repoStatus,
  onNavigateToRepository,
  onNavigateToSearch,
}) => {
  return (
    <div className="tab-pane view-overview">
      <WelcomeHero
        hasRepository={Boolean(repoStatus)}
        onNavigateToSearch={onNavigateToSearch}
        onNavigateToRepository={onNavigateToRepository}
      />

      {repoStatus && (
        <div className="active-repo-banner" style={{ marginTop: '0.5rem' }}>
          <div className="active-repo-info">
            <span className="active-repo-badge">Active Indexed Codebase</span>
            <h3 className="active-repo-title">{repoStatus.name}</h3>
            <div className="active-repo-stats">
              <span><strong>{repoStatus.total_files}</strong> files</span>
              <span>•</span>
              <span><strong>{repoStatus.total_symbols}</strong> symbols</span>
              <span>•</span>
              <span><strong>{repoStatus.total_lines.toLocaleString()}</strong> lines</span>
            </div>
          </div>
          {onNavigateToSearch && (
            <button
              type="button"
              className="action-primary-btn"
              onClick={onNavigateToSearch}
            >
              Search Now →
            </button>
          )}
        </div>
      )}

      <SearchBar
        value={searchQuery}
        onChange={onSearchChange}
        onSubmit={onSearchSubmit}
      />

      <RepoUploadZone
        selectedFile={selectedFile}
        onFileSelect={onFileSelect}
        onGitUrlSubmit={onGitUrlSubmit}
      />

      {selectedFile && onNavigateToRepository && (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: '-0.5rem' }}>
          <button
            type="button"
            className="action-primary-btn"
            onClick={onNavigateToRepository}
          >
            Review & Index Archive in Repository Tab →
          </button>
        </div>
      )}

      <ArchitectureGrid />
    </div>
  );
};
