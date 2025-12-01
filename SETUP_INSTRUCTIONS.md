# Cloud Native Medical Data ETL Pipeline - Setup Instructions

## Part 1: Prerequisites

### 1.1 Install Tools
- **Docker Desktop**: Enable Kubernetes in settings
- **Python 3.9+**
- **AWS CLI**
- **Helm** (for Airflow)
- **PostgreSQL 14+** (Local installation)

### 1.2 Python Environment
```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Part 2: AWS Configuration

### 2.1 Configure AWS CLI
```powershell
aws configure
# Enter your AWS Access Key ID, Secret Access Key, Region (us-east-1), and Output format (json)
```

### 2.2 Create S3 Resources
```powershell
# Create bucket
aws s3 mb s3://medical-etl-data-lake-[YOUR-UNIQUE-ID]

# Create folders
aws s3api put-object --bucket medical-etl-data-lake-[YOUR-UNIQUE-ID] --key raw/
aws s3api put-object --bucket medical-etl-data-lake-[YOUR-UNIQUE-ID] --key processed/
aws s3api put-object --bucket medical-etl-data-lake-[YOUR-UNIQUE-ID] --key logs/
```

---

## Part 3: Kubernetes Setup

### 3.1 Create Namespace
```powershell
kubectl create namespace airflow
kubectl config set-context --current --namespace=airflow
```

### 3.2 Create Secrets
```powershell
# Create secret for AWS credentials and config
kubectl create secret generic airflow-env-vars `
  --from-literal=AWS_ACCESS_KEY_ID=[YOUR_ACCESS_KEY] `
  --from-literal=AWS_SECRET_ACCESS_KEY=[YOUR_SECRET_KEY] `
  --from-literal=AWS_DEFAULT_REGION=us-east-1 `
  --from-literal=S3_BUCKET=medical-etl-data-lake-[YOUR-UNIQUE-ID] `
  --from-literal=DOCKER_IMAGE=medical-etl-transform:v1 `
  -n airflow
```

---

## Part 4: Docker Setup

### 4.1 Build Transform Image
```powershell
# Build the image
docker build -f docker/Dockerfile.transform -t medical-etl-transform:v1 .
```

---

## Part 5: Airflow Installation (Git-Sync Method)

### 5.1 Setup External PostgreSQL
Airflow requires a database. We use a local PostgreSQL instance.

1.  **Install PostgreSQL 14+**
2.  **Create Database & User**:
    ```powershell
    psql -U postgres
    ```
    ```sql
    CREATE DATABASE airflow;
    CREATE USER airflow WITH PASSWORD 'airflow';
    GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;
    \q
    ```
3.  **Verify Connection**:
    ```powershell
    psql -U airflow -d airflow -h localhost -W
    # Password: airflow
    ```

### 5.2 Configure Airflow
Ensure your `airflow-values.yaml` file is configured for Git-Sync and External PostgreSQL.

**Key configurations in `airflow-values.yaml`:**
- `postgresql.enabled: false`
- `data.metadataConnection` configured for local PostgreSQL
- `dags.gitSync.enabled: true`
- `dags.gitSync.repo`: Your GitHub repository URL

### 5.3 Install/Upgrade Airflow
```powershell
# Add Helm repo
helm repo add apache-airflow https://airflow.apache.org
helm repo update

#github should be public or the container will not be able to pull the DAGs from the git repo.


# Install Airflow
helm install airflow apache-airflow/airflow `
  --namespace airflow `
  -f airflow-values.yaml `
  --timeout 15m
```

**If you need to update the configuration:**
```powershell
helm upgrade airflow apache-airflow/airflow `
  --namespace airflow `
  -f airflow-values.yaml `
  --timeout 15m


helm uninstall airflow -n airflow
kubectl delete pvc -n airflow --all
kubectl delete pod -n airflow --all
```

### 5.4 Verify Deployment
```powershell
# Watch pods until they are Running
kubectl get pods -n airflow -w

