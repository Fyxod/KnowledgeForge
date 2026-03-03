import { API_URL } from '../../config';

// Types
export interface User {
  userId: string;
  name: string;
  email: string;
  threads: Record<string, Thread>;
}

export interface ThreadInstruction {
  id: string;
  text: string;
  selected: boolean;
}

export interface Thread {
  thread_name: string;
  createdAt: string;
  updatedAt: string;
  documents: Document[];
  chats: Chat[];
  instructions?: ThreadInstruction[];
}

export interface Document {
  docId: string;
  title: string;
  type: string;
  time_uploaded: string;
  file_name: string;
}

export interface Chat {
  type: 'user' | 'agent';
  content: string;
  timestamp: string;
  // Enhanced metadata fields from Phase 1/2 backend
  confidence_score?: string | number; // Backend sends "high"/"medium"/"low"
  thought_process?: string; // For Deep Reasoning output
  sources?: {
    documents_used: Array<{
      title: string;
      document_id: string;
      page_no: number;
    }>;
    web_used: Array<{
      title: string;
      url: string;
      favicon: string | null;
    }>;
  };
}

export interface DeleteChatResponse {
  status: string;
  message: string;
  thread_id: string;
  deleted_index: number;
  chats: Chat[];
}

export interface ClearChatsResponse {
  status: string;
  message: string;
  thread_id: string;
  chats: Chat[];
}

export interface DeleteDocumentResponse {
  status: string;
  message: string;
  thread_id: string;
  deleted_doc_id: string;
  documents: Document[];
}

export interface AddExistingDocumentResponse {
  status: string;
  message: string;
  thread_id: string;
  document: Document;
}

export interface LoginResponse {
  status: string;
  message: string;
  user: User;
  token: string;
}

export interface UploadResponse {
  status: string;
  message: string;
  thread_id: string;
  documents: Document[];
}

export interface QueryResponse {
  thread_id: string;
  user_id: string;
  question: string;
  answer: string;
  use_self_knowledge?: boolean;
  // Enhanced metadata fields
  confidence_score?: string | number;
  thought_process?: string;
  // Original shape (legacy)
  docs_used?: Array<{
    title: string;
    document_id: string;
    page_no: number;
  }>;
  web_used?: Array<{
    title: string;
    url: string;
    favicon: string | null;
  }>;
  // Newer shape returned by backend under a `sources` object
  sources?: {
    documents_used?: Array<{
      title: string;
      document_id: string;
      page_no: number;
    }>;
    web_used?: Array<{
      title: string;
      url: string;
      favicon: string | null;
    }>;
  };
}

// Mind map types
export interface MindMapNode {
  id: string;
  title: string;
  description?: string | null;
  parent_id?: string | null;
  children: MindMapNode[];
}

export interface GlobalMindMap {
  user_id: string;
  thread_id: string;
  roots: MindMapNode[];
}

export interface MindMapResponse {
  mind_map: boolean;
  status?: boolean; // only present when mind_map is true
  message: string;
  data?: GlobalMindMap; // present when mind_map && status
}

export interface SummaryResponse {
  status?: boolean;
  summary?: string;
  message?: string;
  error?: string;
  failed?: boolean;
}

// Roadmap types (mirror backend Pydantic models)
export interface VisionAndEndGoal {
  description: string;
  success_criteria: string[];
}

export interface SWOT {
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
}

export interface CurrentBaseline {
  summary: string;
  swot: SWOT;
}

export interface StrategicPillar {
  pillar_name: string;
  description: string;
}

export interface PhasedRoadmapItem {
  phase: string;
  time_frame: string;
  key_objectives: string[];
  key_initiatives: string[];
  expected_outcomes: string[];
}

export interface EnablersAndDependencies {
  technologies: string[];
  skills_and_resources: string[];
  stakeholders: string[];
}

export interface RiskAndMitigation {
  risk: string;
  mitigation_strategy: string;
}

export interface KeyMetricsAndMilestone {
  year_or_phase: string;
  metrics: string[];
}

export interface LLMInferredAddition {
  section_title: string;
  content: string;
}

