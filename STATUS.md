# Project Status

## Current Phase

- MVP Buildout
- Status: Core phases completed

## Working Rules

- Re-read `ROADMAP.md` and `karpathy-guidelines` before each major execution step
- Complete one phase at a time
- After each phase, run a review
- Fix review findings before moving to the next phase

## Environment Notes

- `node`: available
- `npm`: available
- `npx`: available
- `python3`: available
- `uv`: not installed
- `pnpm`: not installed
- `fastapi`: not installed

## Phase Log

### Phase 1

- Confirmed roadmap and execution constraints
- Confirmed local toolchain
- Chose minimal manual skeleton instead of interactive scaffolding
- Created initial frontend/backend skeleton
- Installed backend dependencies
- Frontend dependency installation partially succeeded but runtime verification failed
- Phase 1 review findings:
  - P1: Python package architecture mismatch in `pydantic-core` under the current `python3` environment
  - P1: `vite` package installation is incomplete or corrupted in `apps/web/node_modules`
- Repair plan:
  - Backend: switch Phase 1 dependency set to a `FastAPI + pydantic v1` combination to avoid native wheel mismatch
  - Frontend: re-verify current `vite` install before making any package changes
- Next: repair dependency/runtime issues, rerun Phase 1 verification, then review again

### Phase 1 Review Round 2

- Verified backend health endpoint with local server running
- Verified frontend dev server startup
- Verified frontend production build
- Remaining P1 finding:
  - Backend dependencies are installed in the user-level Python environment instead of a project-local virtual environment
- Next: move backend runtime into a project-local `.venv`, rerun verification, and close Phase 1

### Phase 1 Review Round 3

- Created project-local `.venv`
- Installed backend dependencies into `.venv`
- Verified backend health endpoint using `.venv`
- Phase 1 closed with no remaining P1+ findings

### Phase 2

- Implemented backend SQLite-backed settings storage
- Added `GET /api/settings` and `PUT /api/settings`
- Built frontend settings form for API key, default model, default ratio, and default resolution
- Verified settings persistence through API
- Verified frontend production build
- Restored local settings to default values after verification
- Phase 2 review result: no remaining P1+ findings

### Phase 3

- Implemented initial Phase 3 backend job flow for `gpt-image-2-official`
- Added job persistence, provider request building, polling, and download paths
- Added first round of backend tests for validation, moderation, and completed-job handling
- Phase 3 review round 1 findings:
  - P1: test module import path is wrong for current project layout
  - Validation note: `compileall` is not a reliable verification step here because sandboxed cache writes are blocked
- Next: fix verification path issues, rerun tests, then continue Phase 3 review

### Phase 3 Review Round 2

- Fixed test import path
- Replaced the blocked `compileall` check with a local `py_compile` check
- Backend unit tests passed
- Remaining P1 finding:
  - If remote completion succeeds but local image download fails, the job may escape the state machine instead of being marked as `failed`
- Next: fix the download-failure state transition and rerun tests

### Phase 3 Review Round 3

- Fixed the download-failure transition after remote completion
- Added a regression test for failed local downloads
- Remaining P1 finding:
  - Local file write errors inside the download step are not yet converted into a stored failed job state
- Next: close the remaining file-write error path and rerun tests

### Phase 3 Review Round 4

- Converted local file write failures into `ProviderError`
- Added a regression test for local write failure handling
- Backend tests now pass:
  - validation
  - moderation enforcement
  - successful completion path
  - failed download paths
- Phase 3 closed with no remaining P1+ findings

### Phase 4

- Added Gemini Pro validation and provider payload shaping into the shared job flow
- Extended backend tests to cover Gemini payload rules
- Phase 4 review round 1 findings:
  - P1: Gemini jobs currently produce a null `moderation` value but the jobs table stores `moderation` as `NOT NULL`
- Next: fix Gemini job persistence and rerun tests

### Phase 4 Review Round 2

- Fixed Gemini job persistence by storing a non-null moderation string
- Added a regression test for Gemini job persistence
- Backend tests now pass for both model paths
- Phase 4 closed with no remaining P1+ findings

### Phase 5

- Built the first main workspace UI around the existing settings and job APIs
- Added prompt, model, ratio, resolution, count, reference URL, mask URL, submit, polling status, and result panels
- Verified frontend production build
- Phase 5 review round 1 findings:
  - P1: the UI does not yet expose GPT Image 2 `auto` ratio in the main workflow or settings
- Next: add the missing `auto` ratio path and continue Phase 5 review

