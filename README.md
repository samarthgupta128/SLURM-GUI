# SLURM-GUI

A modern web-based **Graphical User Interface (GUI)** for the **SLURM Workload Manager**, designed to simplify cluster job management, monitoring, and submission.  
This project provides an intuitive and user-friendly way for researchers, system administrators, and HPC users to interact with SLURM without relying on command-line operations.

---

## 🚀 Features

- **Job Management**
  - Submit, cancel, and view SLURM jobs directly from the GUI.
  - Display live job status and resource usage.
  - Filter and search jobs by user, state, partition, or node.

- **Cluster Monitoring**
  - Visualize node health, partitions, and current workload.
  - Real-time refresh of SLURM queue information.

- **User Dashboard**
  - Personalized job statistics and recent activity.
  - Resource utilization insights (CPU, memory, time, etc.).

- **Interactive Interface**
  - Clean, responsive frontend built with **React + Vite + TailwindCSS + shadcn/ui**.
  - API-based communication with backend SLURM commands.

---

## 🧩 Architecture Overview

```
┌───────────────────────────┐
│         Frontend          │
│ (React, Vite, Tailwind)   │
│      │                    │
│      ▼                    │
│   REST API Requests        │
└────────────┬──────────────┘
             │
             ▼
┌───────────────────────────┐
│         Backend            │
│  (Python / FastAPI / Flask)│
│  Executes SLURM commands   │
│  - squeue, sbatch, srun    │
│  - sinfo, scancel, etc.    │
└────────────┬──────────────┘
             │
             ▼
┌───────────────────────────┐
│       SLURM Cluster       │
│   (Controller + Nodes)    │
└───────────────────────────┘
```

---

## ⚙️ Installation and Setup

### Prerequisites

- **SLURM** installed and configured on the backend system.
- **Python 3.9+** for backend services.
- **Node.js (v18+) & npm** for frontend.
- (Optional) **Docker** for containerized deployment.

---

### 🖥️ Frontend Setup

```bash
# Clone the repository
git clone https://github.com/samarthgupta128/SLURM-GUI.git
cd SLURM-GUI

# Install dependencies
npm install

# Start the development server
npm run dev
```

The GUI will be available at:  
👉 **http://localhost:5173** (or the port displayed in the terminal)

---

### ⚙️ Backend Setup (Python)

Create a backend Python service (e.g., using Flask or FastAPI) that exposes endpoints wrapping SLURM commands:

Example structure:

```bash
backend/
 ├── main.py
 ├── requirements.txt
 └── slurm_utils.py
```

Install dependencies and run:

```bash
cd backend
pip install -r requirements.txt
python main.py
```

---

### 🐳 Docker Deployment (Optional)

You can also run the entire GUI + backend in containers.

```bash
docker-compose up --build
```

Modify the `docker-compose.yml` file to include your backend’s SLURM access configuration.

---

## 🔐 SLURM Integration

The backend should have access to SLURM commands like `squeue`, `sinfo`, `sbatch`, etc.  
Ensure the backend is running **on a node with SLURM client access** (typically the head node or controller).

For remote clusters, use SSH with proper credentials to communicate with SLURM nodes.

---

## 🧠 Future Improvements

- ✅ Job submission templates and presets  
- ✅ Multi-user authentication and roles  
- ⏳ Advanced analytics and usage reports  
- ⏳ Notifications for job completion/failure  
- ⏳ Integration with external schedulers or databases  

---

## 🧑‍💻 Contributing

Contributions are welcome!  
If you’d like to add features or fix bugs:

1. Fork this repo  
2. Create a new branch (`feature/your-feature-name`)  
3. Commit and push your changes  
4. Open a Pull Request

---

## 🧾 License

This project is licensed under the **MIT License** — feel free to modify and distribute it under the same terms.

---

## 📬 Contact

**Author:** [Samarth Gupta](https://github.com/samarthgupta128), Yatin Saini , Shiva Singh , Satyam Kaushik.  
**Project Repository:** [SLURM-GUI](https://github.com/samarthgupta128/SLURM-GUI)  
For questions, suggestions, or collaboration, open an issue or contact via GitHub.

---

> ⚡ *Simplify your SLURM experience — from terminal commands to clean, modern UI.*
