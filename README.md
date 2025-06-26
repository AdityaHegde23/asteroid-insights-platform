# Asteroid Insights Platform

A comprehensive Azure cloud-based data processing pipeline that fetches asteroid data from NASA's API, processes it through ETL pipelines, and stores insights in Azure SQL Database.

## 🎯 Project Overview

This is a learning project designed to understand Azure cloud services through building a real-world asteroid data processing pipeline. The goal is to create a comprehensive Azure DevOps pipeline that can be completed in a few hours and showcased on a resume.

### Key Features
- **NASA API Integration**: Fetches real asteroid data from NASA's Near Earth Object API
- **Azure Blob Storage**: Stores raw NASA API responses for audit and backup
- **Azure SQL Database**: Stores structured raw data and processed insights
- **Azure Functions**: Serverless ETL processing with automatic scaling
- **Infrastructure as Code**: Complete Azure Bicep templates for reproducible deployments
- **Azure DevOps Pipeline**: Automated CI/CD with multiple environments
- **Monitoring & Logging**: Application Insights integration

## 🏗️ Architecture

```
NASA API → Azure Blob Storage (Raw JSON) → ETL Processing → Azure SQL Database (Insights)
                ↓
        Azure Functions (Serverless)
                ↓
        Application Insights (Monitoring)
```

### Data Flow
1. **Raw Data**: NASA API responses stored as JSON files in Blob Storage
2. **Structured Data**: Raw asteroid data stored in SQL Database with proper schema
3. **Processed Insights**: Calculated risk scores, orbital insights, and threat assessments
4. **Monitoring**: Application Insights tracks performance and errors

## 🚀 Quick Start

