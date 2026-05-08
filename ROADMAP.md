# AIGC Local Studio Roadmap

## 1. Project Goal

Build a local-first image generation tool for personal use by two people.

This version is intentionally narrow:

- No multi-user system
- No cloud deployment
- No third-party sharing or publishing flow
- No plugin system
- No model marketplace

The app only needs to solve one core workflow well:

1. Enter a prompt
2. Choose one of two fixed models
3. Choose basic or advanced generation parameters
4. Submit a generation task
5. Poll task status
6. Download and save the result locally
7. View result history later

## 2. Fixed Product Scope

### Included in MVP

- Local web app running on `localhost`
- Two model options only:
  - `gpt-image-2-official`
  - `gemini-3-pro-image-preview`
- Manual API Key input by the user
- Baseline ratio choices must include at least the Hailuo-style settings set shown in the reference UI:
  - `auto` for GPT Image 2
  - `21:9`
  - `16:9`
  - `5:4`
  - `4:3`
  - `3:2`
  - `1:1`
  - `2:3`
  - `3:4`
  - `4:5`
  - `9:16`
- Advanced mode adds only documented extra ratios not present in the baseline set
- Text-to-image
- Image-to-image
- Multi-reference image input
- Mask-based inpainting for `gpt-image-2-official`
- Ratio selection up to each model's documented limit
- Resolution selection up to each model's documented limit
- Multi-image generation with `n=1..4`
- Resolution choices must include:
  - `1K`
  - `2K`
  - `4K`
- Fixed default resolution: `1K`
- Fixed default image count: `1`
- GPT Image 2 moderation is fixed to `low`, never `auto`
- Prompt input
- Task status display
- Result preview
- Local history
- Basic export
- Basic error handling

### Excluded from MVP

- Deployment and hosting
- Account system
- Team collaboration
- Share links
- Batch generation
- Prompt template system
- Automatic model routing
- Billing dashboard

## 3. Product Principles

### Principle 1: Keep it local

The app runs only on the user's machine.

- Frontend talks only to local backend
- Backend talks to APIMart
- Generated images are downloaded immediately and stored locally

### Principle 2: Keep it fixed

Do not over-design for future extensibility in MVP.

- Fixed two-model selector
- Fixed two-level parameter model:
  - Basic mode exposes the full Hailuo-style baseline ratio set plus `1K / 2K / 4K`
  - Advanced mode exposes model-specific limits
- Fixed single-user local storage

### Principle 3: Keep secrets off the frontend

`API Key` must be entered by the user and stored locally in the backend database. It must never be embedded in frontend code.

### Principle 4: Keep one workflow clean

The primary success path is more important than feature count.

### Principle 5: Reach documented model limits, not speculative ones

If a capability is explicitly documented for one of the two chosen models, it belongs in scope.

- No silent downgrade to weaker model variants
- Use `gemini-3-pro-image-preview`, not Nano Banana 2 / Gemini 3.1 variants
- Respect documented upper bounds such as `n <= 4`
- Force `moderation=low` on every `gpt-image-2-official` request

### Principle 6: Prefer Aceternity UI first

For reusable frontend components, check `https://ui.aceternity.com/` first.

- Reuse Aceternity UI components whenever they fit the product
- If Aceternity UI does not provide a suitable component, implement it locally
- Do not introduce another component library as a first choice for MVP

## 4. Recommended Architecture

### Frontend

- `React`
- `Vite`
- `TypeScript`
- `Tailwind CSS`

Responsibilities:

- Prompt input
- Model selection
- Basic/advanced mode switch
- Ratio selection
- Resolution selection
- Image count selection
- Reference image upload
- Mask upload for GPT Image 2
- Model-specific advanced parameter controls
- Settings page
- Task status display
- Result preview
- History browsing

Preferred component source:

- Use Aceternity UI first for reusable UI building blocks
- Write local components when Aceternity UI does not cover the use case

Aceternity UI components likely usable in this project:

- `Tabs` for model/basic-advanced switching
- `File Upload` for reference image upload
- `Animated Modal` for settings
- `Stateful Button` for generate action
- `Loader` for task polling state
- `Lens` for result preview zoom
- `Backgrounds` or `Grid and Dot Backgrounds` for subtle page atmosphere

