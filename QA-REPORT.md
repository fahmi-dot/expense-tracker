# QA Report — Expense Tracker

**Verdict: NO-GO** — multiple Must requirements fail: noncanonical date accepted, delete/cancel semantics broken, invalid report filters silently accepted. Automated existing tests pass, but their coverage is shallow.

## Scope and environment
- Reviewed `PRD.md`, `FSD.md`, `README.md`, `app.py`, templates, and tests.
- Python 3.14 runtime, Flask test client, SQLite temporary DB, pytest 9.2.0.
- Existing suite: `PYTHONPATH=. pytest -q` → **4 passed**, 35 DeprecationWarnings (`datetime.utcnow()`). `python -m py_compile app.py` → success.
- Added independent `tests/qa_probe.py`; ran `PYTHONPATH=. pytest -q -s tests/qa_probe.py` → 1 passed, 14 warnings. Probe prints actual behavior; it does not assert known defects.
- A separate direct shell probe initially failed with `ModuleNotFoundError: No module named 'flask'` under that shell’s Python. Project test invocation had dependencies available, so functional tests ran via pytest.

## Results overview
- Test cases: 12; passed 5, failed 7; blocked/not tested: not counted as test cases. Existing suite 4/4 passed.
- Open defects: Critical 0, High 4, Medium 2, Low 0.

## Traceability matrix
| Requirement | Test cases | Result |
|---|---|---|
| FR-001 add | QA-01 | Pass: valid add returns 303 and appears in list; existing test confirms amount/description |
| FR-002 validation | QA-02 | Fail: noncanonical date accepted; zero/negative/fraction/bad calendar date/missing category rejected |
| FR-003 list | QA-03 | Pass: list shows date/category/amount/description and actions in template |
| FR-004 edit | QA-04 | Not tested: automated suite lacks edit execution |
| FR-005 delete | QA-05 | Fail: UI confirmation cancellable, but no confirmation form; absent ID falsely redirects |
| FR-006 categories | QA-06 | Fail: missing-ID operations falsely redirect; existing test covers add/duplicate only |
| FR-007 daily | QA-07 | Fail: malformed date query returns 200 rather than validation error; totals otherwise exercised by existing test |
| FR-008 monthly | QA-08 | Fail: invalid month returns 200; existing month aggregate basic path passes |
| FR-009 CSV | QA-09 | Pass for Unicode, commas, quotes, newline; no systematic period/empty export test |
| FR-010 seed | QA-10 | Pass: seeded categories visible in existing suite |
| NFR-001 local/no login | QA-11 | Partial: README specifies local URL, `app.py` binds 127.0.0.1; no live-server/network isolation test |
| NFR-002 persistence | QA-12 | Not tested across restart; validation atomicity probe showed extra row from accepted bad-format date |
| NFR-003 privacy | QA-11 | Not tested with network instrumentation; code inspection found no external HTTP client/call |
| NFR-004 field errors | QA-02 | Partial/fail: common invalid forms show field messages; malformed report query has no error |
| NFR-005 date/IDR | QA-01, QA-03 | Partial: IDR formatter and ISO examples present; parser accepts noncanonical input and echoes noncanonical dates |
| NFR-006 aggregates | QA-07, QA-08 | Partial: simple totals pass; boundary/leap-year cases not tested |

## Test cases
| ID | Steps / expected | Actual / status |
|---|---|---|
| QA-01 | POST valid expense; expect 303 and saved/listed | `add=303`; existing expense test passes. **Pass** |
| QA-02 | Submit zero, negative, fractional, invalid calendar date, noncanonical date, nonexistent category; invalid inputs should be rejected and DB unchanged | Outputs: zero/negative/fraction/bad_calendar_date/missing_category 400; `noncanonical_date=303`; `count_after_invalid=2` (valid initial row plus improperly accepted row). **Fail** |
| QA-03 | Inspect expense list output and controls | `templates/list.html` renders required fields and edit/delete controls; existing test confirms amount and description. **Pass** |
| QA-04 | Edit valid and invalid existing transaction, ensure target-only update | Not executed. **Not tested** |
| QA-05 | Cancel delete; confirm delete; try nonexistent ID | UI only submits `confirm=yes` and JS `confirm()`; decline means no request, but direct POST immediately deletes. `POST /expenses/999/delete` → 302, not expected 404. **Fail** |
| QA-06 | Delete nonexistent category/update nonexistent category; expect 404 | `POST /categories/999` and `/categories/999/delete` both → 302. **Fail** |
| QA-07 | GET valid daily date and invalid query date; malformed date should reject | Existing valid daily test passes. `/reports/daily?date=notdate` → 200. **Fail** |
| QA-08 | GET valid month and invalid month; malformed month should reject | Existing valid monthly total passes. `/reports/monthly?month=2026-99` → 200. **Fail** |
| QA-09 | Export Unicode/comma/quote/newline; CSV should parse intact | `GET /export.csv` emitted header and correctly quoted `Kopi, "pagi" ☕\nbaris`. **Pass** |
| QA-10 | First-run defaults available | Existing test confirms `Makanan`; `app.py` seeds six named categories. **Pass** |
| QA-11 | Confirm no login and local bind/no external service | Source has no auth and `app.run` defaults host to 127.0.0.1. No live bind or network capture. **Partial / not fully tested** |
| QA-12 | Restart persistence, empty export/month, aggregate boundary, CSRF/security checks | Not executed. **Not tested** |

