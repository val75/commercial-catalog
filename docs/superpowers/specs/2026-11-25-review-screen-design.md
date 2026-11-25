# Review queue and review screen: design

Date: 2026-11-25. Status: draft, waiting for approval.

Mockups (private): https://claude.ai/artifact/Nzx3xgn7pQYGiRDwPC5hCi.
Board A ("Side by side") is the chosen review screen and board D is the queue.
Boards B and C were rejected alternatives, and only C's badge colors carry over.
All data in the mockups is invented.

---

## 1. Why

When a vendor quote arrives, the user checks it by hand today. For each quote they work out:

- how many servers were quoted (often unclear: one, or many?);
- what parts are in each server, and exactly what each one is: manufacturer, model, cores and so on;
- whether the memory is DDR4 or DDR5.

An approved quote is then used to build a similar offer for the user's own customers, based on (1) the
hardware configuration a customer asks for (a particular GPU, an amount of RAM, a CPU) and (2) the price.

The pipeline (`pipeline.process_file` / `process_text`) already turns an upload into quote drafts with
checks. What's missing is the place where a person looks at a draft next to the original, settles what
the pipeline couldn't, and approves it. This is the last piece of the Phase 1 workflow in
`docs/00-purpose.md`: upload, review, approve (search comes after).

## 2. Goals

- A queue of quotes waiting for review, with enough on each row to choose which to open.
- A review screen that shows the original document next to what the AI read, with every issue on the
  part it belongs to, so a typical quote is checked in well under a minute.
- Nothing uncertain reaches the catalog without a person choosing it.
- Approved and rejected quotes are kept, together with every decision the reviewer made.

## 3. Non-goals (this project)

- **Warranties.** Set aside by the user for now; extraction leaves them out.
- Matching parts to a component library, or servers to a system library (docs/04, docs/03 §7).
- Hermes (docs/07), confidence scores, "Assigned to".
- Search (docs/08). It's the next project and will read what this one stores.
- Treating a PDF and its spreadsheet export as one quote.
- Scanned PDFs (OCR) and DOCX.
- Quote revisions, and comparing them.
- Splitting a bundled server price across its parts.

## 4. Anti-goals

The project fails, even if it works, if:

- a guessed (inferred) value ends up in an approved quote without the reviewer ticking it or typing it;
- a quote can be approved while a question is still open;
- the original document is changed, lost, or not visible while reviewing;
- an import fails and nobody notices, because it never appears anywhere;
- real quote data (vendor, customer, prices, codes) appears in code, tests, fixtures or docs. The repo
  is public.

## 5. Constraints

- Python 3.11, FastAPI, PostgreSQL, React (docs/09). Postgres and Node are installed locally through
  Homebrew. Node is only for development: the built React files are served by FastAPI, so the server
  needs no Node at runtime (decided 2026-11-25).
- **PostgreSQL, not a document database such as MongoDB** (decided 2026-11-25). Drafts, decisions and
  approved snapshots go in JSONB columns, which gives the same flexibility while the draft format
  changes. The catalog itself is relational: one list of components that quotes and systems point to,
  queries across quotes by configuration and price, and approval updating several records together.
- **One user, no login** for now (decided 2026-11-25). Nothing in the design should assume a single
  user so firmly that adding sign-in later means a rewrite: decisions record "who" as a plain field.
- The model's base URL comes from config/env (`MODEL_BASE_URL`), never from code.
- **Extraction runs one document at a time.** Parallel requests to the model server changed the drafts,
  so the server processes uploads in order, never several at once.
- `review_draft` never changes a draft. Proposals (such as 3.84 TB) are applied only by review.
- Keep the three layers of every import: the original file, the normalized Markdown and the extracted
  draft, so extraction can be re-run without re-uploading.
- Tests build their own inputs in memory and use invented data. Model tests stay behind
  `RUN_MODEL_TESTS=1`.

## 6. Build order (decided)