### Backend

- `FastAPI`

Responsibilities:

- Read and store local settings
- Validate request parameters
- Create local jobs
- Submit tasks to APIMart
- Poll APIMart task status in background
- Download result images
- Persist history into SQLite
- Enforce model-specific parameter limits before remote submission
- Force `moderation=low` on GPT Image 2 payloads

### Storage

- `SQLite` for metadata
- `SQLite` for settings, including the saved API Key
- Local folders for image files

Suggested local data:

- task records
- prompt
- selected model
- selected ratio
- selected resolution
- selected image count
- task status
- local image path
- created time

## 5. Core Pages

### 5.1 Main Workspace

Must include:

- Prompt textarea
- Model switcher
- Basic/advanced mode switch
- Ratio switcher
- Resolution switcher
- Image count switcher (`1..4`)
- Reference image uploader
- Mask uploader for GPT Image 2
- Generate button
- Current task status
- Result preview area

UI sourcing rule:

- Check Aceternity UI before building each major component
- If prompt input, uploader, modal, preview, or loading state is not covered well enough, write a local component

### 5.2 History Panel

Must include:

- Recent generation list
- Thumbnail
- Prompt preview
- Model label
- Time
- Click to reopen image

### 5.3 Settings Page

Must include:

- APIMart API Key input
- Default model
- Default ratio
- Default resolution
- Save button

## 6. Backend Flow

### Generation flow

1. Frontend sends prompt, model, and ratio to local backend
2. Frontend may also send advanced parameters such as resolution, image count, reference images, and mask
3. Backend validates input against the selected model's documented limits
4. Backend rejects unsupported baseline options for the current model, such as `auto` on Gemini if the provider does not document support
5. Backend normalizes provider payload
6. Backend creates a local `job_id`
7. Backend submits request to APIMart
8. Backend stores remote `task_id`
9. Backend polls APIMart task status in background until complete or failed
10. Backend downloads final image immediately
11. Backend stores metadata in SQLite
12. Frontend polls local `job_id` status and shows result when ready

### Error flow

Must handle:

- missing API Key
- invalid API Key
- unsupported ratio for current model
- unsupported ratio-resolution combination
- too many images requested
- too many reference images uploaded
- APIMart request failure
- timeout while polling
- download failure
- task failed status

## 7. Data Model

MVP only needs one main history record.

Suggested fields:

- `id`
- `prompt`
- `model`
- `mode`
- `ratio`
- `resolution`
- `image_count`
- `quality`
- `moderation`
- `reference_image_count`
- `mask_enabled`
- `status`
- `remote_task_id`
- `local_image_path`
- `created_at`
- `updated_at`
- `error_message`

No speculative tables unless implementation actually needs them.

## 8. Development Plan

### Phase 1: Project Setup

Goal:

Set up runnable frontend and backend skeleton.

Tasks:

- Create frontend app
- Create backend app
- Add health check endpoint
- Verify frontend can call backend

Done when:

- Frontend starts locally
- Backend starts locally
- Health check works end to end

### Phase 2: Settings and Local Config

Goal:

Let the user input and save their own API Key locally.

Tasks:

- Build settings page
- Add API Key input
- Add default model selector
- Add default ratio selector
- Add default resolution selector
- Save config locally through backend into SQLite

Done when:

- User can save API Key
- Refresh keeps saved settings
- Frontend never directly stores provider secret in code

### Phase 3: First Model Integration

Goal:

Make `gpt-image-2-official` fully usable.

Tasks:

- Add create job endpoint
- Add get job status endpoint
- Add APIMart request adapter
- Add background polling logic
- Add final image download
- Support text-to-image
- Support image-to-image with up to 16 reference images
- Support mask-based inpainting
- Support `resolution=1K/2K/4K`
- Support `n=1..4`
- Force `moderation=low` on every GPT Image 2 request
- Validate 4K size restrictions before submit
- Return result to frontend

Done when:

