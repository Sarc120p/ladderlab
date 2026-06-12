# LadderLab — Industrial PLC Simulator & Visual Ladder Editor

> **A software‑only PLC laboratory for learning industrial automation, Ladder Logic and control systems engineering.**

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/fastapi-modern-green.svg)
![WebSockets](https://img.shields.io/badge/realtime-WebSockets-purple.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![PLC](https://img.shields.io/badge/automation-PLC-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**LadderLab** is an industrial automation platform that simulates the internal operation of a real PLC, allowing users to create, execute and visualize Ladder Logic programs through a real‑time web interface.

Built with Python, FastAPI and WebSockets, LadderLab combines a PLC execution engine, visual Ladder editor, industrial process simulations and real‑time monitoring into a single software‑only environment.

**Repository:** [https://github.com/Sarc120p/ladderlab](https://github.com/Sarc120p/ladderlab)

---

## Highlights

- Realistic PLC scan cycle (Read → Execute → Write)
- Visual drag‑and‑drop Ladder editor with free canvas
- Real‑time execution monitoring via WebSockets
- Industrial process simulations (conveyor, tank, traffic light)
- TON / TOF timers and CTU / CTD counters
- Live power flow visualization
- Alarm management and event logging
- PostgreSQL program persistence
- Fully containerized with Docker Compose

---

## Overview
```
Visual Ladder Editor
         │
         ▼
    Ladder Program
         │
         ▼
    PLC Engine
(Read → Execute → Write)
         │
         ▼
 FastAPI + WebSockets
         │
         ▼
 Real-Time Dashboard
         │
         ▼
 Industrial Simulations
```

LadderLab simulates how a real PLC operates internally. Programs are executed through a configurable scan cycle, digital inputs are evaluated, timers and counters are updated, and outputs are written back to the process. The resulting state is streamed live to the browser using WebSockets, allowing users to monitor and debug Ladder Logic programs in real time.



## Why It Matters

Industrial PLCs are the backbone of manufacturing, robotics and process control systems.

LadderLab was built to demonstrate the core concepts behind industrial automation, including:

- PLC scan cycles
- Ladder Logic execution
- Process control
- Industrial communications
- Real‑time monitoring
- Event‑driven architectures

Unlike traditional PLC software, LadderLab runs entirely in software, making it accessible for learning, experimentation and portfolio demonstration.


## Features
```
| Feature | Details |
|----------|----------|
| PLC Scan Cycle | Realistic Read → Execute → Write execution loop |
| Ladder Logic Engine | Supports NO/NC contacts, coils, timers and counters |
| Real‑Time Dashboard | Live tag updates via WebSockets |
| Visual Ladder Editor | Drag‑and‑drop blocks on a free‑canvas with zoom/pan |
| Live Power Flow | Active wires and blocks highlight during execution |
| Industrial Simulations | Conveyor belt, tank process and traffic light |
| Program Persistence | Save, load and manage Ladder programs (PostgreSQL) |
| Alarm Manager | Motor faults, sensor timeouts and custom alarms |
| REST API | Program loading, I/O forcing and diagnostics |
| Docker Support | Entire system runs through Docker Compose |

```

## Project Statistics
```
| Metric | Value |
|--------|-------|
| PLC Instructions | 10+ |
| Simulations | 3 (conveyor, tank, traffic light) |
| Real‑Time Updates | WebSockets |
| Supported Timers | TON, TOF |
| Supported Counters | CTU, CTD |
| Persistence | PostgreSQL |
| API Documentation | Swagger / OpenAPI |
```
---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

### Installation & Running

1. Clone the repository:
   ```bash
   git clone https://github.com/Sarc120p/ladderlab.git
   cd ladderlab
   ```
2. Build and start the containers:
   ```bash
   docker compose up --build
   ```
3. Open your browser at [http://localhost:8000](http://localhost:8000).

The dashboard loads the **Conveyor** simulation by default.

---

## Usage

### Dashboard Controls

| Button   | Behaviour |
|----------|-----------|
| START    | Sends a pulse to the `START_BUTTON` input. Latch circuits keep the motor on. |
| STOP     | Sends a pulse to `STOP_BUTTON`. Pauses the process but preserves the visual state. |
| E‑STOP   | Toggles the emergency stop signal. While active, all outputs are forced off. |
| RESET    | Resets the conveyor visualisation (only works when the motor is stopped). |
| **Ladder Editor** | Opens the full‑screen visual editor. |

### Loading Programs

- **Dropdown + Load** – choose one of the built‑in examples (Conveyor, Tank, Traffic Light).
- **Upload JSON** – load a custom Ladder program from a local file.
- **Save** – store the currently loaded program to the database (with a custom name).
- **Saved** – browse previously saved programs and load or delete them.

### Visual Ladder Editor

1. Click **Ladder Editor** to open the canvas.
2. Drag items from the palette (NO Contact, NC Contact, Coil, TON, CTU) onto the canvas.
3. Click the purple circle on a block to start a connection, then click the circle on another block to wire them together.
4. Move blocks freely; pan with mouse drag, zoom with the mouse wheel.
5. Click **Run on PLC** to send the program to the engine.
6. Close the editor, press START on the dashboard, then reopen the editor to see live power feedback (active blocks and wires light up).

### Conveyor Simulation

<!-- Add GIF here -->
<!-- ![Conveyor Demo](screenshots/conveyor.gif) -->

### Tank Simulation

<!-- Add GIF here -->
<!-- ![Tank Demo](screenshots/tank.gif) -->

### Traffic Light Simulation

<!-- Add GIF here -->
<!-- ![Traffic Light Demo](screenshots/traffic.gif) -->

---

## Ladder Program Format

Programs are stored as JSON. Example structure:

```json
{
  "rungs": [
    {
      "contacts": [
        [
          { "tag": "START_BUTTON", "type": "NO" },
          { "tag": "CONVEYOR_MOTOR", "type": "NO" }
        ],
        { "tag": "STOP_BUTTON", "type": "NC" },
        { "tag": "EMERGENCY_STOP", "type": "NC" }
      ],
      "coil": "CONVEYOR_MOTOR"
    }
  ]
}
```

- Contacts in a top‑level list are wired in **series** (AND).
- A **list inside a list** represents **parallel** contacts (OR).
- `coil`, `timer`, or `counter` define the output of the rung.

---

## API Endpoints

| Method | Endpoint                     | Description |
|--------|------------------------------|-------------|
| GET    | `/`                          | Dashboard HTML |
| GET    | `/api/tags`                  | Snapshot of all tag values |
| GET    | `/api/events`                | Recent alarms & events |
| GET    | `/api/programs`              | List saved programs |
| GET    | `/api/programs/{id}`         | Get a specific program (with content) |
| POST   | `/api/program`               | Load a new program (JSON) |
| POST   | `/api/inputs/{tag}?value=…`  | Force a digital input |
| DELETE | `/api/programs/{id}`         | Delete a saved program |
| WS     | `/ws`                        | WebSocket for real‑time tag updates |

---

## Project Structure

```
ladderlab/
├── engine/                     # PLC Engine (pure Python)
│   ├── __init__.py
│   ├── scan_cycle.py           # Scan cycle loop
│   ├── ladder_executor.py      # Ladder logic evaluator
│   ├── tags.py                 # Tag definitions and memory map
│   ├── timers.py               # TON, TOF
│   ├── counters.py             # CTU, CTD
│   └── alarm_manager.py        # Alarm system
├── backend/                    # FastAPI application
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point, WebSocket endpoint
│   ├── routes.py               # REST API routes
│   ├── schemas.py              # Pydantic models
│   ├── config.py               # Configuration (database URL)
│   ├── database.py             # SQLAlchemy async engine & session
│   ├── event_persistence.py    # Background worker for event logging
│   └── models.py               # ORM models (Program, ExecutionLog)
├── frontend/                   # Static web dashboard
│   ├── index.html              # Main HMI page
│   ├── css/
│   │   └── style.css           # Industrial dark theme
│   └── js/
│       └── dashboard.js        # WebSocket client, I/O panel, editor
├── programs/                   # Ladder programs in JSON
│   ├── example_motor_start.json
│   ├── example_conveyor.json
│   ├── example_tank.json
│   └── example_traffic.json
├── docker/
│   └── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Roadmap

### Core PLC Engine
- [x] Scan cycle implementation
- [x] Digital inputs and outputs
- [x] Internal memory bits
- [x] Ladder execution engine

### Advanced Logic
- [x] TON timers
- [x] TOF timers
- [x] CTU counters
- [x] CTD counters

### Industrial Simulations
- [x] Conveyor belt
- [x] Tank filling process
- [x] Traffic light controller

### Visual Programming
- [x] Drag‑and‑drop Ladder editor
- [x] Zoom and pan support
- [x] Live power flow visualisation
- [ ] Inline tag editing
- [ ] Curved wire routing

### Future
- [ ] Modbus TCP integration
- [ ] OPC UA support
- [ ] Raspberry Pi deployment
- [ ] Multi‑PLC simulation

---

## What This Project Demonstrates

LadderLab showcases concepts commonly found in industrial automation systems:

- PLC scan cycles
- Ladder Logic execution
- Digital I/O processing
- Timers (TON / TOF)
- Counters (CTU / CTD)
- Interlocks and safety logic
- Real‑time process monitoring
- Industrial dashboard development
- FastAPI and WebSocket communication
- Docker‑based deployment

The project was developed as part of a learning path focused on industrial automation, robotics, and Industry 4.0 technologies.

---

## Portfolio Journey

```
FlowDesk       → Business Software
VirtualTank    → SCADA & Modbus TCP
SensorFlow     → Industrial IoT & MQTT
LadderLab      → PLC Logic & Control Systems
RoboFlow       → Robotics (planned)
AI Vision      → Industrial Computer Vision (planned)
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
```
