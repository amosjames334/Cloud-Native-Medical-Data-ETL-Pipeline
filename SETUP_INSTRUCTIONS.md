# Setup Instructions - Medical ETL Pipeline

Complete guide to set up and run the Medical Data ETL Pipeline project.

## Prerequisites

### Required Software
- Python 3.9 or higher
- Docker Desktop (20.10+)
- kubectl (1.24+)
- AWS CLI v2
- Git
- Minikube or Docker Desktop with Kubernetes enabled

### Required Accounts
- AWS Account (Free tier sufficient)
- FDA OpenFDA account (optional, for higher rate limits)

### Knowledge Prerequisites
- Basic Python programming
- Understanding of ETL concepts
- Familiarity with Docker
- Basic AWS S3 knowledge

---

## Part 1: Environment Setup

### 1.1 Clone the Repository

```bash
# Create project directory
mkdir medical-etl-pipeline
cd medical-etl-pipeline

# Initialize git
git init
```

### 1.2 Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Mac/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 1.3 Install Python Dependencies

```bash
# Install requirements
pip install -r requirements.txt
```

**requirements.txt contents**:
```
apache-airflow[kubernetes,amazon]==2.7.3
pandas==2.1.3
requests==2.31.0
boto3==1.29.7
great-expectations==0.18.8
pytest==7.4.3
python-dotenv==1.0.0
pyyaml==6.0.1
```

---

## Part 2: AWS Configuration

### 2.1 Create AWS IAM User

1. Log into AWS Console
2. Navigate to IAM → Users → Add User
3. Username: `medical-etl-user`
4. Enable: "Programmatic access"
5. Attach policy: `AmazonS3FullAccess`
6. Save Access Key ID and Secret Access Key

### 2.2 Configure AWS CLI

```bash
aws configure

# Enter when prompted:
AWS Access Key ID: [YOUR_ACCESS_KEY]
AWS Secret Access Key: [YOUR_SECRET_KEY]
Default region: us-east-1
Default output format: json
```

### 2.3 Create S3 Bucket

```bash
# Create bucket (bucket names must be globally unique)
aws s3 mb s3://medical-etl-data-lake-[YOUR-UNIQUE-ID]

# Verify bucket creation
aws s3 ls
```

### 2.4 Create S3 Folder Structure

```bash
# Create partitioned folder structure
aws s3api put-object --bucket medical-etl-data-lake-[YOUR-UNIQUE-ID] --key raw/
aws s3api put-object --bucket medical-etl-data-lake-[YOUR-UNIQUE-ID] --key processed/
aws s3api put-object --bucket medical-etl-data-lake-[YOUR-UNIQUE-ID] --key logs/
```

---

## Part 3: Kubernetes Setup

### 3.1 Start Local Kubernetes Cluster

**Option A: Using Minikube**
```bash
# Start minikube
minikube start --cpus=4 --memory=8192

# Enable metrics
minikube addons enable metrics-server

# Verify
kubectl cluster-info
```

**Option B: Using Docker Desktop**
```bash
# Enable Kubernetes in Docker Desktop settings
# Verify
kubectl get nodes
```

### 3.2 Create Kubernetes Namespace

```bash
# Create namespace for Airflow
kubectl create namespace airflow

# Set as default namespace
kubectl config set-context --current --namespace=airflow
```

### 3.3 Create Kubernetes Secrets

```bash
# Store AWS credentials
kubectl create secret generic aws-credentials \
  --from-literal=aws_access_key_id=[YOUR_ACCESS_KEY] \
  --from-literal=aws_secret_access_key=[YOUR_SECRET_KEY]

# Verify secret
kubectl get secrets
```

---

## Part 4: Docker Setup

### 4.1 Build Transform Container

```bash
# Navigate to docker directory
cd docker

# Build image
docker build -f Dockerfile.transform -t medical-etl-transform:v1 .

# Verify image
docker images | grep medical-etl
```

### 4.2 Test Container Locally

```bash
# Run test transformation
docker run --rm \
  -e AWS_ACCESS_KEY_ID=[YOUR_KEY] \
  -e AWS_SECRET_ACCESS_KEY=[YOUR_SECRET] \
  -e S3_BUCKET=medical-etl-data-lake-[YOUR-ID] \
  medical-etl-transform:v1 \
  python -m src.transformers.drug_transformer --date 2024-01-01
```

### 4.3 Push to Container Registry (Optional)

```bash
# Tag for Docker Hub
docker tag medical-etl-transform:v1 [YOUR_DOCKERHUB_USERNAME]/medical-etl-transform:v1

# Login and push
docker login
docker push [YOUR_DOCKERHUB_USERNAME]/medical-etl-transform:v1
```

---

## Part 5: Airflow Installation

### 5.1 Install Airflow with Helm

```bash
# Add Airflow Helm repository
helm repo add apache-airflow https://airflow.apache.org
helm repo update

# Create values.yaml for configuration
cat > airflow-values.yaml <<EOF
executor: KubernetesExecutor
dags:
  gitSync:
    enabled: false
env:
  - name: AIRFLOW__CORE__LOAD_EXAMPLES
    value: "False"
  - name: AWS_DEFAULT_REGION
    value: "us-east-1"
EOF

# Install Airflow
helm install airflow apache-airflow/airflow \
  --namespace airflow \
  -f airflow-values.yaml \
  --timeout 10m
```

### 5.2 Access Airflow UI

