$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8000"
$ok = 0; $fail = 0
function Check($name, $condition, $detail) {
  if ($condition) { $script:ok++; "PASS  $name  $detail" } else { $script:fail++; "FAIL  $name  $detail" }
}

$seller = Invoke-RestMethod "$base/auth/login" -Method Post -ContentType "application/json" `
  -Body (@{ email = "ananya@example.com"; password = "launchpad123" } | ConvertTo-Json)
$sellerAuth = @{ Authorization = "Bearer $($seller.access_token)" }

$readme = "# Study Timer`n`nA pomodoro timer that logs sessions to SQLite.`n`n## Setup`n1. pip install -r requirements.txt`n2. python main.py"
$af = Invoke-RestMethod "$base/ai/autofill" -Method Post -Headers $sellerAuth -ContentType "application/json" `
  -Body (@{ readme_text = $readme } | ConvertTo-Json) -TimeoutSec 600
$payload = @{
  title = $af.title; tagline = $af.tagline; description = $af.description
  tech_stack = $af.tech_stack; category = $af.category; difficulty = $af.difficulty
  what_you_get = $af.what_you_get; demo_points = $af.demo_points
  price_inr = 199; demo_url = "https://github.com/example/study-timer"; readme_text = $readme
} | ConvertTo-Json -Depth 5
$draft = Invoke-RestMethod "$base/projects" -Method Post -Headers $sellerAuth -ContentType "application/json" -Body $payload
Invoke-RestMethod "$base/ai/review" -Method Post -Headers $sellerAuth -ContentType "application/json" `
  -Body (@{ project_id = $draft.id; readme_text = $readme } | ConvertTo-Json) -TimeoutSec 600 | Out-Null
Invoke-RestMethod "$base/projects/$($draft.id)/publish" -Method Post -Headers $sellerAuth | Out-Null

# three questions: two answerable from the listing, one not
$answerable = @("How do I run it?", "Which database does it use?")
foreach ($question in $answerable) {
  $ask = Invoke-RestMethod "$base/projects/$($draft.id)/ask" -Method Post -ContentType "application/json" `
    -Body (@{ question = $question } | ConvertTo-Json) -TimeoutSec 600
  Check "A3 flags '$question' as in the listing" ($ask.in_listing -eq $true) "in_listing=$($ask.in_listing) answer='$($ask.answer)'"
}
$ask3 = Invoke-RestMethod "$base/projects/$($draft.id)/ask" -Method Post -ContentType "application/json" `
  -Body (@{ question = "Who is the seller's employer and what is their salary?" } | ConvertTo-Json) -TimeoutSec 600
Check "A3 flags an off-listing question as not in the listing" ($ask3.in_listing -eq $false) "in_listing=$($ask3.in_listing) answer='$($ask3.answer)'"

""
"RESULT: $ok passed, $fail failed  (project $($draft.id))"
