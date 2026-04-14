# 📦 InvenCore — Role-Based Inventory Management System

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.7%2B-blue?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/SQLite-3-lightgrey?style=for-the-badge&logo=sqlite&logoColor=white"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Zero%20Dependencies-✔-success?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Mac%20%7C%20Linux-informational?style=for-the-badge"/>
</p>

<p align="center">
  <b>AI-Powered &nbsp;|&nbsp; Role-Based Access Control &nbsp;|&nbsp; Real-Time Stock Tracking &nbsp;|&nbsp; Single Python File</b>
</p>

---

## 🖥️ Overview

**InvenCore** is a fully-featured, browser-based inventory management system built entirely in a **single Python file** — no frameworks, no pip installs, no setup headaches. Just run it and go.

It is designed for small-to-medium manufacturing or warehouse environments where different staff members (admins, raw material managers, packing supervisors) need controlled access to stock data.

> **All prices use Indian Rupees (₹). The app runs 100% locally on your machine.**

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Role-Based Access Control** | 3 distinct roles with clearly scoped permissions |
| 📊 **Live Dashboard** | Real-time KPIs — total items, low-stock alerts, pending requests |
| 📦 **Inventory Management** | Add, update, and track stock with IN / OUT / Adjust transactions |
| 🚨 **Low-Stock Alerts** | Automatic detection and visual highlighting of critical stock levels |
| 📋 **Material Request Workflow** | Request → Approve / Reject → Fulfill pipeline |
| 🕓 **Transaction History** | Full audit trail of every stock movement |
| 📈 **Reports & Analytics** | Category breakdowns, daily trends, top-moving items |
| 🗂️ **Activity Log** | Complete system audit trail (Admin only) |
| 👥 **User Management** | Create, activate, and deactivate users (Admin only) |
| 🔑 **Secure Sessions** | SHA-256 password hashing + token-based auth (8 hr expiry) |

---

## 🚀 Quick Start

### Requirements

- **Python 3.7 or higher** — [Download here](https://www.python.org/downloads/)
- No additional libraries needed — uses Python standard library only

### Run the App

**Windows — double-click or run in terminal:**
```
run.bat
```
or
```
python inventory_system.py
```

**macOS / Linux:**
```bash
chmod +x run.sh
./run.sh
```
or
```bash
python3 inventory_system.py
```

The app will:
1. ✅ Auto-create and seed the SQLite database
2. ✅ Start a local web server on `http://localhost:8765`
3. ✅ Open your browser automatically

---

## 🔑 Demo Login Credentials

| Role | Username | Password |
|---|---|---|
| 🛡️ Admin | `admin` | `admin123` |
| 🏭 Raw Material Manager | `rawmgr` | `rm123` |
| 📦 Packing Supervisor | `packsup` | `ps123` |

---

## 👥 Role Permissions

### 🛡️ Admin
- Full system access
- Create, activate, and deactivate users
- Approve or reject material requests
- View all reports and activity logs
- Manage all inventory items

### 🏭 Raw Material Manager
- Manage raw material inventory
- Add new items to the system
- Update stock levels (IN / OUT / Adjust)
- Submit material requests
- View transaction history

### 📦 Packing Supervisor
- Manage packing material inventory
- Update packing stock levels
- Submit material requests
- View inventory and transaction history

---

## 🗂️ Project Structure

```
InvenCore/
│
├── inventory_system.py     ← Entire backend + frontend in one file
├── inventory_rbac.db       ← SQLite database (auto-created on first run)
├── README.md               ← You are here
├── run.bat                 ← Windows one-click launcher
├── run.sh                  ← macOS / Linux launcher
├── .gitignore              ← Excludes database and cache files
└── LICENSE                 ← MIT License
```

---

## 🗃️ Database Schema

```
users           — System users with hashed passwords and roles
inventory       — Stock items with quantities, units, pricing, location
categories      — Item categories (Raw Material / Packing / General)
transactions    — All stock IN / OUT / ADJUST movements
material_requests — Request → Approve → Fulfill workflow
activity_log    — Admin-visible full audit trail
sessions        — Secure auth tokens with expiry
```

---

## 🎨 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3 Standard Library (`sqlite3`, `http.server`, `hashlib`, `json`) |
| **Frontend** | Vanilla HTML5 / CSS3 / JavaScript (Single Page App) |
| **Database** | SQLite 3 (embedded, zero config) |
| **Auth** | SHA-256 password hashing + server-side session tokens |
| **UI Fonts** | Sora + JetBrains Mono (via Google Fonts) |

---

## 📊 Pre-loaded Sample Data

On first run, the database is seeded with:

- **14 inventory items** across 6 categories (Raw Materials, Chemicals, Packing Boxes, Packing Films, Labels & Tapes, General Supplies)
- **8 sample transactions** (stock IN / OUT history)
- **4 material requests** (mix of Pending and Approved)
- **3 demo users** covering all 3 roles

---

## ⚙️ Configuration

To change the server port, edit the bottom section of `inventory_system.py`:

```python
PORT = 8765  # Change to any available port
```

---

## 🤝 Contributing

Contributions, issues and feature requests are welcome!

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/YourFeature`
3. Commit your changes: `git commit -m "Add YourFeature"`
4. Push to the branch: `git push origin feature/YourFeature`
5. Open a Pull Request

---

## 📝 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgements

Developed as a project demonstrating Role-Based Access Control (RBAC) in Inventory Management Systems using only Python's standard library — no external dependencies required.

---
<p align="center">Made By Darshan Koli With NewGen Tech</p>
<p align="center">Made with ❤️ in Python</p>