## Defects
### D-01 — Noncanonical date accepted as valid
- **Severity:** High; **Requirement:** FR-002, NFR-005.
- **Preconditions:** running Flask app with temporary DB.
- **Reproduction:** POST `/expenses` with `expense_date=2026-2-3`, `amount=1000`, `category_id=1`.
- **Expected:** 400; date must match exact `YYYY-MM-DD`; no row saved.
- **Actual:** 303; SQLite stores `2026-2-3`; report/list filters use string equality/prefix, so aggregates/export periods may omit or misclassify it.
- **Evidence:** `tests/qa_probe.py`; output `noncanonical_date=303`, `count_after_invalid=2`; `app.py:27` uses `datetime.strptime` without round-trip format equality.

### D-02 — Delete transaction has no server-side confirmation and nonexistent ID reports success
- **Severity:** High; **Requirement:** FR-005.
- **Preconditions:** existing transaction or arbitrary ID.
- **Reproduction:** POST `/expenses/<id>/delete` with `confirm=yes` directly, without confirmation page; also try nonexistent ID.
- **Expected:** server presents confirmation before mutation; cancel leaves row; nonexistent ID returns 404.
- **Actual:** UI sends destructive POST directly after a browser JS confirmation; crafted POST deletes immediately. Missing ID returns 302 as success.
- **Evidence:** `templates/list.html` has direct POST form; `app.py:63-66`; probe output `missing_expense_delete=302`.

### D-03 — Category update/delete accept nonexistent IDs as successful redirects
- **Severity:** High; **Requirement:** FR-006, FSD 6.1/6.2.
- **Reproduction:** POST `/categories/999` with `name=X`; POST `/categories/999/delete`.
- **Expected:** 404 for missing resource.
- **Actual:** both redirect 302 without changing records.
- **Evidence:** probe output `missing_category_update=302`, `missing_category_delete=302`; `app.py:75-83` lacks existence checks.

### D-04 — Invalid daily/monthly filter values silently render success
- **Severity:** High; **Requirement:** FR-007/008, FSD 6.2/7.4.
- **Reproduction:** GET `/reports/daily?date=notdate`; GET `/reports/monthly?month=2026-99`.
- **Expected:** invalid filter rejected with 400 and useful message.
- **Actual:** both return 200; malformed periods produce misleading empty/zero reports.
- **Evidence:** probe outputs both statuses 200; `app.py:84-89` does not validate query formats/calendar ranges.

### D-05 — Cancel affordance relies on JavaScript; no explicit cancel flow
- **Severity:** Medium; **Requirement:** FR-005, FSD 6.3/7.2.
- **Reproduction:** disable JavaScript and inspect/delete form; there is no confirmation page/token or cancel control.
- **Expected:** confirmation/cancel behavior remains clear; cancel preserves transaction.
- **Actual:** HTML form submits delete immediately when activated; only `onclick=confirm()` provides cancellation. Without JS, action deletes directly.
- **Evidence:** `templates/list.html`, direct POST with hidden `confirm=yes`; FSD specifies confirmation browser/halaman and no JS dependency for core flow.

## Not tested / limitations
- Valid edit, edit validation atomicity, confirmed/cancel UI flow, empty export, CSV period filters, leap-year/year-boundary totals, restart persistence, DB failure rollback, keyboard/accessibility, live local server, network isolation, and CSRF were not fully tested.
- No tests against user database; QA probe used temporary SQLite.

## Regression and retest log
- No fixes delivered during this QA pass; no retest round.

## Recommendations
1. Fix D-01 through D-04 before release; validate canonical date and report filters at server boundary; 404 missing IDs; require explicit server-side delete confirmation.
2. Add tests for edit/delete, category missing IDs, period boundaries, empty export, restart persistence, and no-write assertions.
3. Resolve shell runtime discrepancy for documented setup; test project install/run in a clean environment.
4. Replace deprecated `datetime.utcnow()` with timezone-aware UTC timestamps.
