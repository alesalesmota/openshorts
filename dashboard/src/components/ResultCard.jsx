import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  Calendar,
  CheckCircle,
  Clock,
  Download,
  Instagram,
  Loader2,
  Share2,
  Type,
  Video,
  Wand2,
  X,
  Youtube,
} from 'lucide-react';
import { getApiUrl } from '../config';
import { renderInBrowser } from '../lib/renderInBrowser';
import HookModal from './HookModal';
import SubtitleModal from './SubtitleModal';

const buildAiHeaders = (aiConfig) => {
  const headers = {
    'X-AI-Provider': aiConfig.provider,
    'X-AI-API-Key': aiConfig.apiKey,
  };
  if (aiConfig.model) headers['X-AI-Model'] = aiConfig.model;
  if (aiConfig.baseUrl) headers['X-AI-Base-URL'] = aiConfig.baseUrl;
  if (aiConfig.azureEndpoint) headers['X-Azure-OpenAI-Endpoint'] = aiConfig.azureEndpoint;
  if (aiConfig.azureDeployment) headers['X-Azure-OpenAI-Deployment'] = aiConfig.azureDeployment;
  if (aiConfig.azureApiVersion) headers['X-Azure-OpenAI-API-Version'] = aiConfig.azureApiVersion;
  if (aiConfig.provider === 'gemini') headers['X-Gemini-Key'] = aiConfig.apiKey;
  return headers;
};

const filenameFromUrl = (url) => {
  try {
    return decodeURIComponent(new URL(url, window.location.origin).pathname.split('/').pop());
  } catch {
    return url.split('/').pop();
  }
};

