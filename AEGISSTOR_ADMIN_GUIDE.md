# AEGISSTOR — Administrator Guide

## 1. Responsibilities
Administrators manage system configuration, user accounts & permissions, data source connectors, API keys, and Control Plane approvals.

## 2. Key Workflows
- **Data Sources & Connections**: Register `LINUX_HOST`, `PROMETHEUS`, `CSV_HISTORICAL`, `HTTP_API`, or read-only database metadata connectors (`POSTGRESQL`, `MYSQL`, `MARIADB`, `MSSQL`, `ORACLE`). Use **Test** and **Collect** to verify real connectivity and inspect honest status (`CONNECTED`, `NOT_CONFIGURED`, `DRIVER_MISSING`, `ERROR`).
- **API Keys**: Issue collector API keys (displayed once at creation; stored as SHA-256 hashes) and revoke compromised keys.
- **Users & Roles**: Create/update `ADMIN`, `OPERATOR`, and `VIEWER` accounts and inspect effective permissions.
- **Control Plane & Approvals**: Review high-impact operator requests and approve or reject them with full audit logging.
- **Real-Time Collaboration**: Changes made by Operators (tasks, imports, forecasts, Control Plane requests) appear live on the Administrator's screen via WebSocket events.