# Verify Git-Sync is working (check dag-processor logs, NOT scheduler)
# Since you have a standalone DAG processor, git-sync runs there.
kubectl logs -n airflow deployment/airflow-dag-processor -c git-sync --tail=20

# List DAGs (run on dag-processor)
kubectl exec -it deployment/airflow-dag-processor -n airflow -c dag-processor -- airflow dags list

# If DAGs are missing, check for import errors:
kubectl exec -it deployment/airflow-dag-processor -n airflow -c dag-processor -- airflow dags list-import-errors
```

### 5.5 Access Airflow UI
```powershell
# Port-forward
kubectl port-forward svc/airflow-api-server 8080:8080 --namespace airflow

# Access at http://localhost:8080
# User: admin / Password: admin
```

---

## Part 6: CI/CD and Dashboard Setup

### 6.1 Create Airflow API User
```powershell
# Run the script to create API user
.\scripts\create-airflow-user.ps1

# Save the credentials - you'll need them for GitHub Secrets and the dashboard
```

### 6.2 Configure GitHub Secrets
Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

- `AIRFLOW_URL`: Your Airflow URL (e.g., `http://localhost:8080`)
- `AIRFLOW_USERNAME`: API user username
- `AIRFLOW_PASSWORD`: API user password
- `EMAIL_USERNAME`: Your Gmail address
- `EMAIL_PASSWORD`: Gmail app password (see CICD_GUIDE.md)

### 6.3 Deploy Frontend Dashboard
```powershell
# Deploy the dashboard to Kubernetes
.\scripts\deploy-frontend.ps1

# Port-forward to access locally
kubectl port-forward svc/frontend-service 3000:80 -n airflow

# Open http://localhost:3000 in your browser
```

For detailed CI/CD and dashboard instructions, see Part 8 below.

---

## Part 7: Running the Pipeline

1.  **Trigger DAG**: Go to Airflow UI -> `medical_etl_pipeline` -> Trigger DAG.
2.  **Monitor**: Check logs in UI or use `kubectl logs`.
3.  **Verify Data**: Check S3 bucket for processed files.

---

## Part 8: CI/CD Pipeline and Frontend Dashboard Guide

