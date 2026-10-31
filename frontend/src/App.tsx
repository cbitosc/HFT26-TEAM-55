import { useState, useEffect } from 'react';
import {
  TabType,
  HealthData,
  RepositoryMetadata,
  RepositoryStatusResponse,
  UploadResponse,
  SearchResponse,
  SearchResultItem,
} from './types/navigation';
import { GeometricBackground } from './components/GeometricBackground';
import { Sidebar } from './components/Sidebar';
import { OverviewView } from './components/views/OverviewView';
import { RepositoryView } from './components/views/RepositoryView';
import { SearchView } from './components/views/SearchView';
import { SettingsView } from './components/views/SettingsView';
import './App.css';

export function App() {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);

  // Health check state
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Repository state
  const [repoStatus, setRepoStatus] = useState<RepositoryMetadata | null>(null);
  const [loadingRepo, setLoadingRepo] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Search state
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [totalMatches, setTotalMatches] = useState<number>(0);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState<boolean>(false);

  const fetchHealth = async () => {
    setLoadingHealth(true);
    setHealthError(null);
    try {
      const res = await fetch('/api/health');
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: HealthData = await res.json();
      setHealth(data);
    } catch (err) {
      setHealthError(err instanceof Error ? err.message : 'Backend unreachable');
      setHealth(null);
    } finally {
      setLoadingHealth(false);
    }
  };

  const fetchRepositoryStatus = async () => {
    setLoadingRepo(true);
    try {
      const res = await fetch('/api/repository/status');
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: RepositoryStatusResponse = await res.json();
      setRepoStatus(data.has_repository ? data.repository : null);
    } catch {
      setRepoStatus(null);
    } finally {
      setLoadingRepo(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchRepositoryStatus();
  }, []);

  const handleUploadArchive = async (fileToUpload: File) => {
    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);
    try {
      const formData = new FormData();
      formData.append('file', fileToUpload);

      const res = await fetch('/api/repository/upload', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        try {
          const errData = await res.json();
          if (errData.detail) msg = errData.detail;
        } catch {
          // fallback to status code message
        }
        throw new Error(msg);
      }

      const data: UploadResponse = await res.json();
      const excludedNote = data.excluded_files_count
        ? ` (${data.excluded_files_count} build artifacts safely excluded)`
        : '';
      setUploadSuccess(
        `Indexed "${data.repo_name}" successfully: ${data.total_symbols} symbols, ${data.total_files} Python files, ${data.total_lines.toLocaleString()} lines${excludedNote}.`
      );
      setSelectedFile(null);
      await fetchRepositoryStatus();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Archive upload and indexing failed');
    } finally {
      setIsUploading(false);
    }
  };

  const executeSearch = async (queryText: string) => {
    const trimmed = queryText.trim();
    setSearchQuery(trimmed);
    if (!trimmed) {
      setSearchResults([]);
      setTotalMatches(0);
      setHasSearched(false);
      return;
    }

    setIsSearching(true);
    setSearchError(null);
    setHasSearched(true);

    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(trimmed)}&limit=30`);
      if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        try {
          const errData = await res.json();
          if (errData.detail) msg = errData.detail;
        } catch {
          // fallback
        }
        throw new Error(msg);
      }

      const data: SearchResponse = await res.json();
      setSearchResults(data.results || []);
      setTotalMatches(data.total_matches || 0);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'Search failed');
      setSearchResults([]);
      setTotalMatches(0);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchSubmit = (query: string) => {
    setActiveTab('search');
    executeSearch(query);
  };

  return (
    <div className="codecompass-root">
      {/* Background with floating triangles, polygons & parallax */}
      <GeometricBackground />

      {/* Main app layout wrapper */}
      <div className="layout-shell">
        {/* Modular Sidebar navigation */}
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          health={health}
          loadingHealth={loadingHealth}
          healthError={healthError}
          onRefreshHealth={fetchHealth}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen((prev) => !prev)}
        />

        {/* Primary view content area */}
        <div className="content-area">
          {/* Top header navigation bar */}
          <header className="topbar">
            <div className="topbar-left">
              <button
                className="mobile-menu-trigger"
                onClick={() => setSidebarOpen(true)}
                aria-label="Open sidebar"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="3" y1="12" x2="21" y2="12" />
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="18" x2="21" y2="18" />
                </svg>
              </button>

              <div className="breadcrumb-trail">
                <span className="breadcrumb-root">Workspace</span>
                <span className="breadcrumb-sep">/</span>
                <span className="breadcrumb-current">
                  {activeTab === 'overview' && 'Overview'}
                  {activeTab === 'repository' && 'Repository Management'}
                  {activeTab === 'search' && 'Code Search'}
                  {activeTab === 'settings' && 'Settings'}
                </span>
              </div>
            </div>

            <div className="topbar-right">
              {repoStatus ? (
                <div className="engine-pill repo-active-pill" onClick={() => setActiveTab('repository')} title="View repository details" role="button" tabIndex={0}>
                  <span className="engine-pulse" />
                  <span className="repo-pill-name">{repoStatus.name}</span>
                  <span className="repo-pill-stats">• {repoStatus.total_symbols} symbols</span>
                </div>
              ) : (
                <div className="engine-pill">
                  <span className="engine-pulse" />
                  <span>SQLite FTS5 Ready</span>
                </div>
              )}
            </div>
          </header>

          {/* Modular Dynamic Content Views */}
          <main className="main-viewport">
            {activeTab === 'overview' && (
              <OverviewView
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                onSearchSubmit={handleSearchSubmit}
                selectedFile={selectedFile}
                onFileSelect={setSelectedFile}
                repoStatus={repoStatus}
                onNavigateToRepository={() => setActiveTab('repository')}
                onNavigateToSearch={() => setActiveTab('search')}
              />
            )}

            {activeTab === 'repository' && (
              <RepositoryView
                selectedFile={selectedFile}
                onFileSelect={setSelectedFile}
                repoStatus={repoStatus}
                loadingRepo={loadingRepo}
                onUpload={handleUploadArchive}
                isUploading={isUploading}
                uploadError={uploadError}
                uploadSuccess={uploadSuccess}
                onNavigateToSearch={() => setActiveTab('search')}
              />
            )}

            {activeTab === 'search' && (
              <SearchView
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                onSearchSubmit={executeSearch}
                repoStatus={repoStatus}
                searchResults={searchResults}
                totalMatches={totalMatches}
                isSearching={isSearching}
                searchError={searchError}
                hasSearched={hasSearched}
                onNavigateToRepository={() => setActiveTab('repository')}
              />
            )}

            {activeTab === 'settings' && (
              <SettingsView
                health={health}
                loadingHealth={loadingHealth}
                healthError={healthError}
                onRefreshHealth={fetchHealth}
              />
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

export default App;
