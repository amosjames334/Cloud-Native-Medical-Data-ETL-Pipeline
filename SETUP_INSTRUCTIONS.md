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

## Part 6: Running the Pipeline

1.  **Trigger DAG**: Go to Airflow UI -> `medical_etl_pipeline` -> Trigger DAG.
2.  **Monitor**: Check logs in UI or use `kubectl logs`.
3.  **Verify Data**: Check S3 bucket for processed files.
