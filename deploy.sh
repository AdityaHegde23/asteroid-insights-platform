#!/bin/bash

# Asteroid Insights Platform - Deployment Script
# This script deploys the complete infrastructure using Azure Bicep

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Azure CLI is installed
check_azure_cli() {
    if ! command -v az &> /dev/null; then
        print_error "Azure CLI is not installed. Please install it first: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    print_success "Azure CLI is installed"
}

# Check if user is logged in
check_azure_login() {
    if ! az account show &> /dev/null; then
        print_warning "You are not logged in to Azure. Please log in:"
        az login
    fi
    print_success "Logged in to Azure"
}

# Get deployment parameters
get_deployment_params() {
    print_status "Getting deployment parameters..."
    
    # Get current subscription
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)
    SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
    
    print_status "Using subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)"
    
    # Get resource group
    read -p "Enter resource group name (or press Enter for 'asteroid-insights-rg'): " RESOURCE_GROUP
    RESOURCE_GROUP=${RESOURCE_GROUP:-asteroid-insights-rg}
    
    # Get location
    read -p "Enter Azure region (or press Enter for 'East US'): " LOCATION
    LOCATION=${LOCATION:-East US}
    
    # Get environment
    read -p "Enter environment (dev/staging/prod) [default: dev]: " ENVIRONMENT
    ENVIRONMENT=${ENVIRONMENT:-dev}
    
    print_success "Deployment parameters set"
}

# Create resource group
create_resource_group() {
    print_status "Creating resource group: $RESOURCE_GROUP"
    
    if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
        print_warning "Resource group $RESOURCE_GROUP already exists"
    else
        az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
        print_success "Resource group created"
    fi
}

# Deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure using Bicep..."
    
    # Generate unique names for resources
    TIMESTAMP=$(date +%Y%m%d%H%M%S)
    STORAGE_ACCOUNT_NAME="asteroiddata${TIMESTAMP}"
    SQL_SERVER_NAME="asteroid-sql-${ENVIRONMENT}"
    FUNCTION_APP_NAME="asteroid-processor-${ENVIRONMENT}"
    APP_SERVICE_PLAN_NAME="asteroid-plan-${ENVIRONMENT}"
    APP_INSIGHTS_NAME="asteroid-insights-${ENVIRONMENT}"
    KEY_VAULT_NAME="asteroid-kv-${ENVIRONMENT}"
    
    # Generate a secure password for SQL Server
    SQL_ADMIN_PASSWORD=$(openssl rand -base64 32)
    
    # Deploy using Bicep
    DEPLOYMENT_NAME="asteroid-insights-deployment-${TIMESTAMP}"
    
    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DEPLOYMENT_NAME" \
        --template-file "infrastructure/main.bicep" \
        --parameters \
            environment="$ENVIRONMENT" \
            location="$LOCATION" \
            storageAccountName="$STORAGE_ACCOUNT_NAME" \
            sqlServerName="$SQL_SERVER_NAME" \
            functionAppName="$FUNCTION_APP_NAME" \
            appServicePlanName="$APP_SERVICE_PLAN_NAME" \
            appInsightsName="$APP_INSIGHTS_NAME" \
            keyVaultName="$KEY_VAULT_NAME" \
            sqlAdminPassword="$SQL_ADMIN_PASSWORD"
    
    print_success "Infrastructure deployment completed"
    
    # Store the password for later use
    echo "$SQL_ADMIN_PASSWORD" > .sql_password
    chmod 600 .sql_password
}