### Phase 5 Review Round 2

- Added GPT Image 2 `auto` ratio back to the main UI and settings flow
- Verified frontend production build again
- Remaining P1 finding:
  - Changing the saved default model does not normalize an unsupported default ratio, so `auto` can remain selected for Gemini
- Next: normalize the saved default ratio when the default model changes

### Phase 5 Review Round 3

- Normalized the saved default ratio when the saved default model changes away from GPT Image 2
- Verified frontend production build again
- Phase 5 closed with no remaining P1+ findings

### Phase 6

- Next: render persisted jobs into a local history panel and support reopening previous results
- Added backend job list API and frontend history panel
- Added reopen flow from history into the result panel
- Verified backend tests and frontend production build
- Phase 6 review round 1 findings:
  - P1: reopening an in-progress history item incorrectly forces the UI state to `completed`
- Next: fix history-to-UI state mapping and continue Phase 6 review

### Phase 6 Review Round 2

- Fixed history-to-UI state mapping for in-progress jobs
- Verified frontend production build again
- Phase 6 closed with no remaining P1+ findings

### Phase 7

- Next: improve user-facing error handling and add basic file export actions
- Added pre-submit validation messages for common request mistakes
- Added copy-path and download actions in the result panel
- Verified frontend production build
- Phase 7 review round 1 findings:
  - P1: `file://` download links are not a reliable browser export mechanism
- Next: switch export links to local HTTP-served files

### Phase 7 Review Round 2

- Switched export links toward a local HTTP-served file strategy
- Remaining P1 findings:
  - Backend static mounting currently fails in test/runtime import paths when the generated directory does not already exist
  - Frontend helper used `replaceAll`, which is incompatible with the current TypeScript lib target
- Next: create the generated directory before mounting and replace the incompatible string helper

### Phase 7 Review Round 3

- Created the generated directory before backend static mounting
- Replaced the incompatible frontend string helper
- Verified backend syntax checks
- Verified backend unit tests
- Verified frontend production build
- Phase 7 closed with no remaining P1+ findings

## Remaining Risks

- No real APIMart end-to-end run has been executed yet because there is no live API key in the workspace
- Real provider behavior for submission, polling, and file download still needs live verification after local startup

## Ongoing UI Refinement

### UI Refinement Round 1

- Reworked the main workspace from a three-column layout into two sections
- Merged settings into the main generation area
- Removed outer panel corner radii and switched the main split to divider-based sections
- Reduced all interactive corner radii to `6px` or less
- Translated remaining frontend runtime messages to Chinese
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 2

- Replaced the main generation selects with bottom-row dropdown buttons inspired by the referenced Untitled UI dropdown pattern
- Kept settings as native fields for now and limited the change to the main generation controls
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 3

- Replaced reference URL input with a file upload dropzone inspired by the referenced Untitled UI uploader pattern
- Converted uploaded images to `data:` URLs in the frontend so the existing backend job API could remain unchanged
- Removed the mask URL input from the user interface
- Removed the output compression input from the user interface
- Kept backend payload compatibility by sending `mask_url: null` and `output_compression: null`
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### Backend Config Round 1

