import { useEffect, useMemo, useRef, useState } from "react";
import {
  closestCenter,
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import {
  arrayMove,
  rectSortingStrategy,
  SortableContext,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { createEditor, Editor, Element as SlateElement, Node, Path, Point, Range, Text, Transforms } from "slate";
import { Editable, RenderElementProps, Slate, ReactEditor, useSelected, useSlateStatic, withReact } from "slate-react";


type HealthState = "loading" | "ready" | "error";
type SaveState = "idle" | "saving" | "saved" | "error";
type JobState = "idle" | "submitting" | "polling" | "completed" | "error";
type ProjectSaveStatus = "idle" | "saving" | "saved" | "error";

type Settings = {
  api_key: string;
  api_key_gpt_image_2: string;
  api_key_gpt_image_2_vip: string;
  api_key_nano_banana_pro: string;
  default_model: string;
  default_ratio: string;
  default_resolution: string;
  output_dir: string;
  project_dirs: ProjectDir[];
};

type ProjectDir = {
  name: string;
  path: string;
};

type JobResponse = {
  id: string;
  model: string;
  prompt: string;
  size: string;
  resolution: string;
  quality: string;
  background: string;
  moderation: string;
  output_format: string;
  output_compression: number | null;
  n: number;
  image_urls: string[];
  reference_image_urls: string[];
  mask_url: string | null;
  status: string;
  remote_task_id: string | null;
  result_paths: string[];
  error_message: string | null;
  created_at: number;
  updated_at: number;
};

type PendingJobDraft = {
  id: string;
  model: string;
  prompt: string;
  resolution: string;
  n: number;
  created_at: number;
};

type FormState = {
  prompt: string;
  model: string;
  size: string;
  resolution: string;
  n: number;
  quality: string;
  moderation: string;
  background: string;
  output_format: string;
  reference_images: string[];
  reference_names: string[];
  reference_ids: string[];
};

type PromptReferenceTrigger = {
  range: Range;
  query: string;
  matches: number[];
};

type PromptTextNode = {
  text: string;
};

type PromptReferenceElement = {
  type: "reference";
  referenceNumber: number;
  children: PromptTextNode[];
};

type PromptParagraphElement = {
  type: "paragraph";
  children: PromptDescendant[];
};

type PromptDescendant = PromptParagraphElement | PromptReferenceElement | PromptTextNode;


const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:38381";
const MODEL_OPTIONS = [
  "gpt-image-2",
  "gpt-image-2-vip",
  "gemini-3-pro-image-preview",
] as const;
const LEGACY_MODEL_ALIASES: Record<string, string> = {
  "gpt-image-2-official": "gpt-image-2",
  "gemini-3-pro-image-preview-official": "gemini-3-pro-image-preview",
};
const BASIC_RATIO_OPTIONS = [
  "1:1",
  "16:9",
  "9:16",
  "21:9",
  "5:4",
  "4:3",
  "3:2",
  "2:3",
  "3:4",
  "4:5",
] as const;
const GPT_BASIC_RATIO_OPTIONS = ["auto", ...BASIC_RATIO_OPTIONS] as const;
const GPT_RATIO_OPTIONS = [
  "auto",
  "1:1",
  "3:2",
  "2:3",
  "4:3",
  "3:4",
  "5:4",
  "4:5",
  "16:9",
  "9:16",
  "2:1",
  "1:2",
  "21:9",
  "9:21",
] as const;
const GEMINI_RATIO_OPTIONS = [
  "1:1",
  "2:3",
  "3:2",
  "3:4",
  "4:3",
  "4:5",
  "5:4",
  "9:16",
  "16:9",
  "21:9",
] as const;
const RESOLUTION_OPTIONS = ["1K", "2K", "4K"] as const;
const IMAGE_COUNT_OPTIONS = [1, 2, 3, 4] as const;
const QUALITY_OPTIONS = ["auto", "low", "medium", "high"] as const;
const MODERATION_OPTIONS = ["auto", "low"] as const;
const OUTPUT_FORMAT_OPTIONS = ["png", "jpeg", "webp"] as const;
const DEFAULT_SETTINGS: Settings = {
  api_key: "",
  api_key_gpt_image_2: "",
  api_key_gpt_image_2_vip: "",
  api_key_nano_banana_pro: "",
  default_model: "gpt-image-2",
  default_ratio: "1:1",
  default_resolution: "1K",
  output_dir: "",
  project_dirs: [],
};
const DEFAULT_EDITOR_RATIO = 0.6;
const MIN_PANEL_RATIO = 0.32;
const MAX_PANEL_RATIO = 0.68;
const MIN_PREVIEW_PANEL_WIDTH_PX = 360;
const MIN_EDITOR_PANEL_WIDTH_PX = 452;
const REFERENCE_DRAFT_STORAGE_KEY = "aigc-reference-draft-v1";
const FAVORITE_JOB_IDS_STORAGE_KEY = "aigc-favorite-job-ids-v1";
const MAX_REFERENCE_IMAGE_EDGE = 1536;
const REFERENCE_IMAGE_QUALITY = 0.82;
const EMPTY_PROMPT_DOCUMENT: PromptParagraphElement[] = [
  {
    type: "paragraph",
    children: [{ text: "" }],
  },
];
const PROMPT_REFERENCE_ANCHOR = "\uFEFF";

const withPromptReferences = (editor: ReactEditor & Editor) => {
  const { isInline, isVoid } = editor;
  editor.isInline = (element) =>
    isPromptReferenceElement(element) ? true : isInline(element);
  editor.isVoid = (element) =>
    isPromptReferenceElement(element) ? true : isVoid(element);
  return editor;
};


export default function App() {
  const [health, setHealth] = useState<HealthState>("loading");
  const [healthMessage, setHealthMessage] = useState("正在检查本地后端...");
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveMessage, setSaveMessage] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [editorWidthRatio, setEditorWidthRatio] = useState(DEFAULT_EDITOR_RATIO);
  const [galleryDensity, setGalleryDensity] = useState(4);
  const [isResizingPanels, setIsResizingPanels] = useState(false);
  const [form, setForm] = useState<FormState>({
    prompt: "",
    model: DEFAULT_SETTINGS.default_model,
    size: DEFAULT_SETTINGS.default_ratio,
    resolution: DEFAULT_SETTINGS.default_resolution,
    n: 1,
    quality: "auto",
    moderation: "auto",
    background: "auto",
    output_format: "png",
    reference_images: [],
    reference_names: [],
    reference_ids: [],
  });
  const [jobState, setJobState] = useState<JobState>("idle");
  const [jobMessage, setJobMessage] = useState("准备开始生成。");
  const [currentJob, setCurrentJob] = useState<JobResponse | null>(null);
  const [history, setHistory] = useState<JobResponse[]>([]);
  const [viewerJobId, setViewerJobId] = useState<string | null>(null);
  const [favoriteJobIds, setFavoriteJobIds] = useState<string[]>(() => loadFavoriteJobIds());
  const [galleryMode, setGalleryMode] = useState<"all" | "favorites">("all");
  const [projectSaveState, setProjectSaveState] = useState<ProjectSaveStatus>("idle");
  const [projectSaveMessage, setProjectSaveMessage] = useState("");
  const [savingProjectName, setSavingProjectName] = useState<string | null>(null);
  const [referencePickerIndex, setReferencePickerIndex] = useState(0);
  const [promptDocument, setPromptDocument] =
    useState<PromptParagraphElement[]>(EMPTY_PROMPT_DOCUMENT);
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);
  const pollTimerRef = useRef<number | null>(null);
  const projectSaveToastTimerRef = useRef<number | null>(null);
  const workspaceShellRef = useRef<HTMLDivElement | null>(null);
  const promptEditor = useMemo(
    () => withPromptReferences(withReact(createEditor() as ReactEditor & Editor)),
    [],
  );
  const referencePromptMatch = getReferencePromptTrigger(
    promptEditor,
    form.reference_images.length,
  );
  const referencePickerItems =
    referencePromptMatch?.matches.map((referenceNumber) => ({
      referenceNumber,
      image: form.reference_images[referenceNumber - 1],
      name: form.reference_names[referenceNumber - 1] ?? `参考图 ${referenceNumber}`,
    })) ?? [];

  useEffect(() => {
    const savedDraft = loadReferenceDraft();
    if (!savedDraft) {
      return;
    }

    setPromptDocument(deserializePrompt(savedDraft.prompt, savedDraft.images));
    setForm((current) => ({
      ...current,
      prompt: savedDraft.prompt,
      model: normalizeModelValue(savedDraft.model),
      size: savedDraft.size,
      resolution: savedDraft.resolution,
      n: savedDraft.n,
      quality: savedDraft.quality,
      moderation: savedDraft.moderation,
      reference_images: savedDraft.images,
      reference_names: savedDraft.names,
      reference_ids: savedDraft.ids,
    }));
  }, []);

  useEffect(() => {
    const promptText = serializePrompt(promptDocument);
    if (promptText !== form.prompt) {
      setForm((current) => ({
        ...current,
        prompt: promptText,
      }));
      return;
    }

    saveReferenceDraft({
      prompt: promptText,
      model: form.model,
      size: form.size,
      resolution: form.resolution,
      n: form.n,
      quality: form.quality,
      moderation: form.moderation,
      images: form.reference_images,
      names: form.reference_names,
      ids: form.reference_ids,
    });
  }, [
    form.prompt,
    promptDocument,
    form.model,
    form.size,
    form.resolution,
    form.n,
    form.quality,
    form.moderation,
    form.reference_images,
    form.reference_names,
    form.reference_ids,
  ]);

  useEffect(() => {
    saveFavoriteJobIds(favoriteJobIds);
  }, [favoriteJobIds]);

  useEffect(() => {
    let cancelled = false;

    async function loadPageData() {
      try {
        const [healthResponse, settingsResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/api/health`),
          fetch(`${API_BASE_URL}/api/settings`),
        ]);

        if (!healthResponse.ok) {
          throw new Error(`本地后端健康检查失败（${healthResponse.status}）`);
        }

        if (!settingsResponse.ok) {
          throw new Error(`设置加载失败（${settingsResponse.status}）`);
        }

        const healthData: { status: string; service: string } =
          await healthResponse.json();
        const settingsData: Settings = await settingsResponse.json();
        const historyData = await fetchJobHistory();

        if (!cancelled) {
          setHealth("ready");
          setHealthMessage(
            healthData.status === "ok"
              ? "本地后端运行正常"
              : `${healthData.service}: ${healthData.status}`,
          );
          setSettings(settingsData);
          setHistory(historyData);
          setForm((current) =>
            current.prompt.trim() !== "" ||
            current.reference_images.length > 0 ||
            current.model !== DEFAULT_SETTINGS.default_model ||
            current.size !== DEFAULT_SETTINGS.default_ratio ||
            current.resolution !== DEFAULT_SETTINGS.default_resolution ||
            current.n !== 1 ||
            current.quality !== "auto" ||
            current.moderation !== "auto"
              ? current
              : {
                  ...current,
                  model: settingsData.default_model,
                  size: settingsData.default_ratio,
                  resolution: settingsData.default_resolution,
                },
          );
        }
      } catch (error) {
        if (!cancelled) {
          setHealth("error");
          setHealthMessage(error instanceof Error ? error.message : "加载失败");
        }
      }
    }

    void loadPageData();

    return () => {
      cancelled = true;
      if (pollTimerRef.current !== null) {
        window.clearTimeout(pollTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (projectSaveToastTimerRef.current !== null) {
      window.clearTimeout(projectSaveToastTimerRef.current);
      projectSaveToastTimerRef.current = null;
    }

    if (projectSaveState !== "saved" && projectSaveState !== "error") {
      return;
    }

    projectSaveToastTimerRef.current = window.setTimeout(() => {
      setProjectSaveState("idle");
      setProjectSaveMessage("");
    }, 3000);

    return () => {
      if (projectSaveToastTimerRef.current !== null) {
        window.clearTimeout(projectSaveToastTimerRef.current);
        projectSaveToastTimerRef.current = null;
      }
    };
  }, [projectSaveMessage, projectSaveState]);

  useEffect(() => {
    setReferencePickerIndex(0);
  }, [referencePromptMatch?.query, referencePromptMatch?.matches.join(",")]);

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }

      if (
        target.closest(
          ".dropdown-field, .settings-popover-shell, .panel-field, .selector-modal-shell",
        )
      ) {
        return;
      }

      setOpenDropdown(null);
      setSettingsOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
    };
  }, []);

  useEffect(() => {
    if (!isResizingPanels) {
      return;
    }

    function updatePanelRatio(clientX: number) {
      const shell = workspaceShellRef.current;
      if (!shell) {
        return;
      }

      const bounds = shell.getBoundingClientRect();
      const rawRatio = (clientX - bounds.left) / bounds.width;
      const minRatio = Math.max(MIN_PANEL_RATIO, MIN_EDITOR_PANEL_WIDTH_PX / bounds.width);
      const maxRatio = Math.min(MAX_PANEL_RATIO, 1 - MIN_PREVIEW_PANEL_WIDTH_PX / bounds.width);
      const safeRatio = minRatio <= maxRatio ? clamp(rawRatio, minRatio, maxRatio) : 0.5;
      setEditorWidthRatio(safeRatio);
    }

    function handlePointerMove(event: PointerEvent) {
      updatePanelRatio(event.clientX);
    }

    function handlePointerUp() {
      setIsResizingPanels(false);
    }

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);

    return () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [isResizingPanels]);

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaveState("saving");
    setSaveMessage("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(settings),
      });

      if (!response.ok) {
        throw new Error(`设置保存失败（${response.status}）`);
      }

      const data: Settings = await response.json();
      setSettings(data);
      setSaveState("saved");
      setSaveMessage("设置已保存到本地。");
    } catch (error) {
      setSaveState("error");
      setSaveMessage(error instanceof Error ? error.message : "保存失败");
    }
  }

  async function requestSystemDirectory() {
    if (window.showDirectoryPicker) {
      const directoryHandle = await window.showDirectoryPicker();
      return directoryHandle.name;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/system/pick-directory`, {
        method: "POST",
      });

      if (!response.ok) {
        const errorBody = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        throw new Error(errorBody?.detail ?? `打开文件夹选择器失败（${response.status}）`);
      }

      const data: { path: string } = await response.json();
      return data.path;
    } catch (error) {
      throw error instanceof Error ? error : new Error("选择文件夹失败");
    }
  }

  async function handleChooseOutputDir() {
    try {
      const path = await requestSystemDirectory();
      if (!path) {
        return;
      }

      setSettings((current) => ({
        ...current,
        output_dir: path,
      }));
      setSaveState("idle");
      setSaveMessage("已选择图片保存文件夹。");
    } catch (error) {
      setSaveState("error");
      setSaveMessage(error instanceof Error ? error.message : "选择文件夹失败");
    }
  }

  async function handleChooseProjectDir(index: number) {
    try {
      const path = await requestSystemDirectory();
      if (!path) {
        return;
      }

      setSettings((current) => ({
        ...current,
        project_dirs: current.project_dirs.map((project, itemIndex) =>
          itemIndex === index
            ? {
                ...project,
                path,
              }
            : project,
        ),
      }));
      setSaveState("idle");
      setSaveMessage("已选择项目文件夹。");
    } catch (error) {
      setSaveState("error");
      setSaveMessage(error instanceof Error ? error.message : "选择项目文件夹失败");
    }
  }

  function handleAddProjectDir() {
    setSettings((current) => {
      if (current.project_dirs.length >= 4) {
        setSaveState("error");
        setSaveMessage("最多只能添加 4 个项目文件夹。");
        return current;
      }

      return {
        ...current,
        project_dirs: [...current.project_dirs, { name: "", path: "" }],
      };
    });
  }

  async function appendReferenceFiles(files: File[]) {
    if (files.length === 0) {
      return;
    }

    const encodedImages = await Promise.all(
      files.map((file) => readFileAsCompressedDataUrl(file)),
    );
    setForm((current) => ({
      ...current,
      reference_images: [...current.reference_images, ...encodedImages],
      reference_names: [
        ...current.reference_names,
        ...files.map((file) => file.name || "粘贴图片"),
      ],
      reference_ids: [
        ...current.reference_ids,
        ...files.map((file, index) =>
          createReferenceImageId(
            file.name || "pasted-image",
            encodedImages[index],
            current.reference_ids.length + index,
          ),
        ),
      ],
    }));
  }

  function appendReferenceImageUrl(imageUrl: string, name: string) {
    setForm((current) => {
      if (current.reference_images.includes(imageUrl)) {
        return current;
      }

      return {
        ...current,
        reference_images: [...current.reference_images, imageUrl],
        reference_names: [...current.reference_names, name],
        reference_ids: [
          ...current.reference_ids,
          createReferenceImageId(name, imageUrl, current.reference_ids.length),
        ],
      };
    });
  }

  async function handleGenerate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setJobState("submitting");
    setJobMessage("正在提交生成任务...");
    setCurrentJob(null);

    const preflightError = validateBeforeSubmit(form);
    if (preflightError) {
      setJobState("error");
      setJobMessage(preflightError);
      return;
    }

    const queuedDraft: PendingJobDraft = {
      id: `pending-${Date.now()}`,
      model: form.model,
      prompt: form.prompt,
      resolution: form.resolution,
      n: form.n,
      created_at: Date.now(),
    };
    const queuedJob = createPendingGalleryJob(queuedDraft);
    setHistory((current) => mergeJobIntoHistory(current, queuedJob));

    const payload = {
      prompt: form.prompt,
      model: form.model,
      size: form.size,
      resolution: form.resolution,
      quality: form.quality,
      moderation: form.moderation,
      background: "auto",
      output_format: "png",
      output_compression: null,
      n: form.n,
      image_urls: form.reference_images,
      mask_url: null,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/api/jobs`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorBody = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        throw new Error(errorBody?.detail ?? `提交失败（${response.status}）`);
      }

      const data: JobResponse = await response.json();
      setCurrentJob(data);
      setHistory((current) =>
        mergeJobIntoHistory(current.filter((job) => job.id !== queuedJob.id), data),
      );
      setJobState(data.status === "completed" ? "completed" : "polling");
      setJobMessage(
        data.status === "completed"
          ? `任务 ${data.id} 已完成。`
          : `任务 ${data.id} 已提交。`,
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "提交失败";
      setHistory((current) =>
        mergeJobIntoHistory(
          current.filter((job) => job.id !== queuedJob.id),
          createFailedGalleryJob(queuedJob, message),
        ),
      );
      setJobState("error");
      setJobMessage(message);
    }
  }

  async function handleSaveImageToProject(sourcePath: string, projectName: string) {
    setProjectSaveState("saving");
    setProjectSaveMessage("");
    setSavingProjectName(projectName);

    try {
      const response = await fetch(`${API_BASE_URL}/api/projects/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source_path: sourcePath,
          project_name: projectName,
        }),
      });

      if (!response.ok) {
        const errorBody = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        throw new Error(errorBody?.detail ?? `保存到项目失败（${response.status}）`);
      }

      const data: { saved_path: string; project_name: string } = await response.json();
      setProjectSaveState("saved");
      setProjectSaveMessage(`已保存到 ${data.project_name}`);
      void navigator.clipboard.writeText(data.saved_path);
    } catch (error) {
      setProjectSaveState("error");
      setProjectSaveMessage(error instanceof Error ? error.message : "保存到项目失败");
    } finally {
      setSavingProjectName(null);
    }
  }

  function handleReuseJob(job: JobResponse) {
    const referenceImages = getJobReferenceImages(job);
    setPromptDocument(deserializePrompt(job.prompt, referenceImages));
    setForm((current) => ({
      ...current,
      prompt: job.prompt,
      model: normalizeModelValue(job.model),
      size: job.size,
      resolution: job.resolution,
      n: job.n,
      quality: job.quality,
      moderation: job.model === "gpt-image-2" ? "low" : current.moderation,
      reference_images: [...referenceImages],
      reference_names: referenceImages.map((_, index) => `参考图 ${index + 1}`),
      reference_ids: referenceImages.map((image, index) =>
        createReferenceImageId(`reference-${index + 1}`, image, index),
      ),
    }));
    setViewerJobId(null);
  }

  async function handleDeleteJob(jobId: string) {
    setDeletingJobId(jobId);
    try {
      let response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`, {
        method: "DELETE",
      });
      if (response.status === 405) {
        response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/delete`, {
          method: "POST",
        });
      }
      if (!response.ok) {
        const errorBody = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        throw new Error(errorBody?.detail ?? `删除失败（${response.status}）`);
      }

      const refreshedHistory = await fetchJobHistory();
      setHistory(refreshedHistory);
      if (currentJob?.id === jobId) {
        setCurrentJob(null);
      }
      if (viewerJobId === jobId) {
        setViewerJobId(null);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "删除失败";
      setSaveState("error");
      setSaveMessage(message);
      window.alert(message);
    } finally {
      setDeletingJobId(null);
    }
  }

  function applyReferenceSelection(referenceNumber: number) {
    if (!referencePromptMatch) {
      return;
    }

    Transforms.select(promptEditor, referencePromptMatch.range);
    Transforms.delete(promptEditor);
    insertPromptReference(promptEditor, referenceNumber);
    setReferencePickerIndex(0);
    ReactEditor.focus(promptEditor);
  }

  async function fetchJobHistory() {
    const response = await fetch(`${API_BASE_URL}/api/jobs`);

    if (!response.ok) {
      throw new Error(`历史记录加载失败（${response.status}）`);
    }

    return (await response.json()) as JobResponse[];
  }

  const ratioOptions =
    form.model === "gpt-image-2"
      ? GPT_BASIC_RATIO_OPTIONS
      : form.model === "gpt-image-2-vip"
        ? BASIC_RATIO_OPTIONS
        : BASIC_RATIO_OPTIONS;

  const modelLabel = formatModelLabel(form.model);
  const qualityLabel = formatQualityLabel(form.quality);
  const moderationLabel = formatModerationLabel(form.moderation);
  const allGalleryJobs = currentJob
    ? mergeJobIntoHistory(history, currentJob)
    : history;
  const galleryJobs =
    galleryMode === "favorites"
      ? allGalleryJobs.filter((job) => favoriteJobIds.includes(job.id))
      : allGalleryJobs;
  const galleryCardSize = Math.max(144, 320 - galleryDensity * 22);
  const galleryGridClassName =
    galleryDensity >= 7 ? "gallery-grid gallery-grid-dense" : "gallery-grid";
  const activeProjectDirs = settings.project_dirs.filter(
    (project) => project.name.trim() !== "" && project.path.trim() !== "",
  );
  const viewerIndex = viewerJobId
    ? galleryJobs.findIndex((job) => job.id === viewerJobId)
    : -1;
  const viewerJob = viewerIndex >= 0 ? galleryJobs[viewerIndex] : null;

  function toggleFavoriteJob(jobId: string) {
    setFavoriteJobIds((current) =>
      current.includes(jobId)
        ? current.filter((item) => item !== jobId)
        : [jobId, ...current],
    );
  }

  return (
    <main className="app-shell">
      <div
        ref={workspaceShellRef}
        className="workspace-shell"
        style={
          {
            "--editor-panel-width": `${editorWidthRatio * 100}%`,
            "--gallery-card-size": `${galleryCardSize}px`,
          } as React.CSSProperties
        }
      >
        <section className="workspace-section workspace-editor">
          <div className="editor-toolbar">
            <div className="settings-popover-shell">
              <button
                type="button"
                className="ghost-button icon-button"
                onClick={() => setSettingsOpen((current) => !current)}
                aria-label={settingsOpen ? "收起设置" : "打开设置"}
                title={settingsOpen ? "收起设置" : "打开设置"}
              >
                <SettingsIcon />
              </button>

              {settingsOpen ? (
                <div
                  className="settings-backdrop"
                  onClick={() => setSettingsOpen(false)}
                  role="presentation"
                >
                  <form
                    className="settings-form settings-popover"
                    onSubmit={handleSave}
                    onClick={(event) => event.stopPropagation()}
                  >
                    <div className="section-header">
                      <h2>设置</h2>
                      <span className={`save-message save-${saveState}`}>{saveMessage}</span>
                    </div>

                    <div className="compact-grid compact-grid-settings">
                      <label className="field">
                        <span>image-2官转版 Key</span>
                        <input
                          type="password"
                          value={settings.api_key_gpt_image_2}
                          onChange={(event) =>
                            setSettings((current) => ({
                              ...current,
                              api_key_gpt_image_2: event.target.value,
                            }))
                          }
                          placeholder="粘贴 image-2官转版 token / key"
                        />
                      </label>

                      <label className="field">
                        <span>image-2-VIP Key</span>
                        <input
                          type="password"
                          value={settings.api_key_gpt_image_2_vip}
                          onChange={(event) =>
                            setSettings((current) => ({
                              ...current,
                              api_key_gpt_image_2_vip: event.target.value,
                            }))
                          }
                          placeholder="粘贴 image-2-VIP token / key"
                        />
                      </label>

                      <label className="field">
                        <span>nanobananapro Key</span>
                        <input
                          type="password"
                          value={settings.api_key_nano_banana_pro}
                          onChange={(event) =>
                            setSettings((current) => ({
                              ...current,
                              api_key_nano_banana_pro: event.target.value,
                            }))
                          }
                          placeholder="粘贴 nanobananapro token / key"
                        />
                      </label>

                      <label className="field">
                        <span>兼容旧单 Key</span>
                        <input
                          type="password"
                          value={settings.api_key}
                          onChange={(event) =>
                            setSettings((current) => ({
                              ...current,
                              api_key: event.target.value,
                            }))
                          }
                          placeholder="不单独填写时可留作兜底"
                        />
                      </label>

                      <label className="field">
                        <span>默认模型</span>
                        <select
                          value={settings.default_model}
                          onChange={(event) =>
                            setSettings((current) => ({
                              ...current,
                              default_model: event.target.value,
                              default_ratio:
                                event.target.value === "gemini-3-pro-image-preview" &&
                                current.default_ratio === "auto"
                                  ? "1:1"
                                  : current.default_ratio,
                            }))
                          }
                        >
                          {MODEL_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                              {formatModelLabel(option)}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label className="field field-output-dir">
                        <span>图片保存文件夹</span>
                        <div className="inline-field-action">
                          <input
                            type="text"
                            value={settings.output_dir}
                            onChange={(event) =>
                              setSettings((current) => ({
                                ...current,
                                output_dir: event.target.value,
                              }))
                            }
                            placeholder="/Users/you/Pictures/AIGC"
                          />
                          <button
                            type="button"
                            className="ghost-button"
                            onClick={() => void handleChooseOutputDir()}
                          >
                            选择文件夹
                          </button>
                        </div>
                      </label>

                      <div className="field field-output-dir">
                        <span>项目文件夹</span>
                        <div className="project-folder-list">
                          {settings.project_dirs.map((project, index) => (
                            <div key={index} className="project-folder-row">
                              <input
                                type="text"
                                value={project.name}
                                onChange={(event) =>
                                  setSettings((current) => ({
                                    ...current,
                                    project_dirs: current.project_dirs.map((item, itemIndex) =>
                                      itemIndex === index
                                        ? { ...item, name: event.target.value }
                                        : item,
                                    ),
                                  }))
                                }
                                placeholder="项目名称"
                              />
                              <input
                                type="text"
                                value={project.path}
                                onChange={(event) =>
                                  setSettings((current) => ({
                                    ...current,
                                    project_dirs: current.project_dirs.map((item, itemIndex) =>
                                      itemIndex === index
                                        ? { ...item, path: event.target.value }
                                        : item,
                                    ),
                                  }))
                                }
                                placeholder="/Users/you/Pictures/Project"
                              />
                              <button
                                type="button"
                                className="ghost-button"
                                onClick={() => void handleChooseProjectDir(index)}
                              >
                                选择
                              </button>
                              <button
                                type="button"
                                className="ghost-button"
                                onClick={() =>
                                  setSettings((current) => ({
                                    ...current,
                                    project_dirs: current.project_dirs.filter(
                                      (_, itemIndex) => itemIndex !== index,
                                    ),
                                  }))
                                }
                              >
                                删除
                              </button>
                            </div>
                          ))}
                          <button
                            type="button"
                            className="ghost-button project-folder-add"
                            onClick={handleAddProjectDir}
                            disabled={settings.project_dirs.length >= 4}
                          >
                            添加项目文件夹
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="actions">
                      <button type="submit" className="save-button">
                        {saveState === "saving" ? "保存中..." : "保存设置"}
                      </button>
                    </div>
                  </form>
                </div>
              ) : null}
            </div>
          </div>

          <form className="generator-form" onSubmit={handleGenerate}>
            <div className="compact-grid compact-grid-full">
              <label className="field">
                <span>参考图上传</span>
                <FileUploadField
                  ids={form.reference_ids}
                  files={form.reference_names}
                  images={form.reference_images}
                  onFilesSelected={appendReferenceFiles}
                  onClear={() =>
                    setForm((current) => ({
                      ...current,
                      reference_images: [],
                      reference_names: [],
                      reference_ids: [],
                    }))
                  }
                  onRemove={(index) =>
                    setForm((current) => ({
                      ...current,
                      reference_images: current.reference_images.filter(
                        (_, itemIndex) => itemIndex !== index,
                      ),
                      reference_names: current.reference_names.filter(
                        (_, itemIndex) => itemIndex !== index,
                      ),
                      reference_ids: current.reference_ids.filter(
                        (_, itemIndex) => itemIndex !== index,
                      ),
                    }))
                  }
                  onReorder={(fromIndex, toIndex) =>
                    setForm((current) => ({
                      ...current,
                      reference_images: arrayMove(current.reference_images, fromIndex, toIndex),
                      reference_names: arrayMove(current.reference_names, fromIndex, toIndex),
                      reference_ids: arrayMove(current.reference_ids, fromIndex, toIndex),
                    }))
                  }
                />
              </label>
            </div>

            <label className="field field-wide">
              <div className="prompt-field-shell">
                {referencePickerItems.length > 0 ? (
                  <div className="prompt-reference-menu" role="listbox" aria-label="参考图引用">
                    {referencePickerItems.map((item, index) => (
                      <button
                        key={item.referenceNumber}
                        type="button"
                        className={`prompt-reference-option ${
                          index === referencePickerIndex ? "prompt-reference-option-active" : ""
                        }`}
                        onMouseDown={(event) => {
                          event.preventDefault();
                          applyReferenceSelection(item.referenceNumber);
                        }}
                      >
                        <img
                          className="prompt-reference-thumb"
                          src={item.image}
                          alt={`图片${item.referenceNumber}`}
                        />
                        <span className="prompt-reference-copy">
                          <strong>{`图片${item.referenceNumber}`}</strong>
                          <span>{item.name}</span>
                        </span>
                      </button>
                    ))}
                  </div>
                ) : null}

                <Slate
                  key={serializePrompt(promptDocument)}
                  editor={promptEditor}
                  initialValue={promptDocument}
                  onChange={(value) => {
                    setPromptDocument(value as PromptParagraphElement[]);
                  }}
                >
                  <Editable
                    className="prompt-editor"
                    placeholder="描述你要生成的画面..."
                    renderElement={(props) => (
                      <PromptElement
                        {...props}
                        referenceImages={form.reference_images}
                        referenceNames={form.reference_names}
                      />
                    )}
                    onKeyDown={(event) => {
                      if (event.key === "Backspace" || event.key === "Delete") {
                        const deletionTarget = getPromptReferenceDeletionTarget(
                          promptEditor,
                          event.key,
                        );
                        if (deletionTarget) {
                          event.preventDefault();
                          if (isPromptReferenceSelected(promptEditor, deletionTarget.range)) {
                            removePromptReference(promptEditor, deletionTarget.path);
                            return;
                          }

                          Transforms.select(promptEditor, deletionTarget.range);
                          return;
                        }
                      }

                      if (referencePickerItems.length === 0) {
                        return;
                      }

                      if (event.key === "ArrowDown") {
                        event.preventDefault();
                        setReferencePickerIndex((current) =>
                          (current + 1) % referencePickerItems.length,
                        );
                        return;
                      }

                      if (event.key === "ArrowUp") {
                        event.preventDefault();
                        setReferencePickerIndex((current) =>
                          (current - 1 + referencePickerItems.length) % referencePickerItems.length,
                        );
                        return;
                      }

                      if (event.key === "Enter" || event.key === "Tab") {
                        const activeItem =
                          referencePickerItems[
                            Math.min(referencePickerIndex, referencePickerItems.length - 1)
                          ];
                        if (!activeItem) {
                          return;
                        }

                        event.preventDefault();
                        applyReferenceSelection(activeItem.referenceNumber);
                      }
                    }}
                    onPaste={(event) => {
                      const items = Array.from(event.clipboardData?.items ?? []);
                      const files = items
                        .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
                        .map((item) => item.getAsFile())
                        .filter((file): file is File => file !== null);

                      if (files.length === 0) {
                        return;
                      }

                      event.preventDefault();
                      void appendReferenceFiles(files);
                    }}
                  />
                </Slate>
              </div>
            </label>

            <div className="option-strip">
              <DropdownField
                id="model"
                label="模型"
                valueLabel={modelLabel}
                isOpen={openDropdown === "model"}
                onToggle={() =>
                  setOpenDropdown((current) => (current === "model" ? null : "model"))
                }
                options={MODEL_OPTIONS.map((option) => ({
                  value: option,
                  label: formatModelLabel(option),
                }))}
                onSelect={(value) => {
                  setOpenDropdown(null);
                  setForm((current) => ({
                    ...current,
                    model: value,
                    size:
                      value === "gpt-image-2"
                        ? current.size === "auto"
                          ? "auto"
                          : current.size
                        : current.size === "auto"
                          ? "1:1"
                          : current.size,
                  }));
                }}
              />

              <DropdownField
                id="count"
                label="数量"
                valueLabel={`${form.n} 张`}
                isOpen={openDropdown === "count"}
                onToggle={() =>
                  setOpenDropdown((current) => (current === "count" ? null : "count"))
                }
                options={IMAGE_COUNT_OPTIONS.map((option) => ({
                  value: String(option),
                  label: `${option} 张`,
                }))}
                onSelect={(value) => {
                  setOpenDropdown(null);
                  setForm((current) => ({
                    ...current,
                    n: Number.parseInt(value, 10),
                  }));
                }}
              />

              <SelectorModalField
                valueLabel={`${form.size} · ${form.resolution}`}
                isOpen={openDropdown === "size-resolution"}
                onToggle={() =>
                  setOpenDropdown((current) =>
                    current === "size-resolution" ? null : "size-resolution",
                  )
                }
              >
                <div className="settings-group">
                  <div className="ratio-grid">
                    {ratioOptions.map((option, index) => (
                      <button
                        key={option}
                        type="button"
                        className={`choice-tile ${
                          form.size === option ? "choice-tile-active" : ""
                        } ${index === 0 ? "choice-tile-auto" : ""}`}
                        onClick={() =>
                          setForm((current) => ({
                            ...current,
                            size: option,
                          }))
                        }
                      >
                        <span
                          className="choice-icon"
                          style={{ aspectRatio: getRatioPreviewAspect(option) }}
                        />
                        <span className="choice-label">{option}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="settings-group">
                  <span className="settings-group-title">分辨率</span>
                  <div className="segment-group">
                    {RESOLUTION_OPTIONS.map((option) => (
                      <button
                        key={option}
                        type="button"
                        className={`segment-button ${
                          form.resolution === option ? "segment-button-active" : ""
                        }`}
                        onClick={() =>
                          setForm((current) => ({
                            ...current,
                            resolution: option,
                          }))
                        }
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>
              </SelectorModalField>

              <DropdownField
                id="quality"
                label="质量"
                valueLabel={qualityLabel}
                isOpen={openDropdown === "quality"}
                onToggle={() =>
                  setOpenDropdown((current) => (current === "quality" ? null : "quality"))
                }
                options={QUALITY_OPTIONS.map((option) => ({
                  value: option,
                  label: formatQualityLabel(option),
                }))}
                onSelect={(value) => {
                  setOpenDropdown(null);
                  setForm((current) => ({
                    ...current,
                    quality: value,
                  }));
                }}
              />

              <DropdownField
                id="moderation"
                label="审核"
                valueLabel={moderationLabel}
                isOpen={openDropdown === "moderation"}
                disabled={form.model === "gemini-3-pro-image-preview"}
                onToggle={() =>
                  setOpenDropdown((current) =>
                    current === "moderation" ? null : "moderation",
                  )
                }
                options={MODERATION_OPTIONS.map((option) => ({
                  value: option,
                  label: formatModerationLabel(option),
                }))}
                onSelect={(value) => {
                  setOpenDropdown(null);
                  setForm((current) => ({
                    ...current,
                    moderation: value,
                  }));
                }}
              />

            </div>

            <div className="form-footer">
              <button type="submit" className="save-button">
                {jobState === "submitting" ? "提交中..." : "开始生成"}
              </button>
            </div>
          </form>
        </section>

        <div
          className={`panel-resizer ${isResizingPanels ? "panel-resizer-active" : ""}`}
          role="separator"
          aria-label="调整左右面板宽度"
          aria-orientation="vertical"
          onPointerDown={(event) => {
            event.preventDefault();
            setIsResizingPanels(true);
          }}
        />

        <section className="workspace-section workspace-preview">
          <div className="section-header gallery-header">
            <h2>图片列表</h2>
            <div className="gallery-header-actions">
              <button
                type="button"
                className={`gallery-favorites-toggle ${
                  galleryMode === "favorites" ? "gallery-favorites-toggle-active" : ""
                }`}
                onClick={() =>
                  setGalleryMode((current) => (current === "favorites" ? "all" : "favorites"))
                }
              >
                收藏
              </button>

              <div className="gallery-density-control" aria-label="调整图片列表密度">
                <span>大</span>
                <input
                  type="range"
                  min="1"
                  max="8"
                  step="1"
                  value={galleryDensity}
                  onChange={(event) => setGalleryDensity(Number(event.target.value))}
                />
                <span>小</span>
              </div>
            </div>
          </div>

          {galleryJobs.length === 0 ? (
            <div className="empty-state">
              <p>{galleryMode === "favorites" ? "还没有收藏图片。" : "还没有图片。"}</p>
              <span>
                {galleryMode === "favorites"
                  ? "在图片卡片右上角点收藏后，会显示在这里。"
                  : "提交任务后，新的图片会自动出现在这里。"}
              </span>
            </div>
          ) : (
            <div className={galleryGridClassName}>
              {galleryJobs.map((job, index) => (
                <article
                  key={job.id}
                  className={`gallery-item ${index % 3 === 0 ? "gallery-item-edge-left" : ""}`}
                >
                  <div className="gallery-preview">
                    {job.status === "completed" && job.result_paths.length > 0 ? (
                      <>
                        <button
                          type="button"
                          className="gallery-image-button"
                          onClick={() => setViewerJobId(job.id)}
                          aria-label="查看大图"
                        >
                          <img
                            className="gallery-image"
                            src={toGeneratedUrl(job.result_paths[0])}
                            alt={job.prompt}
                          />
                        </button>
                        <div className="gallery-save-menu">
                          <div className="gallery-card-actions">
                            <button
                              type="button"
                              className={`gallery-favorite-trigger ${
                                favoriteJobIds.includes(job.id) ? "gallery-favorite-trigger-active" : ""
                              }`}
                              aria-label={favoriteJobIds.includes(job.id) ? "取消收藏" : "收藏图片"}
                              onClick={() => toggleFavoriteJob(job.id)}
                            >
                              <StarIcon filled={favoriteJobIds.includes(job.id)} />
                            </button>
                            <div className="gallery-save-trigger-shell">
                              <button
                                type="button"
                                className="gallery-save-trigger"
                                aria-label="保存到项目"
                              >
                                ↓
                              </button>
                              <div className="gallery-save-panel">
                                {activeProjectDirs.length === 0 ? (
                                  <span>先在设置里添加项目文件夹</span>
                                ) : (
                                  activeProjectDirs.map((project) => (
                                    <button
                                      key={project.name}
                                      type="button"
                                      className={
                                        savingProjectName === project.name
                                          ? "project-save-button project-save-button-saving"
                                          : "project-save-button"
                                      }
                                      disabled={savingProjectName === project.name}
                                      onClick={() =>
                                        void handleSaveImageToProject(
                                          job.result_paths[0],
                                          project.name,
                                        )
                                      }
                                    >
                                      {savingProjectName === project.name
                                        ? `保存到 ${project.name} 中...`
                                        : project.name}
                                    </button>
                                  ))
                                )}
                              </div>
                            </div>
                            <button
                              type="button"
                              className="gallery-delete-trigger"
                              aria-label="删除图片"
                              disabled={deletingJobId === job.id}
                              onClick={() => {
                                if (window.confirm("确定删除这张图片吗？")) {
                                  void handleDeleteJob(job.id);
                                }
                              }}
                            >
                              ×
                            </button>
                          </div>
                        </div>
                        <button
                          type="button"
                          className="gallery-reuse-button"
                          onClick={() => handleReuseJob(job)}
                        >
                          生成同款
                        </button>
                        <button
                          type="button"
                          className="gallery-reference-button"
                          onClick={() =>
                            appendReferenceImageUrl(
                              toGeneratedUrl(job.result_paths[0]),
                              `生成图 ${job.created_at}`,
                            )
                          }
                        >
                          参考生图
                        </button>
                      </>
                    ) : job.status === "failed" ? (
                      <div className="gallery-placeholder gallery-error">
                        <span>生成失败</span>
                      </div>
                    ) : (
                      <div className="gallery-placeholder">
                        <span>生成中</span>
                      </div>
                    )}
                  </div>

                </article>
              ))}
            </div>
          )}
        </section>
      </div>

      {viewerJob ? (
        <ImageViewer
          jobs={galleryJobs}
          selectedIndex={viewerIndex}
          activeProjectDirs={activeProjectDirs}
          projectSaveState={projectSaveState}
          projectSaveMessage={projectSaveMessage}
          savingProjectName={savingProjectName}
          onClose={() => setViewerJobId(null)}
          onSelect={(jobId) => setViewerJobId(jobId)}
          onReuseJob={(job) => handleReuseJob(job)}
          onSaveToProject={(sourcePath, projectName) =>
            void handleSaveImageToProject(sourcePath, projectName)
          }
        />
      ) : null}
    </main>
  );
}

function mapJobStateToTone(jobState: JobState): SaveState {
  if (jobState === "submitting" || jobState === "polling") {
    return "saving";
  }

  if (jobState === "completed") {
    return "saved";
  }

  if (jobState === "error") {
    return "error";
  }

  return "idle";
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

type DropdownOption = {
  value: string;
  label: string;
};

type ImageViewerProps = {
  jobs: JobResponse[];
  selectedIndex: number;
  activeProjectDirs: ProjectDir[];
  projectSaveState: ProjectSaveStatus;
  projectSaveMessage: string;
  savingProjectName: string | null;
  onClose: () => void;
  onSelect: (jobId: string) => void;
  onReuseJob: (job: JobResponse) => void;
  onSaveToProject: (sourcePath: string, projectName: string) => void;
};

function ImageViewer({
  jobs,
  selectedIndex,
  activeProjectDirs,
  projectSaveState,
  projectSaveMessage,
  savingProjectName,
  onClose,
  onSelect,
  onReuseJob,
  onSaveToProject,
}: ImageViewerProps) {
  const selectedJob = jobs[selectedIndex];
  const referenceImages = getJobReferenceImages(selectedJob);
  const [referencePage, setReferencePage] = useState(0);
  const [referencePreviewIndex, setReferencePreviewIndex] = useState<number | null>(null);
  const [isReferencePopoverOpen, setIsReferencePopoverOpen] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const referencePageCount = Math.max(1, Math.ceil(referenceImages.length / 9));
  const clampedReferencePage = Math.min(referencePage, referencePageCount - 1);
  const referencePageStart = clampedReferencePage * 9;
  const referencePageItems = referenceImages.slice(referencePageStart, referencePageStart + 9);
  const previewReferenceImage =
    referencePreviewIndex === null ? null : referenceImages[referencePreviewIndex] ?? null;

  useEffect(() => {
    setReferencePage(0);
    setReferencePreviewIndex(null);
    setIsReferencePopoverOpen(false);
    setCopyState("idle");
  }, [selectedJob.id]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
        return;
      }

      if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
        const nextIndex = (selectedIndex - 1 + jobs.length) % jobs.length;
        onSelect(jobs[nextIndex].id);
      }

      if (event.key === "ArrowDown" || event.key === "ArrowRight") {
        const nextIndex = (selectedIndex + 1) % jobs.length;
        onSelect(jobs[nextIndex].id);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [jobs, onClose, onSelect, selectedIndex]);

  async function handleCopyPrompt() {
    try {
      await navigator.clipboard.writeText(selectedJob.prompt);
      setCopyState("copied");
    } catch {
      setCopyState("error");
    }
  }

  return (
    <div className="viewer-backdrop" role="dialog" aria-modal="true">
      <div className="viewer-shell">
        <button type="button" className="viewer-close" onClick={onClose} aria-label="关闭大图查看">
          ←
        </button>

        <section className="viewer-stage">
          <div className="viewer-media-frame">
            {selectedJob.status === "completed" && selectedJob.result_paths.length > 0 ? (
              <img
                className="viewer-image"
                src={toGeneratedUrl(selectedJob.result_paths[0])}
                alt={selectedJob.prompt}
              />
            ) : selectedJob.status === "failed" ? (
              <div className="viewer-placeholder viewer-placeholder-error">生成失败</div>
            ) : (
              <div className="viewer-placeholder">生成中</div>
            )}
          </div>
        </section>

        <aside className="viewer-info">
          <div className="viewer-info-header">
            <h3>提示词</h3>
            <button type="button" className="viewer-copy-button" onClick={() => void handleCopyPrompt()}>
              <CopyIcon />
              <span>{copyState === "copied" ? "已复制" : copyState === "error" ? "复制失败" : "复制"}</span>
            </button>
          </div>

          <div className="viewer-info-body">
            {referenceImages.length > 0 ? (
              <div
                className="viewer-reference-shell"
                onMouseEnter={() => setIsReferencePopoverOpen(true)}
                onMouseLeave={() => setIsReferencePopoverOpen(false)}
              >
                <button
                  type="button"
                  className="viewer-reference-trigger"
                  onClick={() => setIsReferencePopoverOpen((current) => !current)}
                >
                  <span>参考图 {referenceImages.length}</span>
                  <span className="viewer-reference-trigger-caret">▾</span>
                </button>

                {isReferencePopoverOpen ? (
                  <div className="viewer-reference-popover">
                    <div className="viewer-reference-grid">
                      {referencePageItems.map((image, index) => {
                        const absoluteIndex = referencePageStart + index;
                        return (
                          <button
                            key={`${selectedJob.id}-reference-${absoluteIndex}`}
                            type="button"
                            className="viewer-reference-thumb"
                            onClick={() => setReferencePreviewIndex(absoluteIndex)}
                          >
                            <img src={image} alt={`参考图 ${absoluteIndex + 1}`} />
                          </button>
                        );
                      })}
                    </div>

                    {referencePageCount > 1 ? (
                      <div className="viewer-reference-pagination">
                        <button
                          type="button"
                          className="viewer-reference-page-button"
                          disabled={clampedReferencePage === 0}
                          onClick={() =>
                            setReferencePage((current) => Math.max(0, current - 1))
                          }
                        >
                          上一页
                        </button>
                        <span>
                          {clampedReferencePage + 1} / {referencePageCount}
                        </span>
                        <button
                          type="button"
                          className="viewer-reference-page-button"
                          disabled={clampedReferencePage >= referencePageCount - 1}
                          onClick={() =>
                            setReferencePage((current) =>
                              Math.min(referencePageCount - 1, current + 1),
                            )
                          }
                        >
                          下一页
                        </button>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}

            <p className="viewer-prompt">{selectedJob.prompt}</p>

            <div className="viewer-tags">
              <span className="viewer-tag">{formatModelLabel(selectedJob.model)}</span>
              <span className="viewer-tag">{selectedJob.size || "未记录比例"}</span>
              <span className="viewer-tag">{selectedJob.resolution}</span>
            </div>

            {selectedJob.error_message ? (
              <p className="viewer-error-text">{selectedJob.error_message}</p>
            ) : null}
          </div>

          {selectedJob.status === "completed" && selectedJob.result_paths.length > 0 ? (
            <div className="viewer-actions">
              <div className="viewer-actions-row">
                <button
                  type="button"
                  className="viewer-reuse-button"
                  onClick={() => onReuseJob(selectedJob)}
                >
                  生成同款
                </button>
              </div>

              {activeProjectDirs.length > 0 ? (
                <div className="viewer-projects">
                  {activeProjectDirs.map((project) => (
                    <button
                      key={project.name}
                      type="button"
                      className={
                        savingProjectName === project.name
                          ? "viewer-project-button viewer-project-button-saving"
                          : "viewer-project-button"
                      }
                      disabled={savingProjectName === project.name}
                      onClick={() =>
                        void onSaveToProject(selectedJob.result_paths[0], project.name)
                      }
                    >
                      {savingProjectName === project.name
                        ? `保存到 ${project.name} 中...`
                          : `保存到 ${project.name}`}
                    </button>
                  ))}
                </div>
              ) : null}

              {projectSaveMessage ? (
                <span className={`project-save-toast save-${projectSaveState}`}>
                  {projectSaveMessage}
                </span>
              ) : null}
            </div>
          ) : null}
        </aside>

        <aside className="viewer-rail">
          <div className="viewer-thumbs">
            {jobs.map((job) => {
              const isActive = job.id === selectedJob.id;
              return (
                <button
                  key={job.id}
                  type="button"
                  className={`viewer-thumb ${isActive ? "viewer-thumb-active" : ""}`}
                  onClick={() => onSelect(job.id)}
                >
                  {job.status === "completed" && job.result_paths.length > 0 ? (
                    <img src={toGeneratedUrl(job.result_paths[0])} alt={job.prompt} />
                  ) : job.status === "failed" ? (
                    <span>失败</span>
                  ) : (
                    <span>中</span>
                  )}
                </button>
              );
            })}
          </div>
        </aside>
      </div>

      {previewReferenceImage ? (
        <button
          type="button"
          className="viewer-reference-preview-backdrop"
          onClick={() => setReferencePreviewIndex(null)}
          aria-label="关闭参考图预览"
        >
          <img src={previewReferenceImage} alt="参考图放大预览" />
        </button>
      ) : null}
    </div>
  );
}

function SettingsIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M19.14 12.94c.04-.31.06-.63.06-.94s-.02-.63-.06-.94l2.03-1.58a.5.5 0 0 0 .12-.64l-1.92-3.32a.5.5 0 0 0-.6-.22l-2.39.96a7.05 7.05 0 0 0-1.63-.94l-.36-2.54A.5.5 0 0 0 13.9 2h-3.8a.5.5 0 0 0-.49.42l-.36 2.54c-.58.23-1.13.54-1.63.94l-2.39-.96a.5.5 0 0 0-.6.22L2.7 8.48a.5.5 0 0 0 .12.64l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94L2.82 14.16a.5.5 0 0 0-.12.64l1.92 3.32a.5.5 0 0 0 .6.22l2.39-.96c.5.4 1.05.72 1.63.94l.36 2.54a.5.5 0 0 0 .49.42h3.8a.5.5 0 0 0 .49-.42l.36-2.54c.58-.23 1.13-.54 1.63-.94l2.39.96a.5.5 0 0 0 .6-.22l1.92-3.32a.5.5 0 0 0-.12-.64l-2.03-1.58ZM12 15.5A3.5 3.5 0 1 1 12 8a3.5 3.5 0 0 1 0 7.5Z"
        fill="currentColor"
      />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M16 1H6a2 2 0 0 0-2 2v12h2V3h10V1Zm3 4H10a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2Zm0 16H10V7h9v14Z"
        fill="currentColor"
      />
    </svg>
  );
}

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="m12 3.6 2.56 5.18 5.72.83-4.14 4.03.98 5.69L12 16.64 6.88 19.33l.98-5.69-4.14-4.03 5.72-.83L12 3.6Z"
        fill={filled ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

type DropdownFieldProps = {
  id: string;
  label: string;
  valueLabel: string;
  options: DropdownOption[];
  isOpen: boolean;
  disabled?: boolean;
  onToggle: () => void;
  onSelect: (value: string) => void;
};

function DropdownField({
  id,
  label,
  valueLabel,
  options,
  isOpen,
  disabled = false,
  onToggle,
  onSelect,
}: DropdownFieldProps) {
  return (
    <div className={`dropdown-field ${disabled ? "dropdown-disabled" : ""}`}>
      <button
        type="button"
        className={`dropdown-trigger ${isOpen ? "dropdown-trigger-open" : ""}`}
        onClick={onToggle}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={`${id}-listbox`}
        disabled={disabled}
      >
        <strong>{valueLabel}</strong>
        <span className="dropdown-caret">▾</span>
      </button>

      {isOpen ? (
        <div className="dropdown-menu" role="listbox" id={`${id}-listbox`}>
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              className="dropdown-option"
              onClick={() => onSelect(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

type SelectorModalFieldProps = {
  valueLabel: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
};

function SelectorModalField({
  valueLabel,
  isOpen,
  onToggle,
  children,
}: SelectorModalFieldProps) {
  return (
    <div className="selector-modal-shell">
      <button
        type="button"
        className={`dropdown-trigger ${isOpen ? "dropdown-trigger-open" : ""}`}
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <strong>{valueLabel}</strong>
        <span className="dropdown-caret">▾</span>
      </button>

      {isOpen ? (
        <div className="selector-modal-panel">{children}</div>
      ) : null}
    </div>
  );
}

type FileUploadFieldProps = {
  ids: string[];
  files: string[];
  images: string[];
  onFilesSelected: (files: File[]) => void | Promise<void>;
  onClear: () => void;
  onRemove: (index: number) => void;
  onReorder: (fromIndex: number, toIndex: number) => void;
};

function FileUploadField({
  ids,
  files,
  images,
  onFilesSelected,
  onClear,
  onRemove,
  onReorder,
}: FileUploadFieldProps) {
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const previewImage = previewIndex === null ? null : images[previewIndex];
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 6,
      },
    }),
  );

  useEffect(() => {
    if (previewIndex === null) {
      return;
    }

    function handlePreviewKeydown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setPreviewIndex(null);
        return;
      }

      if (event.key === "ArrowLeft") {
        setPreviewIndex((current) =>
          current === null ? current : (current - 1 + images.length) % images.length,
        );
      }

      if (event.key === "ArrowRight") {
        setPreviewIndex((current) =>
          current === null ? current : (current + 1) % images.length,
        );
      }
    }

    window.addEventListener("keydown", handlePreviewKeydown);
    return () => window.removeEventListener("keydown", handlePreviewKeydown);
  }, [images.length, previewIndex]);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) {
      return;
    }

    const fromIndex = ids.indexOf(String(active.id));
    const toIndex = ids.indexOf(String(over.id));
    if (fromIndex < 0 || toIndex < 0) {
      return;
    }

    setPreviewIndex(null);
    onReorder(fromIndex, toIndex);
  }

  return (
    <div className="file-upload">
      <label className="file-upload-dropzone">
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          multiple
          className="file-upload-input"
          onChange={(event) => {
            const nextFiles = Array.from(event.target.files ?? []);
            if (nextFiles.length > 0) {
              void onFilesSelected(nextFiles);
            }
            event.target.value = "";
          }}
        />
        <span className="file-upload-title">拖拽图片到这里，或点击上传</span>
      </label>

      {files.length > 0 ? (
        <div className="file-upload-list">
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={ids} strategy={rectSortingStrategy}>
              <div className="file-upload-thumbs">
                {images.map((image, index) => (
                  <SortableReferenceThumb
                    key={ids[index]}
                    id={ids[index]}
                    image={image}
                    name={files[index] ?? "参考图"}
                    onPreview={() => setPreviewIndex(index)}
                    onRemove={() => {
                      setPreviewIndex(null);
                      onRemove(index);
                    }}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
          <button
            type="button"
            className="ghost-button file-upload-clear"
            onClick={() => {
              setPreviewIndex(null);
              onClear();
            }}
          >
            清空
          </button>
        </div>
      ) : null}

      {previewImage ? (
        <button
          type="button"
          className="file-preview-backdrop"
          onClick={() => setPreviewIndex(null)}
          aria-label="关闭参考图预览"
        >
          <img src={previewImage} alt="参考图预览" />
        </button>
      ) : null}
    </div>
  );
}

type SortableReferenceThumbProps = {
  id: string;
  image: string;
  name: string;
  onPreview: () => void;
  onRemove: () => void;
};

function SortableReferenceThumb({
  id,
  image,
  name,
  onPreview,
  onRemove,
}: SortableReferenceThumbProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      className={`file-upload-thumb-shell ${isDragging ? "file-upload-thumb-dragging" : ""}`}
      style={style}
      {...attributes}
      {...listeners}
    >
      <button type="button" className="file-upload-thumb" onClick={onPreview} title={name}>
        <img src={image} alt={name} />
      </button>
      <button type="button" className="file-upload-remove" onClick={onRemove} aria-label="删除参考图">
        ×
      </button>
    </div>
  );
}

function mergeJobIntoHistory(history: JobResponse[], incoming: JobResponse): JobResponse[] {
  const next = [incoming, ...history.filter((job) => job.id !== incoming.id)];
  return next.slice(0, 20);
}

function createPendingGalleryJob(draft: PendingJobDraft): JobResponse {
  return {
    id: draft.id,
    model: draft.model,
    prompt: draft.prompt,
    size: "",
    resolution: draft.resolution,
    quality: "auto",
    background: "auto",
    moderation: "low",
    output_format: "png",
    output_compression: null,
    n: draft.n,
    image_urls: [],
    reference_image_urls: [],
    mask_url: null,
    status: "queued",
    remote_task_id: null,
    result_paths: [],
    error_message: null,
    created_at: draft.created_at,
    updated_at: draft.created_at,
  };
}

function createFailedGalleryJob(job: JobResponse, message: string): JobResponse {
  return {
    ...job,
    status: "failed",
    error_message: message,
    updated_at: Math.floor(Date.now() / 1000),
  };
}

function getJobReferenceImages(job: JobResponse): string[] {
  if (Array.isArray(job.reference_image_urls) && job.reference_image_urls.length > 0) {
    return job.reference_image_urls.map(normalizeReferenceImageUrl);
  }

  return Array.isArray(job.image_urls) ? job.image_urls.map(normalizeReferenceImageUrl) : [];
}

function normalizeReferenceImageUrl(imageUrl: string): string {
  try {
    const parsed = new URL(imageUrl);
    if (
      (parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost") &&
      parsed.pathname.startsWith("/reference-assets/")
    ) {
      return `${API_BASE_URL}${parsed.pathname}`;
    }
  } catch {
    return imageUrl;
  }

  return imageUrl;
}

function createReferenceImageId(fileName: string, image: string, index: number): string {
  return `reference-${Date.now()}-${index}-${fileName}-${image.length}`;
}

type ReferenceDraft = {
  prompt: string;
  model: string;
  size: string;
  resolution: string;
  n: number;
  quality: string;
  moderation: string;
  images: string[];
  names: string[];
  ids: string[];
};

function loadReferenceDraft(): ReferenceDraft | null {
  try {
    const rawDraft = window.localStorage.getItem(REFERENCE_DRAFT_STORAGE_KEY);
    if (!rawDraft) {
      return null;
    }

    const draft = JSON.parse(rawDraft) as ReferenceDraft;
    if (
      typeof draft.prompt !== "string" ||
      typeof draft.model !== "string" ||
      typeof draft.size !== "string" ||
      typeof draft.resolution !== "string" ||
      typeof draft.n !== "number" ||
      typeof draft.quality !== "string" ||
      typeof draft.moderation !== "string" ||
      !Array.isArray(draft.images) ||
      !Array.isArray(draft.names) ||
      !Array.isArray(draft.ids) ||
      draft.images.length !== draft.names.length ||
      draft.images.length !== draft.ids.length
    ) {
      return null;
    }

    return draft;
  } catch {
    return null;
  }
}

function saveReferenceDraft(draft: ReferenceDraft): void {
  try {
    if (draft.images.length === 0) {
      if (draft.prompt.trim() === "") {
        window.localStorage.removeItem(REFERENCE_DRAFT_STORAGE_KEY);
        return;
      }
    }

    if (
      draft.prompt.trim() === "" &&
      draft.model === DEFAULT_SETTINGS.default_model &&
      draft.size === DEFAULT_SETTINGS.default_ratio &&
      draft.resolution === DEFAULT_SETTINGS.default_resolution &&
      draft.n === 1 &&
      draft.quality === "auto" &&
      draft.moderation === "auto" &&
      draft.images.length === 0 &&
      draft.names.length === 0 &&
      draft.ids.length === 0
    ) {
      window.localStorage.removeItem(REFERENCE_DRAFT_STORAGE_KEY);
      return;
    }

    window.localStorage.setItem(REFERENCE_DRAFT_STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // Data URLs can exceed localStorage quota; generation still works for the current session.
  }
}

function loadFavoriteJobIds(): string[] {
  try {
    const raw = window.localStorage.getItem(FAVORITE_JOB_IDS_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter((item): item is string => typeof item === "string");
  } catch {
    return [];
  }
}

function saveFavoriteJobIds(ids: string[]): void {
  try {
    window.localStorage.setItem(FAVORITE_JOB_IDS_STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Ignore localStorage write errors; favorites will still work for the current session.
  }
}

function validateBeforeSubmit(form: FormState): string | null {
  if (form.prompt.trim() === "") {
    return "提示词不能为空。";
  }

  if (form.n < 1 || form.n > 4) {
    return "图片数量必须在 1 到 4 之间。";
  }

  const referenceCount = form.reference_images.length;

  if (form.model === "gpt-image-2") {
    if (referenceCount > 16) {
      return "GPT Image 2 最多支持 16 张参考图。";
    }

    if (form.resolution === "4K") {
      const invalid4kSizes = new Set(["1:1", "3:2", "2:3", "4:3", "3:4", "5:4", "4:5"]);
      if (invalid4kSizes.has(form.size)) {
        return `比例 ${form.size} 不支持 4K。`;
      }
    }
  } else if (form.model === "gpt-image-2-vip") {
    if (referenceCount > 16) {
      return "GPT Image 2 VIP 最多支持 16 张参考图。";
    }
  } else {
    if (referenceCount > 14) {
      return "Nano Banana Pro 最多支持 14 张参考图。";
    }

    if (form.size === "auto") {
      return "Nano Banana Pro 不支持自动比例。";
    }
  }

  return null;
}

function getRatioPreviewAspect(ratio: string): string {
  if (ratio === "auto") {
    return "1 / 1";
  }

  const [width, height] = ratio.split(":").map(Number);
  if (!width || !height) {
    return "1 / 1";
  }

  return `${width} / ${height}`;
}

function formatJobStatus(status: string): string {
  switch (status) {
    case "queued":
      return "生成中";
    case "created":
      return "生成中";
    case "submitted":
      return "生成中";
    case "in_progress":
      return "生成中";
    case "completed":
      return "已完成";
    case "failed":
      return "失败";
    default:
      return status;
  }
}

function formatModelLabel(model: string): string {
  model = normalizeModelValue(model);

  if (model === "gpt-image-2") {
    return "image-2官转版";
  }

  if (model === "gpt-image-2-vip") {
    return "image-2-VIP";
  }

  if (model === "gemini-3-pro-image-preview") {
    return "nanobananapro";
  }

  return model;
}

function normalizeModelValue(model: string): string {
  return LEGACY_MODEL_ALIASES[model] ?? model;
}

function formatQualityLabel(quality: string): string {
  switch (quality) {
    case "auto":
      return "自动";
    case "low":
      return "低";
    case "medium":
      return "中";
    case "high":
      return "高";
    default:
      return quality;
  }
}

function formatModerationLabel(moderation: string): string {
  switch (moderation) {
    case "auto":
      return "自动";
    case "low":
      return "低";
    default:
      return moderation;
  }
}

function formatBackgroundLabel(background: string): string {
  switch (background) {
    case "auto":
      return "自动";
    case "opaque":
      return "不透明";
    case "transparent":
      return "透明";
    default:
      return background;
  }
}

function formatOutputFormatLabel(outputFormat: string): string {
  switch (outputFormat) {
    case "png":
      return "PNG";
    case "jpeg":
      return "JPEG";
    case "webp":
      return "WEBP";
    default:
      return outputFormat;
  }
}

function toGeneratedUrl(path: string): string {
  const normalized = path.split("\\").join("/");
  const filename = normalized.split("/").pop() ?? "";
  return `${API_BASE_URL}/generated/${encodeURIComponent(filename)}`;
}

async function readFileAsCompressedDataUrl(file: File): Promise<string> {
  const dataUrl = await readBlobAsDataUrl(file);
  if (typeof createImageBitmap !== "function") {
    return dataUrl;
  }

  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_REFERENCE_IMAGE_EDGE / Math.max(bitmap.width, bitmap.height));
  const targetWidth = Math.max(1, Math.round(bitmap.width * scale));
  const targetHeight = Math.max(1, Math.round(bitmap.height * scale));

  const canvas = document.createElement("canvas");
  canvas.width = targetWidth;
  canvas.height = targetHeight;

  const context = canvas.getContext("2d");
  if (!context) {
    bitmap.close();
    return dataUrl;
  }

  context.drawImage(bitmap, 0, 0, targetWidth, targetHeight);
  bitmap.close();

  try {
    if (file.type === "image/png") {
      return canvas.toDataURL("image/png");
    }

    const compressedDataUrl = canvas.toDataURL("image/jpeg", REFERENCE_IMAGE_QUALITY);
    return compressedDataUrl || dataUrl;
  } catch {
    return dataUrl;
  }
}

function readBlobAsDataUrl(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
        return;
      }

      reject(new Error("文件读取失败"));
    };
    reader.onerror = () => {
      reject(new Error("文件读取失败"));
    };
    reader.readAsDataURL(file);
  });
}

function isPromptReferenceElement(
  value: SlateElement,
): value is PromptReferenceElement {
  return "type" in value && value.type === "reference";
}

function serializePrompt(value: PromptParagraphElement[]): string {
  return value
    .map((node) => serializePromptNode(node))
    .join("\n")
    .replace(new RegExp(PROMPT_REFERENCE_ANCHOR, "g"), "")
    .replace(/\u00a0/g, " ");
}

function serializePromptNode(node: PromptDescendant): string {
  if (Text.isText(node)) {
    return node.text;
  }

  if (isPromptReferenceElement(node)) {
    return `图片${node.referenceNumber}`;
  }

  return node.children.map((child) => serializePromptNode(child)).join("");
}

function deserializePrompt(
  prompt: string,
  referenceImages: string[],
): PromptParagraphElement[] {
  const lines = prompt.split("\n");
  return lines.map((line) => ({
    type: "paragraph",
    children: buildPromptChildrenFromText(line, referenceImages),
  }));
}

function buildPromptChildrenFromText(
  text: string,
  referenceImages: string[],
): PromptDescendant[] {
  const parts: PromptDescendant[] = [];
  const pattern = /图片(\d+)/g;
  let cursor = 0;
  let match = pattern.exec(text);

  while (match) {
    const start = match.index;
    const end = start + match[0].length;
    const referenceNumber = Number.parseInt(match[1], 10);

    if (start > cursor) {
      parts.push({ text: text.slice(cursor, start) });
    }

    if (referenceImages[referenceNumber - 1]) {
      parts.push({
        type: "reference",
        referenceNumber,
        children: [{ text: "" }],
      });
      parts.push({ text: PROMPT_REFERENCE_ANCHOR });
    } else {
      parts.push({ text: match[0] });
    }

    cursor = end;
    match = pattern.exec(text);
  }

  if (cursor < text.length) {
    parts.push({ text: text.slice(cursor) });
  }

  if (parts.length === 0) {
    parts.push({ text: "" });
  }

  return parts;
}

function getReferencePromptTrigger(
  editor: Editor,
  referenceCount: number,
): PromptReferenceTrigger | null {
  if (referenceCount === 0 || !editor.selection || !Range.isCollapsed(editor.selection)) {
    return null;
  }

  const triggerRange = Editor.before(editor, editor.selection.anchor, { unit: "line" });
  const from = triggerRange ?? Editor.start(editor, []);
  const range = { anchor: from, focus: editor.selection.anchor };
  const beforeText = Editor.string(editor, range);
  const tokenMatch = /=([0-9]*)$/.exec(beforeText);
  if (!tokenMatch) {
    return null;
  }

  const query = tokenMatch[1] ?? "";
  const matches = findReferenceMatches(query, referenceCount);
  if (matches.length === 0) {
    return null;
  }

  const start = Editor.before(editor, editor.selection.anchor, {
    distance: query.length + 1,
    unit: "character",
  });
  if (!start) {
    return null;
  }

  return {
    range: { anchor: start, focus: editor.selection.anchor },
    query,
    matches,
  };
}

function findReferenceMatches(query: string, referenceCount: number): number[] {
  const candidates = Array.from({ length: referenceCount }, (_, index) => index + 1);
  if (query === "") {
    return candidates;
  }

  return candidates.filter((item) => String(item).startsWith(query));
}

function getPromptReferenceDeletionTarget(
  editor: Editor,
  key: "Backspace" | "Delete",
): { path: Path; range: Range } | null {
  if (!editor.selection) {
    return null;
  }

  if (!Range.isCollapsed(editor.selection)) {
    const selectedEntry = Editor.above(editor, {
      at: editor.selection,
      match: (node) => SlateElement.isElement(node) && isPromptReferenceElement(node),
    });
    if (!selectedEntry) {
      return null;
    }

    const [, selectedPath] = selectedEntry;
    return {
      path: selectedPath,
      range: Editor.range(editor, selectedPath),
    };
  }

  const currentPoint = editor.selection.anchor;
  const anchorTarget = getPromptReferenceAnchorTarget(editor, currentPoint, key);
  if (anchorTarget) {
    return anchorTarget;
  }

  const adjacentPoint = key === "Backspace"
    ? Editor.before(editor, currentPoint, { unit: "offset" })
    : Editor.after(editor, currentPoint, { unit: "offset" });
  if (!adjacentPoint) {
    return null;
  }

  const entry = Editor.above(editor, {
    at: adjacentPoint,
    match: (node) => SlateElement.isElement(node) && isPromptReferenceElement(node),
  });
  if (!entry) {
    return null;
  }

  const [, path] = entry;
  return {
    path,
    range: Editor.range(editor, path),
  };
}

function getPromptReferenceAnchorTarget(
  editor: Editor,
  point: Point,
  key: "Backspace" | "Delete",
): { path: Path; range: Range } | null {
  const [node] = Editor.node(editor, point.path);
  if (!Text.isText(node)) {
    return null;
  }

  if (key === "Backspace" && point.offset === PROMPT_REFERENCE_ANCHOR.length) {
    const anchorText = node.text.slice(0, PROMPT_REFERENCE_ANCHOR.length);
    if (anchorText === PROMPT_REFERENCE_ANCHOR) {
      return getPreviousPromptReferenceTarget(editor, point.path);
    }
  }

  if (key === "Delete" && point.offset === 0) {
    const anchorText = node.text.slice(0, PROMPT_REFERENCE_ANCHOR.length);
    if (anchorText === PROMPT_REFERENCE_ANCHOR) {
      return getPreviousPromptReferenceTarget(editor, point.path);
    }
  }

  return null;
}

function getPreviousPromptReferenceTarget(
  editor: Editor,
  path: Path,
): { path: Path; range: Range } | null {
  if (path[path.length - 1] <= 0) {
    return null;
  }

  const previousPath = Path.previous(path);
  const previousNode = Node.get(editor, previousPath);
  if (!SlateElement.isElement(previousNode) || !isPromptReferenceElement(previousNode)) {
    return null;
  }

  return {
    path: previousPath,
    range: Editor.range(editor, previousPath),
  };
}

function isPromptReferenceSelected(editor: Editor, range: Range): boolean {
  if (!editor.selection || Range.isCollapsed(editor.selection)) {
    return false;
  }

  return Range.equals(editor.selection, range);
}

function insertPromptReference(editor: Editor, referenceNumber: number) {
  const referenceNode: PromptReferenceElement = {
    type: "reference",
    referenceNumber,
    children: [{ text: "" }],
  };

  Transforms.insertNodes(editor, [
    referenceNode,
    { text: PROMPT_REFERENCE_ANCHOR },
  ]);
}

function removePromptReference(editor: Editor, path: Path) {
  const cleanupPath = Path.hasPrevious(path) ? Path.previous(path) : path;
  Transforms.removeNodes(editor, { at: path });
  removePromptReferenceAnchorsAt(editor, cleanupPath);
  removePromptReferenceAnchorsAt(editor, path);
}

function removePromptReferenceAnchorsAt(editor: Editor, path: Path) {
  if (!Node.has(editor, path)) {
    return;
  }

  const node = Node.get(editor, path);
  if (!Text.isText(node) || !node.text.includes(PROMPT_REFERENCE_ANCHOR)) {
    return;
  }

  for (let index = node.text.length - 1; index >= 0; index -= 1) {
    if (node.text[index] !== PROMPT_REFERENCE_ANCHOR) {
      continue;
    }

    Transforms.delete(editor, {
      at: {
        anchor: { path, offset: index },
        focus: { path, offset: index + PROMPT_REFERENCE_ANCHOR.length },
      },
    });
  }
}

function PromptElement({
  attributes,
  children,
  element,
  referenceImages,
  referenceNames,
}: {
  attributes: RenderElementProps["attributes"];
  children: React.ReactNode;
  element: SlateElement;
  referenceImages: string[];
  referenceNames: string[];
}): React.JSX.Element {
  if (isPromptReferenceElement(element)) {
    return (
      <PromptReferenceNode
        attributes={attributes}
        element={element}
        referenceImages={referenceImages}
        referenceNames={referenceNames}
      >
        {children}
      </PromptReferenceNode>
    );
  }

  return <p {...attributes}>{children}</p>;
}

function PromptReferenceNode({
  attributes,
  children,
  element,
  referenceImages,
  referenceNames,
}: {
  attributes: RenderElementProps["attributes"];
  children: React.ReactNode;
  element: PromptReferenceElement;
  referenceImages: string[];
  referenceNames: string[];
}): React.JSX.Element {
  const editor = useSlateStatic() as ReactEditor & Editor;
  const selected = useSelected();
  const path = ReactEditor.findPath(editor, element);
  const isCursorAdjacent =
    !!editor.selection &&
    Range.isCollapsed(editor.selection) &&
    (Point.equals(editor.selection.anchor, Editor.start(editor, path)) ||
      Point.equals(editor.selection.anchor, Editor.end(editor, path)));
  const isActive = selected || isCursorAdjacent;
  const referenceImage = referenceImages[element.referenceNumber - 1];
  const referenceName =
    referenceNames[element.referenceNumber - 1] ?? `图片${element.referenceNumber}`;

  return (
    <span
      {...attributes}
      contentEditable={false}
      className={`prompt-inline-reference-shell ${
        isActive ? "prompt-inline-reference-shell-active" : ""
      }`}
    >
      <span className="prompt-inline-reference-spacer" aria-hidden="true">
        {" "}
      </span>
      <span className="prompt-inline-reference">
        {referenceImage ? (
          <img
            className="prompt-inline-reference-thumb"
            src={referenceImage}
            alt={referenceName}
          />
        ) : null}
        <span>{`图片${element.referenceNumber}`}</span>
      </span>
      <span className="prompt-inline-reference-spacer" aria-hidden="true">
        {" "}
      </span>
      {children}
    </span>
  );
}