### Prerequisites
- Azure CLI installed and logged in
- Azure subscription with appropriate permissions
- NASA API key (free from https://api.nasa.gov/)

### 1. Deploy Infrastructure
```bash
# Run the deployment script
./deploy.sh
```

This will:
- Create Azure Resource Group
- Deploy all Azure resources using Bicep
- Set up database schema
- Create environment file with connection strings

### 2. Configure Environment
```bash
# Update the generated .env file with your NASA API key
nano .env
```

### 3. Run the Pipeline
```bash
# Deploy to Azure DevOps
az pipelines run --name 'asteroid-insights-pipeline'
```

## 📁 Project Structure

```
astroid-insights-platform/
├── infrastructure/
│   ├── main.bicep              # Main Azure Bicep template
│   └── parameters.json         # Deployment parameters
├── src/
│   ├── asteroid_processor.py   # Main ETL processor
│   ├── nasa_api_client.py      # NASA API client
│   └── utils.py                # Utility functions
├── sql/
│   └── schema.sql              # Database schema
├── tests/
│   └── test_asteroid_processor.py
├── azure-pipelines.yml         # Azure DevOps pipeline
├── requirements.txt            # Python dependencies
├── deploy.sh                   # Infrastructure deployment script
└── README.md
```

## 🏛️ Infrastructure Components

### Azure Resources Created
- **Storage Account**: Blob storage for raw NASA API responses
- **SQL Database**: Structured data storage with two tables
- **Function App**: Serverless ETL processing
- **Application Insights**: Monitoring and logging
- **Key Vault**: Secure secret management
- **App Service Plan**: Hosting for Function App

### Database Schema
- **raw_asteroid_data**: Stores structured NASA API data
- **processed_asteroid_insights**: Stores calculated insights and risk assessments

## 🔧 Configuration

### Environment Variables
```bash
# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=

# Azure SQL Database
AZURE_SQL_CONNECTION_STRING=

# Azure Function
AZURE_FUNCTION_URL=

# Application Insights
APPINSIGHTS_INSTRUMENTATIONKEY=

# NASA API
NASA_API_KEY=your_api_key_here
```

### Pipeline Variables
Set these in Azure DevOps:
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_SQL_CONNECTION_STRING`
- `NASA_API_KEY`
- `RESOURCE_GROUP`
- `ENVIRONMENT`

## 📊 Data Processing

### Raw Data Storage (Blob Storage)
- **Container**: `asteroid-raw`
- **Format**: JSON files with NASA API responses
- **Naming**: `asteroid_data_YYYYMMDD_HHMMSS.json`

### Structured Data (SQL Database)
- **Table**: `raw_asteroid_data`
- **Content**: Parsed NASA API data with proper data types
- **Indexes**: Optimized for querying by date, risk level, and size

### Processed Insights (SQL Database)
- **Table**: `processed_asteroid_insights`
- **Content**: Calculated risk scores, orbital insights, threat assessments
- **Features**: Risk scoring, hazard classification, orbital analysis

## 🔄 Pipeline Stages

### 1. Build Stage
- Python code compilation
- Unit tests execution
- Code quality checks

### 2. Deploy Infrastructure Stage
- Azure Bicep deployment
- Resource creation and configuration
- Database schema deployment

### 3. Deploy Application Stage
- Function App deployment
- Environment configuration
- Application Insights setup

### 4. Data Processing Stage
- NASA API data fetching
- ETL processing
- Data storage and insights generation

### 5. Validation Stage
- Data quality checks
- Performance validation
- Integration tests

### 6. Notification Stage
- Success/failure notifications
- Deployment summaries
- Monitoring alerts

## 🧪 Testing

### Unit Tests
```bash
# Run unit tests
python -m pytest tests/
```

### Integration Tests
```bash
# Run with test environment
python src/asteroid_processor.py --mode manual-validation
```

## 📈 Monitoring

### Application Insights
- Performance monitoring
- Error tracking
- Custom metrics
- Dependency tracking

### Key Metrics
- API response times
- Processing duration
- Error rates
- Data quality scores

## 🔒 Security

### Authentication
- Azure Managed Identity for Function App
- Key Vault for secret management
- RBAC for resource access

### Data Protection
- Encrypted storage at rest
- TLS 1.2 for data in transit
- Private endpoints (configurable)

## 🚀 Deployment Options

### Manual Deployment
```bash
# Deploy infrastructure
./deploy.sh

# Run processor manually
python src/asteroid_processor.py --mode manual-full
```

### Automated Pipeline
- Triggered on code changes
- Manual triggers available
- Environment-specific deployments

## 📝 API Documentation

### NASA API Integration
- **Endpoint**: https://api.nasa.gov/neo/rest/v1/feed
- **Rate Limit**: 1000 requests per hour
- **Data**: Near Earth Objects with orbital parameters

### Function App Endpoints
- **Process Asteroids**: `/api/process-asteroids`
- **Health Check**: `/api/health`

## 🛠️ Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AZURE_STORAGE_CONNECTION_STRING="your_connection_string"
export AZURE_SQL_CONNECTION_STRING="your_sql_connection_string"

# Run locally
python src/asteroid_processor.py --mode manual-incremental
```

### Code Quality
- Type hints throughout
- Comprehensive error handling
- Logging and monitoring
- Unit test coverage

## 📚 Learning Objectives

This project demonstrates:
- **Azure DevOps**: CI/CD pipeline automation
- **Infrastructure as Code**: Bicep templates
- **Cloud Services**: Storage, Database, Functions
- **Data Processing**: ETL pipelines and analytics
- **Monitoring**: Application Insights and logging
- **Security**: Managed identities and Key Vault

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is for educational purposes. NASA API data is subject to NASA's terms of service.

## 🆘 Troubleshooting

### Common Issues
1. **Container not found**: Run `./deploy.sh` to create infrastructure
2. **SQL connection failed**: Check firewall rules and connection string
3. **API rate limit**: NASA API has 1000 requests/hour limit
4. **Function timeout**: Increase timeout in Function App configuration

### Support
- Check Application Insights for detailed error logs
- Review Azure Monitor for resource metrics
- Consult Azure documentation for service-specific issues

---

**Note**: This is a learning project designed to demonstrate Azure cloud services and DevOps practices. For production use, additional security, monitoring, and compliance measures should be implemented. 