- Added a tiny startup-time local `.env` loader in `apps/api/main.py`
- Persisted Supabase local upload config in `apps/api/.env`
- Configured local GPT reference-image upload path to read:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_BUCKET`
- Next: restart backend and verify the previous `Supabase 未配置` failure no longer occurs for GPT local reference images

### Backend Config Round 1 Review

- Restarted the local backend so the new `.env` values were loaded
- Re-tested `POST /api/jobs` with `gpt-image-2` plus a local `data:` reference image
- Confirmed the previous immediate failure path:
  - `检测到本地参考图，但 Supabase 未配置`
  no longer occurs
- Current result moved forward to a later request stage and now returns a different `400`, which indicates the local Supabase configuration is being read successfully
- Review result: no remaining P1+ issue in this specific config-persistence step

### UI Refinement Round 4

- Removed the background selector from the main generation controls
- Removed the output format selector from the main generation controls
- Fixed generation submissions to always use `background=auto` and `output_format=png`
- Removed default ratio and default resolution fields from the settings section
- Kept settings persistence compatible by still reading existing stored values in the backend payload shape
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 5

- Removed the outer blue gradient shell treatment
- Removed the large white-card container treatment around the whole workspace
- Made the two main workspace sections stretch directly to the viewport height
- Added root-level height rules so the page stays full-height across device sizes
- Kept the divider-based split between left and right work areas
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### Backend Provider Stability Round 1

- Investigated the `image-2-VIP` failure using backend runtime logs instead of frontend console guesses
- Confirmed the real breakage path was in Supabase signed URL creation for local reference images
- Confirmed the backend was throwing an uncaught low-level connection exception, which surfaced as `500` and then appeared in the browser as a misleading CORS error
- Added explicit handling for low-level Supabase connection exceptions in `perform_supabase_request`

### Backend Provider Stability Round 1 Review

- Re-ran backend syntax verification
- Restarted the backend
- Re-tested `gpt-image-2-vip` with a local `data:` reference image
- Confirmed the prior `500 Internal Server Error` path no longer occurs
- Confirmed the backend now returns `200 OK` for the same `VIP + local reference image` path
- Review result: no remaining P1+ issue in this specific crash-fix step

### Reference Persistence Round 1

- Split the old overloaded `image_urls` meaning into:
  - provider input URLs
  - persisted reference image URLs for history / reuse
- Added local persistent reference image storage under `data/reference-assets`
- Added content-hash based deduplication for locally uploaded reference images
- Added `/reference-assets/{filename}` for stable local reference image reads
- Updated frontend history reuse and viewer flows to read persisted reference image URLs first, with fallback for older jobs
- Switched GPT image jobs with reference images toward the edit endpoint flow instead of treating local upload as UI-only state

### Reference Persistence Round 1 Review

- Backend syntax verification passed
- Frontend production build passed
- Fixed one P1 runtime regression during review:
  - `jobs` insert placeholder count did not match the new column count
- Re-tested `gpt-image-2-vip` edit flow with local reference images
- Confirmed the previous fake-upload path has been replaced by a real backend image-edit submission path
- Current live-provider verification with a real reference image is in progress because the `VIP` endpoint is synchronous and high-latency

### UI Refinement Round 6

- Added a dedicated `生成同款` action into the image detail viewer action area
- Placed the reuse action in the viewer bottom-right controls so it matches the gallery-level reuse flow
- Reused the existing job-to-form restore logic instead of creating a second implementation path
- Next: verify frontend build and review this viewer change for layout or interaction regressions

### UI Refinement Round 6

- Removed the remaining left-side descriptive header copy and inline status helper text requested by screenshot feedback
- Increased section padding and spacing so content sits less tightly against the split edges
- Reworked the right-side area from split result/history sections into a single image-list surface
- Added generating placeholders so a new task appears in the image list before completion
- Changed the image list toward a thumbnail-grid presentation instead of stacked detail cards
- Kept the existing local history API as the backing data source for the unified image grid
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 7

- Tightened the delete-image flow so a successful delete now re-syncs the gallery from the backend instead of only mutating local state
- Added explicit delete failure feedback so API errors no longer look like a no-op in the UI
- Next: verify frontend build and review whether delete now closes the viewer and removes the image consistently with no remaining P1+ issues

- Removed the basic/advanced mode toggle and fixed the UI to the baseline parameter set only
- Moved ratio and resolution controls into the settings popover as grouped button selectors
- Fixed the settings popover so it opens inside the viewport instead of spilling off-screen
- Restored the ratio selector layout so all options remain visible across two rows on desktop
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 8

- Kept the combined ratio/resolution picker as a floating selector above the bottom control row
- Reduced the floating selector to a compact small-panel size instead of a large modal-like panel
- Set the outer floating selector radius to `6px`
- Compressed ratio tiles and resolution buttons while keeping resolution in one row and ratios in grid rows
- Removed stale mobile backdrop styling for the old selector modal behavior
- Verified frontend production build

### UI Refinement Round 9

- Added delete endpoint compatibility on the backend so image deletion now works through both `DELETE /api/jobs/{id}` and `POST /api/jobs/{id}/delete`
- Added frontend fallback logic so a `405 Method Not Allowed` on the delete request automatically retries through the compatible POST path
- Next: verify frontend build, backend syntax, and review that no new P1+ issue remains in the delete flow

### UI Refinement Round 10

- Removed the unnecessary Supabase dependency for local reference images when the selected model is Gemini Nano Banana Pro
- Kept GPT local-reference behavior unchanged because that provider path still needs externally reachable image URLs
- Next: restart backend on current code and verify Gemini local-reference submission no longer fails with `400`

### UI Refinement Round 11

- Normalized legacy model aliases into the current model ids across backend validation, backend job serialization, and frontend draft/reuse flows
- This closes a stale-state path where old history or saved drafts could re-submit deprecated model names even though the current GPT routes themselves work
- Next: rebuild frontend, restart backend, and verify GPT generation after replaying history or draft state
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 9

- Removed the static outer border treatment from unselected ratio tiles
- Kept selected ratio tiles visually distinct with a light border and white background
- Made ratio preview icons reflect their actual width-to-height ratio instead of using one fixed rectangle
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 10

- Changed model, count, and quality dropdown menus to open upward from the bottom control row
- Added `6px` radius to the dropdown menu panels
- Removed the ratio/resolution popover header, close button, and ratio title text
- Removed the visible prompt field label while keeping the prompt textarea
- Restored the prompt textarea to fill its original flexible height after removing the label
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 11

- Moved the reference image uploader above the prompt textarea
- Kept the prompt textarea as the main flexible-height area below the uploader
- Left the parameter row and generate button below the prompt area
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 12

- Removed the file uploader's secondary format/limit helper text
- Added fixed-size cropped thumbnail previews for uploaded reference images
- Added click-to-preview behavior for uploaded reference thumbnails
- Ensured clearing uploaded images also closes any open preview overlay
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 13

- Added keyboard navigation inside the reference image preview overlay
- `ArrowLeft` and `ArrowRight` now cycle through uploaded reference images
- `Escape` closes the preview overlay
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 14

- Added a hover-only delete control to each uploaded reference thumbnail
- Deleting one thumbnail removes the matching image data and filename together
- Closing/removing a thumbnail also closes any active preview state
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 15

- Replaced the custom reference uploader with FilePond and its image preview plugin
- Enabled FilePond multi-image upload, delete, and drag reorder
- Synced FilePond's current order back into `reference_images` and `reference_names`
- Kept click-to-preview and keyboard navigation for uploaded reference images
- Reduced the FilePond idle upload area height to keep the control compact
- Verified frontend production build
- Audit note: `npm audit --omit dev` could not complete because registry DNS lookup failed in the current environment
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 16

- Separated the FilePond upload drop area from the uploaded thumbnail list visually
- Forced uploaded FilePond previews back into fixed `58px` square thumbnails
- Hid FilePond file name/status text in thumbnail mode
- Made FilePond remove controls hover-only again
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 17

- Reverted the FilePond uploader integration at user request
- Removed FilePond-related frontend dependencies
- Restored the custom uploader with fixed cropped thumbnails
- Restored hover-only thumbnail delete controls
- Kept click-to-preview and keyboard navigation for uploaded reference images
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 18

- Added `dnd-kit` to the custom reference thumbnail uploader
- Enabled drag sorting for uploaded reference thumbnails without replacing the custom UI
- Reordering thumbnails now updates `reference_images` and `reference_names` in the same order
- Preserved cropped thumbnails, hover delete, click preview, and keyboard preview navigation
- Verified frontend production build
- Audit note: installing `dnd-kit` surfaced an existing high-severity npm audit warning; no force audit fix was applied
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 19

- Reverted the `dnd-kit` thumbnail sorting integration after the page showed a runtime white screen
- Removed `@dnd-kit/core`, `@dnd-kit/sortable`, and `@dnd-kit/utilities`
- Restored the stable custom reference uploader state from before sorting
- Verified frontend production build
- Review result: no remaining P1+ findings for restoring page availability

### UI Refinement Round 20

- Added custom pointer-based drag sorting for reference thumbnails without third-party dependencies
- Dragging a thumbnail over another thumbnail and releasing now reorders both image data and file names
- Preserved upload, cropped thumbnails, hover delete, click preview, and keyboard preview navigation
- Added click suppression after a drag so releasing a drag does not accidentally open preview
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 21

- Reintroduced `dnd-kit` for reference thumbnail sorting using stable per-image IDs
- Added `reference_ids` to keep thumbnail sort identity separate from array index
- Scoped `SortableContext` to thumbnails only, leaving upload and clear controls outside sorting
- Kept cropped thumbnails, hover delete, click preview, and keyboard preview navigation
- Verified frontend production build
- Review result: no remaining P1+ findings from static/build checks

### UI Refinement Round 22

- Diagnosed the post-`dnd-kit` white screen as Vite dev server optimized dependency cache returning `504 Outdated Optimize Dep`
- Restarted the frontend dev server with `vite --force` through `npm run dev -- --host 127.0.0.1 --port 5173 --force`
- Verified the frontend dev server responds with HTTP 200
- Backend dev server on `127.0.0.1:8000` was left running
- Review result: no remaining P1+ findings for local dev server availability

### UI Refinement Round 23

- Changed reference image uploads from replace behavior to append behavior
- Added localStorage persistence for uploaded reference images, file names, and stable sort IDs
- Restored persisted reference images after page refresh
- Clear/delete/reorder flows now update the persisted draft automatically
- Verified frontend production build
- Review note: very large/many reference images can exceed browser localStorage quota; current-session generation still works if persistence fails
- Review result: no remaining P1+ findings for this round

### Settings Round 24

- Added `output_dir` to persisted backend settings with migration for existing databases
- Added a settings UI field for the image save folder
- New generated images are downloaded into the configured folder instead of always using `data/generated`
- `/generated/{filename}` now serves from the configured folder first, then falls back to the default generated folder
- Added backend regression tests for configured output directory downloads and dynamic generated-file serving
- Verified backend unit tests and frontend production build
- Review note: browsers cannot reliably expose an absolute folder path through `showDirectoryPicker`; users can manually paste an absolute local path for precise save location
- Review result: no remaining P1+ findings for this round

### Settings Round 25

- Added up to 4 project folders to persisted backend settings
- Added project folder editing UI with project name, folder path, choose, delete, and add controls
- Added `POST /api/projects/save` to copy a completed generated image into a selected project folder
- Added collision-safe project saves so existing files are not overwritten
- Added hover-only project save menu on completed gallery images
- Filtered incomplete project folder rows out of the gallery save menu
- Added backend regression tests for project folder limit, project copy, and non-overwrite behavior
- Review fix: restored GPT provider payload to always send `moderation=low`
- Verified backend unit tests and frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 26

- Fixed high-density gallery layout when many images are present
- Kept the density slider upper range, but clamped the gallery card minimum width to avoid unusably narrow cards
- Added dense-mode spacing and text truncation so failed placeholders, model labels, status labels, prompts, and error messages do not overflow or visually overlap
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 27

- Added prompt-side reference image mention support triggered by `=`
- Typing `=数字` now matches the current reference image order and inserts `图片N` when the number resolves to an existing image
- Invalid or non-existent numbers remain normal text and do not hijack prompt input
- Added an inline candidate menu above the prompt input with thumbnail previews for the current reference images
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 28

- Added inline prompt rendering for inserted `图片N` references
- Reference mentions now render with a colored bold label and a 1:1 thumbnail on the left while keeping the underlying prompt as plain text
- Kept the existing textarea editing path intact by using a visual mirror layer instead of replacing the input model
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 29

- Changed prompt reference mentions from bold text to colored inline labels
- Added a rounded hover/selection chip around each inline reference mention
- Implemented two-step keyboard deletion for prompt reference mentions:
  the first `Backspace`/`Delete` selects the whole mention and the second removes it
- Kept the reference mention thumbnail slightly taller than the text while preserving inline text flow
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 30

- Fixed prompt inline reference mentions so they stay in the same text flow as surrounding prompt text
- Narrowed the generic `.field` span styling so it no longer leaks into prompt inline mention rendering
- Increased reference mention text color contrast while keeping the font size aligned with surrounding prompt text
- Relaxed mention deletion targeting so the first delete selects the mention when the caret is inside it and the next delete removes it
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 31

- Replaced the prompt `textarea` and visual mirror layer with a real Slate editor
- Implemented prompt image mentions as Slate inline-void reference nodes instead of simulated plain-text tokens
- Kept the existing `=` reference picker flow, but now insertion creates atomic editor nodes so cursoring and deletion follow editor semantics instead of text-length heuristics
- Preserved prompt draft persistence and backend API compatibility by serializing the Slate document back into plain prompt text
- Installed `slate` and `slate-react` in the frontend workspace
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 32

- Expanded the prompt reference mention hover shell to include the left and right caret gaps around the inline mention node
- Adjusted prompt mention insertion so the editor selection lands immediately after the mention, allowing continuous typing without an extra click
- Removed stale `prompt-input` style references that no longer apply after the Slate migration
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 33

- Added Slate-side `Backspace` / `Delete` interception for prompt reference mentions
- The first delete keypress next to a reference mention now selects the whole inline mention node instead of deleting it immediately
- A follow-up delete keypress removes the selected inline mention node
- Kept the cursor-adjacent active-state styling aligned with the same inline mention selection semantics
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### Provider Reference Reliability Round 1

- Reviewed the reference-image strategy with `karpathy-guidelines` and narrowed the fix to provider request correctness rather than UI redesign
- Fixed GPT Image 2 moderation enforcement so every GPT-family request is forced to `low` server-side, independent of frontend state
- Corrected `gpt-image-2-vip` 4K size mappings to match the provided APIYI 30-size table
- Changed multi-image generation (`n=1..4`) to run up to 4 provider calls in parallel from the backend, avoiding unsupported `n` forwarding for VIP
- Removed unsupported `quality` and `n` fields from VIP text-to-image requests
- Kept GPT official reference-image edits on multipart `image[]` and VIP reference-image edits on repeated multipart `image`
- Changed VIP reference-image edit requests to use `size=auto`, avoiding provider size-budget failures on edit/fusion requests while preserving locked sizes for VIP text-to-image
- Fixed Nano Banana Pro / Gemini requests to use Bearer authorization, `generationConfig.imageConfig`, and camelCase `inlineData`
- Changed Gemini reference images so local persisted assets and remote URLs are converted to inline image bytes before provider submission, avoiding unreachable `127.0.0.1` file URLs
- Added backend tests covering:
  - GPT moderation low enforcement
  - GPT/VIP text-to-image request fields
  - GPT/VIP multipart edit fields and reference order
  - Gemini local/remote reference image inline payloads
  - Gemini ratio/resolution payload fields
  - reference asset content-hash deduplication
  - multi-image backend fan-out
  - history reference URL persistence
  - configured output folder, project-folder save, and delete flows
- Verified backend syntax check
- Verified backend unit tests: 19 tests passed
- Verified frontend production build
- Restarted the local backend on `127.0.0.1:8000`
- Verified backend health endpoint after restart
- Review result: no remaining P1+ findings in local request-construction and persistence paths
- Remaining external risk: provider-side visual adherence to reference images still requires real generation result inspection, but the local code now verifies that references are sent to each provider in a reachable format and preserved order

### Provider Reference Reliability Round 2

- Investigated the latest `gpt-image-2-vip` frontend `502 Bad Gateway`
- Confirmed the actual backend failure was `Download failed: Forbidden`, not a reference upload or size-validation failure
- Root cause: VIP was requested with `response_format=url`, then the backend had to download the returned provider URL and that URL returned `403 Forbidden`
- Changed VIP text-to-image and VIP image-edit requests to use `response_format=b64_json`
- Kept existing local base64 save logic, so VIP results no longer depend on a second download from a temporary provider URL
- Updated backend tests to assert VIP requests now use `b64_json`
- Verified backend syntax check
- Verified backend unit tests: 19 tests passed
- Verified frontend production build
- Restarted the backend on `127.0.0.1:8000`
- Verified backend health endpoint after restart
- Review result: no remaining P1+ findings for the VIP 403-download failure path

### Provider Reference Reliability Round 3

- Re-investigated repeated `gpt-image-2-vip` failures after the `b64_json` change
- Confirmed latest failures changed from local `Download failed: Forbidden` to provider-side generic failures with trace IDs
- Reviewed the current VIP edit request shape against the APIYI VIP edit documentation
- Identified a new P1 issue: VIP reference-image edit requests were still sending `size=auto`, so the frontend-selected `3:4 · 4K` was not being passed as the documented fixed VIP size
- Changed VIP reference-image edit requests to send the resolved pixel size, e.g. `3:4 · 4K` -> `2480x3312`
- Kept `response_format=b64_json` to avoid the prior provider URL download `403`
- Updated backend tests to assert VIP edit requests use the resolved pixel size
- Verified backend syntax check
- Verified backend unit tests: 19 tests passed
- Verified frontend production build
- Restarted the backend on `127.0.0.1:8000`
- Verified backend health endpoint after restart
- Review result: no remaining local P1+ findings in the VIP request-construction path
- Remaining external risk: a real VIP 4K edit request must be retried to determine whether the provider accepts `2480x3312` with references or still fails upstream

### UI Refinement Round 34

- Added a gallery hover action named `参考生图` on completed generated images
- The existing `生成同款` action remains on the hover overlay and still replaces prompt/reference images with the selected job's original inputs
- `参考生图` appends the generated image's local `/generated/...` URL into the current reference image list without replacing the current prompt or existing references
- New generated-image references are appended after the current reference order and are deduplicated by URL so repeated clicks do not add duplicates
- Added backend coverage proving generated image URLs can be reused as reference images and are downloaded into provider file payloads
- Verified backend syntax check
- Verified backend unit tests: 20 tests passed
- Verified frontend production build
- Verified backend health endpoint
- Review result: no remaining P1+ findings for this round

### UI Refinement Round 35

- Made gallery hover action buttons respond to the current gallery card size
- Added container-based sizing so `生成同款` and `参考生图` reduce padding, font size, and edge offsets when cards become small
- Kept the existing hover behavior and action placement unchanged
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### Windows Share Round 1

- Added `start-windows.bat` for a one-click Windows startup flow
- The script checks for Python and npm, creates `.venv`, installs backend dependencies, installs frontend dependencies, creates local data folders, starts backend/frontend windows, and opens `http://127.0.0.1:5173`
- Added `WINDOWS_SHARE.md` explaining how to package a clean copy for a friend
- The share guide explicitly removes `data/app.db`, generated images, reference assets, `.venv`, and `node_modules`
- The share guide keeps `apps/api/.env` so the same Supabase configuration can be reused while the friend enters their own API keys in settings
- Verified backend syntax check
- Verified backend unit tests: 20 tests passed
- Verified frontend production build
- Review result: no remaining P1+ findings for this round