This guide explains how to set up and use the CI/CD pipeline and monitoring dashboard for the Medical ETL Pipeline project.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Setting Up CI/CD Pipeline](#setting-up-cicd-pipeline)
4. [Deploying the Frontend Dashboard](#deploying-the-frontend-dashboard)
5. [Using the Dashboard](#using-the-dashboard)
6. [Troubleshooting](#troubleshooting)

## Overview

The Medical ETL Pipeline now includes:

- **GitHub Actions CI/CD**: Automatically validates, tests, and triggers DAGs when code changes
- **Frontend Dashboard**: Real-time monitoring of DAG runs, task status, and error logs
- **Email Notifications**: Automatic alerts on deployment success/failure

### Architecture

```
┌─────────────────┐
│  GitHub Push    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GitHub Actions  │
│  - Validate     │
│  - Test         │
│  - Trigger DAG  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Airflow API    │◄─────┤ Frontend         │
│  (Kubernetes)   │      │ Dashboard        │
└─────────────────┘      └──────────────────┘
```

## Prerequisites

Before setting up the CI/CD pipeline and dashboard, ensure you have:

- [x] Airflow deployed on Kubernetes (see Parts 1-5 above)
- [x] GitHub repository with push access
- [x] kubectl configured to access your Kubernetes cluster
- [x] Email account for notifications (Gmail recommended)

## Setting Up CI/CD Pipeline

### Step 1: Create Airflow API User

The CI/CD pipeline needs an Airflow user with API permissions.

**Windows (PowerShell):**
```powershell
cd d:\College\Projects\Cloud-Native-Medical-Data-ETL-Pipeline
.\scripts\create-airflow-user.ps1
```

**Linux/Mac:**
```bash
cd /path/to/Cloud-Native-Medical-Data-ETL-Pipeline
chmod +x scripts/create-airflow-user.sh
./scripts/create-airflow-user.sh
```

**Save the credentials** displayed - you'll need them for GitHub Secrets.

### Step 2: Update Airflow Configuration

The `airflow-values.yaml` has been updated to enable the REST API. Apply the changes:

```powershell
helm upgrade airflow apache-airflow/airflow `
  --namespace airflow `
  --values airflow-values.yaml `
  --timeout 10m
```

Wait for pods to restart:
```powershell
kubectl get pods -n airflow -w
```

### Step 3: Configure GitHub Secrets

Add the following secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `AIRFLOW_URL` | `http://your-airflow-url:8080` | Your Airflow webserver URL |
| `AIRFLOW_USERNAME` | `api_user` | Username from Step 1 |
| `AIRFLOW_PASSWORD` | `your-password` | Password from Step 1 |
| `EMAIL_USERNAME` | `your-email@gmail.com` | Gmail address for notifications |
| `EMAIL_PASSWORD` | `your-app-password` | Gmail app password (see below) |

#### Getting Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** if not already enabled
3. Go to **App passwords**
4. Generate a new app password for "Mail"
5. Use this password for `EMAIL_PASSWORD` secret

### Step 4: Test the CI/CD Pipeline

Make a change to trigger the pipeline:

```powershell
# Make a small change
echo "# Test CI/CD" >> README.md

# Commit and push
git add README.md
git commit -m "test: trigger CI/CD pipeline"
git push origin main
```

Check the GitHub Actions tab to see the pipeline running.

## Deploying the Frontend Dashboard

### Step 1: Deploy to Kubernetes

**Windows (PowerShell):**
```powershell
.\scripts\deploy-frontend.ps1
```

**Linux/Mac:**
```bash
chmod +x scripts/deploy-frontend.sh
./scripts/deploy-frontend.sh
```

### Step 2: Access the Dashboard

#### Option 1: Port-Forward (Recommended for Local Development)

```powershell
kubectl port-forward svc/frontend-service 3000:80 -n airflow
```

Open your browser to: **http://localhost:3000**

#### Option 2: Ingress (For Production)

If you have an Ingress controller installed:

1. Get the Ingress IP:
   ```powershell
   kubectl get ingress frontend-ingress -n airflow
   ```

2. Add to your hosts file:
   - **Windows**: `C:\Windows\System32\drivers\etc\hosts`
   - **Linux/Mac**: `/etc/hosts`
   
   Add line:
   ```
   <INGRESS_IP> medical-etl-dashboard.local
   ```

3. Open: **http://medical-etl-dashboard.local**

### Step 3: Login to Dashboard

When you first open the dashboard, you'll be prompted for credentials:

- **Username**: `api_user` (or your created username)
- **Password**: Your Airflow API password

The credentials are stored in browser localStorage for convenience.

## Using the Dashboard

### Dashboard Features

#### 1. **Stats Cards**
- **Success Rate**: Percentage of successful DAG runs
- **Total Runs**: Total number of DAG runs
- **Avg Duration**: Average execution time
- **Last Run**: Time since last execution

#### 2. **Recent DAG Runs**
- View all recent DAG runs
- Filter by status (All, Success, Failed, Running)
- Click to view detailed task information

#### 3. **Current Run Details**
- Detailed information about selected DAG run
- Task success/failure counts
- Execution timeline
- Configuration parameters

#### 4. **Task Status Grid**
- Visual representation of all tasks
- Color-coded by status:
  - 🟢 Green: Success
  - 🔴 Red: Failed
  - 🔵 Blue: Running
  - 🟡 Yellow: Queued

#### 5. **Error Logs**
- Automatic display of failed task logs
- Search functionality
- Expandable log entries

#### 6. **Run Statistics Chart**
- 7-day trend of successful vs failed runs
- Visual performance tracking

### Manual DAG Triggering

1. Click the **"Trigger DAG"** button in the header
2. Select an execution date (defaults to today)
3. Optionally modify the JSON configuration
4. Click **"Trigger DAG"**

The dashboard will automatically refresh and show the new run.

### Auto-Refresh

The dashboard automatically refreshes every 5 seconds to show real-time updates. You can also manually refresh using the **"Refresh"** button.

## Troubleshooting

### CI/CD Pipeline Issues

#### Pipeline Fails on DAG Validation

**Problem**: DAG syntax errors or import issues

**Solution**:
1. Check the GitHub Actions logs for specific errors
2. Test locally:
   ```powershell
   python -m py_compile dags\medical_etl_dag.py
   ```
3. Fix syntax errors and push again

#### DAG Trigger Fails (HTTP 401)

**Problem**: Authentication failure

**Solution**:
1. Verify GitHub Secrets are set correctly
2. Test credentials manually:
   ```powershell
   curl -X GET http://localhost:8080/api/v2/dags `
     -H "Authorization: Basic $(echo -n 'api_user:password' | base64)"
   ```
3. Recreate the Airflow user if needed

#### Email Notifications Not Sending

**Problem**: Gmail authentication failure

**Solution**:
1. Ensure 2-Step Verification is enabled
2. Use an App Password, not your regular password
3. Check GitHub Secrets for typos
4. Verify `EMAIL_USERNAME` and `EMAIL_PASSWORD` are correct

### Frontend Dashboard Issues

#### Dashboard Shows "Disconnected"

**Problem**: Cannot connect to Airflow API

**Solution**:
1. Verify port-forward is running:
   ```powershell
   kubectl port-forward svc/airflow-api-server 8080:8080 -n airflow
   ```
2. Check Airflow webserver is running:
   ```powershell
   kubectl get pods -n airflow -l component=webserver
   ```
3. Verify credentials are correct

#### CORS Errors in Browser Console

**Problem**: Cross-Origin Request Blocked

**Solution**:
1. Ensure `airflow-values.yaml` has CORS configuration
2. Upgrade Airflow Helm release:
   ```powershell
   helm upgrade airflow apache-airflow/airflow -n airflow --values airflow-values.yaml
   ```
3. Clear browser cache and reload

#### No DAG Runs Displayed

**Problem**: API returns empty results

**Solution**:
1. Verify the DAG exists in Airflow UI
2. Check DAG ID matches in `app.js` (should be `medical_etl_pipeline`)
3. Trigger a manual run to create data
4. Check browser console for API errors

### Kubernetes Deployment Issues

#### Frontend Pods Not Starting

**Problem**: ConfigMap or deployment issues

**Solution**:
1. Check pod status:
   ```powershell
   kubectl get pods -n airflow -l app=medical-etl-frontend
   ```
2. View pod logs:
   ```powershell
   kubectl logs -n airflow -l app=medical-etl-frontend
   ```
3. Verify ConfigMap exists:
   ```powershell
   kubectl get configmap frontend-files -n airflow
   ```
4. Redeploy if needed:
   ```powershell
   .\scripts\deploy-frontend.ps1
   ```

## Advanced Configuration

### Changing Refresh Interval

Edit `frontend/app.js`:
```javascript
const CONFIG = {
    refreshInterval: 10000, // Change to 10 seconds
    // ...
};
```

Redeploy the frontend.

### Customizing Email Templates

Edit `.github/workflows/ci-cd.yml` and modify the email body in the `notify-completion` job.

### Adding More Metrics

Extend the dashboard by:
1. Adding new API calls in `app.js`
2. Creating new UI components in `index.html`
3. Styling with `styles.css`

## Security Best Practices

1. **Never commit credentials** to Git
2. **Use GitHub Secrets** for all sensitive data
3. **Rotate passwords** regularly
4. **Use HTTPS** in production (configure Ingress with TLS)
5. **Limit API user permissions** to only what's needed
6. **Enable audit logging** in Airflow

## Next Steps

- [ ] Set up HTTPS with cert-manager for production
- [ ] Add Slack notifications in addition to email
- [ ] Implement user authentication for dashboard
- [ ] Add more detailed metrics and analytics
- [ ] Create custom alerts based on DAG performance

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review GitHub Actions logs
3. Check Kubernetes pod logs
4. Review Airflow webserver logs

---

**Happy Monitoring! 🚀**
