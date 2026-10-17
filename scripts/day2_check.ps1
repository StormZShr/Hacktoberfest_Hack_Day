$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8000"
$tmp = if ($env:LAUNCHPAD_TMP) { $env:LAUNCHPAD_TMP } else { Join-Path $env:TEMP "launchpad-checks" }
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$ok = 0; $fail = 0
function Check($name, $condition, $detail) {
  if ($condition) { $script:ok++; "PASS  $name  $detail" } else { $script:fail++; "FAIL  $name  $detail" }
}
function ErrText($e) { return "$($e.Exception.Response.StatusCode.value__) $($e.ErrorDetails.Message)" }
function AuthHeader($token) { return @{ Authorization = "Bearer $token" } }

# curl.exe status code for a request (used for multipart uploads and downloads)
function CurlCode($curlArgs) { return (& curl.exe -s -o NUL -w "%{http_code}" @curlArgs) }

$h = $null
for ($i = 0; $i -lt 40; $i++) {
  try { $h = Invoke-RestMethod "$base/health" -TimeoutSec 5; break } catch { Start-Sleep -Milliseconds 500 }
}
Check "health ok with model pulled" ($h.status -eq "ok" -and $h.ollama.model_pulled) "status=$($h.status) model=$($h.model)"

# fixtures
$payloadDir = Join-Path $tmp "day2_payload"
New-Item -ItemType Directory -Force -Path $payloadDir | Out-Null
Set-Content -Path (Join-Path $payloadDir "README.md") -Value "# Queue Tracker`n`nRun: python main.py"
Set-Content -Path (Join-Path $payloadDir "main.py") -Value "print('hello from the ZIP')"
$zipPath = Join-Path $tmp "day2_project.zip"
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path (Join-Path $payloadDir "*") -DestinationPath $zipPath
$zipBytes = (Get-Item $zipPath).Length
$emptyZip = Join-Path $tmp "day2_empty.zip"
New-Item -ItemType File -Force -Path $emptyZip | Out-Null
$notZip = Join-Path $tmp "day2_notes.txt"
Set-Content -Path $notZip -Value "not a zip"

# users
$seller = Invoke-RestMethod "$base/auth/login" -Method Post -ContentType "application/json" `
  -Body (@{ email = "ananya@example.com"; password = "launchpad123" } | ConvertTo-Json)
$sellerAuth = AuthHeader $seller.access_token
$buyerEmail = "buyer.$([DateTime]::UtcNow.Ticks)@example.com"
$buyerReg = Invoke-RestMethod "$base/auth/register" -Method Post -ContentType "application/json" `
  -Body (@{ email = $buyerEmail; name = "Day Two Buyer"; password = "launchpad123" } | ConvertTo-Json)
$buyerAuth = AuthHeader $buyerReg.access_token
$otherReg = Invoke-RestMethod "$base/auth/register" -Method Post -ContentType "application/json" `
  -Body (@{ email = "other.$([DateTime]::UtcNow.Ticks)@example.com"; name = "Someone Else"; password = "launchpad123" } | ConvertTo-Json)
$otherAuth = AuthHeader $otherReg.access_token

# seller flow: README -> autofill -> save -> upload -> review -> publish
$readme = "# Canteen Queue Tracker`n`nShows the canteen queue length. FastAPI + SQLite.`n`n## Setup`n1. pip install -r requirements.txt`n2. uvicorn main:app --reload"
$af = Invoke-RestMethod "$base/ai/autofill" -Method Post -Headers $sellerAuth -ContentType "application/json" `
  -Body (@{ readme_text = $readme } | ConvertTo-Json) -TimeoutSec 600
Check "A1 autofill from the seller's README" ([bool]$af.title -and [bool]$af.description) "title='$($af.title)'"

$payload = @{
  title = $af.title; tagline = $af.tagline; description = $af.description
  tech_stack = $af.tech_stack; category = $af.category; difficulty = $af.difficulty
  what_you_get = $af.what_you_get; demo_points = $af.demo_points
  price_inr = 349; demo_url = ""; readme_text = $readme
} | ConvertTo-Json -Depth 5
$draft = Invoke-RestMethod "$base/projects" -Method Post -Headers $sellerAuth -ContentType "application/json" -Body $payload
Check "draft saved from the filled listing" ($draft.status -eq "draft" -and $draft.has_file -eq $false) "id=$($draft.id) has_file=$($draft.has_file)"

