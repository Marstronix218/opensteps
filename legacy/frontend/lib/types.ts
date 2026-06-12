export type Event = {
  id: string;
  event_type: string;
  agent_id: string | null;
  user_id: string | null;
  tool: string | null;
  action: string | null;
  resource: string | null;
  input_hash: string | null;
  output_hash: string | null;
  policy_decision: string | null;
  approval_id: string | null;
  previous_hash: string | null;
  event_hash: string;
  signature: string | null;
  timestamp: string;
};

export type Run = {
  id: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  root_agent_id: string | null;
  events?: Event[];
};

export type Approval = {
  id: string;
  status: string;
  run_id: string;
  scope_json: Record<string, string>;
  expires_at: string;
  created_at: string;
  approved_by: string | null;
};

export type Policy = {
  id: string;
  name: string;
  policy_yaml: string;
  status: string;
  created_at: string;
};

export type Checkpoint = {
  id: string;
  from_event_id: string;
  to_event_id: string;
  event_count: number;
  merkle_root: string;
  signature: string;
  created_at: string;
};