export interface StrategicRoadmapLLMOutput {
  roadmap_title: string;
  vision_and_end_goal: VisionAndEndGoal;
  current_baseline: CurrentBaseline;
  strategic_pillars: StrategicPillar[];
  phased_roadmap: PhasedRoadmapItem[];
  enablers_and_dependencies: EnablersAndDependencies;
  risks_and_mitigation: RiskAndMitigation[];
  key_metrics_and_milestones: KeyMetricsAndMilestone[];
  future_opportunities: string[];
  llm_inferred_additions: LLMInferredAddition[];
}

export interface StrategicRoadmapResponse {
  status?: boolean;
  strategic_roadmap?: StrategicRoadmapLLMOutput;
  message?: string;
  error?: string;
  failed?: boolean;
}

// Technical Roadmap types (mirror backend Pydantic models provided)
export interface OverallVision {
  goal: string;
  success_metrics: string[];
}

export interface CurrentStateAnalysis {
  summary: string;
  key_challenges: string[];
  existing_capabilities: string[];
}

export interface TechnologyDomain {
  domain_name: string;
  description: string;
}

export interface Initiative {
  initiative: string;
  objective: string;
  expected_outcome: string;
}

export interface PhasedRoadmapPhase {
  time_frame: string;
  focus_areas: string[];
  key_initiatives: Initiative[];
  dependencies: string[];
}

export interface PhasedRoadmap {
  short_term: PhasedRoadmapPhase;
  mid_term: PhasedRoadmapPhase;
  long_term: PhasedRoadmapPhase;
}

export interface KeyTechnologyEnabler {
  enabler: string;
  impact: string;
}

export interface RiskAndMitigationItem {
  risk: string;
  mitigation: string;
}

export interface InnovationOpportunity {
  idea: string;
  description: string;
  maturity_level: string;
}

export interface TabularSummaryRow {
  time_frame: string;
  key_points: string[];
}

export interface LLMInferredAddition {
  section_title: string;
  content: string;
}

export interface TechnicalRoadmapLLMOutput {
  roadmap_title: string;
  overall_vision: OverallVision;
  current_state_analysis: CurrentStateAnalysis;
  technology_domains: TechnologyDomain[];
  phased_roadmap: PhasedRoadmap;
  key_technology_enablers: KeyTechnologyEnabler[];
  risks_and_mitigations: RiskAndMitigationItem[];
  innovation_opportunities: InnovationOpportunity[];
  tabular_summary: TabularSummaryRow[];
  llm_inferred_additions?: LLMInferredAddition[] | null;
}

export interface TechnicalRoadmapResponse {
  status?: boolean;
  technical_roadmap?: TechnicalRoadmapLLMOutput;
  message?: string;
  error?: string;
  failed?: boolean;
}

// Insights types (mirror backend Pydantic models)
export interface DocumentSummary {
  title: string;
  purpose: string;
  key_themes: string[];
}

export interface KeyDiscussionPoint {
  topic: string;
  details: string;
}

export interface StrengthItem {
  aspect: string;
  evidence_or_example: string;
}

export interface ImprovementOrMissingArea {
  gap: string;
  suggested_improvement: string;
}

export interface FutureConsideration {
  focus_area: string;
  recommendation: string;
}

export interface InnovationAspect {
  innovation_title: string;
  description: string;
  potential_impact: string;
}

export interface PseudocodeOrTechnicalOutline {
  section?: string | null;
  pseudocode?: string | null;
}

export interface InsightsLLMOutput {
  document_summary: DocumentSummary;
  key_discussion_points: KeyDiscussionPoint[];
  strengths: StrengthItem[];
  improvement_or_missing_areas: ImprovementOrMissingArea[];
  future_considerations: FutureConsideration[];
  innovation_aspects: InnovationAspect[];
  pseudocode_or_technical_outline?: PseudocodeOrTechnicalOutline[] | null;
  llm_inferred_additions?: LLMInferredAddition[] | null;
}

export interface InsightsResponse {
  status?: boolean;
  insights?: InsightsLLMOutput;
  message?: string;
  error?: string;
  failed?: boolean;
}

// Strategic Analysis types (mirror backend Pydantic models)
export interface StrategicIntent {
  vision_statement: string;
  stated_objectives: string[];
  implicit_aspirations: string[];
}

export interface StrategicPositioning {
  current_position: string;
  target_position: string;
  competitive_landscape: string;
}

export interface StrategicTheme {
  theme: string;
  description: string;
  evidence_from_document: string;
}

