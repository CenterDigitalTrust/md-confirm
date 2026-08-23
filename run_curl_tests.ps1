$mockHash = "test_hash_" + (Get-Date -UFormat "%s")
$mockContent = "this is a mock image " + $mockHash
$fileBytes = [System.Text.Encoding]::UTF8.GetBytes($mockContent)
$fileHash = (Get-FileHash -InputStream ([System.IO.MemoryStream]::new($fileBytes)) -Algorithm SHA256).Hash.ToLower()

Write-Host "=== 1. SIGNING A MOCK FILE ==="
Write-Host "Computed hash: $fileHash"

# We'll use Invoke-RestMethod for /sign
$boundary = [System.Guid]::NewGuid().ToString()
$LF = "`r`n"
$bodyLines = (
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"test.jpg`"",
    "Content-Type: image/jpeg",
    "",
    $mockContent,
    "--$boundary--"
) -join $LF

$resSign = Invoke-RestMethod -Uri "http://localhost:8000/sign" -Method Post -Body $bodyLines -ContentType "multipart/form-data; boundary=$boundary" -Headers @{"X-Device-Attestation-Key"="valid-hardware-key-123"}
Write-Host ($resSign | ConvertTo-Json -Depth 5)

Write-Host "`n=== 2. VERIFYING CONTENT (Agent 2 & 3) ==="
$bodyLinesVerify = (
    "--$boundary",
    "Content-Disposition: form-data; name=`"file`"; filename=`"test.jpg`"",
    "Content-Type: image/jpeg",
    "",
    $mockContent,
    "--$boundary",
    "Content-Disposition: form-data; name=`"is_original`"",
    "",
    "true",
    "--$boundary",
    "Content-Disposition: form-data; name=`"high_priority`"",
    "",
    "true",
    "--$boundary--"
) -join $LF

$resVerify = Invoke-RestMethod -Uri "http://localhost:8000/verify" -Method Post -Body $bodyLinesVerify -ContentType "multipart/form-data; boundary=$boundary"
Write-Host ($resVerify | ConvertTo-Json -Depth 5)

Write-Host "`n=== 3. TESTING RECEIPT FOR $fileHash (SUCCESS) ==="
$resReceipt = Invoke-RestMethod -Uri "http://localhost:8000/receipt/$fileHash" -Method Get
Write-Host ($resReceipt | ConvertTo-Json -Depth 5)

Write-Host "`n=== 4. TESTING RECEIPT FOR FAKE HASH (404) ==="
try {
    $resFail = Invoke-RestMethod -Uri "http://localhost:8000/receipt/0000000000000000000000000000000000000000000000000000000000000000" -Method Get
} catch {
    Write-Host $_.Exception.Response.StatusCode
    $stream = $_.Exception.Response.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($stream)
    Write-Host $reader.ReadToEnd()
}