export default function ResultCard({ clip, index, jobId, uploadPostKey, uploadUserId, aiConfig, onPlay, onPause }) {
  const videoRef = React.useRef(null);
  const originalVideoUrl = getApiUrl(clip.video_url);
  const [currentVideoUrl, setCurrentVideoUrl] = useState(originalVideoUrl);
  const [serverFilename, setServerFilename] = useState(() => filenameFromUrl(originalVideoUrl));
  const [clipDuration, setClipDuration] = useState(clip.end && clip.start ? clip.end - clip.start : 30);
  const [activeLayers, setActiveLayers] = useState({ subtitles: null, hook: null, effects: null });
  const [showPostModal, setShowPostModal] = useState(false);
  const [showSubtitleModal, setShowSubtitleModal] = useState(false);
  const [showHookModal, setShowHookModal] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSubtitling, setIsSubtitling] = useState(false);
  const [isHooking, setIsHooking] = useState(false);
  const [editError, setEditError] = useState(null);
  const [posting, setPosting] = useState(false);
  const [postResult, setPostResult] = useState(null);
  const [postTitle, setPostTitle] = useState(clip.video_title_for_youtube_short || '');
  const [postDescription, setPostDescription] = useState(clip.video_description_for_tiktok || clip.video_description_for_instagram || '');
  const [isScheduling, setIsScheduling] = useState(false);
  const [scheduleDate, setScheduleDate] = useState('');
  const [platforms, setPlatforms] = useState({ tiktok: true, instagram: true, youtube: true });

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const updateDuration = () => {
      if (Number.isFinite(video.duration) && video.duration > 0) setClipDuration(video.duration);
    };
    video.addEventListener('loadedmetadata', updateDuration);
    return () => video.removeEventListener('loadedmetadata', updateDuration);
  }, [currentVideoUrl]);

  useEffect(() => {
    fetch(getApiUrl(`/api/clip/${jobId}/${index}/transcript`))
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.captions?.length) {
          setActiveLayers((prev) => ({
            ...prev,
            subtitles: {
              captions: data.captions,
              durationSec: data.durationSec || clipDuration,
              position: 'bottom',
              fontSize: 24,
              fontColor: '#FFFFFF',
              highlightColor: '#FFDD00',
              borderColor: '#000000',
              borderWidth: 2,
              bgColor: '#000000',
              bgOpacity: 0,
              animation: 'pop',
            },
          }));
        }
      })
      .catch(() => {});
  }, [jobId, index]);

  const currentFilename = () => {
    if (currentVideoUrl.startsWith('blob:')) return serverFilename;
    return filenameFromUrl(currentVideoUrl) || serverFilename;
  };

  const handleAutoEdit = async () => {
    if (aiConfig.provider !== 'gemini') {
      setEditError('Auto Edit currently requires Gemini video upload. Clip analysis is provider-agnostic.');
      return;
    }
    setIsEditing(true);
    setEditError(null);
    try {
      const effectsRes = await fetch(getApiUrl('/api/effects/generate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...buildAiHeaders(aiConfig) },
        body: JSON.stringify({ job_id: jobId, clip_index: index, input_filename: currentFilename() }),
      });
      if (!effectsRes.ok) throw new Error(await effectsRes.text());
      const effectsData = await effectsRes.json();
      const effects = effectsData.effects;

      const blobUrl = await renderInBrowser({
        videoUrl: currentVideoUrl,
        durationInSeconds: clipDuration,
        effects,
        subtitles: activeLayers.subtitles,
        hook: activeLayers.hook,
      });
      setActiveLayers((prev) => ({ ...prev, effects }));
      setCurrentVideoUrl(blobUrl);
    } catch (e) {
      setEditError(e.message || 'Auto Edit failed');
    } finally {
      setIsEditing(false);
    }
  };

  const handleSubtitle = async (options) => {
    setIsSubtitling(true);
    setEditError(null);
    try {
      if (options.remotion) {
        const newLayers = { ...activeLayers, subtitles: options.remotion };
        const blobUrl = await renderInBrowser({
          videoUrl: originalVideoUrl,
          durationInSeconds: clipDuration,
          subtitles: newLayers.subtitles,
          hook: newLayers.hook,
          effects: newLayers.effects,
        });
        setActiveLayers(newLayers);
        setCurrentVideoUrl(blobUrl);
        setShowSubtitleModal(false);
        return;
      }

      const res = await fetch(getApiUrl('/api/subtitle'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...options, job_id: jobId, clip_index: index, input_filename: currentFilename() }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const nextUrl = getApiUrl(data.new_video_url);
      setCurrentVideoUrl(nextUrl);
      setServerFilename(filenameFromUrl(nextUrl));
      setShowSubtitleModal(false);
    } catch (e) {
      setEditError(e.message || 'Subtitle generation failed');
    } finally {
      setIsSubtitling(false);
    }
  };

  const handleHook = async (hookData) => {
    setIsHooking(true);
    setEditError(null);
    try {
      if (hookData.remotion) {
        const newLayers = { ...activeLayers, hook: hookData.remotion };
        const blobUrl = await renderInBrowser({
          videoUrl: originalVideoUrl,
          durationInSeconds: clipDuration,
          subtitles: newLayers.subtitles,
          hook: newLayers.hook,
          effects: newLayers.effects,
        });
        setActiveLayers(newLayers);
        setCurrentVideoUrl(blobUrl);
        setShowHookModal(false);
        return;
      }

      const payload = typeof hookData === 'string' ? { text: hookData, position: 'top', size: 'M' } : hookData;
      const res = await fetch(getApiUrl('/api/hook'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, job_id: jobId, clip_index: index, input_filename: currentFilename() }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const nextUrl = getApiUrl(data.new_video_url);
      setCurrentVideoUrl(nextUrl);
      setServerFilename(filenameFromUrl(nextUrl));
      setShowHookModal(false);
    } catch (e) {
      setEditError(e.message || 'Hook generation failed');
    } finally {
      setIsHooking(false);
    }
  };

  const handlePost = async () => {
    if (!uploadPostKey || !uploadUserId) {
      setPostResult({ success: false, msg: 'Configure Upload-Post key and profile in Settings first.' });
      return;
    }
    const selectedPlatforms = Object.keys(platforms).filter((platform) => platforms[platform]);
    if (!selectedPlatforms.length) {
      setPostResult({ success: false, msg: 'Select at least one platform.' });
      return;
    }

    setPosting(true);
    setPostResult(null);
    try {
      const payload = {
        job_id: jobId,
        clip_index: index,
        api_key: uploadPostKey,
        user_id: uploadUserId,
        platforms: selectedPlatforms,
        title: postTitle,
        description: postDescription,
      };
      if (isScheduling && scheduleDate) {
        payload.scheduled_date = new Date(scheduleDate).toISOString();
        payload.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      }

      const res = await fetch(getApiUrl('/api/social/post'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      setPostResult({ success: true, msg: isScheduling ? 'Post scheduled.' : 'Upload started.' });
    } catch (e) {
      setPostResult({ success: false, msg: e.message || 'Publish failed' });
    } finally {
      setPosting(false);
    }
  };

  const handleDownload = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(currentVideoUrl);
      if (!response.ok) throw new Error('Download failed');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `clip-${index + 1}.mp4`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      window.open(currentVideoUrl, '_blank');
    }
  };

  return (
    <div className="flex min-h-[300px] flex-col overflow-hidden rounded-2xl border border-white/5 bg-surface transition-all hover:border-white/10 md:flex-row">
      <div className="relative aspect-[9/16] w-full shrink-0 bg-black md:w-[200px] md:aspect-auto">
        <video
          ref={videoRef}
          src={currentVideoUrl}
          controls
          loop
          className="h-full w-full object-cover"
          onPlay={() => onPlay?.(clip.start + (videoRef.current?.currentTime || 0))}
          onPause={() => onPause?.()}
        />
        <div className="absolute left-3 top-3 rounded-md border border-white/10 bg-black/60 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-white backdrop-blur-md">
          Clip {index + 1}
        </div>
        {isEditing && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/60 p-4 text-center backdrop-blur-sm">
            <Loader2 size={32} className="mb-3 animate-spin text-primary" />
            <span className="text-xs font-bold uppercase tracking-wider text-white">Auto Edit running</span>
          </div>
        )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-[#121214] p-5">
        <div className="mb-4">
          <h3 className="mb-2 line-clamp-2 break-words text-base font-bold leading-tight text-white">
            {clip.video_title_for_youtube_short || 'Generated Short'}
          </h3>
          <div className="flex flex-wrap gap-2 font-mono text-[10px] text-zinc-500">
            <span className="rounded border border-white/5 bg-white/5 px-1.5 py-0.5">{Math.floor((clip.end || 0) - (clip.start || 0))}s</span>
            <span className="rounded border border-white/5 bg-white/5 px-1.5 py-0.5">start {clip.start}s</span>
            <span className="rounded border border-white/5 bg-white/5 px-1.5 py-0.5">end {clip.end}s</span>
          </div>
        </div>

        <div className="mb-4 flex-1 space-y-3 overflow-y-auto pr-2">
          <div className="rounded-lg border border-white/5 bg-black/20 p-3">
            <div className="mb-1.5 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-red-400">
              <Youtube size={12} /> YouTube title
            </div>
            <p className="select-all break-words text-xs text-zinc-300">{clip.video_title_for_youtube_short || 'Generated Short'}</p>
          </div>
          <div className="rounded-lg border border-white/5 bg-black/20 p-3">
            <div className="mb-1.5 flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-zinc-400">
              <Video size={12} className="text-cyan-400" />
              <Instagram size={12} className="text-pink-400" />
              Caption
            </div>
            <p className="line-clamp-3 select-all break-words text-xs text-zinc-300 hover:line-clamp-none">
              {clip.video_description_for_tiktok || clip.video_description_for_instagram}
            </p>
          </div>
        </div>

        {editError && (
          <div className="mb-3 flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-2 text-[10px] text-red-400">
            <AlertCircle size={12} /> {editError}
          </div>
        )}

        <div className="mt-auto grid grid-cols-2 gap-3 border-t border-white/5 pt-4">
          <button onClick={handleAutoEdit} disabled={isEditing} className="flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 px-2 py-2 text-xs font-bold text-white transition-all hover:from-purple-500 hover:to-indigo-500 disabled:opacity-60">
            {isEditing ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
            {isEditing ? 'Editing...' : 'Auto Edit'}
          </button>
          <button onClick={() => setShowSubtitleModal(true)} disabled={isSubtitling} className="flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-yellow-600 to-orange-600 px-2 py-2 text-xs font-bold text-white transition-all hover:from-yellow-500 hover:to-orange-500 disabled:opacity-60">
            {isSubtitling ? <Loader2 size={14} className="animate-spin" /> : <Type size={14} />}
            {isSubtitling ? 'Adding...' : 'Subtitles'}
          </button>
          <button onClick={() => setShowHookModal(true)} disabled={isHooking} className="flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-amber-400 to-yellow-500 px-2 py-2 text-xs font-bold text-black transition-all hover:from-amber-300 hover:to-yellow-400 disabled:opacity-60">
            {isHooking ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
            {isHooking ? 'Adding...' : 'Viral Hook'}
          </button>
          <button onClick={() => setShowPostModal(true)} className="flex items-center justify-center gap-2 rounded-lg bg-primary px-2 py-2 text-xs font-bold text-white transition-colors hover:bg-blue-600">
            <Share2 size={14} /> Post
          </button>
          <button onClick={handleDownload} className="col-span-2 flex items-center justify-center gap-2 rounded-lg border border-white/5 bg-white/5 px-2 py-2 text-xs font-medium text-zinc-300 transition-colors hover:bg-white/10 hover:text-white">
            <Download size={14} /> Download
          </button>
        </div>
      </div>

      {showPostModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
          <div className="relative max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl border border-white/10 bg-[#121214] p-6 shadow-2xl">
            <button onClick={() => setShowPostModal(false)} className="absolute right-4 top-4 text-zinc-500 hover:text-white">
              <X size={20} />
            </button>
            <h3 className="mb-4 text-lg font-bold text-white">Post / Schedule</h3>
            {!uploadPostKey && (
              <div className="mb-4 flex items-start gap-2 rounded-lg border border-yellow-500/20 bg-yellow-500/10 p-3 text-xs text-yellow-200">
                <AlertCircle size={14} /> Configure Upload-Post in Settings first.
              </div>
            )}
            <div className="mb-6 space-y-4">
              <label className="block">
                <span className="mb-1 block text-xs font-bold text-zinc-400">Video title</span>
                <input value={postTitle} onChange={(e) => setPostTitle(e.target.value)} className="w-full rounded-lg border border-white/10 bg-black/40 p-2 text-sm text-white focus:border-primary/50 focus:outline-none" />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-bold text-zinc-400">Caption</span>
                <textarea value={postDescription} onChange={(e) => setPostDescription(e.target.value)} rows={4} className="w-full resize-none rounded-lg border border-white/10 bg-black/40 p-2 text-sm text-white focus:border-primary/50 focus:outline-none" />
              </label>
              <div className="rounded-lg border border-white/5 bg-white/5 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-medium text-white"><Calendar size={16} className="text-purple-400" /> Schedule</div>
                  <input type="checkbox" checked={isScheduling} onChange={(e) => setIsScheduling(e.target.checked)} />
                </div>
                {isScheduling && (
                  <div className="relative mt-3">
                    <input type="datetime-local" value={scheduleDate} onChange={(e) => setScheduleDate(e.target.value)} className="w-full rounded-lg border border-white/10 bg-black/40 p-2 pl-9 text-sm text-white [color-scheme:dark] focus:border-purple-500/50 focus:outline-none" />
                    <Clock size={14} className="absolute left-3 top-2.5 text-zinc-500" />
                  </div>
                )}
              </div>
              <div className="grid gap-2">
                {['tiktok', 'instagram', 'youtube'].map((platform) => (
                  <label key={platform} className="flex cursor-pointer items-center gap-3 rounded-lg border border-white/5 bg-white/5 p-3 text-sm capitalize text-white transition-colors hover:bg-white/10">
                    <input type="checkbox" checked={platforms[platform]} onChange={(e) => setPlatforms({ ...platforms, [platform]: e.target.checked })} />
                    {platform}
                  </label>
                ))}
              </div>
            </div>
            {postResult && (
              <div className={`mb-4 flex items-start gap-2 rounded-lg p-3 text-xs ${postResult.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                {postResult.success ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                {postResult.msg}
              </div>
            )}
            <button onClick={handlePost} disabled={posting || !uploadPostKey} className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3 font-bold text-white transition-all hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50">
              {posting ? <Loader2 size={16} className="animate-spin" /> : <Share2 size={16} />}
              {isScheduling ? 'Schedule Post' : 'Publish Now'}
            </button>
          </div>
        </div>
      )}

      <SubtitleModal
        isOpen={showSubtitleModal}
        onClose={() => setShowSubtitleModal(false)}
        onGenerate={handleSubtitle}
        isProcessing={isSubtitling}
        videoUrl={originalVideoUrl}
        jobId={jobId}
        clipIndex={index}
        existingHook={activeLayers.hook}
      />
      <HookModal
        isOpen={showHookModal}
        onClose={() => setShowHookModal(false)}
        onGenerate={handleHook}
        isProcessing={isHooking}
        videoUrl={originalVideoUrl}
        initialText={clip.viral_hook_text}
        durationInSeconds={clipDuration}
        existingSubtitles={activeLayers.subtitles}
      />
    </div>
  );
}