$fileUrl = "$base/projects/$($draft.id)/file"
$bearer = "Authorization: Bearer $($seller.access_token)"
$code = CurlCode @("-X", "POST", "-H", $bearer, "-F", "file=@$notZip", $fileUrl)
Check "non-ZIP upload rejected" ($code -eq "400") "http $code"
$code = CurlCode @("-X", "POST", "-H", $bearer, "-F", "file=@$emptyZip", $fileUrl)
Check "empty ZIP rejected" ($code -eq "400") "http $code"
$code = CurlCode @("-X", "POST", "-H", "Authorization: Bearer $($otherReg.access_token)", "-F", "file=@$zipPath", $fileUrl)
Check "another seller cannot upload" ($code -eq "403") "http $code"

$uploaded = (curl.exe -s -X POST -H $bearer -F "file=@$zipPath" $fileUrl) | ConvertFrom-Json
Check "ZIP upload attaches the file" ($uploaded.has_file -eq $true) "has_file=$($uploaded.has_file)"

$review = Invoke-RestMethod "$base/ai/review" -Method Post -Headers $sellerAuth -ContentType "application/json" `
  -Body (@{ project_id = $draft.id; readme_text = $readme } | ConvertTo-Json) -TimeoutSec 600
Check "A2 review on the saved draft" ($review.score -ge 0 -and $review.score -le 100) "score=$($review.score) missing=$($review.missing_items.Count)"

$published = Invoke-RestMethod "$base/projects/$($draft.id)/publish" -Method Post -Headers $sellerAuth
Check "publish with ZIP and review" ($published.status -eq "published") "status=$($published.status)"
$public = Invoke-RestMethod "$base/projects/$($draft.id)"
Check "published listing is public and hides the README" ($public.id -eq $draft.id -and $public.has_file -eq $true) "has_file=$($public.has_file)"

# A3 ask
$ask = Invoke-RestMethod "$base/projects/$($draft.id)/ask" -Method Post -ContentType "application/json" `
  -Body (@{ question = "How do I run it?" } | ConvertTo-Json) -TimeoutSec 600
Check "A3 answers from the listing text" ([bool]$ask.answer) "in_listing=$($ask.in_listing) answer='$($ask.answer)'"
$ask2 = Invoke-RestMethod "$base/projects/$($draft.id)/ask" -Method Post -ContentType "application/json" `
  -Body (@{ question = "What is the annual revenue and how many staff does the company employ?" } | ConvertTo-Json) -TimeoutSec 600
Check "A3 flags an answer that is not in the listing" ($ask2.in_listing -eq $false) "in_listing=$($ask2.in_listing) answer='$($ask2.answer)'"

# download gating
$downloadUrl = "$base/projects/$($draft.id)/download"
$code = CurlCode @("-H", "Authorization: Bearer $($buyerReg.access_token)", $downloadUrl)
Check "buyer without an order gets 403" ($code -eq "403") "http $code"
$code = CurlCode @($downloadUrl)
Check "anonymous download gets 401" ($code -eq "401") "http $code"

# buy with the mock provider
try { Invoke-RestMethod "$base/orders" -Method Post -Headers $sellerAuth -ContentType "application/json" `
        -Body (@{ project_id = $draft.id } | ConvertTo-Json) | Out-Null
      Check "seller cannot buy their own project" $false "no error raised" }
catch { Check "seller cannot buy their own project" ($_.Exception.Response.StatusCode.value__ -eq 400) (ErrText $_) }

$order = Invoke-RestMethod "$base/orders" -Method Post -Headers $buyerAuth -ContentType "application/json" `
  -Body (@{ project_id = $draft.id } | ConvertTo-Json)
Check "order created pending with a mock reference" ($order.status -eq "pending" -and $order.provider -eq "mock" -and $order.amount_inr -eq 349 -and $order.provider_ref -like "mock_*") `
  "status=$($order.status) ref=$($order.provider_ref) amount=$($order.amount_inr)"

$code = CurlCode @("-H", "Authorization: Bearer $($buyerReg.access_token)", $downloadUrl)
Check "pending order still blocks the download" ($code -eq "403") "http $code"

