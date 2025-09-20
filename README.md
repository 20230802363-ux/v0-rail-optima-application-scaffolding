# RailOptima - AI-Driven Railway Decision Support System

RailOptima is a comprehensive microservices-based application designed to optimize railway operations for Indian Railways section controllers. The system provides real-time decision support through AI-driven optimization, simulation capabilities, and an intuitive dashboard interface.

## 🏗️ Architecture

The application follows a microservices architecture with the following components:

- **Data Service** (Python/FastAPI): Handles data ingestion, storage, and retrieval
- **Optimization Engine** (Python/OR-Tools): Provides AI-driven scheduling optimization
- **Simulator** (Node.js): Enables "what-if" scenario analysis
- **UI Dashboard** (React/TypeScript): Interactive web interface for controllers
- **Infrastructure**: PostgreSQL, RabbitMQ, monitoring stack (Prometheus/Grafana)

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for UI development)
- Python 3.11+ (for service development)
- Git

### Local Development Setup

1. **Clone the repository**
   \`\`\`bash
   git clone <repository-url>
   cd railoptima
   \`\`\`

2. **Set up environment variables**
   \`\`\`bash
   cp .env.example .env
   # Edit .env with your configuration
   \`\`\`

3. **Start all services**
   \`\`\`bash
   docker-compose up -d
   \`\`\`

4. **Verify services are running**
   \`\`\`bash
   # Check service health
   curl http://localhost:8000/  # Data Service
   curl http://localhost:8001/  # Optimization Engine
   curl http://localhost:8002/  # Simulator
   
   # Access UI Dashboard
   open http://localhost:3000
   \`\`\`

5. **Access monitoring dashboards**
   - Grafana: http://localhost:3001 (admin/admin)
   - Prometheus: http://localhost:9090
   - Kibana: http://localhost:5601
   - RabbitMQ Management: http://localhost:15672 (railoptima/password)

## 🧪 Testing

### Run all tests
\`\`\`bash
# Data Service tests
cd data-service && python -m pytest tests/

# Optimization Engine tests
cd opt-engine && python -m pytest tests/

# Simulator tests
cd simulator && npm test

# UI tests
cd ui && npm test
\`\`\`

### Integration tests
\`\`\`bash
# Run end-to-end tests
cd ui && npm run test:e2e
\`\`\`

## 📊 API Documentation

Once services are running, access interactive API documentation:

- Data Service: http://localhost:8000/docs
- Optimization Engine: http://localhost:8001/docs
- Simulator: http://localhost:8002/ (REST endpoints)

## 🔧 Development

### Service Development

Each service can be developed independently:

\`\`\`bash
# Data Service
cd data-service
pip install -r requirements.txt
uvicorn src.app:app --reload --port 8000

# Optimization Engine
cd opt-engine
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8001

# Simulator
cd simulator
npm install
npm run dev

# UI Dashboard
cd ui
npm install
npm start
\`\`\`

### Database Migrations

\`\`\`bash
# Create new migration
cd data-service
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
\`\`\`

## 🚢 Deployment

### Kubernetes Deployment

1. **Build and push images**
   \`\`\`bash
   # This will be automated via GitHub Actions
   docker build -t railoptima/data-service:latest ./data-service
   docker build -t railoptima/opt-engine:latest ./opt-engine
   docker build -t railoptima/simulator:latest ./simulator
   docker build -t railoptima/ui:latest ./ui
   \`\`\`

2. **Deploy to Kubernetes**
   \`\`\`bash
   # Using Helm (recommended)
   helm install railoptima ./infra/helm/railoptima
   
   # Or using kubectl
   kubectl apply -f infra/k8s/
   \`\`\`

### Production Configuration

- Configure persistent volumes for PostgreSQL
- Set up SSL/TLS certificates
- Configure authentication (Auth0 or similar)
- Set up backup strategies
- Configure monitoring alerts

## 📈 Monitoring & Observability

The system includes comprehensive monitoring:

- **Metrics**: Prometheus collects metrics from all services
- **Visualization**: Grafana dashboards for operational insights
- **Logging**: Centralized logging with ELK stack
- **Health Checks**: Built-in health endpoints for all services

## 🔐 Security

- Environment variables for sensitive configuration
- CORS configuration for API security
- Helmet.js for Express.js security headers
- Input validation using Pydantic schemas
- Database connection pooling and prepared statements

## 📚 Documentation

- [Architecture Documentation](docs/architecture.md)
- [API Reference](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Development Guide](docs/development.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation in the `docs/` directory
- Review the API documentation at service endpoints

---

**RailOptima Team** - Optimizing Railway Operations with AI
