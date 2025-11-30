# Script to deploy frontend to Kubernetes (Windows PowerShell)
# This creates a ConfigMap from the frontend files and applies the deployment

$ErrorActionPreference = "Stop"

$NAMESPACE = "airflow"
$FRONTEND_DIR = "frontend"

Write-Host "Deploying Medical ETL Frontend Dashboard..." -ForegroundColor Green

# Check if frontend directory exists
if (-not (Test-Path $FRONTEND_DIR)) {
    Write-Host "Error: frontend directory not found" -ForegroundColor Red
    exit 1
}

# Create or update frontend-files ConfigMap
Write-Host "Creating ConfigMap from frontend files..." -ForegroundColor Yellow
kubectl create configmap frontend-files `
    --from-file=$FRONTEND_DIR/ `
    --namespace=$NAMESPACE `
    --dry-run=client -o yaml | kubectl apply -f -

Write-Host "ConfigMap created/updated" -ForegroundColor Green

# Apply Kubernetes resources
Write-Host "Applying Kubernetes resources..." -ForegroundColor Yellow
kubectl apply -f kubernetes/frontend-deployment.yaml

Write-Host "Waiting for deployment to be ready..." -ForegroundColor Yellow
kubectl rollout status deployment/frontend -n $NAMESPACE --timeout=120s

Write-Host "Frontend deployed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Access options:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Port-forward (localhost access):" -ForegroundColor White
Write-Host "   kubectl port-forward svc/frontend-service 3000:80 -n $NAMESPACE" -ForegroundColor Gray
Write-Host "   Then open: http://localhost:3000" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Ingress (if configured):" -ForegroundColor White
Write-Host "   Update C:\Windows\System32\drivers\etc\hosts with: [INGRESS_IP] medical-etl-dashboard.local" -ForegroundColor Gray
Write-Host "   Then open: http://medical-etl-dashboard.local" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Get service details:" -ForegroundColor White
Write-Host "   kubectl get svc frontend-service -n $NAMESPACE" -ForegroundColor Gray