- GPT Image 2 can complete:
  - one text-to-image job
  - one image-to-image job
  - one mask inpainting job
  - one `n=4` job
  - one valid 4K job
  - one request verified with `moderation=low`

### Phase 4: Second Model Integration

Goal:

Make `gemini-3-pro-image-preview` usable with the same UI flow.

Tasks:

- Add second adapter path
- Reuse same task lifecycle
- Normalize response shape for frontend
- Support documented Gemini Pro ratios
- Support `resolution=1K/2K/4K`
- Support `n=1..4`
- Support image reference input
- Use `gemini-3-pro-image-preview`, not Gemini 3.1 Nano Banana 2

Done when:

- Gemini Pro can complete:
  - one text-to-image job
  - one reference-image job
  - one `n=4` job
  - one 4K job

### Phase 5: Main Workspace UI

Goal:

Build the single-page generation workflow.

Tasks:

- Add prompt input
- Add model selector
- Add basic/advanced mode switch
- Add ratio selector
- Add resolution selector
- Add image count selector
- Add generate action
- Add loading and status UI
- Add preview panel
- Add reference image upload UI
- Add conditional mask upload UI for GPT Image 2
- Show the full baseline ratio set from the reference UI
- Show `1K / 2K / 4K` resolution choices

Done when:

- User can complete text-to-image, image-to-image, and GPT Image 2 inpainting in one page without dev tools

### Phase 6: Local History

Goal:

Persist and reopen previous results.

Tasks:

- Add SQLite table
- Save task metadata
- Save local image paths
- Save multiple output image paths for `n > 1`
- Render history list in UI
- Reopen previous result

Done when:

- Restarting the app still shows previous generations

### Phase 7: Error Handling and Export

Goal:

Make the tool usable without fragile manual recovery.

Tasks:

- Show missing API Key error
- Show invalid auth error
- Show invalid 4K ratio error before submit
- Show reference image count limit error before submit
- Show `n > 4` validation error before submit
- Show timeout error
- Show failed task error
- Add image download action

Done when:

- Common failures are understandable
- User can download image files easily

## 9. Suggested Build Order

1. Frontend/backend skeleton
2. Settings page
3. First model integration
4. Second model integration
5. Generation UI
6. Local history
7. Error handling
8. Export polish

This order is intentionally biased toward getting one complete working path early.

## 10. Acceptance Criteria

The MVP is done when all of the following are true:

1. The app runs locally on one machine.
2. The user can manually enter and save an APIMart API Key.
3. The user can choose between exactly two models.
4. The app exposes at least this baseline ratio set in the main UI: `auto` for GPT Image 2, `21:9`, `16:9`, `5:4`, `4:3`, `3:2`, `1:1`, `2:3`, `3:4`, `4:5`, `9:16`.
5. The app exposes all three resolution choices in the main UI: `1K`, `2K`, `4K`.
6. The user can submit text-to-image, image-to-image, and GPT Image 2 inpainting tasks.
7. The app enforces documented limits before request submission, including `n <= 4` and invalid 4K ratio combinations.
8. The app shows task progress or status.
9. The app downloads the finished image locally.
10. The app saves generation history locally.
11. The user can reopen previous results after restarting the app.
12. GPT Image 2 can complete text-to-image, image-to-image, inpainting, `n=4`, and a valid 4K flow.
13. All GPT Image 2 requests are sent with `moderation=low`, never `auto`.
14. Gemini Pro can complete text-to-image, reference-image generation, `n=4`, and a 4K flow.
15. Common failure cases show clear error messages.

## 11. What Not to Do Yet

Do not add these before MVP is working:

- Tauri packaging
- Complex design system work
- A second UI component library unless Aceternity UI clearly does not cover the need
- Provider abstraction for many future models
- Queue tuning for high concurrency
- Shared libraries split across many packages
- Cloud sync
- User accounts

## 12. Immediate Next Step

Start with Phase 1 and Phase 2 only.

The first milestone should be:

- app boots locally
- settings page works
- API Key can be saved

After that, complete the `gpt-image-2-official` minimum working flow first, then add `gemini-3-pro-image-preview`, then build the full generation UI with the required ratio, resolution, reference image, mask, and `n=1..4` controls.
