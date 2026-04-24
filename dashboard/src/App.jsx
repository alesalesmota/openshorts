import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  Brain,
  Check,
  ChevronDown,
  CircleDollarSign,
  Clock3,
  FileVideo,
  Instagram,
  LayoutDashboard,
  RefreshCw,
  RotateCcw,
  Scissors,
  Settings,
  Shield,
  Sparkles,
  Terminal,
  Upload,
  Youtube,
} from 'lucide-react';
import MediaInput from './components/MediaInput';
import ProcessingAnimation from './components/ProcessingAnimation';
import ResultCard from './components/ResultCard';
import { getApiUrl } from './config';

const SECRET_KEY = import.meta.env.VITE_ENCRYPTION_KEY || 'OpenShorts-Static-Salt-Change-Me';
const ENCRYPTION_PREFIX = 'ENC:';
const SESSION_KEY = 'openshorts_session';
const SESSION_MAX_AGE = 3600000;

const providerOptions = [
  { value: 'gemini', label: 'Gemini', defaultModel: 'gemini-2.5-flash' },
  { value: 'openai', label: 'OpenAI', defaultModel: 'gpt-4o-mini' },
  { value: 'azure-openai', label: 'Azure OpenAI', defaultModel: '' },
  { value: 'openrouter', label: 'OpenRouter', defaultModel: 'openai/gpt-4o-mini' },
  { value: 'nvidia-nim', label: 'NVIDIA NIM', defaultModel: 'meta/llama-3.1-70b-instruct' },
  { value: 'custom-openai-compatible', label: 'Custom OpenAI-compatible', defaultModel: '' },
];

const encrypt = (text) => {
  if (!text) return '';
  try {
    const xor = text.split('').map((c, i) =>
      String.fromCharCode(c.charCodeAt(0) ^ SECRET_KEY.charCodeAt(i % SECRET_KEY.length))
    ).join('');
    return ENCRYPTION_PREFIX + btoa(xor);
  } catch {
    return text;
  }
};

const decrypt = (text) => {
  if (!text) return '';
  if (!text.startsWith(ENCRYPTION_PREFIX)) return text;
  try {
    const xor = atob(text.slice(ENCRYPTION_PREFIX.length));
    return xor.split('').map((c, i) =>
      String.fromCharCode(c.charCodeAt(0) ^ SECRET_KEY.charCodeAt(i % SECRET_KEY.length))
    ).join('');
  } catch {
    return '';
  }
};

const buildAiHeaders = (aiConfig) => {
  const headers = {
    'X-AI-Provider': aiConfig.provider,
  };
  if (aiConfig.apiKey) headers['X-AI-API-Key'] = aiConfig.apiKey;
  if (aiConfig.model) headers['X-AI-Model'] = aiConfig.model;
  if (aiConfig.baseUrl) headers['X-AI-Base-URL'] = aiConfig.baseUrl;
  if (aiConfig.azureEndpoint) headers['X-Azure-OpenAI-Endpoint'] = aiConfig.azureEndpoint;
  if (aiConfig.azureDeployment) headers['X-Azure-OpenAI-Deployment'] = aiConfig.azureDeployment;
  if (aiConfig.azureApiVersion) headers['X-Azure-OpenAI-API-Version'] = aiConfig.azureApiVersion;
  if (aiConfig.provider === 'gemini') headers['X-Gemini-Key'] = aiConfig.apiKey;
  return headers;
};

const sortModelOptions = (options, sortMode) => {
  const list = [...options];
  const byRecommended = (a, b) =>
    Number(Boolean(b.is_default)) - Number(Boolean(a.is_default)) ||
    (a.cost_rank ?? 99) - (b.cost_rank ?? 99) ||
    (b.intelligence_rank ?? 0) - (a.intelligence_rank ?? 0);

  if (sortMode === 'cheapest') return list.sort((a, b) => (a.cost_rank ?? 99) - (b.cost_rank ?? 99));
  if (sortMode === 'smartest') return list.sort((a, b) => (b.intelligence_rank ?? 0) - (a.intelligence_rank ?? 0));
  if (sortMode === 'newest') return list.sort((a, b) => String(b.release_date || '').localeCompare(String(a.release_date || '')));
  if (sortMode === 'fastest') return list.sort((a, b) => (a.speed_rank ?? 99) - (b.speed_rank ?? 99));
  return list.sort(byRecommended);
};