### Provider Error Handling Round 1

- Investigated the latest official `gpt-image-2` failure shown as `400 Bad Request`
- Confirmed the failing backend job was rejected by the provider safety system with `safety_violations=[sexual]`
- Confirmed the official `gpt-image-2` request path is still functional because a later `gpt-image-2` job completed successfully
- Added provider safety-error normalization so future safety rejections show a Chinese, actionable message instead of only exposing a generic 400
- Preserved useful diagnostics in the user-facing error, including violation type and provider request ID when present
- Verified backend syntax check
- Verified backend unit tests: 21 tests passed
- Verified frontend production build
- Review result: no remaining local P1+ findings for request construction or safety-error display in this round
- Remaining external risk: provider moderation is not deterministic from local code; prompts/reference images that trigger upstream safety policy can still fail, but now the app identifies that failure mode clearly

### History Loading Round 1

- Investigated why the gallery appeared empty after switching the frontend to a new port
- Confirmed the database was not cleared: `data/app.db` still had 67 job records and `data/generated` still had generated image files
- Confirmed `/api/jobs` was returning history, but recent jobs included very large original `data:image/...base64` reference inputs in `image_urls`
- Changed the history list serializer to return stable `reference_image_urls` in `image_urls` when available, keeping the list response lightweight while preserving full detail serialization internally
- Added backend coverage for lightweight history-list serialization
- Verified backend syntax check
- Verified backend unit tests: 22 tests passed
- Verified frontend production build
- Restarted backend on `127.0.0.1:8001`
- Verified `/api/jobs` returns 20 history rows and the latest row's `image_urls` payload is now a small stable reference URL instead of a large base64 blob
- Review result: no remaining P1+ findings for history loading after port changes

