# Context Switch Simulator

A Python desktop application for simulating and comparing CPU scheduling
algorithms. It displays process timelines and calculates common scheduling
metrics such as completion time, turnaround time, waiting time, weighted
turnaround time, and CPU utilization.

## Features

- Manual process input and random process generation
- Simulation of:
  - First-Come, First-Served (FCFS)
  - Shortest Job First (SJF)
  - Priority scheduling
  - Preemptive Priority scheduling
  - Round Robin
  - Shortest Remaining Time Next (SRTN)
- Configurable Round Robin time quantum
- Algorithm comparison using the same process set
- Performance tables and graphs

## Requirements

- Python 3.10 or newer
- Tkinter
- `matplotlib` for performance graphs

On Ubuntu/Debian, install Tkinter with:

```bash
sudo apt install python3-tk
```

## Setup

From the project directory, create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install matplotlib
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\activate
```

## Run the application

Linux/macOS:

```bash
PYTHONPATH=src python -m context_switch.main
```

Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m context_switch.main
```

The application opens with three tabs:

1. **Simulation** - add processes manually or generate them randomly, choose
   an algorithm, and run the simulation.
2. **Algorithm Comparison** - compare all six algorithms using the current
   process set.
3. **Performance Graphs** - view metric comparisons graphically.

For manual input, provide a process ID, arrival time, burst time, and priority.
Lower priority numbers represent higher priority. The quantum is used by
Round Robin.

## Manual testing

Run the application and test each scheduling algorithm from the **Simulation**
tab. Add processes manually or use random generation, run the selected
algorithm, and use **View Results** to inspect the timeline and calculated
metrics. The **Algorithm Comparison** and **Performance Graphs** tabs can be
used to compare the same process set across all algorithms.

## Project structure

```text
src/context_switch/
├── domain/       Data models and validation
├── generation/   Random process generation
├── gui/          Tkinter user interface and performance views
├── metrics/      Scheduling metric calculations
├── scheduling/   CPU scheduling algorithms
└── simulation/   Algorithm comparison
```
