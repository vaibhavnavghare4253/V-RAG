export interface Organization {
  id: string;
  name: string;
  tier: string;
  created_at: string;
}

export interface User {
  id: string;
  organization_id: string;
  email: string;
  full_name?: string;
  role: 'admin' | 'member' | 'viewer';
  is_active: boolean;
  created_at: string;
  organization?: Organization;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type DocumentStatus = 'pending' | 'processing' | 'indexed' | 'failed';
export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface IngestionJob {
  id: string;
  document_id: string;
  status: JobStatus;
  current_stage: number;
  total_stages: number;
  stage_name: string;
  error_message?: string;
  created_at: string;
}

export interface DocumentItem {
  id: string;
  organization_id: string;
  filename: string;
  file_size_bytes: number;
  page_count: number;
  status: DocumentStatus;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  job_id: string;
  filename: string;
  file_size_bytes: number;
  status: DocumentStatus;
  message: string;
}

export interface PaginatedDocuments {
  items: DocumentItem[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface Citation {
  document_id: string;
  document_name: string;
  page_number: number;
  asset_id?: string;
  asset_type?: string;
  bounding_box?: Record<string, number>;
  snippet: string;
}

export interface QueryResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  decision: string;
  uncertainty_score: number;
  citations: Citation[];
  latency_ms: number;
  diagnostics?: Record<string, unknown>;
}

export interface Conversation {
  id: string;
  user_id: string;
  document_id?: string;
  title: string;
  created_at: string;
  updated_at: string;
}

