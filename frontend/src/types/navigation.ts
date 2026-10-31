export type TabType = 'overview' | 'repository' | 'search' | 'settings';

export interface HealthData {
  status: string;
  service: string;
  environment: string;
}

export interface ExampleQuery {
  id: string;
  query: string;
  tag: string;
}

export interface SearchResultItem {
  symbol_id: number;
  file_id: number;
  name: string;
  file_path: string;
  parent_scope: string | null;
  kind: string;
  start_line: number;
  end_line: number;
  docstring: string | null;
  snippet: string;
  highlight: string;
  rank: number;
}

export interface SearchResponse {
  query: string;
  total_matches: number;
  repository_name: string | null;
  results: SearchResultItem[];
}

export interface RepositoryMetadata {
  id: string;
  name: string;
  uploaded_at: string;
  total_files: number;
  total_symbols: number;
  total_lines: number;
}

export interface RepositoryStatusResponse {
  has_repository: boolean;
  repository: RepositoryMetadata | null;
}

export interface UploadResponse {
  status: string;
  repository_id: string;
  repo_name: string;
  total_files: number;
  total_symbols: number;
  total_lines: number;
  skipped_files_count: number;
  excluded_files_count?: number;
  skipped_files_sample?: string[];
  failed_files: Array<{ path: string; error: string; line: number | null }>;
}

export interface ExplainCodeRequest {
  symbol_id: number;
  query_context?: string;
}

export interface ExplainCodeResponse {
  status: string;
  model: string;
  symbol_id: number;
  symbol_name: string;
  kind: string;
  file_path: string;
  start_line: number;
  end_line: number;
  explanation: string;
  tokens_used?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface AIStatusResponse {
  configured: boolean;
  model: string;
  provider: string;
}
