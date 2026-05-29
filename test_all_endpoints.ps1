# AI DocMaster - Complete Endpoint Test Script
# Tests all 6 features end-to-end

$BASE = "http://localhost:5001"
$testEmail = "testuser_$(Get-Random)@test.com"
$testPass = "test123456"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  AI DocMaster - Endpoint Test Suite" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ── 1. Health Check ──
Write-Host "[1/8] Health Check..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$BASE/health" -Method GET -TimeoutSec 10
    Write-Host "  Status: $($health.status)" -ForegroundColor Green
    Write-Host "  MongoDB: $($health.mongodb)" -ForegroundColor Green
    Write-Host "  Gemini: $($health.gemini_configured)" -ForegroundColor Green
    Write-Host "  Tesseract: $($health.tesseract_found)" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# ── 2. Register Test User ──
Write-Host "`n[2/8] Registering test user ($testEmail)..." -ForegroundColor Yellow
try {
    $signupBody = @{ name = "Test User"; email = $testEmail; password = $testPass } | ConvertTo-Json
    $signup = Invoke-RestMethod -Uri "$BASE/auth/signup" -Method POST -Body $signupBody -ContentType "application/json" -TimeoutSec 10
    Write-Host "  Signup: $($signup.message)" -ForegroundColor Green
} catch {
    $errBody = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
    Write-Host "  Signup note: $($errBody.error)" -ForegroundColor DarkYellow
}

