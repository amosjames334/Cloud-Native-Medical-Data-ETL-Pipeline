# Script to create Airflow API user for CI/CD and frontend access (Windows PowerShell)

$ErrorActionPreference = "Stop"

$NAMESPACE = "airflow"
$USERNAME = "api_user"
$PASSWORD = if ($env:AIRFLOW_API_PASSWORD) { $env:AIRFLOW_API_PASSWORD } else { "changeme123" }
$EMAIL = "api@medical-etl.local"

Write-Host "🔐 Creating Airflow API User..." -ForegroundColor Green

# Get the webserver pod name
$WEBSERVER_POD = kubectl get pods -n $NAMESPACE -l component=webserver -o jsonpath='{.items[0].metadata.name}'

if (-not $WEBSERVER_POD) {
    Write-Host "❌ Error: Airflow webserver pod not found" -ForegroundColor Red
    exit 1
}

Write-Host "📡 Found webserver pod: $WEBSERVER_POD" -ForegroundColor Yellow

# Create the user
Write-Host "👤 Creating user: $USERNAME" -ForegroundColor Yellow
kubectl exec -it $WEBSERVER_POD -n $NAMESPACE -- `
    airflow users create `
    --username $USERNAME `
    --password $PASSWORD `
    --firstname API `
    --lastname User `
    --role Admin `
    --email $EMAIL

Write-Host "✅ User created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Credentials:" -ForegroundColor Cyan
Write-Host "   Username: $USERNAME" -ForegroundColor White
Write-Host "   Password: $PASSWORD" -ForegroundColor White
Write-Host "   Role: Admin" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  IMPORTANT: Save these credentials securely!" -ForegroundColor Yellow
Write-Host ""
Write-Host "🔧 Next steps:" -ForegroundColor Cyan
Write-Host "1. Add to GitHub Secrets:" -ForegroundColor White
Write-Host "   - AIRFLOW_USERNAME: $USERNAME" -ForegroundColor Gray
Write-Host "   - AIRFLOW_PASSWORD: $PASSWORD" -ForegroundColor Gray
Write-Host "   - AIRFLOW_URL: http://localhost:8080 (or your Airflow URL)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Use in frontend dashboard when prompted" -ForegroundColor White