1. **Storage** in Postgres: documents, imports, drafts, review decisions, approved quotes.
2. **Server API** in FastAPI: upload, list the queue, get one quote, record decisions, approve, reject,
   undo, retry and remove failed imports.
3. **The two screens** in React: the queue (board D) and the review screen (board A).

Each step is usable and tested before the next starts.

---

## 7. The queue (board D)

The app opens on the queue when there's something to review (docs/10).

**Top bar.** App name, the search box (inactive until search exists), and the main menu: Review queue,
Search, Components, Systems, Vendors, Settings. Only Review queue works in this project.

**Failed imports.** A red section above the queue, one row per failed import, with the file name, the
date received, and the reason in plain words:

- a model failure (no reply, cut-off reply, reply that doesn't fit the schema): the reason, a line on
  what it usually means, and **Retry**, **Download log** and **Remove**;
- a scanned PDF: "A scanned image with no text. Scanned PDFs aren't supported yet." and **Remove** only.

The section is hidden when nothing failed.

**Controls.** A filter with "All N quotes" and "Ready to approve N" (counts are quotes, not rows), the
note "Oldest first", and an **Upload quote** button.

**One row per quote**, oldest first, in four columns:

| Column | Content |
|---|---|
| Quote | Vendor · quote number, then the date received and the source file (or "pasted text") |
| What was quoted | One line: server count × model, then CPU, GPU (or "no GPU") and total memory with DDR type |
| Price | Price per server, then the total |
| To check | Compact badges that may wrap onto two lines |

The badges and their colors are shared with the review screen:

- **question** (orange), **guess** (grey), **change** (blue), each with a count;
- **✓ Ready** (green) when no question is open. A quote with nothing at all to check shows ✓ Ready alone.

**A file or paste that held several quotes** gets one main row: a +/− button, the vendor, a "N quotes"
tag, the date and file, the quote numbers, and a summary badge such as "2 ready" or "3 questions".
Opening it shows each quote as its own row underneath, indented and shaded, with a line on its left. Each
child row shows its file and where in it the quote sits ("page 1", "pages 2–3") when that's known.

Clicking a quote row opens the review screen.

## 8. The review screen (board A)

**Header.** Back to the queue; quote number and vendor; servers, price per server, total and date
received; on the far right, the three badges (questions, guesses, changes) with counts.

**Left: the original document.** For a PDF, the real page, not extracted text. For a spreadsheet or a
paste, its text. It's always visible. Clicking a part on the right highlights the line(s) it came from.

**Right: what the AI read.** One section per quote item (a quote with two server models has two
sections). Parts are listed per server, each with its make, model and key properties: for memory, always
the DDR type. A small note confirms counts, for example "8 across 4 servers".

**Issues sit under the part they belong to,** on a background tinted in their badge's color:

- **Question** (orange). Something the pipeline can't decide, today the number per server when the quote
  is ambiguous. One-click answers ("1 per server", "4 per server") plus "Another number". **Approve stays
  disabled until every question is answered.**
- **Guess** (grey). A value marked inferred: not in the quote, worked out by the model, for example core
  counts from a CPU model name. It's shown with its reason and starts **unticked**. The reviewer either
  ticks it to use it, or types a different value in the field next to it. An unticked guess with nothing
  typed is left empty in the approved quote.
- **Change** (blue). A value the code adjusted, today the standard SSD size (3.8 TB recorded as 3.84 TB
  on full-server quotes). It's applied unless the reviewer clicks to keep the original.

Guesses and changes never block approval.

**Correcting a plain mistake.** Any value on the right can be clicked and corrected, including its basis
(stated or inferred), as `docs/review-fixes.md` asks.

**Other things the screen shows**, from `docs/review-fixes.md`, which the builder must read:

- the reason next to every value that has one, and its basis, so a stated value with an "implies" reason
  stands out;
- long reasons folded, with a visible marker;
- a server item with an empty chassis shown as missing, not hidden;
- the model's own review notes (`review_flags` on quotes and parts) shown on the quote or the part, as
  notes that don't block approval.

**Bottom.** **Reject** and **Approve**, with a line saying what still blocks approval.

## 9. Approve, reject, undo (decided)

- **Approve** saves the quote with the reviewer's decisions applied, removes it from the queue and goes
  back to the queue list. A note at the top says "Approved Q-48210" with an **Undo** button.
- **Reject** asks for a one-line reason, keeps the quote and its document, and goes back to the queue
  list.
- **Undo** puts the quote back in the queue with all its decisions as they were.

---

## 10. How the pipeline's output maps to the screen

| Pipeline output | Shown as |
|---|---|
| `QuantityCheck` with `per_server` None (its flags give the question) | Question; blocks approval |
| `QuantityCheck` with a number, `calculated` True | The "8 across 4 servers" note on the part |
| A property with `basis` inferred | Guess, unticked, editable |
| `inferred_without_reason` flag | Shown on that guess: "no reason given" |
| `CapacityCheck` with `automatic` True | Change, applied unless kept |
| `CapacityCheck` flags without an automatic value | Note on the drive (builder: confirm what each issue means) |
| `review_flags` strings from the model | Note on the quote or part |

Several lines of one kind can share one `QuantityCheck` (one question for two RAID controller lines).
The screen asks it once and the answer applies to all of them.

## 11. Storage (step 1)

The builder designs the tables. What they must hold:

- **Document:** the original file's bytes (or a path to them), name, type, SHA-256, received date, the
  normalized Markdown, its warnings and meta. Never changed after upload.
- **Import:** one per upload. Status (waiting, processing, done, failed), the failure reason and a log.
  Retry runs extraction again from the stored Markdown.
- **Draft:** one per quote found in the document, in document order, with the extracted JSON exactly as
  the model returned it after cleanup, and the checks from `review_draft`.
- **Review:** per draft. Status (needs review, approved, rejected), every decision (answer, ticked guess,
  typed value, kept original, correction), the reject reason, and who/when.
- **Approved quote:** the draft with the decisions applied, plus the vendor, quote number, date, currency
  and prices as columns, so search can find them later.

Keeping decisions apart from the draft is what makes Undo and re-running extraction possible, and lets
Hermes learn from corrections later.

## 12. Server API (step 2)

The builder shapes the endpoints. They must cover: upload a file or pasted text; list the queue (with
failed imports and groups); get one quote with its document, draft, checks and decisions; serve the
original file and any page images; record a decision; approve; reject with a reason; undo; retry and
remove a failed import; download an import's log.

Uploads return straight away. Extraction runs in the background, one document at a time.

## 13. Calls I made (check these)

- **Processing state.** Not in the mockups. While a document is waiting or being read, the queue shows
  it as a row with "Reading the quote…" and no badges.
- **Duplicate upload.** A file whose SHA-256 is already stored isn't imported again. The user is told
  and shown the existing quote.
- **Approved quotes are stored as a JSON snapshot plus a few columns** in this project. The full table
  structure for search (vendors, quotes, line items, components) is designed with search.
- **Original files** live in a folder set by config, not in the database.
- **Undo** stays available until the note is dismissed or another quote is approved. After that,
  approved quotes can't be reopened in this project.
- **Rejected quotes** are found through a "Rejected" filter on the queue.
- **Page locations** for child rows ("page 1") are worked out by finding the quote number in the PDF's
  page text. When it can't be found, the row shows only the file name.
- **Source highlighting** finds the part's vendor code, part number or description in the document,
  the same way `extraction/cleanup.py` finds a part's line. On a PDF page it uses the word positions
  pdfplumber gives. When nothing is found, nothing is highlighted, and that's fine.
- The other suggestions in `docs/review-fixes.md` (short forms for network technology, a choice list
  for adapter type, OPN lookup, marking a chassis model that equals the server's) come later.

## 14. Left to the builder

Table and column names, endpoint paths and payloads, the background worker, the React component
structure and state, how a PDF page is rendered, error messages, and visual details within the mockups'
look (Inter, the warm grey palette, the badge colors).
