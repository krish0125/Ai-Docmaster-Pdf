$body = '{"email":"test@test.com","password":"test123"}'
try {
    $result = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/auth/login' -Method POST -ContentType 'application/json' -Body $body -UseBasicParsing
    Write-Host "Status: $($result.StatusCode)"
    Write-Host "Body: $($result.Content)"
} catch {
    Write-Host "Error Status: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "Error: $($_.Exception.Message)"
}
