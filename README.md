# 📦 InvenCore — Role-Based Inventory Management System

> **AI-Powered | RBAC | Real-Time Tracking | Single Python File**

---

## 🚀 Quick Start

### Requirements
- Python 3.7 or higher (no additional libraries needed — uses only standard library)

### Run the System

**Windows:**
```
Double-click: run.bat
```
**OR**
```
python inventory_system.py
```

**Mac / Linux:**
```bash
python3 inventory_system.py
```

The system will:
1. Initialize the database automatically
2. Open your browser at `http://localhost:8765`

---

## 🔑 Demo Login Credentials

| Role                  | Username  | Password  |
|-----------------------|-----------|-----------|
| 🛡️ Admin             | `admin`   | `admin123`|
| 🏭 Raw Material Mgr  | `rawmgr`  | `rm123`   |
| 📦 Packing Supervisor | `packsup` | `ps123`   |

---

## 👥 Role-Based Access Control (RBAC)

### 🛡️ Admin
- Full system access
- User management (create, activate, deactivate)
- Approve/reject material requests
- View all reports and activity logs
- Add, update, and manage all inventory

### 🏭 Raw Material Manager
- Manage raw material inventory
- Add new items to inventory
- Update stock levels (IN / OUT / Adjust)
- Submit material requests
- View transaction history and reports

### 📦 Packing Supervisor
- Manage packing material inventory
- Update packing stock levels
- Submit material requests
- View inventory and transactions

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **RBAC Security** | 3 roles with clearly defined permissions |
| **Real-Time Inventory** | Live stock tracking with progress indicators |
| **Stock Alerts** | Automatic low-stock detection and highlighting |
| **Material Requests** | Request → Approve → Fulfill workflow |
| **Transaction History** | Full audit trail of all stock movements |
| **Reports & Analytics** | Category breakdown, daily trends, top items |
| **Activity Log** | Complete system audit trail (Admin) |
| **User Management** | Create and manage users (Admin) |
| **Session Auth** | Secure token-based sessions (8hr expiry) |

---

## 🗂️ Project Structure

```
inventory_system.py    ← Single file containing everything
inventory_rbac.db      ← SQLite database (auto-created on first run)
README.md              ← This file
run.bat                ← Windows launcher
run.sh                 ← Mac/Linux launcher
```

---

## 🗃️ Database Schema

| Table | Purpose |
|---|---|
| `users` | System users with roles |
| `inventory` | Stock items |
| `categories` | Item categories |
| `transactions` | All stock movements |
| `material_requests` | Request/approval workflow |
| `activity_log` | Audit trail |
| `sessions` | Auth tokens |

---

## 🎨 Technology Stack

- **Backend:** Python 3 (stdlib only — `sqlite3`, `http.server`, `json`, `hashlib`)
- **Frontend:** Vanilla HTML5 / CSS3 / JavaScript (Single Page App)
- **Database:** SQLite 3
- **Auth:** SHA-256 hashed passwords + secure session tokens
- **UI Font:** Sora + JetBrains Mono (Google Fonts)

---

## 📊 Pre-loaded Sample Data

The system comes with:
- **14 inventory items** across 6 categories
- **8 sample transactions**
- **4 material requests** (pending + approved)
- **3 users** with different roles

---

## 🔧 Configuration

Change the port in the last section of `inventory_system.py`:
```python
PORT = 8765  # Change to any available port
```

---

## 📝 Notes

- Database file `inventory_rbac.db` is created in the same directory
- All prices are in Indian Rupees (₹)
- Sessions expire after 8 hours
- The server runs locally — not exposed to the internet

---

*Developed as an academic project demonstrating Role-Based Access Control in Inventory Management Systems.*