export interface StakeholderInsight {
  stakeholder: string;
  role_or_interest: string;
  influence_level: string;
}

export interface ResourceAndCapability {
  resource: string;
  current_state: string;
  strategic_relevance: string;
}

export interface IdentifiedRisk {
  risk: string;
  severity: string;
  context: string;
}

export interface ForwardLookingAssessment {
  opportunities: string[];
  recommended_next_steps: string[];
  potential_challenges: string[];
  overall_assessment: string;
}

export interface StrategicAnalysisLLMOutput {
  analysis_title: string;
  executive_overview: string;
  strategic_intent: StrategicIntent;
  strategic_positioning: StrategicPositioning;
  key_strategic_themes: StrategicTheme[];
  stakeholder_insights: StakeholderInsight[];
  resources_and_capabilities: ResourceAndCapability[];
  identified_risks: IdentifiedRisk[];
  strategic_gaps_and_observations: string[];
  forward_looking_assessment: ForwardLookingAssessment;
  llm_inferred_additions?: LLMInferredAddition[] | null;
}

export interface StrategicAnalysisResponse {
  status?: boolean;
  strategic_analysis?: StrategicAnalysisLLMOutput;
  message?: string;
  error?: string;
  failed?: boolean;
}

// Technical Analysis types (mirror backend Pydantic models)
export interface TechnicalScope {
  domains_covered: string[];
  technology_stack: string[];
  architecture_overview: string;
}

export interface TechnicalDecision {
  decision: string;
  rationale: string;
  implications: string;
}

export interface TechnicalStrength {
  aspect: string;
  evidence: string;
}

export interface TechnicalConcern {
  concern: string;
  impact: string;
  evidence: string;
}

export interface TechnicalInnovation {
  element: string;
  description: string;
  maturity: string;
}

export interface TechnicalAspirations {
  stated_goals: string[];
  implied_direction: string;
  alignment_assessment: string;
}

export interface ImplementationReadiness {
  ready_components: string[];
  gaps_to_address: string[];
  dependencies: string[];
}

export interface TechnicalForwardAssessment {
  scalability_outlook: string;
  technology_evolution: string;
  recommended_focus_areas: string[];
  overall_assessment: string;
}

export interface TechnicalAnalysisLLMOutput {
  analysis_title: string;
  executive_overview: string;
  technical_scope: TechnicalScope;
  technical_decisions: TechnicalDecision[];
  technical_strengths: TechnicalStrength[];
  technical_concerns: TechnicalConcern[];
  innovation_elements: TechnicalInnovation[];
  technical_aspirations: TechnicalAspirations;
  implementation_readiness: ImplementationReadiness;
  forward_looking_assessment: TechnicalForwardAssessment;
  llm_inferred_additions?: LLMInferredAddition[] | null;
}

export interface TechnicalAnalysisResponse {
  status?: boolean;
  technical_analysis?: TechnicalAnalysisLLMOutput;
  message?: string;
  error?: string;
  failed?: boolean;
}

// ── Document Creator types ──

export type DocumentType =
  | 'presentation'
  | 'executive_summary'
  | 'technical_report'
  | 'research_brief'
  | 'project_proposal'
  | 'comparison_report';

export type AudienceType = 'executive' | 'technical' | 'general';
export type ToneType = 'formal' | 'professional' | 'conversational' | 'academic';
export type ContentFormat = 'prose' | 'bullets' | 'table' | 'mixed';
export type SectionStatus =
  | 'pending'
  | 'generating'
  | 'generated'
  | 'approved'
  | 'needs_revision'
  | 'failed';
export type ExportFormat = 'pptx' | 'docx' | 'pdf';

export interface DocumentCreatorConfig {
  document_type: DocumentType;
  audience: AudienceType;
  tone: ToneType;
  source_document_ids?: string[] | null;
  custom_instructions?: string | null;
  length_preference?: string;
}

export interface OutlineSectionSpec {
  section_id: string;
  title: string;
  description: string;
  content_format: ContentFormat;
  heading_level: number;
  guidance?: string | null;
  source_document_ids: string[];
  order: number;
}

export interface SectionVersion {
  version_id: string;
  content: string;
  bullet_points?: string[] | null;
  table_data?: { headers: string[]; rows: string[][] } | null;
  speaker_notes?: string | null;
  key_takeaway?: string | null;
  sources_used: Array<{ document_id: string; title: string; page_no: number }>;
  feedback_used?: string | null;
  generated_at: string;
}

