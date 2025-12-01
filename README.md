# Medical Data ETL Pipeline

A production-grade, cloud-native ETL pipeline for processing FDA drug approvals and clinical trial data using Apache Airflow, Kubernetes, and AWS S3.

## 🎯 Project Objectives

- Demonstrate data engineering best practices in healthcare domain
- Build scalable, containerized data processing workflows
- Implement proper data quality and governance controls
- Create a portfolio-ready project for data engineering roles

## 🚀 Getting Started

For complete setup instructions, including prerequisites, installation, and CI/CD configuration, please refer to [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md).

**Quick Links:**
- [Prerequisites](SETUP_INSTRUCTIONS.md#part-1-prerequisites)
- [Airflow Installation](SETUP_INSTRUCTIONS.md#part-5-airflow-installation-git-sync-method)
- [CI/CD & Dashboard](SETUP_INSTRUCTIONS.md#part-8-cicd-pipeline-and-frontend-dashboard-guide)


## 🏗️ Architecture

```
┌─────────────────┐
│   Data Sources  │
│  - FDA OpenFDA  │
│  - ClinicalTrials│
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Airflow DAG    │◄─────┤  GitHub Actions  │
│  (Orchestrator) │      │  (CI/CD)         │
└────────┬────────┘      └──────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐      ┌──────────────────┐
│   Kubernetes    │      │  Frontend        │
│   Pod Operator  │      │  Dashboard       │
│  (Transform)    │      │  (Monitoring)    │
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│   AWS S3        │
│  (Data Lake)    │
│  Partitioned    │
└─────────────────┘
```

## 📊 Data Sources

### 1. FDA OpenFDA API
- Drug approvals and adverse events
- Public, no authentication required
- Endpoint: `https://api.fda.gov/drug/event.json`

### 2. ClinicalTrials.gov API
- Clinical trial information
- Public access
- Endpoint: `https://clinicaltrials.gov/api/v2/studies`

## 🚀 Features

- **Containerized Processing**: All transformations run in isolated Docker containers
- **Kubernetes Orchestration**: KubernetesPodOperator for scalable execution
- **S3 Data Lake**: Organized with date partitioning (year/month/day)
- **Data Quality Checks**: Built-in validation and error handling
- **Incremental Loading**: Date-based extraction to avoid reprocessing
- **CI/CD Pipeline**: Automated deployment and DAG triggering via GitHub Actions
- **Real-time Monitoring**: Web-based dashboard for DAG runs and task status
- **Email Notifications**: Automatic alerts on deployment and DAG failures
- **API Integration**: RESTful API for programmatic access

## 🛠️ Technology Stack

- **Orchestration**: Apache Airflow 2.7+
- **Container Runtime**: Docker, Kubernetes
- **Cloud Storage**: AWS S3
- **Languages**: Python 3.9+
- **Key Libraries**: pandas, requests, boto3, great_expectations

## 📁 Project Structure

```
medical-etl-pipeline/
├── README.md
├── SETUP_INSTRUCTIONS.md
├── docker/
│   ├── Dockerfile.transform
│   └── requirements.txt
├── dags/
│   ├── medical_etl_dag.py
│   └── config/
│       └── pipeline_config.yaml
├── src/
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── fda_extractor.py
│   │   └── clinicaltrials_extractor.py
│   ├── transformers/
│   │   ├── __init__.py
│   │   ├── drug_transformer.py
│   │   └── data_quality.py
│   ├── loaders/
│   │   ├── __init__.py
│   │   └── s3_loader.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── tests/
│   ├── test_extractors.py
│   ├── test_transformers.py
│   └── test_loaders.py
├── kubernetes/
│   └── pod-template.yaml
├── .env.example
├── requirements.txt
├── scripts/
│   ├── create-airflow-user.ps1
│   └── deploy-frontend.ps1
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── .github/
    └── workflows/
        └── ci-cd.yml

```

## 🎓 Learning Outcomes

This project demonstrates:
- ETL pipeline design and implementation
- Cloud-native architecture patterns
- Container orchestration with Kubernetes
- Healthcare data compliance considerations
- Data quality management
- Infrastructure as Code principles


## 🔐 Data Governance

- All data sources are publicly available
- No PHI (Protected Health Information) processed
- HIPAA considerations documented
- Data retention policies implemented

## 📝 Features Implemented

✅ **Core ETL Pipeline**
- Data extraction from FDA and ClinicalTrials.gov APIs
- Kubernetes-based transformation processing
- S3 data lake with partitioning
- Data quality validation

✅ **CI/CD Pipeline**
- Automated DAG validation and testing
- Automatic deployment on code changes
- DAG triggering via GitHub Actions
- Email notifications

✅ **Monitoring Dashboard**
- Real-time DAG run status
- Task execution visualization
- Error log viewing
- Manual DAG triggering
- Performance statistics


## 🤝 Contributing

This is a portfolio project, but suggestions welcome via issues. Learn, grow, and have fun!

## 📄 License

MIT License - Free for educational and portfolio use

## 📧 Contact

[Amos Jaimes]  
[jaimes.a@northeastern.edu]  
[LinkedIn Profile](https://www.linkedin.com/in/amos-jaimes-a8107621b/)  
[GitHub Profile](https://github.com/amosjames334)

---

**Note**: This project uses public APIs and sample data. For production use with real patient data, additional HIPAA compliance measures would be required.