# ── 3. Login & Get Token ──
Write-Host "`n[3/8] Logging in..." -ForegroundColor Yellow
try {
    $loginBody = @{ email = $testEmail; password = $testPass } | ConvertTo-Json
    $login = Invoke-RestMethod -Uri "$BASE/auth/login" -Method POST -Body $loginBody -ContentType "application/json" -TimeoutSec 10
    $TOKEN = $login.token
    Write-Host "  Login: $($login.message)" -ForegroundColor Green
    Write-Host "  Token: $($TOKEN.Substring(0, 20))..." -ForegroundColor DarkGray
} catch {
    Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

$headers = @{ Authorization = "Bearer $TOKEN" }

# ── Create a small test PDF ──
Write-Host "`n[4/8] Creating test PDF..." -ForegroundColor Yellow
$testPdfPath = "$env:TEMP\test_docmaster.pdf"

# Minimal valid PDF with text content
$pdfContent = @"
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
4 0 obj
<< /Length 284 >>
stream
BT
/F1 16 Tf
50 700 Td
(Artificial Intelligence in Modern Computing) Tj
0 -30 Td
/F1 12 Tf
(Machine learning is a subset of artificial intelligence that enables) Tj
0 -20 Td
(systems to learn and improve from experience without being explicitly) Tj
0 -20 Td
(programmed. Deep learning uses neural networks with many layers.) Tj
0 -20 Td
(Natural language processing allows computers to understand human language.) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000309 00000 n 
0000000240 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
645
%%EOF
"@
[System.IO.File]::WriteAllText($testPdfPath, $pdfContent)
Write-Host "  Created: $testPdfPath" -ForegroundColor Green

# Helper function to send multipart form with a file
function Send-FileRequest {
    param (
        [string]$Url,
        [string]$FilePath,
        [hashtable]$ExtraFields = @{},
        [string]$Token
    )
    
    $boundary = [System.Guid]::NewGuid().ToString()
    $fileName = [System.IO.Path]::GetFileName($FilePath)
    $fileBytes = [System.IO.File]::ReadAllBytes($FilePath)
    
    $bodyLines = New-Object System.Collections.ArrayList
    
    # Add file part
    [void]$bodyLines.Add("--$boundary`r`nContent-Disposition: form-data; name=`"file`"; filename=`"$fileName`"`r`nContent-Type: application/pdf`r`n`r`n")
    
    # Add extra fields
    foreach ($key in $ExtraFields.Keys) {
        [void]$bodyLines.Add("`r`n--$boundary`r`nContent-Disposition: form-data; name=`"$key`"`r`n`r`n$($ExtraFields[$key])")
    }
    
    [void]$bodyLines.Add("`r`n--$boundary--`r`n")
    
    $encoding = [System.Text.Encoding]::UTF8
    $bodyStream = New-Object System.IO.MemoryStream
    
    # Write pre-file text
    $preFileBytes = $encoding.GetBytes($bodyLines[0])
    $bodyStream.Write($preFileBytes, 0, $preFileBytes.Length)
    
    # Write file bytes
    $bodyStream.Write($fileBytes, 0, $fileBytes.Length)
    
    # Write remaining parts
    for ($i = 1; $i -lt $bodyLines.Count; $i++) {
        $partBytes = $encoding.GetBytes($bodyLines[$i])
        $bodyStream.Write($partBytes, 0, $partBytes.Length)
    }
    
    $bodyArray = $bodyStream.ToArray()
    $bodyStream.Dispose()
    
    $response = Invoke-RestMethod -Uri $Url -Method POST -Body $bodyArray `
        -ContentType "multipart/form-data; boundary=$boundary" `
        -Headers @{ Authorization = "Bearer $Token" } `
        -TimeoutSec 120
    
    return $response
}

# ── 5. Test AI Summary ──
Write-Host "`n[5/8] Testing AI Summary (brief mode)..." -ForegroundColor Yellow
try {
    $summaryResult = Send-FileRequest -Url "$BASE/ai/summary" -FilePath $testPdfPath -ExtraFields @{ mode = "brief" } -Token $TOKEN
    Write-Host "  Message: $($summaryResult.message)" -ForegroundColor Green
    $summaryText = $summaryResult.result.summary
    if ($summaryText) {
        Write-Host "  Summary preview: $($summaryText.Substring(0, [Math]::Min(150, $summaryText.Length)))..." -ForegroundColor DarkGray
    }
    Write-Host "  AI Summary: PASSED" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
    try { $errDetail = $_.ErrorDetails.Message | ConvertFrom-Json; Write-Host "  Detail: $($errDetail.error)" -ForegroundColor Red } catch {}
}

# ── 6. Test Resume Analyzer ──
Write-Host "`n[6/8] Testing Resume Analyzer..." -ForegroundColor Yellow
try {
    $resumeResult = Send-FileRequest -Url "$BASE/ai/resume-analyze" -FilePath $testPdfPath -ExtraFields @{ target_role = "Software Engineer" } -Token $TOKEN
    Write-Host "  Message: $($resumeResult.message)" -ForegroundColor Green
    Write-Host "  ATS Score: $($resumeResult.result.ats_score)" -ForegroundColor Green
    Write-Host "  Resume Analyzer: PASSED" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
    try { $errDetail = $_.ErrorDetails.Message | ConvertFrom-Json; Write-Host "  Detail: $($errDetail.error)" -ForegroundColor Red } catch {}
}

# ── 7. Test Notes Generator ──
Write-Host "`n[7/8] Testing Notes Generator..." -ForegroundColor Yellow
try {
    $notesResult = Send-FileRequest -Url "$BASE/ai/notes" -FilePath $testPdfPath -Token $TOKEN
    Write-Host "  Message: $($notesResult.message)" -ForegroundColor Green
    $notesText = $notesResult.result.summary
    if ($notesText) {
        Write-Host "  Notes preview: $($notesText.Substring(0, [Math]::Min(150, $notesText.Length)))..." -ForegroundColor DarkGray
    }
    Write-Host "  Notes Generator: PASSED" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
    try { $errDetail = $_.ErrorDetails.Message | ConvertFrom-Json; Write-Host "  Detail: $($errDetail.error)" -ForegroundColor Red } catch {}
}

# ── 8. Test Flashcard Maker ──
Write-Host "`n[8/8] Testing Flashcard Maker..." -ForegroundColor Yellow
try {
    $flashResult = Send-FileRequest -Url "$BASE/ai/flashcards" -FilePath $testPdfPath -Token $TOKEN
    Write-Host "  Message: $($flashResult.message)" -ForegroundColor Green
    $cardCount = ($flashResult.cards | Measure-Object).Count
    Write-Host "  Cards generated: $cardCount" -ForegroundColor Green
    if ($cardCount -gt 0) {
        Write-Host "  First card Q: $($flashResult.cards[0].question)" -ForegroundColor DarkGray
    }
    Write-Host "  Flashcard Maker: PASSED" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
    try { $errDetail = $_.ErrorDetails.Message | ConvertFrom-Json; Write-Host "  Detail: $($errDetail.error)" -ForegroundColor Red } catch {}
}

# ── Cleanup ──
Remove-Item $testPdfPath -ErrorAction SilentlyContinue

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Test Suite Complete!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