### History Loading Round 2

- Re-investigated the gallery still appearing empty on frontend port `6677`
- Confirmed the root cause was CORS, not missing data: backend middleware still only allowed `5173`, so browser requests from `http://127.0.0.1:6677` were blocked
- Changed backend CORS policy to allow local development origins on any `127.0.0.1` / `localhost` port with `allow_origin_regex`
- Added backend coverage to lock the local-port CORS policy
- Verified backend syntax check
- Verified backend unit tests: 23 tests passed
- Verified frontend production build
- Restarted backend on `127.0.0.1:8001`
- Verified with a real `Origin: http://127.0.0.1:6677` request that `/api/jobs` now returns `access-control-allow-origin: http://127.0.0.1:6677`
- Verified `/api/jobs` still returns 20 history rows and the latest row has a completed result image
- Review result: no remaining local P1+ findings for gallery history loading from the new frontend port

### Reference Reuse Round 1

- Investigated broken reference thumbnails after clicking `生成同款`
- Confirmed the database still contained old stable reference URLs pointing at `http://127.0.0.1:8000/reference-assets/...`
- Root cause: the backend hardcoded local reference asset URLs to port `8000`, while the active backend is now `8001`
- Changed `LOCAL_API_BASE_URL` to default to `http://127.0.0.1:8001` and support `AIGC_LOCAL_API_BASE_URL` override for future port changes
- Added backend serialization normalization so old `localhost` / `127.0.0.1` reference asset URLs are rewritten to the current local API base URL
- Added frontend reuse fallback so any old local `/reference-assets/` URL is mapped to the current `API_BASE_URL` before being placed back into the editor
- Added backend coverage for old-port reference asset URL rewriting
- Verified backend syntax check
- Verified backend unit tests: 24 tests passed
- Verified frontend production build
- Restarted backend on `127.0.0.1:8001`
- Verified `/api/jobs` no longer contains `:8000/reference-assets/` and now contains `:8001/reference-assets/`
- Verified a rewritten reference asset URL returns `200 image/png`
- Review result: no remaining local P1+ findings for `生成同款` reference thumbnail recovery