```bash
# Port forward to access UI
kubectl port-forward svc/airflow-webserver 8080:8080 -n airflow

# Get admin password
kubectl get secret airflow-webserver-secret -n airflow -o jsonpath="{.data.webserver-secret-key}" | base64 -d

# Access at: http://localhost:8080
# Username: admin
# Password: admin (default, change in production)
```

---

## Part 6: Deploy DAGs

### 6.1 Create Environment Variables

```bash
# Create .env file in project root
cat > .env <<EOF
AWS_ACCESS_KEY_ID=[YOUR_ACCESS_KEY]
AWS_SECRET_ACCESS_KEY=[YOUR_SECRET_KEY]
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET=medical-etl-data-lake-[YOUR-UNIQUE-ID]
FDA_API_KEY=  # Optional
DOCKER_IMAGE=medical-etl-transform:v1
EOF
```

### 6.2 Copy DAGs to Airflow

```bash
# Copy DAGs to Airflow pod
kubectl cp dags/medical_etl_dag.py \
  airflow-scheduler-0:/opt/airflow/dags/ \
  -n airflow

# Copy config
kubectl cp dags/config/pipeline_config.yaml \
  airflow-scheduler-0:/opt/airflow/dags/config/ \
  -n airflow

# Verify
kubectl exec -it airflow-scheduler-0 -n airflow -- ls /opt/airflow/dags
```

---

## Part 7: Run the Pipeline

### 7.1 Enable DAG in Airflow UI

1. Navigate to http://localhost:8080
2. Login with admin credentials
3. Find `medical_etl_pipeline` DAG
4. Toggle the switch to enable it
5. Click "Trigger DAG" to run manually

### 7.2 Monitor Execution

```bash
# Watch pods
kubectl get pods -n airflow -w

# Check logs
kubectl logs -f [POD_NAME] -n airflow

# Airflow logs
kubectl exec -it airflow-scheduler-0 -n airflow -- \
  airflow tasks logs medical_etl_pipeline extract_fda_data 2024-01-01
```

### 7.3 Verify Data in S3

```bash
# List processed files
aws s3 ls s3://medical-etl-data-lake-[YOUR-ID]/processed/ --recursive

# Download sample file
aws s3 cp s3://medical-etl-data-lake-[YOUR-ID]/processed/year=2024/month=01/day=01/drugs.parquet ./

# View with Python
python -c "import pandas as pd; print(pd.read_parquet('drugs.parquet').head())"
```

---

## Part 8: Testing

### 8.1 Run Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_extractors.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### 8.2 Validate Data Quality

```bash
# Run data quality checks
python -m src.transformers.data_quality \
  --bucket medical-etl-data-lake-[YOUR-ID] \
  --date 2024-01-01
```

---

## Part 9: Troubleshooting

### Common Issues

**Issue**: Pod fails with ImagePullBackOff
```bash
# Solution: Load image into Minikube
minikube image load medical-etl-transform:v1
```

**Issue**: AWS credentials not found
```bash
# Solution: Recreate secret
kubectl delete secret aws-credentials -n airflow
kubectl create secret generic aws-credentials \
  --from-literal=aws_access_key_id=[YOUR_KEY] \
  --from-literal=aws_secret_access_key=[YOUR_SECRET] \
  -n airflow
```

**Issue**: DAG not appearing in Airflow UI
```bash
# Solution: Restart scheduler
kubectl rollout restart deployment/airflow-scheduler -n airflow
```

**Issue**: API rate limit exceeded
```bash
# Solution: Add delays between requests or get FDA API key
# Register at: https://open.fda.gov/apis/authentication/
```

---

## Part 10: Project Extensions

### 10.1 Add Data Visualization

```bash
# Install Superset
pip install apache-superset

# Initialize database
superset db upgrade
superset init

# Create admin user
superset fab create-admin

# Run Superset
superset run -h 0.0.0.0 -p 8088
```

### 10.2 Implement CI/CD

Create `.github/workflows/ci.yml`:
```yaml
name: CI Pipeline
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: pytest tests/
      - name: Build Docker image
        run: docker build -f docker/Dockerfile.transform -t medical-etl-transform:latest .
```

### 10.3 Add Monitoring

```bash
# Install Prometheus
helm install prometheus prometheus-community/prometheus -n monitoring

# Install Grafana
helm install grafana grafana/grafana -n monitoring

# Access Grafana
kubectl port-forward svc/grafana 3000:80 -n monitoring
```

---

## Part 11: Cleanup

### To Stop Without Deleting

```bash
# Stop Minikube
minikube stop

# Or stop Airflow
helm uninstall airflow -n airflow
```

### To Fully Remove

```bash
# Delete Kubernetes resources
kubectl delete namespace airflow

# Delete Minikube cluster
minikube delete

# Delete S3 bucket (careful!)
aws s3 rb s3://medical-etl-data-lake-[YOUR-ID] --force

# Delete IAM user (via AWS Console)
```

---

## Additional Resources

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [FDA OpenFDA API](https://open.fda.gov/apis/)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [Great Expectations](https://docs.greatexpectations.io/)

---

## Getting Help

If you encounter issues:
1. Check logs: `kubectl logs [POD_NAME] -n airflow`
2. Review Airflow UI error messages
3. Verify AWS credentials: `aws s3 ls`
4. Test API endpoints: `curl https://api.fda.gov/drug/event.json?limit=1`

---

## Timeline Estimate

- **Setup (Parts 1-5)**: 3-4 hours
- **Implementation (Parts 6-7)**: 2-3 hours
- **Testing (Part 8)**: 1-2 hours
- **Documentation**: 1-2 hours

**Total**: 7-11 hours for complete implementation
