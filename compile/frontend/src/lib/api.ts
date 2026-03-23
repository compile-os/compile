import type {
  CompileModule,
  EvolvablePair,
  FitnessFunction,
  Mutation,
  ThreeLayerMap,
  EvolutionJob,
} from '@/types/compile';
import { FALLBACK_MODULES, FALLBACK_FITNESS_FUNCTIONS, FALLBACK_THREE_LAYER_MAP } from '@/lib/compile-data';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

let useFallback = false;

// Auth token for protected endpoints (set after passkey/JWT login)
let authToken: string | null = null;

export function setAuthToken(token: string) {
  authToken = token;
  if (typeof window !== 'undefined') {
    localStorage.setItem('compile_auth_token', token);
  }
}

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== 'undefined') {
    authToken = localStorage.getItem('compile_auth_token');
  }
  return authToken;
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  if (token) {
    return { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
  }
  return { 'Content-Type': 'application/json' };
}

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}/api/v1/compile${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function fetchWithFallback<T>(path: string, fallback: () => T): Promise<T> {
  if (useFallback) return fallback();
  try {
    return await fetchJSON<T>(path);
  } catch {
    useFallback = true;
    console.warn('API unavailable, using fallback data');
    return fallback();
  }
}

export async function fetchModules(role?: string): Promise<CompileModule[]> {
  const query = role ? `?role=${role}` : '';
  return fetchWithFallback(`/modules${query}`, () => {
    const all = FALLBACK_MODULES;
    return role ? all.filter((m) => m.role === role) : all;
  }).then((res) => {
    // API returns {count, modules}, fallback returns array directly
    const arr = Array.isArray(res)
      ? res
      : (res as unknown as { modules: CompileModule[] }).modules ?? [];
    // Coerce string IDs to numbers (Go backend returns string keys)
    return arr.map((m) => ({ ...m, id: typeof m.id === 'string' ? parseInt(m.id, 10) : m.id }));
  });
}

export async function fetchModule(id: number): Promise<CompileModule> {
  return fetchWithFallback(`/modules/${id}`, () => {
    const mod = FALLBACK_MODULES.find((m) => m.id === id);
    if (!mod) throw new Error(`Module ${id} not found`);
    return mod;
  });
}

export async function fetchFitnessFunctions(): Promise<FitnessFunction[]> {
  return fetchWithFallback('/fitness-functions', () => FALLBACK_FITNESS_FUNCTIONS).then(async (res) => {
    // Fallback returns full array with evolvable_pairs as arrays
    if (Array.isArray(res)) return res;
    // API list endpoint returns summaries (evolvable_pairs is a count, not array)
    // Fetch each detail to get the full data
    const summaries = (res as unknown as { fitness_functions: Array<{ name: string }> }).fitness_functions ?? [];
    const details = await Promise.all(
      summaries.map((s) => fetchFitnessFunction(s.name).catch(() => null))
    );
    return details.filter((d): d is FitnessFunction => d !== null);
  });
}

export async function fetchFitnessFunction(name: string): Promise<FitnessFunction> {
  return fetchWithFallback(`/fitness-functions/${name}`, () => {
    const ff = FALLBACK_FITNESS_FUNCTIONS.find((f) => f.name === name);
    if (!ff) throw new Error(`Fitness function ${name} not found`);
    return ff;
  });
}

export async function fetchThreeLayerMap(): Promise<ThreeLayerMap> {
  return fetchWithFallback('/three-layer-map', () => FALLBACK_THREE_LAYER_MAP);
}

export async function fetchMutations(
  fitness: string,
  seed?: number,
): Promise<Mutation[]> {
  const query = seed !== undefined ? `?seed=${seed}` : '';
  return fetchJSON<Mutation[]>(`/mutations?fitness=${fitness}${seed !== undefined ? `&seed=${seed}` : ''}`);
}

export async function fetchConnection(
  src: number,
  tgt: number,
): Promise<{ n_synapses: number; evolvable_in: string[] }> {
  return fetchJSON(`/connections/${src}/${tgt}`);
}

export async function createJob(params: {
  fitness_function: string;
  seed: number;
  generations?: number;
  architecture?: string;
}): Promise<EvolutionJob> {
  const res = await fetch(`${API_BASE}/api/v1/compile/jobs`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(params),
  });
  if (res.status === 401) {
    throw new Error('Authentication required. Please sign in to compile custom behaviors.');
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function streamJob(
  jobId: string,
  onEvent: (data: { type: string; payload: Record<string, unknown> }) => void,
): EventSource {
  const token = getAuthToken();
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : '';
  const source = new EventSource(`${API_BASE}/api/v1/compile/jobs/${jobId}/stream${tokenParam}`);

  // Listen for named SSE events (backend sends event: connected, progress, done, error)
  for (const eventType of ['connected', 'started', 'progress', 'done', 'error']) {
    source.addEventListener(eventType, (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data);
        onEvent({ type: eventType, payload });
      } catch {
        console.error(`Failed to parse SSE ${eventType} event`);
      }
    });
  }

  // Fallback for unnamed events
  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onEvent({ type: 'message', payload: data });
    } catch {
      // ignore
    }
  };

  source.onerror = () => {
    console.error('SSE connection error');
    source.close();
  };
  return source;
}

export interface CatalogData {
  behaviors: Array<{
    id: string;
    label: string;
    category: string;
    improvement: string;
    edges: number;
    description: string;
    capability_family?: string;
    is_precomputed?: boolean;
    is_mine?: boolean;
  }>;
  interference: Array<{
    compiled: string;
    tested: string;
    delta_pct: number;
  }>;
  families: Array<{
    name: string;
    description: string;
    behaviors: string[];
    hub_modules: number[];
    overlap_pct: number;
  }>;
  hub_capacity: {
    total_neurons: number;
    behaviors_compiled: number;
    capability_families: number;
  };
  total_results: number;
  species: number;
}

export async function fetchCatalog(userId?: string): Promise<CatalogData> {
  const query = userId ? `?user_id=${userId}` : '';
  return fetchJSON<CatalogData>(`/catalog${query}`);
}

export async function extractProcessor(params: {
  fitness_function: string;
  method?: string;
}): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/v1/compile/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function generateGrowthProgram(params: {
  processor_id: string;
}): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/api/v1/compile/growth-program`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}


export async function checkApiHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function classifyBehavior(description: string): Promise<{ tag: string; source: string }> {
  const res = await fetch(`${API_BASE}/api/v1/compile/classify-behavior`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description }),
  });
  if (!res.ok) return { tag: 'speed', source: 'fallback' };
  return res.json();
}

export async function recommendArchitecture(
  behaviors: Array<{ id: string; tag: string; label: string }>,
  constraints?: Record<string, unknown>,
): Promise<{ architecture: string; explanation: string; source: string }> {
  const res = await fetch(`${API_BASE}/api/v1/compile/recommend-architecture`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ behaviors, constraints: constraints || {} }),
  });
  if (!res.ok) return { architecture: 'cellular_automaton', explanation: 'Default recommendation', source: 'fallback' };
  return res.json();
}

export function isAuthenticated(): boolean {
  return !!getAuthToken();
}
