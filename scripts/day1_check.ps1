$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8001"
$ok = 0; $fail = 0
function Check($name, $condition, $detail) {
  if ($condition) { $script:ok++; "PASS  $name  $detail" } else { $script:fail++; "FAIL  $name  $detail" }
}
function ErrText($e) {
  $code = $e.Exception.Response.StatusCode.value__
  $body = $e.ErrorDetails.Message
  return "$code $body"
}

# 0. health
$h = $null
for ($i = 0; $i -lt 40; $i++) {
  try { $h = Invoke-RestMethod "$base/health" -TimeoutSec 5; break } catch { Start-Sleep -Milliseconds 500 }
}
Check "health" ($h.status -eq "ok" -and $h.ollama.model_pulled) ($h | ConvertTo-Json -Compress -Depth 5)

# 1. register
$email = "day1.$([DateTime]::UtcNow.Ticks)@example.com"
$reg = Invoke-RestMethod "$base/auth/register" -Method Post -ContentType "application/json" `
  -Body (@{ email = $email; name = "Day One Check"; password = "launchpad123" } | ConvertTo-Json)
$auth = @{ Authorization = "Bearer $($reg.access_token)" }
Check "register returns token" ([bool]$reg.access_token) "user=$email"

# 2. login
$login = Invoke-RestMethod "$base/auth/login" -Method Post -ContentType "application/json" `
  -Body (@{ email = $email; password = "launchpad123" } | ConvertTo-Json)
$auth = @{ Authorization = "Bearer $($login.access_token)" }
$me = Invoke-RestMethod "$base/auth/me" -Headers $auth
Check "login + /auth/me" ($me.email -eq $email) "me.id=$($me.id) name=$($me.name)"

# 3. duplicate register is rejected
try { Invoke-RestMethod "$base/auth/register" -Method Post -ContentType "application/json" `
        -Body (@{ email = $email; name = "Dup"; password = "launchpad123" } | ConvertTo-Json) | Out-Null
      Check "duplicate email rejected" $false "no error raised" }
catch { Check "duplicate email rejected" ($_.Exception.Response.StatusCode.value__ -eq 400) (ErrText $_) }

# 4. create a deliberately weak draft
$weak = @{
  title = "Weak Project"; tagline = ""; description = ""; price_inr = 50; demo_url = ""
  tech_stack = @(); readme_text = "just some notes, no setup steps and no licence"
} | ConvertTo-Json
$p = Invoke-RestMethod "$base/projects" -Method Post -Headers $auth -ContentType "application/json" -Body $weak
Check "create draft" ($p.status -eq "draft" -and $p.id -gt 0) "project id=$($p.id)"

# 5. publish without any demo link/file -> 400
try { Invoke-RestMethod "$base/projects/$($p.id)/publish" -Method Post -Headers $auth | Out-Null
      Check "publish blocked without demo or file" $false "no error raised" }
catch { Check "publish blocked without demo or file" ($_.Exception.Response.StatusCode.value__ -eq 400) (ErrText $_) }

# 6. update draft (partial update)
$upd = Invoke-RestMethod "$base/projects/$($p.id)" -Method Put -Headers $auth -ContentType "application/json" `
  -Body (@{ demo_url = "https://github.com/example/weak-project" } | ConvertTo-Json)
Check "update draft" ($upd.demo_url -eq "https://github.com/example/weak-project") "demo_url set"

# 7. publish with a demo link but no review yet -> 400
try { Invoke-RestMethod "$base/projects/$($p.id)/publish" -Method Post -Headers $auth | Out-Null
      Check "publish blocked before review" $false "no error raised" }
catch { Check "publish blocked before review" ($_.Exception.Response.StatusCode.value__ -eq 400) (ErrText $_) }

# 8. A2 review on the weak listing (real local model call)
$sw = [Diagnostics.Stopwatch]::StartNew()
$rev = Invoke-RestMethod "$base/ai/review" -Method Post -Headers $auth -ContentType "application/json" `
  -Body (@{ project_id = $p.id } | ConvertTo-Json) -TimeoutSec 600
$sw.Stop()
$revText = $rev | ConvertTo-Json -Compress
Check "review returns score + missing_items" `
  ($rev.score -ge 0 -and $rev.score -le 100 -and $rev.missing_items.Count -gt 0) `
  "score=$($rev.score) missing=$($rev.missing_items.Count) flags=$($rev.risk_flags.Count) in $([int]$sw.Elapsed.TotalSeconds)s :: $revText"

# 9. review is cached on the row
$afterReview = Invoke-RestMethod "$base/projects/$($p.id)" -Headers $auth
Check "review cached on project row" ($afterReview.ai_score -eq $rev.score -and $null -ne $afterReview.ai_review) `
  "ai_score=$($afterReview.ai_score)"

# 10. publish now succeeds
$pub = Invoke-RestMethod "$base/projects/$($p.id)/publish" -Method Post -Headers $auth
Check "publish after review" ($pub.status -eq "published") "status=$($pub.status)"

# 11. ownership: another seller cannot edit or publish my project
$other = Invoke-RestMethod "$base/auth/login" -Method Post -ContentType "application/json" `
  -Body (@{ email = "rahul@example.com"; password = "launchpad123" } | ConvertTo-Json)
$otherAuth = @{ Authorization = "Bearer $($other.access_token)" }
try { Invoke-RestMethod "$base/projects/$($p.id)" -Method Put -Headers $otherAuth -ContentType "application/json" `
        -Body (@{ title = "stolen" } | ConvertTo-Json) | Out-Null
      Check "other seller cannot edit" $false "no error raised" }