# Get deployment outputs
get_deployment_outputs() {
    print_status "Getting deployment outputs..."
    
    # Get outputs from the deployment
    OUTPUTS=$(az deployment group show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DEPLOYMENT_NAME" \
        --query properties.outputs \
        --output json)
    
    # Extract values (without sensitive data)
    STORAGE_ACCOUNT_NAME=$(echo "$OUTPUTS" | jq -r '.storageAccountName.value')
    SQL_SERVER_FQDN=$(echo "$OUTPUTS" | jq -r '.sqlServerName.value')
    FUNCTION_APP_URL=$(echo "$OUTPUTS" | jq -r '.functionAppUrl.value')
    APP_INSIGHTS_KEY=$(echo "$OUTPUTS" | jq -r '.appInsightsKey.value')
    
    # Get storage account key separately
    STORAGE_ACCOUNT_KEY=$(az storage account keys list \
        --resource-group "$RESOURCE_GROUP" \
        --account-name "$STORAGE_ACCOUNT_NAME" \
        --query '[0].value' \
        --output tsv)
    
    # Build connection strings
    STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=${STORAGE_ACCOUNT_NAME};AccountKey=${STORAGE_ACCOUNT_KEY};EndpointSuffix=core.windows.net"
    SQL_CONNECTION_STRING="Driver={ODBC Driver 17 for SQL Server};Server=${SQL_SERVER_FQDN};Database=asteroid_insights;Uid=asteroidadmin;Pwd=$(cat .sql_password);"
    
    print_success "Deployment outputs retrieved"
}

# Deploy database schema
deploy_database_schema() {
    print_status "Deploying database schema..."
    
    # Get SQL Server admin password
    SQL_ADMIN_PASSWORD=$(cat .sql_password)
    
    # Deploy schema using sqlcmd (if available) or provide instructions
    if command -v sqlcmd &> /dev/null; then
        print_status "Deploying schema using sqlcmd..."
        sqlcmd -S "$SQL_SERVER_FQDN" -U "asteroidadmin" -P "$SQL_ADMIN_PASSWORD" -i "sql/schema.sql"
        print_success "Database schema deployed"
    else
        print_warning "sqlcmd not found. Please deploy the schema manually:"
        echo "1. Install SQL Server Command Line Utilities"
        echo "2. Run: sqlcmd -S $SQL_SERVER_FQDN -U asteroidadmin -P [password] -i sql/schema.sql"
        echo "3. Or use Azure Data Studio to run the schema.sql file"
        echo "4. Password is stored in .sql_password file"
    fi
}

# Create environment file
create_env_file() {
    print_status "Creating environment file..."
    
    cat > .env << EOF
# Asteroid Insights Platform - Environment Variables
# Generated on $(date)

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION_STRING

# Azure SQL Database
AZURE_SQL_CONNECTION_STRING=$SQL_CONNECTION_STRING

# Azure Function
AZURE_FUNCTION_URL=$FUNCTION_APP_URL

# Application Insights
APPINSIGHTS_INSTRUMENTATIONKEY=$APP_INSIGHTS_KEY

# NASA API (you need to get this from https://api.nasa.gov/)
NASA_API_KEY=your_nasa_api_key_here

# Resource Group
RESOURCE_GROUP=$RESOURCE_GROUP

# Environment
ENVIRONMENT=$ENVIRONMENT
EOF
    
    print_success "Environment file created: .env"
    print_warning "Please update NASA_API_KEY in .env file with your actual API key"
}

# Display deployment summary
show_deployment_summary() {
    print_success "Deployment completed successfully!"
    echo
    echo "=== Deployment Summary ==="
    echo "Resource Group: $RESOURCE_GROUP"
    echo "Environment: $ENVIRONMENT"
    echo "Location: $LOCATION"
    echo
    echo "=== Created Resources ==="
    echo "Storage Account: $STORAGE_ACCOUNT_NAME"
    echo "SQL Server: $SQL_SERVER_NAME"
    echo "Function App: $FUNCTION_APP_NAME"
    echo "App Insights: $APP_INSIGHTS_NAME"
    echo "Key Vault: $KEY_VAULT_NAME"
    echo
    echo "=== Next Steps ==="
    echo "1. Update NASA_API_KEY in .env file"
    echo "2. Deploy database schema (if not done automatically)"
    echo "3. Set up Azure DevOps pipeline variables"
    echo "4. Run the pipeline: az pipelines run --name 'asteroid-insights-pipeline'"
    echo
    echo "=== Connection Strings ==="
    echo "Storage: $STORAGE_CONNECTION_STRING"
    echo "SQL: $SQL_CONNECTION_STRING"
    echo "Function: $FUNCTION_APP_URL"
    echo
    echo "=== Security Notes ==="
    echo "SQL password is stored in .sql_password file (chmod 600)"
    echo "Keep this file secure and do not commit it to version control"
}

# Cleanup function
cleanup() {
    if [ -f .sql_password ]; then
        rm -f .sql_password
    fi
}

# Main deployment function
main() {
    echo "🚀 Asteroid Insights Platform - Deployment Script"
    echo "=================================================="
    echo
    
    # Set up cleanup on exit
    trap cleanup EXIT
    
    # Check prerequisites
    check_azure_cli
    check_azure_login
    
    # Get parameters
    get_deployment_params
    
    # Create resource group
    create_resource_group
    
    # Deploy infrastructure
    deploy_infrastructure
    
    # Get outputs
    get_deployment_outputs
    
    # Deploy database schema
    deploy_database_schema
    
    # Create environment file
    create_env_file
    
    # Show summary
    show_deployment_summary
}

# Run main function
main "$@" 