$confirmed = Invoke-RestMethod "$base/orders/$($order.id)/confirm" -Method Post -Headers $buyerAuth
Check "mock confirm marks the order paid" ($confirmed.status -eq "paid") "status=$($confirmed.status)"
try { Invoke-RestMethod "$base/orders/$($order.id)/confirm" -Method Post -Headers $otherAuth | Out-Null
      Check "another buyer cannot confirm" $false "no error raised" }
catch { Check "another buyer cannot confirm" ($_.Exception.Response.StatusCode.value__ -eq 403) (ErrText $_) }

$outFile = Join-Path $tmp "day2_downloaded.zip"
Remove-Item $outFile -Force -ErrorAction SilentlyContinue
$headersFile = Join-Path $tmp "day2_headers.txt"
$code = (& curl.exe -s -D $headersFile -o $outFile -w "%{http_code}" -H "Authorization: Bearer $($buyerReg.access_token)" $downloadUrl)
$downloaded = Get-Item $outFile
$signature = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($outFile)[0..1])
$disposition = (Select-String -Path $headersFile -Pattern "Content-Disposition").Line
Check "paid buyer downloads the ZIP" ($code -eq "200" -and $downloaded.Length -eq $zipBytes -and $signature -eq "PK") `
  "http $code bytes=$($downloaded.Length)/$zipBytes signature=$signature $($disposition -replace '\r','')"

$sellerFile = Join-Path $tmp "day2_seller.zip"
$code = (& curl.exe -s -o $sellerFile -w "%{http_code}" -H "Authorization: Bearer $($seller.access_token)" $downloadUrl)
Check "seller can download their own ZIP" ($code -eq "200" -and (Get-Item $sellerFile).Length -eq $zipBytes) "http $code bytes=$((Get-Item $sellerFile).Length)"

$code = CurlCode @("-H", "Authorization: Bearer $($otherReg.access_token)", $downloadUrl)
Check "non-buyer still gets 403" ($code -eq "403") "http $code"

try { Invoke-RestMethod "$base/orders" -Method Post -Headers $buyerAuth -ContentType "application/json" `
        -Body (@{ project_id = $draft.id } | ConvertTo-Json) | Out-Null
      Check "second order on the same project rejected" $false "no error raised" }
catch { Check "second order on the same project rejected" ($_.Exception.Response.StatusCode.value__ -eq 400) (ErrText $_) }

$myOrders = Invoke-RestMethod "$base/orders/me" -Headers $buyerAuth
Check "buyer's order list carries the project title" ($myOrders.Count -eq 1 -and [bool]$myOrders[0].project_title) "orders=$($myOrders.Count) title='$($myOrders[0].project_title)'"

$secret = Invoke-RestMethod "$base/projects" -Method Post -Headers $sellerAuth -ContentType "application/json" `
  -Body (@{ title = "Not published yet"; price_inr = 10 } | ConvertTo-Json)
try { Invoke-RestMethod "$base/projects/$($secret.id)/ask" -Method Post -ContentType "application/json" `
        -Body (@{ question = "anything" } | ConvertTo-Json) | Out-Null
      Check "ask on a draft is 404" $false "no error raised" }
catch { Check "ask on a draft is 404" ($_.Exception.Response.StatusCode.value__ -eq 404) (ErrText $_) }

$search = Invoke-RestMethod "$base/projects?q=queue&max_price=400"
$searchHit = (@($search) | Where-Object { $_.title -like "*Queue*" } | Measure-Object).Count
Check "search q + max_price filter" ($searchHit -ge 1) "queue matches=$searchHit of $(@($search).Count)"
$techSearch = Invoke-RestMethod "$base/projects?tech=FastAPI"
Check "tech filter reads the JSON tech_stack" ((@($techSearch) | Measure-Object).Count -ge 1) "matches=$(@($techSearch).Count)"
$catSearch = Invoke-RestMethod "$base/projects?category=web-app"
$catOff = (@($catSearch) | Where-Object { $_.category -ne "web-app" } | Measure-Object).Count
Check "category filter" ($catOff -eq 0) "matches=$(@($catSearch).Count), off-category=$catOff"

""
"RESULT: $ok passed, $fail failed"