### Port Migration Round 1

- Moved the local backend from the common `8001` port to the less common `38381`
- Updated backend `LOCAL_API_BASE_URL` default to `http://127.0.0.1:38381`
- Added frontend `VITE_API_BASE_URL` support with a default of `http://127.0.0.1:38381`
- Added TypeScript `ImportMeta.env` typing for the new frontend environment variable
- Updated `start-windows.bat` to start the backend on `38381` and set `AIGC_LOCAL_API_BASE_URL` consistently
- Updated `WINDOWS_SHARE.md` to document backend port `38381`
- Verified no production code still hardcodes old backend ports `8000` or `8001`
- Verified backend syntax check
- Verified backend unit tests: 24 tests passed
- Verified frontend production build
- Restarted local backend on `127.0.0.1:38381` and frontend on `127.0.0.1:6677`
- Verified `/api/jobs` returns 20 history rows and reference asset URLs now use `:38381`
- Verified CORS allows `http://127.0.0.1:6677` to access `http://127.0.0.1:38381`
- Review result: no remaining local P1+ findings for the backend port migration

### Prompt Reference Editing Round 1

- Investigated Slate prompt editor bugs after typing `=数字` to insert a reference image mention
- Root cause: `insertPromptReference` inserted a space after the inline-void reference and then moved the cursor backward, leaving selection between the reference node and the space instead of in a real text node after the reference
- Secondary issue: delete handling treated any adjacent reference range as already selected, so deleting after typed text could select/delete the reference unexpectedly
- Changed reference insertion to insert the reference node plus an explicit following empty text node, then move selection into that following text node
- Changed deletion handling so the first Backspace/Delete selects the reference node and only a second keypress deletes it when the current selection exactly equals the reference node range
- Verified with a minimal Slate transform script that insertion produces `[text, reference, trailing text]` and selection lands at the trailing text point
- Verified backend syntax check and backend unit tests: 24 tests passed
- Verified frontend production build
- Restarted frontend on `127.0.0.1:6677`
- Review result: no remaining local P1+ findings for reference mention cursor placement and two-step deletion semantics