export interface SectionState {
  spec: OutlineSectionSpec;
  status: SectionStatus;
  versions: SectionVersion[];
  selected_version_index: number;
}

export interface DocumentCreatorOutlineResponse {
  status: string;
  tracking_id?: string;
  doc_gen_id?: string;
  message?: string;
  error?: string;
}

export interface DocumentCreatorStatusResponse {
  state: 'pending' | 'completed' | 'failed';
  data?: {
    doc_gen_id: string;
    phase: string;
    sections: SectionState[];
    document_title?: string;
    document_subtitle?: string;
  };
  error?: string;
}

export interface DocumentCreatorPreviewResponse {
  status: string;
  doc_gen_id: string;
  document_title: string;
  document_subtitle?: string;
  config: DocumentCreatorConfig;
  sections: SectionState[];
  review_result?: {
    overall_score: number;
    coherence_score: number;
    completeness_score: number;
    consistency_score: number;
    issues: string[];
    approved: boolean;
  } | null;
}

export interface DocumentCreatorExportResponse {
  status: string;
  filename?: string;
  download_url?: string;
  error?: string;
}

// Auth helpers
export const getAuthToken = () => localStorage.getItem('auth_token');
export const setAuthToken = (token: string) => localStorage.setItem('auth_token', token);
export const removeAuthToken = () => localStorage.removeItem('auth_token');
export const getCurrentUser = (): User | null => {
  const userStr = localStorage.getItem('current_user');
  return userStr ? JSON.parse(userStr) : null;
};
export const setCurrentUser = (user: User) => localStorage.setItem('current_user', JSON.stringify(user));
export const removeCurrentUser = () => localStorage.removeItem('current_user');

