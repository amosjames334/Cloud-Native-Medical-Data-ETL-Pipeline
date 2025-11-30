#!/bin/bash

# Script to create Airflow API user for CI/CD and frontend access

set -e

NAMESPACE="airflow"
USERNAME="api_user"
PASSWORD="${AIRFLOW_API_PASSWORD:-changeme123}"  # Set via environment variable
EMAIL="api@medical-etl.local"

echo "🔐 Creating Airflow API User..."

# Get the webserver pod name
WEBSERVER_POD=$(kubectl get pods -n $NAMESPACE -l component=webserver -o jsonpath='{.items[0].metadata.name}')

if [ -z "$WEBSERVER_POD" ]; then
    echo "❌ Error: Airflow webserver pod not found"
    exit 1
fi

echo "📡 Found webserver pod: $WEBSERVER_POD"

# Create the user
echo "👤 Creating user: $USERNAME"
kubectl exec -it $WEBSERVER_POD -n $NAMESPACE -- \
    airflow users create \
    --username $USERNAME \
    --password $PASSWORD \
    --firstname API \
    --lastname User \
    --role Admin \
    --email $EMAIL

echo "✅ User created successfully!"
echo ""
echo "📋 Credentials:"
echo "   Username: $USERNAME"
echo "   Password: $PASSWORD"
echo "   Role: Admin"
echo ""
echo "⚠️  IMPORTANT: Save these credentials securely!"
echo ""
echo "🔧 Next steps:"
echo "1. Add to GitHub Secrets:"
echo "   - AIRFLOW_USERNAME: $USERNAME"
echo "   - AIRFLOW_PASSWORD: $PASSWORD"
echo "   - AIRFLOW_URL: http://localhost:8080 (or your Airflow URL)"
echo ""
echo "2. Use in frontend dashboard when prompted"