### Prompt Reference Editing Round 2

- Reproduced the remaining mid-sentence insertion bug with a minimal Slate transform script
- Confirmed the previous `Transforms.move(..., unit: "offset")` fix was still wrong for mid-sentence insertion because Slate already placed selection at the text point immediately after the inline-void reference
- The extra move skipped the first following character, matching the observed cursor jump after `微`
- Removed the explicit cursor move from `insertPromptReference`
- Verified with a minimal Slate script that both mid-sentence and sentence-end insertion now leave selection at the text node immediately after the reference, offset `0`
- Verified no `Transforms.move(editor...)` prompt-reference insertion logic remains
- Verified backend unit tests: 24 tests passed
- Verified frontend production build
- Restarted frontend on `127.0.0.1:6677`
- Review result: no remaining local P1+ findings for mid-sentence reference insertion

### Prompt Reference Editing Round 3

- Investigated the remaining IME bug where only one visible character could be typed after an inline image reference unless a real space existed after it
- Root cause: an empty text node after a Slate inline-void reference is not a stable composition anchor for Chinese IME in this browser/Slate setup
- Added an invisible `\uFEFF` anchor text node after each prompt reference mention so IME has a real text position after the inline-void node without showing a visible space
- Updated prompt serialization to strip the invisible anchor before saving/submitting prompt text, so provider prompts remain unchanged
- Updated prompt deserialization so reused/history references get the same invisible anchor
- Updated Backspace/Delete handling so pressing delete next to the invisible anchor selects the reference node instead of deleting the anchor first
- Updated reference deletion to remove only the deleted reference's adjacent invisible anchor while preserving anchors after other reference mentions
- Verified with Slate scripts:
  - inserted references serialize without the invisible anchor
  - selection lands after the invisible anchor and before the following visible text
  - deleting one reference removes only its adjacent anchor and preserves anchors for other references
- Verified backend unit tests: 24 tests passed
- Verified frontend production build
- Restarted frontend on `127.0.0.1:6677`
- Review result: no remaining local P1+ findings for Chinese IME typing after inline image references