const compactDate = (value) => {
  if (!value) return 'unranked';
  return String(value).slice(0, 7);
};

const pollJob = async (jobId) => {
  const res = await fetch(getApiUrl(`/api/status/${jobId}`));
  if (!res.ok) throw new Error('Status check failed');
  return res.json();
};

const TikTokIcon = ({ size = 16, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M19.589 6.686a4.793 4.793 0 0 1-3.77-4.245V2h-3.445v13.672a2.896 2.896 0 0 1-5.201 1.743 2.895 2.895 0 0 1 3.183-4.51v-3.5a6.329 6.329 0 0 0-5.394 10.692 6.33 6.33 0 0 0 10.857-4.424V8.687a8.182 8.182 0 0 0 4.773 1.526V6.79a4.831 4.831 0 0 1-1.003-.104z" />
  </svg>
);

const UserProfileSelector = ({ profiles, selectedUserId, onSelect }) => {
  const [isOpen, setIsOpen] = useState(false);
  if (!profiles.length) return null;
  const selectedProfile = profiles.find((p) => p.username === selectedUserId) || profiles[0];

  return (
    <div className="relative z-50">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex min-w-[180px] items-center justify-between rounded-lg border border-white/10 bg-surface px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-white/5"
      >
        <span className="flex items-center gap-2">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/20 text-[10px] font-bold text-primary">
            {selectedProfile?.username?.substring(0, 1).toUpperCase() || 'U'}
          </span>
          <span className="max-w-[100px] truncate font-medium text-white">{selectedProfile?.username || 'Select user'}</span>
        </span>
        <ChevronDown size={14} className={`text-zinc-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-64 overflow-hidden rounded-xl border border-white/10 bg-[#1a1a1a] shadow-2xl">
          {profiles.map((profile) => (
            <button
              key={profile.username}
              onClick={() => {
                onSelect(profile.username);
                setIsOpen(false);
              }}
              className="flex w-full items-center justify-between border-b border-white/5 px-4 py-3 text-left transition-colors last:border-0 hover:bg-white/5"
            >
              <span>
                <span className="block text-sm font-medium text-zinc-200">{profile.username}</span>
                <span className="mt-1 flex gap-2 text-zinc-600">
                  <TikTokIcon size={10} className={profile.connected.includes('tiktok') ? 'text-zinc-300' : ''} />
                  <Instagram size={10} className={profile.connected.includes('instagram') ? 'text-pink-400' : ''} />
                  <Youtube size={10} className={profile.connected.includes('youtube') ? 'text-red-400' : ''} />
                </span>
              </span>
              {selectedUserId === profile.username && <Check size={14} className="text-primary" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [aiConfig, setAiConfig] = useState(() => {
    const provider = localStorage.getItem('ai_provider') || 'gemini';
    const providerMeta = providerOptions.find((p) => p.value === provider) || providerOptions[0];
    return {
      provider,
      model: localStorage.getItem('ai_model') || providerMeta.defaultModel,
      apiKey: decrypt(localStorage.getItem('aiApiKey_v1')) || localStorage.getItem('gemini_key') || '',
      baseUrl: localStorage.getItem('ai_base_url') || '',
      azureEndpoint: localStorage.getItem('azure_openai_endpoint') || '',
      azureDeployment: localStorage.getItem('azure_openai_deployment') || '',
      azureApiVersion: localStorage.getItem('azure_openai_api_version') || '2024-10-21',
    };
  });
  const [uploadPostKey, setUploadPostKey] = useState(() => decrypt(localStorage.getItem('uploadPostKey_v3')) || '');
  const [uploadUserId, setUploadUserId] = useState(() => localStorage.getItem('uploadUserId') || '');
  const [userProfiles, setUserProfiles] = useState([]);
  const [backendAiDefaults, setBackendAiDefaults] = useState(null);
  const [modelOptions, setModelOptions] = useState([]);
  const [modelSort, setModelSort] = useState('recommended');
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState(null);
  const [modelSourceNote, setModelSourceNote] = useState('');
  const [modelRefreshNonce, setModelRefreshNonce] = useState(0);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [results, setResults] = useState(null);
  const [logs, setLogs] = useState([]);
  const [logsVisible, setLogsVisible] = useState(true);
  const [processingMedia, setProcessingMedia] = useState(null);
  const [sessionRecovered, setSessionRecovered] = useState(false);
  const [syncedTime, setSyncedTime] = useState(0);
  const [isSyncedPlaying, setIsSyncedPlaying] = useState(false);
  const [syncTrigger, setSyncTrigger] = useState(0);

  const providerLabel = useMemo(
    () => providerOptions.find((p) => p.value === aiConfig.provider)?.label || aiConfig.provider,
    [aiConfig.provider]
  );
  const hasAiCredential = Boolean(aiConfig.apiKey || backendAiDefaults?.has_api_key);
  const sortedModelOptions = useMemo(() => sortModelOptions(modelOptions, modelSort), [modelOptions, modelSort]);
  const showManualModelFallback = aiConfig.provider === 'custom-openai-compatible' || Boolean(modelsError && !modelOptions.length);
  const selectedModelOption = useMemo(
    () => modelOptions.find((option) => (
      option.id === aiConfig.model ||
      option.model === aiConfig.model ||
      option.deployment === aiConfig.azureDeployment
    )),
    [modelOptions, aiConfig.model, aiConfig.azureDeployment]
  );

  useEffect(() => {
    try {
      const saved = localStorage.getItem(SESSION_KEY);
      if (!saved) return;
      const session = JSON.parse(saved);
      if (Date.now() - session.timestamp > SESSION_MAX_AGE) {
        localStorage.removeItem(SESSION_KEY);
        return;
      }
      if (session.jobId && session.status && session.status !== 'idle') {
        setJobId(session.jobId);
        setResults(session.results || null);
        if (session.processingMedia) setProcessingMedia(session.processingMedia);
        setStatus(session.status === 'processing' ? 'processing' : session.status);
        setSessionRecovered(true);
        setTimeout(() => setSessionRecovered(false), 5000);
      }
    } catch {
      localStorage.removeItem(SESSION_KEY);
    }
  }, []);

  useEffect(() => {
    if (status === 'idle') {
      localStorage.removeItem(SESSION_KEY);
      return;
    }
    localStorage.setItem(SESSION_KEY, JSON.stringify({
      jobId,
      status,
      results,
      processingMedia: processingMedia?.type === 'url' ? processingMedia : null,
      timestamp: Date.now(),
    }));
  }, [jobId, status, results, processingMedia]);

  useEffect(() => {
    localStorage.setItem('ai_provider', aiConfig.provider);
    localStorage.setItem('ai_model', aiConfig.model || '');
    localStorage.setItem('ai_base_url', aiConfig.baseUrl || '');
    localStorage.setItem('azure_openai_endpoint', aiConfig.azureEndpoint || '');
    localStorage.setItem('azure_openai_deployment', aiConfig.azureDeployment || '');
    localStorage.setItem('azure_openai_api_version', aiConfig.azureApiVersion || '');
    if (aiConfig.apiKey) {
      localStorage.setItem('aiApiKey_v1', encrypt(aiConfig.apiKey));
      if (aiConfig.provider === 'gemini') localStorage.setItem('gemini_key', aiConfig.apiKey);
    } else if (backendAiDefaults?.has_api_key) {
      localStorage.removeItem('aiApiKey_v1');
      localStorage.removeItem('gemini_key');
    }
  }, [aiConfig, backendAiDefaults?.has_api_key]);

  useEffect(() => {
    if (uploadPostKey) localStorage.setItem('uploadPostKey_v3', encrypt(uploadPostKey));
    if (uploadUserId) localStorage.setItem('uploadUserId', uploadUserId);
  }, [uploadPostKey, uploadUserId]);

  useEffect(() => {
    if (uploadPostKey && !userProfiles.length) fetchUserProfiles();
  }, [uploadPostKey]);

  useEffect(() => {
    fetch(getApiUrl('/api/ai/defaults'))
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data) return;
        setBackendAiDefaults(data);
        if (!data.has_api_key) return;
        setAiConfig((prev) => ({
          ...prev,
          apiKey: '',
          provider: data.provider || prev.provider,
          model: data.model || data.azureDeployment || prev.model,
          baseUrl: data.baseUrl || prev.baseUrl,
          azureEndpoint: data.azureEndpoint || prev.azureEndpoint,
          azureDeployment: data.azureDeployment || prev.azureDeployment,
          azureApiVersion: data.azureApiVersion || prev.azureApiVersion || '2024-10-21',
        }));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    setModelsLoading(true);
    setModelsError(null);

    fetch(getApiUrl(`/api/ai/models?provider=${encodeURIComponent(aiConfig.provider)}`), {
      headers: buildAiHeaders(aiConfig),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json();
      })
      .then((data) => {
        if (cancelled) return;
        const options = data.models || [];
        setModelOptions(options);
        setModelSourceNote(data.notes || '');

        const hasCurrent = options.some((option) => (
          option.id === aiConfig.model ||
          option.model === aiConfig.model ||
          option.deployment === aiConfig.azureDeployment
        ));
        if (!hasCurrent && options.length) {
          const first = sortModelOptions(options, modelSort)[0];
          setAiConfig((prev) => ({
            ...prev,
            model: first.deployment || first.model || first.id,
            azureDeployment: prev.provider === 'azure-openai' ? (first.deployment || first.id) : prev.azureDeployment,
          }));
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setModelOptions([]);
          setModelsError(e.message || 'Could not load models');
        }
      })
      .finally(() => {
        if (!cancelled) setModelsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [aiConfig.provider, aiConfig.apiKey, aiConfig.baseUrl, aiConfig.azureEndpoint, backendAiDefaults?.has_api_key, modelRefreshNonce]);

  useEffect(() => {
    let interval;
    if ((status === 'processing' || status === 'completed') && jobId) {
      interval = setInterval(async () => {
        try {
          const data = await pollJob(jobId);
          if (data.result) setResults(data.result);
          if (data.status === 'completed') {
            setStatus('complete');
            clearInterval(interval);
          } else if (data.status === 'failed') {
            setStatus('error');
            setLogs((prev) => [...prev, `Error: ${data.error || data.logs?.at(-1) || 'Process failed'}`]);
            clearInterval(interval);
          } else if (data.logs) {
            setLogs(data.logs);
          }
        } catch (e) {
          console.error('Polling error', e);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [status, jobId]);

  const fetchUserProfiles = async () => {
    if (!uploadPostKey) return;
    try {
      const res = await fetch(getApiUrl('/api/social/user'), {
        headers: { 'X-Upload-Post-Key': uploadPostKey },
      });
      if (!res.ok) throw new Error('Failed to fetch Upload-Post profiles');
      const data = await res.json();
      const profiles = data.profiles || [];
      setUserProfiles(profiles);
      if (profiles.length && !uploadUserId) setUploadUserId(profiles[0].username);
    } catch (e) {
      console.error(e);
      alert('Error fetching Upload-Post profiles. Check key.');
    }
  };

  const handleProcess = async (data) => {
    if (!hasAiCredential) {
      setShowKeyModal(true);
      return;
    }

    setStatus('processing');
    setLogs([`Starting clip analysis with ${providerLabel}...`]);
    setResults(null);
    setProcessingMedia(data);

    try {
      let body;
      const headers = buildAiHeaders(aiConfig);
      if (data.type === 'url') {
        headers['Content-Type'] = 'application/json';
        body = JSON.stringify({ url: data.payload });
      } else {
        const formData = new FormData();
        formData.append('file', data.payload);
        body = formData;
      }

      const res = await fetch(getApiUrl('/api/process'), { method: 'POST', headers, body });
      if (!res.ok) throw new Error(await res.text());
      const resData = await res.json();
      setJobId(resData.job_id);
    } catch (e) {
      setStatus('error');
      setLogs((prev) => [...prev, `Error starting job: ${e.message}`]);
    }
  };

  const handleReset = () => {
    setStatus('idle');
    setJobId(null);
    setResults(null);
    setLogs([]);
    setProcessingMedia(null);
    localStorage.removeItem(SESSION_KEY);
  };

  const handleClipPlay = (startTime) => {
    setSyncedTime(startTime);
    setIsSyncedPlaying(true);
    setSyncTrigger((prev) => prev + 1);
  };

  const handleModelSelect = (optionId) => {
    const option = modelOptions.find((item) => item.id === optionId);
    if (!option) return;
    setAiConfig((prev) => ({
      ...prev,
      model: option.deployment || option.model || option.id,
      azureDeployment: prev.provider === 'azure-openai' ? (option.deployment || option.id) : prev.azureDeployment,
    }));
  };

  const Sidebar = () => (
    <div className="flex h-full w-20 shrink-0 flex-col border-r border-white/5 bg-surface transition-all duration-300 lg:w-64">
      <div className="flex items-center gap-3 p-6">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-white/5 bg-white/5">
          <img src="/logo-openshorts.png" alt="Logo" className="h-full w-full object-cover" />
        </div>
        <span className="hidden text-lg font-bold tracking-tight text-white lg:block">OpenShorts</span>
      </div>

      <nav className="flex-1 space-y-2 px-4 py-4">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 transition-colors ${activeTab === 'dashboard' ? 'bg-primary/10 text-primary' : 'text-zinc-400 hover:bg-white/5 hover:text-white'}`}
        >
          <LayoutDashboard size={20} />
          <span className="hidden font-medium lg:block">Clip Generator</span>
        </button>
        <button
          onClick={() => setActiveTab('settings')}
          className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 transition-colors ${activeTab === 'settings' ? 'bg-primary/10 text-primary' : 'text-zinc-400 hover:bg-white/5 hover:text-white'}`}
        >
          <Settings size={20} />
          <span className="hidden font-medium lg:block">Settings</span>
        </button>
      </nav>

      <div className="border-t border-white/5 p-4">
        <a
          href="https://github.com/mutonby/openshorts"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 rounded-xl bg-white/5 p-3 transition-colors hover:bg-white/10"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-black">
            <Scissors size={16} />
          </div>
          <div className="hidden overflow-hidden lg:block">
            <p className="mb-0.5 text-sm font-bold leading-none text-white">Focused Clips</p>
            <p className="truncate text-[10px] text-zinc-400">Long video cutting workflow</p>
          </div>
        </a>
      </div>
    </div>
  );

  const SettingsView = () => (
    <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-8">
      <div className="mx-auto w-full max-w-4xl space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Settings</h1>
          <p className="mt-1 text-sm text-zinc-500">Configure AI analysis and social publishing.</p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-green-500/20 bg-green-500/10 px-3 py-1 text-[10px] font-medium text-green-400">
          <Shield size={12} /> {backendAiDefaults?.has_api_key ? 'Backend key loaded' : 'Keys stay in this browser'}
        </div>
      </div>

      <section className="glass-panel p-6">
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-lg bg-primary/20 p-2 text-primary">
            <Settings size={20} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">AI Provider</h2>
            <p className="text-xs text-zinc-500">Used for transcript-to-clips analysis.</p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="block text-sm text-zinc-400">Provider</span>
            <select
              value={aiConfig.provider}
              onChange={(e) => {
                const next = providerOptions.find((p) => p.value === e.target.value);
                setAiConfig((prev) => ({
                  ...prev,
                  provider: e.target.value,
                  model: next?.defaultModel || '',
                  azureDeployment: e.target.value === 'azure-openai' ? prev.azureDeployment : '',
                }));
              }}
              className="input-field"
            >
              {providerOptions.map((provider) => (
                <option key={provider.value} value={provider.value}>{provider.label}</option>
              ))}
            </select>
          </label>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <span className="block text-sm text-zinc-400">Model / Deployment</span>
              <select
                value={modelSort}
                onChange={(e) => setModelSort(e.target.value)}
                className="rounded-lg border border-white/10 bg-white/[0.04] px-2 py-1 text-[11px] text-zinc-300 outline-none transition-colors hover:bg-white/[0.07]"
              >
                <option value="recommended">Recommended</option>
                <option value="cheapest">Cheapest</option>
                <option value="smartest">Smartest</option>
                <option value="newest">Newest</option>
                <option value="fastest">Fastest</option>
              </select>
            </div>
            <div className="flex gap-2">
              <select
                value={selectedModelOption?.id || ''}
                onChange={(e) => handleModelSelect(e.target.value)}
                disabled={modelsLoading || !sortedModelOptions.length}
                className="input-field font-mono"
              >
                <option value="" disabled>
                  {modelsLoading ? 'Loading models...' : 'No callable models found'}
                </option>
                {sortedModelOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}{option.deployment ? ` / ${option.deployment}` : ''}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setModelRefreshNonce((value) => value + 1)}
                className="flex h-[46px] w-[46px] shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-zinc-300 transition-colors hover:bg-white/[0.08] hover:text-white"
                title="Refresh model list"
              >
                <RefreshCw size={16} />
              </button>
            </div>
            {showManualModelFallback && (
              <input
                value={aiConfig.model}
                onChange={(e) => setAiConfig((prev) => ({ ...prev, model: e.target.value }))}
                className="input-field font-mono"
                placeholder="Manual model id"
              />
            )}
          </div>

          {(selectedModelOption || modelsError || modelSourceNote) && (
            <div className="md:col-span-2 border-t border-white/10 pt-4">
              {selectedModelOption && (
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate font-mono text-sm font-semibold text-white">
                        {selectedModelOption.label}
                      </span>
                      <span className="rounded-full border border-green-500/20 bg-green-500/10 px-2 py-0.5 text-[10px] font-medium text-green-300">
                        {selectedModelOption.status_label}
                      </span>
                      {selectedModelOption.deployment && (
                        <span className="rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-200">
                          deployed
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-zinc-500">
                      {selectedModelOption.deployment ? `Deployment: ${selectedModelOption.deployment}` : selectedModelOption.model}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] md:grid-cols-4">
                    <span className="flex items-center gap-1 rounded-lg border border-white/5 bg-black/20 px-2 py-1 text-zinc-300">
                      <CircleDollarSign size={12} className="text-emerald-300" /> {selectedModelOption.cost_label}
                    </span>
                    <span className="flex items-center gap-1 rounded-lg border border-white/5 bg-black/20 px-2 py-1 text-zinc-300">
                      <Brain size={12} className="text-sky-300" /> IQ {selectedModelOption.intelligence_rank || '?'}
                    </span>
                    <span className="flex items-center gap-1 rounded-lg border border-white/5 bg-black/20 px-2 py-1 text-zinc-300">
                      <Clock3 size={12} className="text-amber-300" /> {compactDate(selectedModelOption.release_date)}
                    </span>
                    <span className="flex items-center gap-1 rounded-lg border border-white/5 bg-black/20 px-2 py-1 text-zinc-300">
                      <Sparkles size={12} className="text-violet-300" /> {selectedModelOption.quality_label}
                    </span>
                  </div>
                </div>
              )}
              {modelSourceNote && (
                <p className="mt-3 text-xs leading-relaxed text-zinc-500">{modelSourceNote}</p>
              )}
              {modelsError && (
                <p className="mt-3 text-xs text-red-300">{modelsError}</p>
              )}
            </div>
          )}

          <label className="space-y-2 md:col-span-2">
            <span className="block text-sm text-zinc-400">API Key</span>
            <input
              type="password"
              value={aiConfig.apiKey}
              onChange={(e) => setAiConfig((prev) => ({ ...prev, apiKey: e.target.value }))}
              className="input-field font-mono"
              placeholder={backendAiDefaults?.has_api_key ? 'Using backend key for this session' : 'Provider API key'}
            />
            {backendAiDefaults?.has_api_key && !aiConfig.apiKey && (
              <span className="block text-xs text-green-400">Using backend key; raw key is not stored in browser.</span>
            )}
          </label>

          {['openai', 'openrouter', 'nvidia-nim', 'custom-openai-compatible'].includes(aiConfig.provider) && (
            <label className="space-y-2 md:col-span-2">
              <span className="block text-sm text-zinc-400">Base URL</span>
              <input
                value={aiConfig.baseUrl}
                onChange={(e) => setAiConfig((prev) => ({ ...prev, baseUrl: e.target.value }))}
                className="input-field font-mono"
                placeholder="Optional for OpenAI/OpenRouter/NVIDIA, required for custom"
              />
            </label>
          )}

          {aiConfig.provider === 'azure-openai' && (
            <>
              <label className="space-y-2">
                <span className="block text-sm text-zinc-400">Azure Endpoint</span>
                <input
                  value={aiConfig.azureEndpoint}
                  onChange={(e) => setAiConfig((prev) => ({ ...prev, azureEndpoint: e.target.value }))}
                  className="input-field font-mono"
                  placeholder="https://resource.openai.azure.com"
                />
              </label>
              <label className="space-y-2">
                <span className="block text-sm text-zinc-400">Deployment</span>
                <input
                  value={aiConfig.azureDeployment}
                  onChange={(e) => setAiConfig((prev) => ({ ...prev, azureDeployment: e.target.value }))}
                  readOnly={Boolean(selectedModelOption?.deployment)}
                  className="input-field font-mono"
                  placeholder="deployment-name"
                />
              </label>
              <label className="space-y-2">
                <span className="block text-sm text-zinc-400">API Version</span>
                <input
                  value={aiConfig.azureApiVersion}
                  onChange={(e) => setAiConfig((prev) => ({ ...prev, azureApiVersion: e.target.value }))}
                  className="input-field font-mono"
                  placeholder="2024-10-21"
                />
              </label>
            </>
          )}
        </div>
      </section>

      <section className="glass-panel p-6">
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-lg bg-pink-500/20 p-2 text-pink-400">
            <Upload size={20} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Upload-Post</h2>
            <p className="text-xs text-zinc-500">Publish generated clips to TikTok, Instagram Reels, and YouTube Shorts.</p>
          </div>
        </div>

        <div className="space-y-4">
          <label className="block space-y-2">
            <span className="block text-sm text-zinc-400">Upload-Post API Key</span>
            <input
              type="password"
              value={uploadPostKey}
              onChange={(e) => setUploadPostKey(e.target.value)}
              className="input-field font-mono"
              placeholder="Upload-Post API key"
            />
          </label>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={fetchUserProfiles}
              disabled={!uploadPostKey}
              className="rounded-xl bg-white/10 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Fetch profiles
            </button>
            <UserProfileSelector profiles={userProfiles} selectedUserId={uploadUserId} onSelect={setUploadUserId} />
          </div>
        </div>
      </section>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-background selection:bg-primary/30">
      <Sidebar />
      <main className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-white/5 bg-surface/50 px-6 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white">
              {activeTab === 'dashboard' ? 'Clip Generator' : 'Settings'}
            </h1>
            {activeTab === 'dashboard' && (
              <span className="rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs text-primary">
                {providerLabel}{aiConfig.model ? ` / ${aiConfig.model}` : ''}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {uploadPostKey && (
              <span className="hidden items-center gap-2 rounded-full border border-pink-500/20 bg-pink-500/10 px-3 py-1 text-xs text-pink-300 sm:flex">
                <Upload size={12} /> Upload-Post ready
              </span>
            )}
            {status !== 'idle' && (
              <button onClick={handleReset} className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-zinc-400 transition-colors hover:bg-white/5 hover:text-white">
                <RotateCcw size={14} /> New job
              </button>
            )}
          </div>
        </header>

        {activeTab === 'settings' && <SettingsView />}

        {activeTab === 'dashboard' && status === 'idle' && (
          <div className="flex flex-1 flex-col items-center justify-center overflow-y-auto p-6">
            <div className="mb-10 text-center">
              <div className="mb-6 inline-flex rounded-full border border-white/10 bg-white/5 p-3 text-primary">
                <FileVideo size={32} />
              </div>
              <h2 className="mb-3 text-4xl font-bold tracking-tight text-white">Cut long videos into shorts</h2>
              <p className="mx-auto max-w-xl text-zinc-400">
                Upload a long video or paste a YouTube URL. The selected AI provider finds clip-worthy moments; OpenShorts crops, edits, and prepares clips for publishing.
              </p>
            </div>
            <MediaInput onProcess={handleProcess} isProcessing={false} />
          </div>
        )}

        {activeTab === 'dashboard' && status !== 'idle' && (
          <div className="flex h-full min-h-0 flex-col md:flex-row">
            <section className="flex min-h-0 w-full flex-col border-r border-white/5 bg-[#0c0c0e] md:w-1/3">
              <div className="flex items-center justify-between border-b border-white/5 p-4">
                <h2 className="flex items-center gap-2 text-lg font-semibold text-white">
                  <Activity className={`text-primary ${status === 'processing' ? 'animate-pulse' : ''}`} size={20} />
                  Live Analysis
                </h2>
                <span className={`rounded-full border px-2 py-1 text-xs ${status === 'processing' ? 'border-primary/20 bg-primary/10 text-primary' : status === 'complete' ? 'border-green-500/20 bg-green-500/10 text-green-400' : 'border-red-500/20 bg-red-500/10 text-red-400'}`}>
                  {status}
                </span>
              </div>

              {processingMedia && (
                <ProcessingAnimation
                  media={processingMedia}
                  isComplete={status === 'complete'}
                  syncedTime={syncedTime}
                  isPlaying={isSyncedPlaying}
                  syncTrigger={syncTrigger}
                />
              )}

              <div className="min-h-0 flex-1 overflow-hidden border-t border-white/5">
                <button
                  onClick={() => setLogsVisible(!logsVisible)}
                  className="flex w-full items-center justify-between border-b border-white/5 p-3 text-xs font-medium uppercase tracking-wider text-zinc-500 hover:bg-white/5"
                >
                  <span className="flex items-center gap-2"><Terminal size={14} /> logs</span>
                  <span>{logsVisible ? 'hide' : 'show'}</span>
                </button>
                {logsVisible && (
                  <div className="h-full overflow-y-auto bg-black/20 p-4 font-mono text-xs text-zinc-400">
                    {logs.map((log, i) => <div key={i} className="mb-1">{log}</div>)}
                    {status === 'processing' && <div className="animate-pulse text-primary/70">_</div>}
                  </div>
                )}
              </div>
            </section>

            <section className="min-h-0 flex-1 overflow-y-auto p-6">
              {results?.clips?.length ? (
                <div className="space-y-6">
                  {results.cost_analysis && (
                    <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4 text-xs text-zinc-400">
                      Provider: <span className="text-white">{results.cost_analysis.provider || results.cost_analysis.model}</span>
                      {results.cost_analysis.model && <span> / {results.cost_analysis.model}</span>}
                    </div>
                  )}
                  {results.clips.map((clip, i) => (
                    <ResultCard
                      key={i}
                      clip={clip}
                      index={i}
                      jobId={jobId}
                      uploadPostKey={uploadPostKey}
                      uploadUserId={uploadUserId}
                      aiConfig={aiConfig}
                      onPlay={handleClipPlay}
                      onPause={() => setIsSyncedPlaying(false)}
                    />
                  ))}
                </div>
              ) : (
                <div className="flex h-full flex-col items-center justify-center space-y-4 text-zinc-500">
                  <div className="h-12 w-12 animate-spin rounded-full border-2 border-zinc-800 border-t-primary" />
                  <p>{status === 'processing' ? 'Finding clips...' : 'No clips generated yet.'}</p>
                </div>
              )}
            </section>
          </div>
        )}

        {sessionRecovered && (
          <div className="fixed bottom-4 right-4 rounded-xl border border-primary/20 bg-primary/10 px-4 py-3 text-sm text-primary shadow-xl">
            Session restored
          </div>
        )}

        {showKeyModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm" onClick={() => setShowKeyModal(false)}>
            <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#18181b] p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
              <h2 className="mb-2 text-lg font-bold text-white">AI provider key required</h2>
              <p className="mb-4 text-sm text-zinc-400">Set provider and API key in Settings or configure backend AI defaults before processing a video.</p>
              <button onClick={() => { setActiveTab('settings'); setShowKeyModal(false); }} className="w-full rounded-xl bg-primary px-4 py-3 text-sm font-bold text-white hover:bg-blue-600">
                Open settings
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