// API functions
export const api = {
  async register(name: string, email: string, password: string) {
    const response = await fetch(`${API_URL}/user/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });
    return response;
  },

  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${API_URL}/user/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      const errorMessage = errorData.detail || 'Invalid email or password';
      throw new Error(errorMessage);
    }

    return response.json();
  },

  async getUser(userId: string): Promise<User> {
    const token = getAuthToken();
    console.log("Using token:", token);
    console.log("Fetching user with ID:", userId);
    const response = await fetch(`${API_URL}/user/${userId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await response.json();
    return data.user;
  },

  async uploadFiles(data: { thread_name?: string; thread_id?: string; files: File[] }): Promise<UploadResponse> {
    const token = getAuthToken();
    const formData = new FormData();

    if (data.thread_name) formData.append('thread_name', data.thread_name);
    if (data.thread_id) formData.append('thread_id', data.thread_id);
    data.files.forEach(file => formData.append('files', file));

    const response = await fetch(`${API_URL}/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });

    const json = await response.json();

    if (!response.ok || json.error) {
      const errorMessage = json.error || json.detail || 'Failed to upload files';
      throw new Error(errorMessage);
    }

    return json;
  },


  async uploadFilesWithProgress(params: {
    thread_name?: string;
    thread_id?: string;
    files: File[];
    onProgress?: (args: { fileIndex: number; loaded: number; total: number; percent: number }) => void;
  }): Promise<UploadResponse> {
    const token = getAuthToken();

    const uploadSingle = (file: File): Promise<UploadResponse> => {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${API_URL}/upload`, true);
        if (token) {
          xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        }

        xhr.onload = () => {
          try {
            const json = JSON.parse(xhr.responseText);
            resolve(json);
          } catch (e) {
            reject(e);
          }
        };

        xhr.onerror = () => reject(new Error('Network error during upload'));

        const formData = new FormData();
        if (params.thread_name) formData.append('thread_name', params.thread_name);
        if (params.thread_id) formData.append('thread_id', params.thread_id);
        formData.append('files', file);

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable && params.onProgress) {
            const percent = Math.round((event.loaded / event.total) * 100);
          }
        };

        xhr.send(formData);
      });
    };

    const results: UploadResponse = {
      status: 'success',
      message: 'Uploaded',
      thread_id: params.thread_id || '',
      documents: [],
    };

    for (let i = 0; i < params.files.length; i++) {
      const file = params.files[i];
      await new Promise<UploadResponse>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${API_URL}/upload`, true);
        if (token) {
          xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        }

        xhr.onload = () => {
          try {
            const json: UploadResponse = JSON.parse(xhr.responseText);

            // Check for errors in response
            if (xhr.status >= 400 || (json as any).error) {
              const errorMessage = (json as any).error || (json as any).detail || 'Failed to upload file';
              reject(new Error(errorMessage));
              return;
            }

            if (!results.thread_id && json.thread_id) {
              results.thread_id = json.thread_id;
            }
            results.documents = [...results.documents, ...json.documents];
            resolve(json);
          } catch (e) {
            reject(e);
          }
        };

        xhr.onerror = () => reject(new Error('Network error during upload'));

        const formData = new FormData();
        if (params.thread_name) formData.append('thread_name', params.thread_name);
        if (params.thread_id) formData.append('thread_id', params.thread_id);
        formData.append('files', file);

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable && params.onProgress) {
            const percent = Math.round((event.loaded / event.total) * 100);
            params.onProgress({ fileIndex: i, loaded: event.loaded, total: event.total, percent });
          }
        };

        xhr.send(formData);
      });
    }

    return results;
  },

  async getThread(threadId: string): Promise<Thread> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/thread/${threadId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await response.json();

    if (!response.ok || data.error) {
      const errorMessage = data.error || data.detail || 'Failed to load thread';
      throw new Error(errorMessage);
    }

    return data.thread;
  },

  async query(
    threadId: string,
    question: string,
    mode: 'Internal' | 'External',
    useSelfKnowledge: boolean,
    useContext: boolean = false
  ): Promise<QueryResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        thread_id: threadId,
        question,
        mode,
        use_self_knowledge: useSelfKnowledge,
        use_context: useContext,
      }),
    });

    const data = await response.json();

    if (!response.ok || data.error) {
      const errorMessage = data.error || data.detail || 'Failed to get response';
      throw new Error(errorMessage);
    }

    return data;
  },

  async deleteThread(threadId: string): Promise<{ status: boolean }> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/thread/${threadId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    return response.json();
  },

  async deleteDocument(threadId: string, docId: string): Promise<DeleteDocumentResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/thread/${threadId}/document/${docId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      const errorMessage = errorData.error || errorData.detail || 'Failed to delete document';
      throw new Error(errorMessage);
    }

    return response.json();
  },

  async addExistingDocument(
    targetThreadId: string,
    sourceThreadId: string,
    docId: string,
  ): Promise<AddExistingDocumentResponse> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/thread/${targetThreadId}/documents/add-existing`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          source_thread_id: sourceThreadId,
          doc_id: docId,
        }),
      },
    );

    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || data.detail || 'Failed to add document');
    }
    return data;
  },

  async updateThread(threadId: string, data: { thread_name: string }): Promise<{ status: string; message: string; thread_id: string; thread_name: string }> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/thread/${threadId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });

    return response.json();
  },

  async deleteChat(threadId: string, chatIndex: number): Promise<DeleteChatResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/thread/${threadId}/chats/${chatIndex}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      const errorMessage = errorData.error || errorData.detail || 'Failed to delete chat';
      throw new Error(errorMessage);
    }

    return response.json();
  },

  async clearThreadChats(threadId: string): Promise<ClearChatsResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/thread/${threadId}/chats`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      const errorMessage = errorData.error || errorData.detail || 'Failed to clear chats';
      throw new Error(errorMessage);
    }

    return response.json();
  },

  async getMindMap(threadId: string): Promise<MindMapResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/mindmap/${threadId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      // Fallback shape with mind_map=false so UI can display error message
      return { mind_map: false, message: `Failed to fetch mind map (${response.status})` };
    }
    return response.json();
  },

  async summary(threadId: string, documentId: string, regenerate: boolean = false): Promise<SummaryResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/summary`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, document_id: documentId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse summary response (${response.status})` };
    }
    if (!response.ok) {
      // Normalize error shape
      return { status: false, error: data?.detail || data?.message || 'Summary request failed' };
    }
    return data as SummaryResponse;
  },

  async summaryGlobal(threadId: string, regenerate: boolean = false): Promise<SummaryResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/summary/global`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse summary (global) response (${response.status})` };
    }
    if (!response.ok) {
      return { status: false, error: data?.detail || data?.message || 'Summary (global) request failed' };
    }
    return data as SummaryResponse;
  },

  async strategicRoadmap(threadId: string, documentId: string, regenerate: boolean = false): Promise<StrategicRoadmapResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/strategic_roadmap`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, document_id: documentId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse strategic roadmap response (${response.status})` };
    }
    if (!response.ok) {
      return { status: false, error: data?.detail || data?.message || 'Strategic roadmap request failed' };
    }
    // Expected shapes: { status: false, message } or { status: true, strategic_roadmap }
    return data as StrategicRoadmapResponse;
  },

  // Generate strategic roadmap across ALL documents in a thread
  async strategicRoadmapGlobal(threadId: string, regenerate: boolean = false): Promise<StrategicRoadmapResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/strategic_roadmap/global`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse strategic roadmap (global) response (${response.status})` };
    }
    if (!response.ok) {
      return { status: false, error: data?.detail || data?.message || 'Strategic roadmap (global) request failed' };
    }
    return data as StrategicRoadmapResponse;
  },

  async insights(threadId: string, documentId: string, regenerate: boolean = false): Promise<InsightsResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/insights`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, document_id: documentId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse insights response (${response.status})` };
    }
    if (!response.ok) {
      return { status: false, error: data?.detail || data?.message || 'Insights request failed' };
    }
    return data as InsightsResponse; // Expected: { status:false,message } or { status:true, insights }
  },

  async insightsGlobal(threadId: string, regenerate: boolean = false): Promise<InsightsResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/insights/global`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse insights (global) response (${response.status})` };
    }
    if (!response.ok) {
      return { status: false, error: data?.detail || data?.message || 'Insights (global) request failed' };
    }
    return data as InsightsResponse;
  },

  async technicalRoadmap(threadId: string, documentId: string, regenerate: boolean = false): Promise<TechnicalRoadmapResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/technical_roadmap`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, document_id: documentId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse technical roadmap response (${response.status})` };
    }
    if (!response.ok) {
      return { status: false, error: data?.detail || data?.message || 'Technical roadmap request failed' };
    }
    return data as TechnicalRoadmapResponse;
  },

  async technicalRoadmapGlobal(threadId: string, regenerate: boolean = false): Promise<TechnicalRoadmapResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/technical_roadmap/global`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse technical roadmap (global) response (${response.status})` };
    }
    if (!response.ok) {
      return { status: false, error: data?.detail || data?.message || 'Technical roadmap (global) request failed' };
    }
    return data as TechnicalRoadmapResponse;
  },

  // ── Strategic Analysis ──

  async strategicAnalysis(threadId: string, documentId: string, regenerate: boolean = false): Promise<StrategicAnalysisResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/strategic_analysis`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, document_id: documentId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse strategic analysis response (${response.status})` };
    }
    if (!response.ok) {
      return { status: false, error: data?.detail || data?.message || 'Strategic analysis request failed' };
    }
    return data as StrategicAnalysisResponse;
  },

  async strategicAnalysisGlobal(threadId: string, regenerate: boolean = false): Promise<StrategicAnalysisResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/strategic_analysis/global`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse strategic analysis (global) response (${response.status})` };
    }
    if (!response.ok) {
      return { status: false, error: data?.detail || data?.message || 'Strategic analysis (global) request failed' };
    }
    return data as StrategicAnalysisResponse;
  },

  // ── Technical Analysis ──

  async technicalAnalysis(threadId: string, documentId: string, regenerate: boolean = false): Promise<TechnicalAnalysisResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/technical_analysis`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, document_id: documentId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse technical analysis response (${response.status})` };
    }
    if (!response.ok) {
      return { status: false, error: data?.detail || data?.message || 'Technical analysis request failed' };
    }
    return data as TechnicalAnalysisResponse;
  },

  async technicalAnalysisGlobal(threadId: string, regenerate: boolean = false): Promise<TechnicalAnalysisResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/technical_analysis/global`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, regenerate }),
    });
    let data: any = null;
    try {
      data = await response.json();
    } catch (_) {
      return { status: false, error: `Failed to parse technical analysis (global) response (${response.status})` };
    }
    if (!response.ok) {
      return { status: false, error: data?.detail || data?.message || 'Technical analysis (global) request failed' };
    }
    return data as TechnicalAnalysisResponse;
  },

  // ── Thread Instructions ──

  async getInstructions(threadId: string): Promise<ThreadInstruction[]> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/thread/${threadId}/instructions`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || 'Failed to load instructions');
    }
    return data.instructions ?? [];
  },

  async addInstruction(threadId: string, text: string): Promise<ThreadInstruction> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/thread/${threadId}/instructions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ text }),
    });
    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || 'Failed to add instruction');
    }
    return data.instruction;
  },

  async updateInstruction(
    threadId: string,
    instructionId: string,
    updates: { text?: string; selected?: boolean }
  ): Promise<ThreadInstruction> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/thread/${threadId}/instructions/${instructionId}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(updates),
      }
    );
    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || 'Failed to update instruction');
    }
    return data.instruction;
  },

  async deleteInstruction(threadId: string, instructionId: string): Promise<void> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/thread/${threadId}/instructions/${instructionId}`,
      {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || 'Failed to delete instruction');
    }
  },

  // ── Document Creator ──

  async documentCreatorOutline(
    threadId: string,
    config: DocumentCreatorConfig,
  ): Promise<DocumentCreatorOutlineResponse> {
    const token = getAuthToken();
    const response = await fetch(`${API_URL}/document-creator/outline`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ thread_id: threadId, config }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to generate outline');
    }
    return data;
  },

  async documentCreatorOutlineStatus(
    trackingId: string,
  ): Promise<DocumentCreatorStatusResponse> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/document-creator/outline-status/${trackingId}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to check outline status');
    }
    return data;
  },

  async documentCreatorUpdateOutline(
    docGenId: string,
    sections: OutlineSectionSpec[],
    documentTitle?: string,
    documentSubtitle?: string,
  ): Promise<{ status: string }> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/document-creator/outline/${docGenId}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          sections,
          document_title: documentTitle,
          document_subtitle: documentSubtitle,
        }),
      },
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to update outline');
    }
    return data;
  },

  async documentCreatorGenerate(
    docGenId: string,
  ): Promise<{ status: string; message: string }> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/document-creator/generate/${docGenId}`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to start generation');
    }
    return data;
  },

  async documentCreatorStatus(
    docGenId: string,
  ): Promise<DocumentCreatorStatusResponse> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/document-creator/status/${docGenId}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to check generation status');
    }
    return data;
  },

  async documentCreatorPreview(
    docGenId: string,
  ): Promise<DocumentCreatorPreviewResponse> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/document-creator/preview/${docGenId}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to load preview');
    }
    return data;
  },

  async documentCreatorIterate(
    docGenId: string,
    sectionId: string,
    feedback?: string,
  ): Promise<{ status: string; message: string }> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/document-creator/iterate/${docGenId}/${sectionId}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ feedback: feedback || null }),
      },
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to iterate section');
    }
    return data;
  },

  async documentCreatorSelectVersion(
    docGenId: string,
    sectionId: string,
    versionIndex: number,
  ): Promise<{ status: string }> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/document-creator/select-version/${docGenId}/${sectionId}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ version_index: versionIndex }),
      },
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to select version');
    }
    return data;
  },

  async documentCreatorApprove(
    docGenId: string,
    sectionId: string,
  ): Promise<{ status: string }> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/document-creator/approve/${docGenId}/${sectionId}`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to approve section');
    }
    return data;
  },

  async documentCreatorExport(
    docGenId: string,
    format: ExportFormat,
  ): Promise<DocumentCreatorExportResponse> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/document-creator/export/${docGenId}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ format }),
      },
    );
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || data.error || 'Failed to export document');
    }
    return data;
  },

  async documentCreatorDownload(
    docGenId: string,
    filename: string,
  ): Promise<Blob> {
    const token = getAuthToken();
    const response = await fetch(
      `${API_URL}/document-creator/download/${docGenId}/${filename}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    if (!response.ok) {
      throw new Error('Failed to download file');
    }
    return response.blob();
  },
};

// WebSocket helper
export const getWebSocketUrl = (path: string) => {
  // Allow explicit WS base via env, otherwise derive from API_URL
  const base = (import.meta.env.VITE_WS_URL as string | undefined) || API_URL;
  const url = new URL(base);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  // Ensure we don't double up slashes
  const joined = `${url.origin}${path.startsWith('/') ? '' : '/'}${path}`;
  return joined;
};
