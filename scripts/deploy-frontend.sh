#!/bin/bash

# Script to deploy frontend to Kubernetes
# This creates a ConfigMap from the frontend files and applies the deployment

set -e

NAMESPACE="airflow"
FRONTEND_DIR="frontend"

echo "🚀 Deploying Medical ETL Frontend Dashboard..."

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Error: frontend directory not found"
    exit 1
fi

# Create or update frontend-files ConfigMap
echo "📦 Creating ConfigMap from frontend files..."
kubectl create configmap frontend-files \
    --from-file=$FRONTEND_DIR/ \
    --namespace=$NAMESPACE \
    --dry-run=client -o yaml | kubectl apply -f -

echo "✅ ConfigMap created/updated"

# Apply Kubernetes resources
echo "🔧 Applying Kubernetes resources..."
kubectl apply -f kubernetes/frontend-deployment.yaml

echo "⏳ Waiting for deployment to be ready..."
kubectl rollout status deployment/frontend -n $NAMESPACE --timeout=120s

echo "✅ Frontend deployed successfully!"
echo ""
echo "📍 Access options:"
echo ""
echo "1. Port-forward (localhost access):"
echo "   kubectl port-forward svc/frontend-service 3000:80 -n $NAMESPACE"
echo "   Then open: http://localhost:3000"
echo ""
echo "2. Ingress (if configured):"
echo "   Update /etc/hosts with: <INGRESS_IP> medical-etl-dashboard.local"
echo "   Then open: http://medical-etl-dashboard.local"
echo ""
echo "3. Get service details:"
echo "   kubectl get svc frontend-service -n $NAMESPACE"
