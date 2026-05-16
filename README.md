# Driving Dashboard — Driver Operations Coordination System

Operational dashboard and backend platform for coordinating drivers, routes, shift readiness and dispatch workflows.

The project is designed for real operational environments where drivers, dispatchers and route coordinators need a centralized workflow with status tracking and notifications.

---

## Business Problem

Driver coordination is often fragmented across:

- phone calls
- messengers
- spreadsheets
- manual confirmations
- dispatcher notes

This creates delays, missing statuses and poor visibility over operational readiness.

## Solution

Driving Dashboard centralizes driver status workflows through a backend API and dashboard-oriented architecture.

The platform allows drivers to:

- select assigned routes
- confirm readiness
- send comments and statuses
- synchronize operational information
- support dispatcher approval workflows

## Key Capabilities

- Driver readiness tracking
- Route and vehicle selection
- Dispatcher approval workflow
- Time window control
- Telegram integration
- FastAPI backend
- PostgreSQL-ready architecture
- Operational status dashboard

## Tech Stack

- Python 3.11+
- FastAPI
- PostgreSQL
- Telegram Bot API
- Wialon integration-ready architecture
- Linux VPS deployment

## High-Level Architecture

```text
Driver Mobile App / Telegram
                ↓
           FastAPI Backend
                ↓
            PostgreSQL
                ↓
 Dispatcher Dashboard & Alerts
```

## Planned Features

- Driver status synchronization
- Route assignment workflows
- Operational notifications
- Time window monitoring
- Dispatcher approval panel
- Wialon integration
- GPS and telemetry extensions

## Repository Structure

```text
driving-dashboard/
├── app/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── services/
│   └── main.py
├── docs/
├── scripts/
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

## Security Notes

- Do not commit production credentials
- Driver personal information should be anonymized
- Telegram tokens must be stored in `.env`
- Operational exports should not be public

## Roadmap

- Mobile-friendly dashboard
- Driver mobile application integration
- Real-time notifications
- Wialon-based location support
- Docker Compose deployment
- BI analytics for operational KPIs

## Author

Maksim Anisimov — Python automation, operational dashboards and backend systems.
