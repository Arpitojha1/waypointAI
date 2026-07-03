export type OpportunityType = 'job' | 'hackathon' | 'issue';

export interface Opportunity {
  id: string;
  type: OpportunityType;
  title: string;
  description: string | null;
  url: string | null;
  source: string | null;
  company: string | null;
  location: string | null;
  repo_owner: string | null;
  repo_name: string | null;
  issue_number: number | null;
  metadata_?: {
    tags?: string[];
    [key: string]: any;
  };
  is_active: boolean;
  created_at: string;
}

export interface ResourceLink {
  title: string;
  url: string;
}

export type StepStatus = 'pending' | 'done' | 'rejected' | 'skipped';

export interface Step {
  id: string;
  roadmap_id: string;
  order_index: number;
  title: string;
  description: string;
  status: StepStatus;
  resource_links?: ResourceLink[];
  cognee_memified?: boolean;
}

export interface Roadmap {
  id: string;
  opportunity_id: string;
  user_id: string;
  title: string;
  summary: string | null;
  status: string;
  steps: Step[];
  created_at: string;
}

export interface UserProfile {
  id: string;
  user_id: string;
  display_name: string | null;
  skills: string[];
  experience_summary: string | null;
  projects: any[];
  preferences: Record<string, any>;
}
