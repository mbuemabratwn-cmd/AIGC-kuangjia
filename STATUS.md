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