catch { Check "other seller cannot edit" ($_.Exception.Response.StatusCode.value__ -eq 403) (ErrText $_) }

# 12. anonymous can list published projects only
$list = Invoke-RestMethod "$base/projects"
Check "public list returns only published" (($list | Where-Object { $_.status -ne "published" }).Count -eq 0) `
  "published=$($list.Count)"

# 13. draft is 404 for anonymous, visible to its owner
try { Invoke-RestMethod "$base/projects/$($p.id)" -Headers @{} -ErrorAction Stop | Out-Null
      Check "published project is public" $true "owner=false" }
catch { Check "published project is public" $false (ErrText $_) }
$draft = Invoke-RestMethod "$base/projects" -Method Post -Headers $auth -ContentType "application/json" `
  -Body (@{ title = "Secret draft"; price_inr = 10 } | ConvertTo-Json)
try { Invoke-RestMethod "$base/projects/$($draft.id)" | Out-Null; Check "draft hidden from anonymous" $false "no error" }
catch { Check "draft hidden from anonymous" ($_.Exception.Response.StatusCode.value__ -eq 404) (ErrText $_) }
$own = Invoke-RestMethod "$base/projects/$($draft.id)" -Headers $auth
Check "draft visible to owner" ($own.id -eq $draft.id) "id=$($own.id)"

# 14. A1 autofill on a sample README (real local model call)
$readme = @"
# Campus Canteen Queue Tracker

A small FastAPI app that shows how long the canteen queue is right now.
Students tap the queue length at the counter, and the page shows an average
of the last ten taps. Data is stored in SQLite.

## Setup
1. pip install -r requirements.txt
2. uvicorn main:app --reload
3. Open http://localhost:8000

Built with Python, FastAPI, SQLite, HTML and CSS. No licence yet, no tests.
"@
$sw2 = [Diagnostics.Stopwatch]::StartNew()
$af = Invoke-RestMethod "$base/ai/autofill" -Method Post -Headers $auth -ContentType "application/json" `
  -Body (@{ readme_text = $readme } | ConvertTo-Json) -TimeoutSec 600
$sw2.Stop()
$a = $af | ConvertTo-Json -Compress
Check "autofill returns valid listing JSON" `
  ([bool]$af.title -and [bool]$af.tagline -and [bool]$af.description -and $af.tech_stack.Count -gt 0 `
    -and $af.demo_points.Count -eq 3 -and $af.what_you_get.Count -ge 3 `
    -and $af.category -in @("web-app","mobile-app","ml-ai","cli-tool","library","game","data","other") `
    -and $af.difficulty -in @("beginner","intermediate","advanced")) `
  "in $([int]$sw2.Elapsed.TotalSeconds)s :: $a"

# 15. autofill rejects an empty paste
try { Invoke-RestMethod "$base/ai/autofill" -Method Post -Headers $auth -ContentType "application/json" `
        -Body (@{ readme_text = "" } | ConvertTo-Json) | Out-Null
      Check "autofill rejects empty input" $false "no error raised" }
catch { Check "autofill rejects empty input" ($_.Exception.Response.StatusCode.value__ -eq 422) (ErrText $_) }

# 16. review of an unsaved listing (no project_id)
$rev2 = Invoke-RestMethod "$base/ai/review" -Method Post -Headers $auth -ContentType "application/json" `
  -Body (@{ listing = @{ title = "Queue Tracker"; tagline = "shows the canteen queue"; price_inr = 99 } } | ConvertTo-Json) `
  -TimeoutSec 600
Check "review works on an unsaved listing" ($rev2.score -ge 0) "score=$($rev2.score)"

""
"RESULT: $ok passed, $fail failed"
