#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        ROLE-BASED INVENTORY MANAGEMENT SYSTEM                    ║
║        AI-Powered | RBAC | Real-Time Tracking                    ║
║        Single File Application — Python 3.x                      ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import hashlib
import json
import os
import sys
import threading
import webbrowser
import datetime
import random
import string
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from typing import Optional

# ─────────────────────────────────────────────
#  DATABASE LAYER
# ─────────────────────────────────────────────
DB_FILE = "inventory_rbac.db"

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('Admin','Raw Material Manager','Packing Supervisor')),
        full_name TEXT NOT NULL,
        email TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        last_login TEXT
    );

    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('Raw Material','Packing Material','General')),
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_code TEXT UNIQUE NOT NULL,
        item_name TEXT NOT NULL,
        category_id INTEGER REFERENCES categories(id),
        quantity REAL NOT NULL DEFAULT 0,
        unit TEXT NOT NULL DEFAULT 'units',
        min_stock REAL NOT NULL DEFAULT 10,
        max_stock REAL DEFAULT 1000,
        unit_price REAL DEFAULT 0,
        location TEXT,
        supplier TEXT,
        description TEXT,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER REFERENCES inventory(id),
        transaction_type TEXT NOT NULL CHECK(transaction_type IN ('IN','OUT','ADJUST','REQUEST','TRANSFER')),
        quantity REAL NOT NULL,
        previous_qty REAL,
        new_qty REAL,
        reason TEXT,
        performed_by INTEGER REFERENCES users(id),
        approved_by INTEGER REFERENCES users(id),
        status TEXT DEFAULT 'COMPLETED' CHECK(status IN ('COMPLETED','PENDING','APPROVED','REJECTED')),
        reference_no TEXT,
        transaction_date TEXT DEFAULT (datetime('now')),
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS material_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_no TEXT UNIQUE NOT NULL,
        item_id INTEGER REFERENCES inventory(id),
        requested_qty REAL NOT NULL,
        purpose TEXT,
        urgency TEXT DEFAULT 'Normal' CHECK(urgency IN ('Low','Normal','High','Critical')),
        requested_by INTEGER REFERENCES users(id),
        approved_by INTEGER REFERENCES users(id),
        status TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING','APPROVED','REJECTED','FULFILLED')),
        request_date TEXT DEFAULT (datetime('now')),
        approval_date TEXT,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        action TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        timestamp TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        created_at TEXT DEFAULT (datetime('now')),
        expires_at TEXT
    );
    """)
    conn.commit()

    # Seed default admin
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username,password_hash,role,full_name,email) VALUES (?,?,?,?,?)",
              ("admin", admin_hash, "Admin", "System Administrator", "admin@inventory.com"))

    # Seed Raw Material Manager
    rm_hash = hashlib.sha256("rm123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username,password_hash,role,full_name,email) VALUES (?,?,?,?,?)",
              ("rawmgr", rm_hash, "Raw Material Manager", "Ravi Kumar", "ravi@inventory.com"))

    # Seed Packing Supervisor
    ps_hash = hashlib.sha256("ps123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (username,password_hash,role,full_name,email) VALUES (?,?,?,?,?)",
              ("packsup", ps_hash, "Packing Supervisor", "Priya Sharma", "priya@inventory.com"))

    # Seed categories
    cats = [
        ("Raw Materials", "Raw Material", "Base raw materials for production"),
        ("Chemicals", "Raw Material", "Chemical compounds and solvents"),
        ("Packing Boxes", "Packing Material", "Cardboard and corrugated boxes"),
        ("Packing Films", "Packing Material", "Stretch and shrink films"),
        ("Labels & Tapes", "Packing Material", "Labels, tapes and stickers"),
        ("General Supplies", "General", "General office and factory supplies"),
    ]
    for cat in cats:
        c.execute("INSERT OR IGNORE INTO categories (name,type,description) VALUES (?,?,?)", cat)

    conn.commit()

    # Seed inventory items
    items = [
        ("RM-001","Wheat Flour",1,850,"kg",100,2000,45.00,"Warehouse A","ABC Suppliers"),
        ("RM-002","Sugar",1,420,"kg",50,1000,38.50,"Warehouse A","XYZ Traders"),
        ("RM-003","Edible Oil",2,310,"liters",30,500,120.00,"Tank Room","PQR Industries"),
        ("RM-004","Salt",1,680,"kg",50,1000,12.00,"Warehouse B","ABC Suppliers"),
        ("RM-005","Corn Starch",2,175,"kg",20,400,55.00,"Warehouse B","RST Corp"),
        ("PM-001","Cardboard Boxes 20x20",3,1200,"pcs",200,5000,8.50,"Packing Store","Box World"),
        ("PM-002","Cardboard Boxes 30x30",3,560,"pcs",100,3000,14.00,"Packing Store","Box World"),
        ("PM-003","Stretch Film Roll",4,45,"rolls",10,100,380.00,"Packing Store","Film Co"),
        ("PM-004","Shrink Wrap",4,32,"rolls",8,80,450.00,"Packing Store","Film Co"),
        ("PM-005","Product Labels A4",5,8500,"sheets",1000,20000,2.50,"Label Store","Print Pro"),
        ("PM-006","Brown Tape 2-inch",5,280,"rolls",50,500,25.00,"Label Store","Tape Inc"),
        ("PM-007","Bubble Wrap 50m",4,18,"rolls",5,50,650.00,"Packing Store","Film Co"),
        ("GS-001","Safety Gloves",6,120,"pairs",20,300,35.00,"Safety Store","Safety Hub"),
        ("GS-002","Dust Masks",6,350,"pcs",50,1000,8.00,"Safety Store","Safety Hub"),
    ]
    for itm in items:
        c.execute("""INSERT OR IGNORE INTO inventory 
                     (item_code,item_name,category_id,quantity,unit,min_stock,max_stock,unit_price,location,supplier,created_by)
                     VALUES (?,?,?,?,?,?,?,?,?,?,1)""", itm)

    conn.commit()

    # Seed some transactions
    c.execute("SELECT id FROM inventory")
    inv_ids = [r[0] for r in c.fetchall()]
    types = ["IN", "OUT", "IN", "OUT", "IN"]
    for i, iid in enumerate(inv_ids[:8]):
        qty = random.randint(10, 100)
        prev = random.randint(300, 900)
        new = prev + qty if types[i % 5] == "IN" else max(0, prev - qty)
        ref = "REF-" + "".join(random.choices(string.digits, k=6))
        uid = random.choice([1, 2, 3])
        c.execute("""INSERT OR IGNORE INTO transactions 
                     (item_id,transaction_type,quantity,previous_qty,new_qty,reason,performed_by,status,reference_no)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (iid, types[i % 5], qty, prev, new, "Regular stock update", uid, "COMPLETED", ref))

    conn.commit()

    # Seed material requests
    req_data = [
        ("REQ-000001", 6, 500, "Production line packing", "High", 2, None, "PENDING"),
        ("REQ-000002", 1, 200, "Weekly raw material top-up", "Normal", 2, 1, "APPROVED"),
        ("REQ-000003", 3, 100, "Emergency restock", "Critical", 3, 1, "APPROVED"),
        ("REQ-000004", 8, 20, "Monthly packing order", "Normal", 3, None, "PENDING"),
    ]
    for r in req_data:
        c.execute("""INSERT OR IGNORE INTO material_requests 
                     (request_no,item_id,requested_qty,purpose,urgency,requested_by,approved_by,status)
                     VALUES (?,?,?,?,?,?,?,?)""", r)

    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
#  AUTH HELPERS
# ─────────────────────────────────────────────
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def generate_token() -> str:
    return hashlib.sha256(os.urandom(32)).hexdigest()

def create_session(user_id: int) -> str:
    token = generate_token()
    expires = (datetime.datetime.now() + datetime.timedelta(hours=8)).isoformat()
    conn = get_db()
    conn.execute("INSERT INTO sessions (token,user_id,expires_at) VALUES (?,?,?)", (token, user_id, expires))
    conn.execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return token

def validate_session(token: str) -> Optional[dict]:
    if not token:
        return None
    conn = get_db()
    row = conn.execute("""
        SELECT u.id,u.username,u.role,u.full_name,u.email,s.expires_at
        FROM sessions s JOIN users u ON s.user_id=u.id
        WHERE s.token=? AND u.is_active=1
    """, (token,)).fetchone()
    conn.close()
    if not row:
        return None
    if datetime.datetime.fromisoformat(row["expires_at"]) < datetime.datetime.now():
        return None
    return dict(row)

def log_activity(user_id: int, action: str, details: str = ""):
    conn = get_db()
    conn.execute("INSERT INTO activity_log (user_id,action,details) VALUES (?,?,?)", (user_id, action, details))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
#  API HANDLERS
# ─────────────────────────────────────────────
def api_login(data: dict) -> dict:
    username = data.get("username", "").strip()
    password = data.get("password", "")
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND password_hash=? AND is_active=1",
        (username, hash_password(password))
    ).fetchone()
    conn.close()
    if not user:
        return {"success": False, "message": "Invalid credentials"}
    token = create_session(user["id"])
    log_activity(user["id"], "LOGIN", f"User {username} logged in")
    return {"success": True, "token": token, "user": {
        "id": user["id"], "username": user["username"],
        "role": user["role"], "full_name": user["full_name"], "email": user["email"]
    }}

def api_logout(token: str) -> dict:
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()
    return {"success": True}

def api_get_dashboard(user: dict) -> dict:
    conn = get_db()
    total_items = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    low_stock = conn.execute("SELECT COUNT(*) FROM inventory WHERE quantity<=min_stock").fetchone()[0]
    total_value = conn.execute("SELECT SUM(quantity*unit_price) FROM inventory").fetchone()[0] or 0
    pending_req = conn.execute("SELECT COUNT(*) FROM material_requests WHERE status='PENDING'").fetchone()[0]
    today_tx = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE DATE(transaction_date)=DATE('now')"
    ).fetchone()[0]
    recent_tx = conn.execute("""
        SELECT t.id, i.item_name, t.transaction_type, t.quantity, i.unit,
               u.full_name, t.transaction_date, t.status
        FROM transactions t
        JOIN inventory i ON t.item_id=i.id
        JOIN users u ON t.performed_by=u.id
        ORDER BY t.id DESC LIMIT 8
    """).fetchall()
    low_items = conn.execute("""
        SELECT item_code, item_name, quantity, min_stock, unit, supplier
        FROM inventory WHERE quantity<=min_stock ORDER BY (quantity/min_stock) ASC LIMIT 8
    """).fetchall()
    conn.close()
    return {
        "stats": {
            "total_items": total_items,
            "low_stock": low_stock,
            "total_value": round(total_value, 2),
            "pending_requests": pending_req,
            "today_transactions": today_tx
        },
        "recent_transactions": [dict(r) for r in recent_tx],
        "low_stock_items": [dict(r) for r in low_items]
    }

def api_get_inventory(user: dict, filters: dict = {}) -> dict:
    conn = get_db()
    q = """SELECT i.id, i.item_code, i.item_name, c.name as category, c.type as cat_type,
                  i.quantity, i.unit, i.min_stock, i.max_stock, i.unit_price,
                  i.location, i.supplier, i.description, i.updated_at,
                  CASE WHEN i.quantity<=i.min_stock THEN 'Low' 
                       WHEN i.quantity>=i.max_stock*0.9 THEN 'High' 
                       ELSE 'Normal' END as stock_status
           FROM inventory i LEFT JOIN categories c ON i.category_id=c.id
           WHERE 1=1"""
    params = []
    if filters.get("search"):
        q += " AND (i.item_name LIKE ? OR i.item_code LIKE ? OR c.name LIKE ?)"
        s = f"%{filters['search']}%"
        params += [s, s, s]
    if filters.get("category_type") and filters["category_type"] != "All":
        q += " AND c.type=?"
        params.append(filters["category_type"])
    if filters.get("stock_status") == "Low":
        q += " AND i.quantity<=i.min_stock"
    q += " ORDER BY i.item_code"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return {"items": [dict(r) for r in rows]}

def api_add_inventory(user: dict, data: dict) -> dict:
    role = user["role"]
    if role not in ("Admin", "Raw Material Manager", "Packing Supervisor"):
        return {"success": False, "message": "Access denied"}
    required = ["item_code", "item_name", "category_id", "quantity", "unit"]
    for f in required:
        if not data.get(f):
            return {"success": False, "message": f"Field '{f}' is required"}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO inventory 
            (item_code,item_name,category_id,quantity,unit,min_stock,max_stock,unit_price,location,supplier,description,created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data["item_code"], data["item_name"], data["category_id"],
             float(data["quantity"]), data["unit"],
             float(data.get("min_stock", 10)), float(data.get("max_stock", 1000)),
             float(data.get("unit_price", 0)), data.get("location", ""),
             data.get("supplier", ""), data.get("description", ""), user["id"]))
        conn.commit()
        log_activity(user["id"], "ADD_ITEM", f"Added item {data['item_code']} - {data['item_name']}")
        return {"success": True, "message": "Item added successfully"}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "Item code already exists"}
    finally:
        conn.close()

def api_update_stock(user: dict, data: dict) -> dict:
    item_id = data.get("item_id")
    qty_change = float(data.get("quantity", 0))
    tx_type = data.get("transaction_type", "IN")
    reason = data.get("reason", "")
    conn = get_db()
    item = conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone()
    if not item:
        conn.close()
        return {"success": False, "message": "Item not found"}
    prev_qty = item["quantity"]
    new_qty = prev_qty + qty_change if tx_type == "IN" else max(0, prev_qty - qty_change)
    if tx_type == "ADJUST":
        new_qty = qty_change
    conn.execute("UPDATE inventory SET quantity=?, updated_at=datetime('now') WHERE id=?", (new_qty, item_id))
    ref = "REF-" + "".join(random.choices(string.digits, k=6))
    conn.execute("""INSERT INTO transactions 
        (item_id,transaction_type,quantity,previous_qty,new_qty,reason,performed_by,status,reference_no)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (item_id, tx_type, qty_change, prev_qty, new_qty, reason, user["id"], "COMPLETED", ref))
    conn.commit()
    conn.close()
    log_activity(user["id"], "STOCK_UPDATE", f"Item {item['item_code']}: {prev_qty} → {new_qty}")
    return {"success": True, "message": "Stock updated", "new_quantity": new_qty, "reference": ref}

def api_get_transactions(user: dict, filters: dict = {}) -> dict:
    conn = get_db()
    q = """SELECT t.id, i.item_code, i.item_name, i.unit, t.transaction_type,
                  t.quantity, t.previous_qty, t.new_qty, t.reason,
                  u.full_name as performed_by, t.status, t.reference_no, t.transaction_date
           FROM transactions t
           JOIN inventory i ON t.item_id=i.id
           JOIN users u ON t.performed_by=u.id
           WHERE 1=1"""
    params = []
    if filters.get("tx_type") and filters["tx_type"] != "All":
        q += " AND t.transaction_type=?"
        params.append(filters["tx_type"])
    q += " ORDER BY t.id DESC LIMIT 200"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return {"transactions": [dict(r) for r in rows]}

def api_get_requests(user: dict) -> dict:
    conn = get_db()
    q = """SELECT r.id, r.request_no, i.item_code, i.item_name, i.unit,
                  r.requested_qty, r.purpose, r.urgency, r.status,
                  u.full_name as requested_by, r.request_date,
                  a.full_name as approved_by_name, r.notes
           FROM material_requests r
           JOIN inventory i ON r.item_id=i.id
           JOIN users u ON r.requested_by=u.id
           LEFT JOIN users a ON r.approved_by=a.id
           ORDER BY r.id DESC"""
    rows = conn.execute(q).fetchall()
    conn.close()
    return {"requests": [dict(r) for r in rows]}

def api_create_request(user: dict, data: dict) -> dict:
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM material_requests").fetchone()[0] + 1
    req_no = f"REQ-{count:06d}"
    conn.execute("""INSERT INTO material_requests 
        (request_no,item_id,requested_qty,purpose,urgency,requested_by,status)
        VALUES (?,?,?,?,?,?,?)""",
        (req_no, data["item_id"], float(data["quantity"]),
         data.get("purpose", ""), data.get("urgency", "Normal"), user["id"], "PENDING"))
    conn.commit()
    conn.close()
    log_activity(user["id"], "CREATE_REQUEST", f"Request {req_no} for item {data['item_id']}")
    return {"success": True, "message": f"Request {req_no} submitted", "request_no": req_no}

def api_approve_request(user: dict, data: dict) -> dict:
    if user["role"] != "Admin":
        return {"success": False, "message": "Only Admin can approve requests"}
    req_id = data.get("request_id")
    action = data.get("action")  # APPROVED or REJECTED
    conn = get_db()
    req = conn.execute("SELECT * FROM material_requests WHERE id=?", (req_id,)).fetchone()
    if not req:
        conn.close()
        return {"success": False, "message": "Request not found"}
    conn.execute("""UPDATE material_requests SET status=?, approved_by=?, approval_date=datetime('now'), notes=?
                   WHERE id=?""", (action, user["id"], data.get("notes", ""), req_id))
    if action == "APPROVED":
        # Auto-fulfill: deduct stock
        item = conn.execute("SELECT * FROM inventory WHERE id=?", (req["item_id"],)).fetchone()
        if item:
            new_qty = max(0, item["quantity"] - req["requested_qty"])
            conn.execute("UPDATE inventory SET quantity=?, updated_at=datetime('now') WHERE id=?",
                         (new_qty, item["id"]))
            ref = "REF-AUTO-" + "".join(random.choices(string.digits, k=4))
            conn.execute("""INSERT INTO transactions 
                (item_id,transaction_type,quantity,previous_qty,new_qty,reason,performed_by,approved_by,status,reference_no)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (item["id"], "OUT", req["requested_qty"], item["quantity"], new_qty,
                 f"Request {req['request_no']} approved", req["requested_by"], user["id"], "COMPLETED", ref))
            conn.execute("UPDATE material_requests SET status='FULFILLED' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()
    log_activity(user["id"], "REQUEST_ACTION", f"Request {req['request_no']} {action}")
    return {"success": True, "message": f"Request {action.lower()}"}

def api_get_users(user: dict) -> dict:
    if user["role"] != "Admin":
        return {"success": False, "message": "Access denied"}
    conn = get_db()
    rows = conn.execute(
        "SELECT id,username,role,full_name,email,is_active,created_at,last_login FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return {"users": [dict(r) for r in rows]}

def api_add_user(user: dict, data: dict) -> dict:
    if user["role"] != "Admin":
        return {"success": False, "message": "Access denied"}
    conn = get_db()
    try:
        conn.execute("""INSERT INTO users (username,password_hash,role,full_name,email)
                        VALUES (?,?,?,?,?)""",
                     (data["username"], hash_password(data["password"]),
                      data["role"], data["full_name"], data.get("email", "")))
        conn.commit()
        log_activity(user["id"], "ADD_USER", f"Created user {data['username']} with role {data['role']}")
        return {"success": True, "message": "User created successfully"}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "Username already exists"}
    finally:
        conn.close()

def api_toggle_user(user: dict, data: dict) -> dict:
    if user["role"] != "Admin":
        return {"success": False, "message": "Access denied"}
    uid = data.get("user_id")
    if uid == user["id"]:
        return {"success": False, "message": "Cannot deactivate yourself"}
    conn = get_db()
    current = conn.execute("SELECT is_active FROM users WHERE id=?", (uid,)).fetchone()
    new_status = 0 if current["is_active"] else 1
    conn.execute("UPDATE users SET is_active=? WHERE id=?", (new_status, uid))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"User {'activated' if new_status else 'deactivated'}"}

def api_get_categories() -> dict:
    conn = get_db()
    rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return {"categories": [dict(r) for r in rows]}

def api_get_activity_log(user: dict) -> dict:
    if user["role"] != "Admin":
        return {"success": False, "message": "Access denied"}
    conn = get_db()
    rows = conn.execute("""
        SELECT a.id, u.full_name, u.role, a.action, a.details, a.timestamp
        FROM activity_log a JOIN users u ON a.user_id=u.id
        ORDER BY a.id DESC LIMIT 100
    """).fetchall()
    conn.close()
    return {"logs": [dict(r) for r in rows]}

def api_get_reports(user: dict) -> dict:
    conn = get_db()
    # Stock by category
    cat_stock = conn.execute("""
        SELECT c.name, c.type, COUNT(i.id) as item_count,
               SUM(i.quantity) as total_qty, SUM(i.quantity*i.unit_price) as total_value
        FROM categories c LEFT JOIN inventory i ON i.category_id=c.id
        GROUP BY c.id ORDER BY total_value DESC
    """).fetchall()
    # Daily transactions last 7 days
    daily_tx = conn.execute("""
        SELECT DATE(transaction_date) as date,
               SUM(CASE WHEN transaction_type='IN' THEN quantity ELSE 0 END) as total_in,
               SUM(CASE WHEN transaction_type='OUT' THEN quantity ELSE 0 END) as total_out,
               COUNT(*) as count
        FROM transactions
        WHERE transaction_date >= DATE('now', '-7 days')
        GROUP BY DATE(transaction_date) ORDER BY date
    """).fetchall()
    # Top moving items
    top_items = conn.execute("""
        SELECT i.item_name, i.item_code, COUNT(t.id) as tx_count,
               SUM(t.quantity) as total_moved
        FROM transactions t JOIN inventory i ON t.item_id=i.id
        GROUP BY t.item_id ORDER BY tx_count DESC LIMIT 5
    """).fetchall()
    conn.close()
    return {
        "category_stock": [dict(r) for r in cat_stock],
        "daily_transactions": [dict(r) for r in daily_tx],
        "top_items": [dict(r) for r in top_items]
    }

# ─────────────────────────────────────────────
#  HTTP SERVER
# ─────────────────────────────────────────────
SESSIONS = {}

class InventoryHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default server logs

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _get_token(self) -> str:
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("token="):
                return part[6:]
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:]
        return ""

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._send_html(get_html())
            return

        token = self._get_token()
        user = validate_session(token)

        if path == "/api/dashboard":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            self._send_json(api_get_dashboard(user))
        elif path == "/api/inventory":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            filters = {k: v[0] for k, v in qs.items()}
            self._send_json(api_get_inventory(user, filters))
        elif path == "/api/transactions":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            filters = {k: v[0] for k, v in qs.items()}
            self._send_json(api_get_transactions(user, filters))
        elif path == "/api/requests":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            self._send_json(api_get_requests(user))
        elif path == "/api/users":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            self._send_json(api_get_users(user))
        elif path == "/api/categories":
            self._send_json(api_get_categories())
        elif path == "/api/activity-log":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            self._send_json(api_get_activity_log(user))
        elif path == "/api/reports":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            self._send_json(api_get_reports(user))
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except:
            data = {}

        token = self._get_token()
        user = validate_session(token)

        if path == "/api/login":
            self._send_json(api_login(data))
        elif path == "/api/logout":
            self._send_json(api_logout(token))
        elif path == "/api/inventory/add":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            self._send_json(api_add_inventory(user, data))
        elif path == "/api/inventory/update-stock":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            self._send_json(api_update_stock(user, data))
        elif path == "/api/requests/create":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            self._send_json(api_create_request(user, data))
        elif path == "/api/requests/approve":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            self._send_json(api_approve_request(user, data))
        elif path == "/api/users/add":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            self._send_json(api_add_user(user, data))
        elif path == "/api/users/toggle":
            if not user: return self._send_json({"error": "Unauthorized"}, 401)
            self._send_json(api_toggle_user(user, data))
        else:
            self._send_json({"error": "Not found"}, 404)

# ─────────────────────────────────────────────
#  HTML / FRONTEND (Single Page App)
# ─────────────────────────────────────────────
def get_html() -> str:
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>InvenCore — Role-Based Inventory System</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0d14;
    --surface: #111827;
    --surface2: #1a2235;
    --surface3: #1e2d45;
    --border: #1f2d47;
    --border2: #243652;
    --accent: #3b82f6;
    --accent2: #60a5fa;
    --accent3: #93c5fd;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --danger2: #fca5a5;
    --text: #e2e8f0;
    --text2: #94a3b8;
    --text3: #64748b;
    --gold: #fbbf24;
    --purple: #8b5cf6;
    --teal: #14b8a6;
    --radius: 12px;
    --radius-sm: 8px;
    --shadow: 0 4px 24px rgba(0,0,0,0.4);
    --shadow-lg: 0 8px 48px rgba(0,0,0,0.6);
    --glow: 0 0 24px rgba(59,130,246,0.15);
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body { font-family: 'Sora', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; overflow-x: hidden; }
  
  /* ── SCROLLBAR ── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--surface); }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
  
  /* ── LOGIN ── */
  #login-screen {
    position: fixed; inset: 0; z-index: 9999;
    display: flex; align-items: center; justify-content: center;
    background: radial-gradient(ellipse at 20% 50%, #0f1f3d 0%, #0a0d14 60%),
                radial-gradient(ellipse at 80% 20%, #0d1f3a 0%, transparent 50%);
  }
  .login-bg-glow {
    position: absolute; inset: 0; overflow: hidden; pointer-events: none;
  }
  .login-bg-glow::before {
    content: ''; position: absolute; top: -200px; left: -200px;
    width: 600px; height: 600px; background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%);
    animation: floatGlow 8s ease-in-out infinite;
  }
  .login-bg-glow::after {
    content: ''; position: absolute; bottom: -200px; right: -200px;
    width: 500px; height: 500px; background: radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%);
    animation: floatGlow 10s ease-in-out infinite reverse;
  }
  @keyframes floatGlow { 0%,100% { transform: translate(0,0); } 50% { transform: translate(30px, -30px); } }
  
  .login-card {
    background: var(--surface);
    border: 1px solid var(--border2);
    border-radius: 20px;
    padding: 48px 40px;
    width: 420px;
    max-width: 95vw;
    box-shadow: var(--shadow-lg), 0 0 60px rgba(59,130,246,0.08);
    position: relative;
    animation: slideUp 0.5s ease;
  }
  @keyframes slideUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: none; } }
  
  .login-logo {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 8px;
  }
  .login-logo-icon {
    width: 44px; height: 44px; border-radius: 12px;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; box-shadow: 0 4px 16px rgba(59,130,246,0.3);
  }
  .login-logo-text { font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }
  .login-logo-text span { color: var(--accent2); }
  .login-subtitle { font-size: 13px; color: var(--text3); margin-bottom: 36px; }
  
  .demo-creds {
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 16px; margin-bottom: 24px; font-size: 12px;
  }
  .demo-creds .dc-title { color: var(--accent2); font-weight: 600; margin-bottom: 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
  .demo-cred-row { display: flex; justify-content: space-between; color: var(--text2); margin: 3px 0; }
  .demo-cred-row code { font-family: 'JetBrains Mono', monospace; color: var(--text); font-size: 11px; }
  .btn-quick-login { 
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--surface3); border: 1px solid var(--border2);
    color: var(--text2); font-size: 11px; font-family: 'Sora', sans-serif;
    padding: 4px 10px; border-radius: 6px; cursor: pointer; margin-top: 4px;
    transition: all 0.2s;
  }
  .btn-quick-login:hover { border-color: var(--accent); color: var(--accent2); }

  .form-group { margin-bottom: 18px; }
  .form-label { display: block; font-size: 12px; font-weight: 600; color: var(--text2); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
  .form-input {
    width: 100%; padding: 12px 16px; border-radius: var(--radius-sm);
    background: var(--surface2); border: 1px solid var(--border);
    color: var(--text); font-family: 'Sora', sans-serif; font-size: 14px;
    outline: none; transition: all 0.2s;
  }
  .form-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(59,130,246,0.12); }
  .form-input::placeholder { color: var(--text3); }
  select.form-input option { background: var(--surface); }
  
  .btn { 
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    padding: 12px 20px; border-radius: var(--radius-sm); border: none;
    font-family: 'Sora', sans-serif; font-size: 14px; font-weight: 600;
    cursor: pointer; transition: all 0.2s; white-space: nowrap;
  }
  .btn-primary {
    background: linear-gradient(135deg, var(--accent), #6366f1);
    color: white; width: 100%; padding: 14px;
    box-shadow: 0 4px 16px rgba(59,130,246,0.3);
  }
  .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(59,130,246,0.4); }
  .btn-primary:active { transform: none; }
  .btn-sm { padding: 7px 14px; font-size: 12px; border-radius: 6px; }
  .btn-success { background: rgba(16,185,129,0.15); color: var(--success); border: 1px solid rgba(16,185,129,0.3); }
  .btn-success:hover { background: rgba(16,185,129,0.25); }
  .btn-danger { background: rgba(239,68,68,0.15); color: var(--danger); border: 1px solid rgba(239,68,68,0.3); }
  .btn-danger:hover { background: rgba(239,68,68,0.25); }
  .btn-warning { background: rgba(245,158,11,0.15); color: var(--warning); border: 1px solid rgba(245,158,11,0.3); }
  .btn-warning:hover { background: rgba(245,158,11,0.25); }
  .btn-secondary { background: var(--surface2); color: var(--text2); border: 1px solid var(--border); }
  .btn-secondary:hover { border-color: var(--accent); color: var(--accent2); }
  .btn-accent { background: rgba(59,130,246,0.15); color: var(--accent2); border: 1px solid rgba(59,130,246,0.3); }
  .btn-accent:hover { background: rgba(59,130,246,0.25); }
  
  .error-msg { color: var(--danger); font-size: 13px; margin-top: 12px; text-align: center; padding: 10px; background: rgba(239,68,68,0.08); border-radius: 6px; border: 1px solid rgba(239,68,68,0.2); }
  
  /* ── MAIN APP ── */
  #app { display: none; min-height: 100vh; }
  
  /* ── SIDEBAR ── */
  .sidebar {
    position: fixed; left: 0; top: 0; bottom: 0; width: 240px;
    background: var(--surface); border-right: 1px solid var(--border);
    display: flex; flex-direction: column; z-index: 100;
    padding: 0;
    transition: transform 0.3s ease;
  }
  .sidebar-header {
    padding: 24px 20px 20px;
    border-bottom: 1px solid var(--border);
  }
  .sidebar-logo { display: flex; align-items: center; gap: 10px; }
  .sidebar-logo-icon {
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    display: flex; align-items: center; justify-content: center; font-size: 16px;
    flex-shrink: 0;
  }
  .sidebar-logo-text { font-size: 18px; font-weight: 800; letter-spacing: -0.5px; }
  .sidebar-logo-text span { color: var(--accent2); }
  
  .sidebar-user {
    padding: 16px 20px; border-bottom: 1px solid var(--border);
    background: var(--surface2);
  }
  .user-avatar {
    width: 36px; height: 36px; border-radius: 50%;
    background: linear-gradient(135deg, var(--accent), var(--purple));
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 14px; flex-shrink: 0;
  }
  .user-info-wrap { display: flex; align-items: center; gap: 10px; }
  .user-name { font-size: 13px; font-weight: 600; color: var(--text); }
  .user-role-badge {
    display: inline-block; font-size: 10px; font-weight: 600; padding: 2px 8px;
    border-radius: 20px; margin-top: 2px; letter-spacing: 0.3px;
  }
  .role-Admin { background: rgba(139,92,246,0.2); color: #c4b5fd; border: 1px solid rgba(139,92,246,0.3); }
  .role-RawMaterial { background: rgba(16,185,129,0.2); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.3); }
  .role-Packing { background: rgba(245,158,11,0.2); color: #fcd34d; border: 1px solid rgba(245,158,11,0.3); }
  
  .sidebar-nav { flex: 1; overflow-y: auto; padding: 12px 12px; }
  .nav-section-label { font-size: 10px; font-weight: 700; color: var(--text3); text-transform: uppercase; letter-spacing: 1.5px; padding: 8px 8px 4px; }
  .nav-item {
    display: flex; align-items: center; gap: 10px; padding: 10px 12px;
    border-radius: var(--radius-sm); cursor: pointer; transition: all 0.15s;
    font-size: 13px; font-weight: 500; color: var(--text2); margin: 2px 0;
    border: 1px solid transparent;
  }
  .nav-item:hover { background: var(--surface2); color: var(--text); border-color: var(--border); }
  .nav-item.active { background: rgba(59,130,246,0.12); color: var(--accent2); border-color: rgba(59,130,246,0.25); }
  .nav-icon { font-size: 16px; width: 20px; text-align: center; }
  .nav-badge { margin-left: auto; background: var(--danger); color: white; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 10px; min-width: 18px; text-align: center; }
  
  .sidebar-footer { padding: 12px; border-top: 1px solid var(--border); }
  .btn-logout { width: 100%; background: rgba(239,68,68,0.08); color: var(--text3); border: 1px solid transparent; border-radius: var(--radius-sm); padding: 10px; font-size: 13px; font-family: 'Sora', sans-serif; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 8px; }
  .btn-logout:hover { background: rgba(239,68,68,0.15); color: var(--danger); border-color: rgba(239,68,68,0.3); }
  
  /* ── MAIN CONTENT ── */
  .main-content { margin-left: 240px; min-height: 100vh; padding: 32px; }
  .page { display: none; animation: fadeIn 0.3s ease; }
  .page.active { display: block; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
  
  .page-header { margin-bottom: 28px; }
  .page-title { font-size: 26px; font-weight: 800; letter-spacing: -0.5px; }
  .page-subtitle { color: var(--text2); font-size: 14px; margin-top: 4px; }
  .page-header-row { display: flex; align-items: center; justify-content: space-between; flex-wrap: gap; gap: 16px; }
  
  /* ── STATS CARDS ── */
  .stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 28px; }
  .stat-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 20px; position: relative; overflow: hidden;
    transition: all 0.2s;
  }
  .stat-card:hover { border-color: var(--border2); transform: translateY(-2px); box-shadow: var(--shadow); }
  .stat-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    border-radius: 3px 3px 0 0;
  }
  .stat-blue::before { background: linear-gradient(90deg, var(--accent), #6366f1); }
  .stat-green::before { background: linear-gradient(90deg, var(--success), var(--teal)); }
  .stat-yellow::before { background: linear-gradient(90deg, var(--warning), #fb923c); }
  .stat-red::before { background: linear-gradient(90deg, var(--danger), #f97316); }
  .stat-purple::before { background: linear-gradient(90deg, var(--purple), var(--accent)); }
  
  .stat-icon { font-size: 28px; margin-bottom: 12px; }
  .stat-value { font-size: 28px; font-weight: 800; letter-spacing: -1px; font-family: 'JetBrains Mono', monospace; }
  .stat-label { font-size: 12px; color: var(--text2); margin-top: 4px; font-weight: 500; }
  .stat-sub { font-size: 11px; color: var(--text3); margin-top: 2px; }
  
  /* ── TABLES ── */
  .table-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  .table-card-header { padding: 18px 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
  .table-card-title { font-size: 15px; font-weight: 700; }
  .table-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; }
  th { padding: 11px 16px; text-align: left; font-size: 11px; font-weight: 700; color: var(--text3); text-transform: uppercase; letter-spacing: 0.8px; background: var(--surface2); border-bottom: 1px solid var(--border); white-space: nowrap; }
  td { padding: 12px 16px; font-size: 13px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(59,130,246,0.04); }
  
  .code-cell { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--accent3); }
  .num-cell { font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 600; }
  
  /* ── BADGES ── */
  .badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; white-space: nowrap; }
  .badge-success { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.25); }
  .badge-warning { background: rgba(245,158,11,0.15); color: #fcd34d; border: 1px solid rgba(245,158,11,0.25); }
  .badge-danger { background: rgba(239,68,68,0.15); color: var(--danger2); border: 1px solid rgba(239,68,68,0.25); }
  .badge-info { background: rgba(59,130,246,0.15); color: var(--accent2); border: 1px solid rgba(59,130,246,0.25); }
  .badge-purple { background: rgba(139,92,246,0.15); color: #c4b5fd; border: 1px solid rgba(139,92,246,0.25); }
  .badge-gray { background: rgba(100,116,139,0.15); color: var(--text2); border: 1px solid rgba(100,116,139,0.25); }
  
  /* ── PROGRESS BAR ── */
  .progress-wrap { display: flex; align-items: center; gap: 8px; }
  .progress-bar { flex: 1; height: 6px; background: var(--surface2); border-radius: 3px; overflow: hidden; min-width: 60px; }
  .progress-fill { height: 100%; border-radius: 3px; transition: width 0.3s ease; }
  .progress-pct { font-size: 11px; font-family: 'JetBrains Mono', monospace; color: var(--text3); width: 36px; text-align: right; }
  
  /* ── SEARCH & FILTERS ── */
  .filter-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .search-input-wrap { position: relative; flex: 1; min-width: 200px; }
  .search-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); font-size: 16px; color: var(--text3); pointer-events: none; }
  .search-input { padding-left: 38px !important; }
  
  /* ── MODAL ── */
  .modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px);
    z-index: 9000; display: flex; align-items: center; justify-content: center; padding: 20px;
    animation: fadeIn 0.2s ease;
  }
  .modal-box {
    background: var(--surface); border: 1px solid var(--border2);
    border-radius: 16px; padding: 28px; width: 100%; max-width: 520px;
    max-height: 90vh; overflow-y: auto; box-shadow: var(--shadow-lg);
    animation: slideUp 0.25s ease;
  }
  .modal-box.modal-lg { max-width: 700px; }
  .modal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
  .modal-title { font-size: 18px; font-weight: 700; }
  .modal-close { background: none; border: none; color: var(--text3); font-size: 22px; cursor: pointer; padding: 4px; line-height: 1; transition: color 0.2s; }
  .modal-close:hover { color: var(--text); }
  .modal-footer { display: flex; gap: 10px; justify-content: flex-end; margin-top: 24px; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  
  /* ── TOAST ── */
  #toast-container { position: fixed; bottom: 24px; right: 24px; z-index: 99999; display: flex; flex-direction: column; gap: 10px; }
  .toast {
    background: var(--surface2); border: 1px solid var(--border2);
    border-radius: 10px; padding: 14px 18px; min-width: 260px; max-width: 360px;
    box-shadow: var(--shadow); animation: slideInRight 0.3s ease;
    display: flex; align-items: flex-start; gap: 10px;
  }
  @keyframes slideInRight { from { opacity: 0; transform: translateX(100%); } to { opacity: 1; transform: none; } }
  .toast-icon { font-size: 18px; flex-shrink: 0; }
  .toast-content { flex: 1; }
  .toast-title { font-size: 13px; font-weight: 700; }
  .toast-msg { font-size: 12px; color: var(--text2); margin-top: 2px; }
  .toast-success { border-left: 3px solid var(--success); }
  .toast-error { border-left: 3px solid var(--danger); }
  .toast-info { border-left: 3px solid var(--accent); }
  .toast-warning { border-left: 3px solid var(--warning); }

  /* ── DASHBOARD GRIDS ── */
  .dash-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media(max-width:900px) { .dash-grid { grid-template-columns: 1fr; } }
  
  /* ── REPORT CHARTS ── */
  .chart-bar-wrap { display: flex; flex-direction: column; gap: 10px; }
  .chart-bar-row { display: flex; align-items: center; gap: 12px; }
  .chart-bar-label { font-size: 12px; color: var(--text2); width: 120px; flex-shrink: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .chart-bar-outer { flex: 1; height: 10px; background: var(--surface2); border-radius: 5px; overflow: hidden; }
  .chart-bar-inner { height: 100%; border-radius: 5px; transition: width 0.8s ease; }
  .chart-bar-val { font-size: 12px; font-family: 'JetBrains Mono', monospace; color: var(--text3); width: 70px; text-align: right; }
  
  /* ── TX TYPE BADGES ── */
  .tx-IN { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.25); }
  .tx-OUT { background: rgba(239,68,68,0.15); color: #fca5a5; border: 1px solid rgba(239,68,68,0.25); }
  .tx-ADJUST { background: rgba(245,158,11,0.15); color: #fcd34d; border: 1px solid rgba(245,158,11,0.25); }
  
  /* ── URGENCY ── */
  .urgency-Critical { color: var(--danger2); font-weight: 700; }
  .urgency-High { color: var(--warning); font-weight: 600; }
  .urgency-Normal { color: var(--text2); }
  .urgency-Low { color: var(--text3); }
  
  /* ── EMPTY STATE ── */
  .empty-state { padding: 60px 20px; text-align: center; color: var(--text3); }
  .empty-state-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
  .empty-state-text { font-size: 15px; }
  
  /* ── LOADING ── */
  .spinner { display: inline-block; width: 20px; height: 20px; border: 2px solid var(--border2); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.6s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  
  /* ── INFOBOX ── */
  .info-box { background: rgba(59,130,246,0.08); border: 1px solid rgba(59,130,246,0.2); border-radius: var(--radius-sm); padding: 14px 16px; font-size: 13px; color: var(--text2); margin-bottom: 16px; }
  .warn-box { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.2); border-radius: var(--radius-sm); padding: 14px 16px; font-size: 13px; color: var(--warning); margin-bottom: 16px; }
</style>
</head>
<body>

<!-- ═══════════ LOGIN ═══════════ -->
<div id="login-screen">
  <div class="login-bg-glow"></div>
  <div class="login-card">
    <div class="login-logo">
      <div class="login-logo-icon">📦</div>
      <div class="login-logo-text">Inven<span>Core</span></div>
    </div>
    <div class="login-subtitle">Role-Based Inventory Management System</div>
    
    <div class="demo-creds">
      <div class="dc-title">⚡ Demo Credentials</div>
      <div class="demo-cred-row"><span>🛡️ Admin</span><code>admin / admin123</code><button class="btn-quick-login" onclick="quickLogin('admin','admin123')">Login</button></div>
      <div class="demo-cred-row"><span>🏭 Raw Mat. Mgr</span><code>rawmgr / rm123</code><button class="btn-quick-login" onclick="quickLogin('rawmgr','rm123')">Login</button></div>
      <div class="demo-cred-row"><span>📦 Pack. Supervisor</span><code>packsup / ps123</code><button class="btn-quick-login" onclick="quickLogin('packsup','ps123')">Login</button></div>
    </div>
    
    <div class="form-group">
      <label class="form-label">Username</label>
      <input id="login-user" type="text" class="form-input" placeholder="Enter username" autocomplete="username">
    </div>
    <div class="form-group">
      <label class="form-label">Password</label>
      <input id="login-pass" type="password" class="form-input" placeholder="Enter password" autocomplete="current-password">
    </div>
    <button class="btn btn-primary" onclick="doLogin()">
      <span>Sign In to System</span> <span>→</span>
    </button>
    <div id="login-error" class="error-msg" style="display:none"></div>
  </div>
</div>

<!-- ═══════════ APP ═══════════ -->
<div id="app">
  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-logo">
        <div class="sidebar-logo-icon">📦</div>
        <div class="sidebar-logo-text">Inven<span>Core</span></div>
      </div>
    </div>
    <div class="sidebar-user">
      <div class="user-info-wrap">
        <div class="user-avatar" id="sb-avatar">A</div>
        <div>
          <div class="user-name" id="sb-name">Admin</div>
          <div class="user-role-badge role-Admin" id="sb-role">Administrator</div>
        </div>
      </div>
    </div>
    <nav class="sidebar-nav" id="sidebar-nav">
      <!-- Dynamically populated -->
    </nav>
    <div class="sidebar-footer">
      <button class="btn-logout" onclick="doLogout()">🚪 Sign Out</button>
    </div>
  </aside>

  <!-- Main -->
  <main class="main-content">
    <!-- Dashboard -->
    <div class="page active" id="page-dashboard">
      <div class="page-header">
        <div class="page-title">📊 Dashboard</div>
        <div class="page-subtitle" id="dash-greeting">Welcome back!</div>
      </div>
      <div class="stats-grid" id="stats-grid"></div>
      <div class="dash-grid">
        <div class="table-card">
          <div class="table-card-header">
            <div class="table-card-title">🔄 Recent Transactions</div>
          </div>
          <div class="table-wrap" id="recent-tx-table"></div>
        </div>
        <div class="table-card">
          <div class="table-card-header">
            <div class="table-card-title">⚠️ Low Stock Alerts</div>
          </div>
          <div class="table-wrap" id="low-stock-table"></div>
        </div>
      </div>
    </div>

    <!-- Inventory -->
    <div class="page" id="page-inventory">
      <div class="page-header">
        <div class="page-header-row">
          <div>
            <div class="page-title">🗃️ Inventory</div>
            <div class="page-subtitle">Manage and track all stock items</div>
          </div>
          <div style="display:flex;gap:10px;flex-wrap:wrap" id="inv-actions"></div>
        </div>
      </div>
      <div class="table-card">
        <div class="table-card-header">
          <div class="filter-row">
            <div class="search-input-wrap" style="min-width:220px">
              <span class="search-icon">🔍</span>
              <input type="text" class="form-input search-input" id="inv-search" placeholder="Search items..." oninput="loadInventory()">
            </div>
            <select class="form-input" id="inv-cat-filter" onchange="loadInventory()" style="width:160px">
              <option value="All">All Categories</option>
              <option value="Raw Material">Raw Materials</option>
              <option value="Packing Material">Packing</option>
              <option value="General">General</option>
            </select>
            <select class="form-input" id="inv-stock-filter" onchange="loadInventory()" style="width:130px">
              <option value="All">All Stock</option>
              <option value="Low">Low Stock</option>
            </select>
          </div>
        </div>
        <div class="table-wrap" id="inventory-table">
          <div style="padding:40px;text-align:center"><div class="spinner"></div></div>
        </div>
      </div>
    </div>

    <!-- Transactions -->
    <div class="page" id="page-transactions">
      <div class="page-header">
        <div class="page-header-row">
          <div>
            <div class="page-title">🔄 Transactions</div>
            <div class="page-subtitle">Stock movement history</div>
          </div>
          <div style="display:flex;gap:10px" id="tx-actions"></div>
        </div>
      </div>
      <div class="table-card">
        <div class="table-card-header">
          <div class="filter-row">
            <select class="form-input" id="tx-type-filter" onchange="loadTransactions()" style="width:150px">
              <option value="All">All Types</option>
              <option value="IN">Stock In</option>
              <option value="OUT">Stock Out</option>
              <option value="ADJUST">Adjust</option>
            </select>
          </div>
        </div>
        <div class="table-wrap" id="tx-table">
          <div style="padding:40px;text-align:center"><div class="spinner"></div></div>
        </div>
      </div>
    </div>

    <!-- Requests -->
    <div class="page" id="page-requests">
      <div class="page-header">
        <div class="page-header-row">
          <div>
            <div class="page-title">📋 Material Requests</div>
            <div class="page-subtitle">Request and approval workflow</div>
          </div>
          <button class="btn btn-accent btn-sm" onclick="showCreateRequest()">➕ New Request</button>
        </div>
      </div>
      <div class="table-card">
        <div class="table-card-header">
          <div class="table-card-title" id="req-count-label">All Requests</div>
        </div>
        <div class="table-wrap" id="req-table">
          <div style="padding:40px;text-align:center"><div class="spinner"></div></div>
        </div>
      </div>
    </div>

    <!-- Users (Admin only) -->
    <div class="page" id="page-users">
      <div class="page-header">
        <div class="page-header-row">
          <div>
            <div class="page-title">👥 User Management</div>
            <div class="page-subtitle">Manage system users and roles</div>
          </div>
          <button class="btn btn-accent btn-sm" onclick="showAddUser()">➕ Add User</button>
        </div>
      </div>
      <div class="table-card">
        <div class="table-wrap" id="users-table">
          <div style="padding:40px;text-align:center"><div class="spinner"></div></div>
        </div>
      </div>
    </div>

    <!-- Reports -->
    <div class="page" id="page-reports">
      <div class="page-header">
        <div class="page-title">📈 Reports & Analytics</div>
        <div class="page-subtitle">Inventory insights and summaries</div>
      </div>
      <div id="reports-content"><div style="padding:40px;text-align:center"><div class="spinner"></div></div></div>
    </div>

    <!-- Activity Log (Admin) -->
    <div class="page" id="page-activity">
      <div class="page-header">
        <div class="page-title">📜 Activity Log</div>
        <div class="page-subtitle">System audit trail</div>
      </div>
      <div class="table-card">
        <div class="table-wrap" id="activity-table">
          <div style="padding:40px;text-align:center"><div class="spinner"></div></div>
        </div>
      </div>
    </div>
  </main>
</div>

<!-- MODALS -->
<div id="modal-container"></div>
<div id="toast-container"></div>

<script>
// ─────────────────── STATE ───────────────────
let AUTH = { token: '', user: null };
let categories = [];
let inventoryItems = [];
let pendingReqCount = 0;

// ─────────────────── API ───────────────────
async function api(method, path, body = null, params = {}) {
  const url = new URL(path, window.location.href);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + AUTH.token }
  };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  return r.json();
}

// ─────────────────── AUTH ───────────────────
async function doLogin() {
  const u = document.getElementById('login-user').value.trim();
  const p = document.getElementById('login-pass').value;
  const err = document.getElementById('login-error');
  err.style.display = 'none';
  if (!u || !p) { err.textContent = 'Please enter username and password'; err.style.display = 'block'; return; }
  const res = await api('POST', '/api/login', { username: u, password: p });
  if (res.success) {
    AUTH = { token: res.token, user: res.user };
    initApp();
  } else {
    err.textContent = res.message;
    err.style.display = 'block';
  }
}

function quickLogin(u, p) {
  document.getElementById('login-user').value = u;
  document.getElementById('login-pass').value = p;
  doLogin();
}

document.addEventListener('keydown', e => {
  if (e.key === 'Enter' && document.getElementById('login-screen').style.display !== 'none') doLogin();
});

async function doLogout() {
  await api('POST', '/api/logout');
  AUTH = { token: '', user: null };
  document.getElementById('app').style.display = 'none';
  document.getElementById('login-screen').style.display = 'flex';
  document.getElementById('login-pass').value = '';
  document.getElementById('login-error').style.display = 'none';
}

// ─────────────────── APP INIT ───────────────────
function initApp() {
  document.getElementById('login-screen').style.display = 'none';
  document.getElementById('app').style.display = 'block';
  const u = AUTH.user;
  document.getElementById('sb-avatar').textContent = u.full_name.charAt(0).toUpperCase();
  document.getElementById('sb-name').textContent = u.full_name;
  const rb = document.getElementById('sb-role');
  const rk = u.role === 'Raw Material Manager' ? 'RawMaterial' : u.role === 'Packing Supervisor' ? 'Packing' : 'Admin';
  rb.textContent = u.role;
  rb.className = `user-role-badge role-${rk}`;
  buildNav();
  loadCategories().then(() => {
    loadDashboard();
    loadInventory();
    loadTransactions();
    loadRequests();
    if (u.role === 'Admin') { loadUsers(); loadActivity(); }
    loadReports();
  });
}

function buildNav() {
  const role = AUTH.user.role;
  const nav = [
    { id: 'dashboard', icon: '📊', label: 'Dashboard', roles: ['Admin','Raw Material Manager','Packing Supervisor'] },
    { id: 'inventory', icon: '🗃️', label: 'Inventory', roles: ['Admin','Raw Material Manager','Packing Supervisor'] },
    { id: 'transactions', icon: '🔄', label: 'Transactions', roles: ['Admin','Raw Material Manager','Packing Supervisor'] },
    { id: 'requests', icon: '📋', label: 'Requests', badge: 'pendingReqCount', roles: ['Admin','Raw Material Manager','Packing Supervisor'] },
    { id: 'users', icon: '👥', label: 'Users', roles: ['Admin'] },
    { id: 'reports', icon: '📈', label: 'Reports', roles: ['Admin','Raw Material Manager'] },
    { id: 'activity', icon: '📜', label: 'Activity Log', roles: ['Admin'] },
  ];
  const el = document.getElementById('sidebar-nav');
  el.innerHTML = '';
  nav.filter(n => n.roles.includes(role)).forEach(n => {
    const div = document.createElement('div');
    div.className = 'nav-item' + (n.id === 'dashboard' ? ' active' : '');
    div.id = 'nav-' + n.id;
    div.onclick = () => showPage(n.id);
    div.innerHTML = `<span class="nav-icon">${n.icon}</span><span>${n.label}</span>${n.badge ? `<span class="nav-badge" id="badge-req" style="display:none">0</span>` : ''}`;
    el.appendChild(div);
  });
}

function showPage(id) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const navEl = document.getElementById('nav-' + id);
  if (navEl) navEl.classList.add('active');
  const page = document.getElementById('page-' + id);
  if (page) page.classList.add('active');
}

async function loadCategories() {
  const res = await api('GET', '/api/categories');
  categories = res.categories || [];
}

// ─────────────────── DASHBOARD ───────────────────
async function loadDashboard() {
  const res = await api('GET', '/api/dashboard');
  const s = res.stats;
  const hour = new Date().getHours();
  const greet = hour < 12 ? 'Good Morning' : hour < 18 ? 'Good Afternoon' : 'Good Evening';
  document.getElementById('dash-greeting').textContent = `${greet}, ${AUTH.user.full_name}! Here's your inventory overview.`;
  
  document.getElementById('stats-grid').innerHTML = `
    <div class="stat-card stat-blue">
      <div class="stat-icon">📦</div>
      <div class="stat-value">${s.total_items}</div>
      <div class="stat-label">Total Items</div>
      <div class="stat-sub">Active inventory items</div>
    </div>
    <div class="stat-card stat-red">
      <div class="stat-icon">⚠️</div>
      <div class="stat-value">${s.low_stock}</div>
      <div class="stat-label">Low Stock</div>
      <div class="stat-sub">Below minimum level</div>
    </div>
    <div class="stat-card stat-green">
      <div class="stat-icon">💰</div>
      <div class="stat-value">₹${s.total_value.toLocaleString('en-IN', {maximumFractionDigits:0})}</div>
      <div class="stat-label">Total Value</div>
      <div class="stat-sub">Current inventory worth</div>
    </div>
    <div class="stat-card stat-yellow">
      <div class="stat-icon">📋</div>
      <div class="stat-value">${s.pending_requests}</div>
      <div class="stat-label">Pending Requests</div>
      <div class="stat-sub">Awaiting approval</div>
    </div>
    <div class="stat-card stat-purple">
      <div class="stat-icon">🔄</div>
      <div class="stat-value">${s.today_transactions}</div>
      <div class="stat-label">Today's Movements</div>
      <div class="stat-sub">Transactions today</div>
    </div>
  `;

  // Recent transactions
  const txHTML = res.recent_transactions.length === 0 ? emptyState('No transactions yet') :
    `<table><thead><tr><th>Item</th><th>Type</th><th>Qty</th><th>By</th><th>Date</th></tr></thead><tbody>` +
    res.recent_transactions.map(t => `<tr>
      <td>${t.item_name}<br><span class="code-cell">${t.transaction_type === 'IN' ? '+' : '-'}${t.quantity} ${t.unit}</span></td>
      <td><span class="badge badge-${t.transaction_type === 'IN' ? 'success' : t.transaction_type === 'OUT' ? 'danger' : 'warning'} tx-${t.transaction_type}">${t.transaction_type}</span></td>
      <td class="num-cell">${t.quantity}</td>
      <td>${t.full_name}</td>
      <td>${fmtDate(t.transaction_date)}</td>
    </tr>`).join('') + `</tbody></table>`;
  document.getElementById('recent-tx-table').innerHTML = txHTML;

  // Low stock
  const lsHTML = res.low_stock_items.length === 0 ? emptyState('✅ All items are sufficiently stocked!') :
    `<table><thead><tr><th>Code</th><th>Item</th><th>Stock Level</th></tr></thead><tbody>` +
    res.low_stock_items.map(item => {
      const pct = Math.min(100, Math.round((item.quantity / item.min_stock) * 100));
      const color = pct < 30 ? '#ef4444' : pct < 70 ? '#f59e0b' : '#10b981';
      return `<tr>
        <td class="code-cell">${item.item_code}</td>
        <td>${item.item_name}</td>
        <td>
          <div class="progress-wrap">
            <div class="progress-bar"><div class="progress-fill" style="width:${pct}%;background:${color}"></div></div>
            <span class="progress-pct">${item.quantity}/${item.min_stock}</span>
          </div>
        </td>
      </tr>`;
    }).join('') + `</tbody></table>`;
  document.getElementById('low-stock-table').innerHTML = lsHTML;

  // Update pending badge
  pendingReqCount = s.pending_requests;
  const badge = document.getElementById('badge-req');
  if (badge) { badge.textContent = pendingReqCount; badge.style.display = pendingReqCount > 0 ? 'block' : 'none'; }
}

// ─────────────────── INVENTORY ───────────────────
async function loadInventory() {
  const search = document.getElementById('inv-search')?.value || '';
  const catType = document.getElementById('inv-cat-filter')?.value || 'All';
  const stockStatus = document.getElementById('inv-stock-filter')?.value || 'All';
  const res = await api('GET', '/api/inventory', null, { search, category_type: catType, stock_status: stockStatus });
  inventoryItems = res.items || [];
  
  const role = AUTH.user.role;
  // Action buttons
  const actEl = document.getElementById('inv-actions');
  if (actEl) {
    if (role === 'Admin' || role === 'Raw Material Manager' || role === 'Packing Supervisor') {
      actEl.innerHTML = `
        <button class="btn btn-accent btn-sm" onclick="showAddItem()">➕ Add Item</button>
        <button class="btn btn-secondary btn-sm" onclick="showStockUpdate()">📝 Update Stock</button>
      `;
    }
  }

  if (inventoryItems.length === 0) {
    document.getElementById('inventory-table').innerHTML = emptyState('No items found');
    return;
  }

  const html = `<table>
    <thead><tr>
      <th>Code</th><th>Item Name</th><th>Category</th>
      <th>Quantity</th><th>Unit Price</th><th>Stock Status</th>
      <th>Location</th><th>Actions</th>
    </tr></thead>
    <tbody>${inventoryItems.map(item => {
      const pct = Math.min(100, Math.round((item.quantity / item.min_stock) * 100));
      const color = item.stock_status === 'Low' ? '#ef4444' : item.stock_status === 'High' ? '#8b5cf6' : '#10b981';
      const badgeClass = item.stock_status === 'Low' ? 'badge-danger' : item.stock_status === 'High' ? 'badge-purple' : 'badge-success';
      return `<tr>
        <td class="code-cell">${item.item_code}</td>
        <td><strong>${item.item_name}</strong>${item.supplier ? `<br><span style="font-size:11px;color:var(--text3)">${item.supplier}</span>` : ''}</td>
        <td><span class="badge ${item.cat_type === 'Raw Material' ? 'badge-info' : item.cat_type === 'Packing Material' ? 'badge-warning' : 'badge-gray'}">${item.category || '-'}</span></td>
        <td>
          <div class="progress-wrap">
            <div class="progress-bar"><div class="progress-fill" style="width:${Math.min(100,pct)}%;background:${color}"></div></div>
            <span class="num-cell" style="margin-left:8px">${item.quantity}<span style="color:var(--text3);font-size:11px"> ${item.unit}</span></span>
          </div>
          <span style="font-size:10px;color:var(--text3)">Min: ${item.min_stock}</span>
        </td>
        <td class="num-cell">₹${item.unit_price?.toFixed(2)}</td>
        <td><span class="badge ${badgeClass}">${item.stock_status}</span></td>
        <td style="font-size:12px;color:var(--text2)">${item.location || '-'}</td>
        <td>
          <div style="display:flex;gap:6px">
            <button class="btn btn-sm btn-secondary" onclick="showStockUpdateFor(${item.id},'${item.item_name}',${item.quantity})">📝</button>
          </div>
        </td>
      </tr>`;
    }).join('')}</tbody>
  </table>`;
  document.getElementById('inventory-table').innerHTML = html;
}

// ─────────────────── TRANSACTIONS ───────────────────
async function loadTransactions() {
  const txType = document.getElementById('tx-type-filter')?.value || 'All';
  const res = await api('GET', '/api/transactions', null, { tx_type: txType });
  const txs = res.transactions || [];

  const role = AUTH.user.role;
  const actEl = document.getElementById('tx-actions');
  if (actEl) {
    actEl.innerHTML = `<button class="btn btn-accent btn-sm" onclick="showStockUpdate()">➕ Add Transaction</button>`;
  }

  if (txs.length === 0) { document.getElementById('tx-table').innerHTML = emptyState('No transactions found'); return; }
  const html = `<table>
    <thead><tr><th>Ref No</th><th>Item</th><th>Type</th><th>Qty</th><th>Before</th><th>After</th><th>Reason</th><th>By</th><th>Date</th></tr></thead>
    <tbody>${txs.map(t => `<tr>
      <td class="code-cell">${t.reference_no || '-'}</td>
      <td>${t.item_name}<br><span class="code-cell">${t.item_code}</span></td>
      <td><span class="badge tx-${t.transaction_type}">${t.transaction_type}</span></td>
      <td class="num-cell">${t.quantity} ${t.unit}</td>
      <td class="num-cell" style="color:var(--text3)">${t.previous_qty ?? '-'}</td>
      <td class="num-cell" style="color:var(--accent2)">${t.new_qty ?? '-'}</td>
      <td style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:var(--text2)">${t.reason || '-'}</td>
      <td style="font-size:12px">${t.performed_by}</td>
      <td style="font-size:12px;color:var(--text2)">${fmtDate(t.transaction_date)}</td>
    </tr>`).join('')}</tbody>
  </table>`;
  document.getElementById('tx-table').innerHTML = html;
}

// ─────────────────── REQUESTS ───────────────────
async function loadRequests() {
  const res = await api('GET', '/api/requests');
  const reqs = res.requests || [];
  const pending = reqs.filter(r => r.status === 'PENDING').length;
  document.getElementById('req-count-label').textContent = `${reqs.length} Request(s) — ${pending} Pending`;

  if (reqs.length === 0) { document.getElementById('req-table').innerHTML = emptyState('No requests found'); return; }

  const role = AUTH.user.role;
  const html = `<table>
    <thead><tr><th>Request No</th><th>Item</th><th>Qty</th><th>Purpose</th><th>Urgency</th><th>Status</th><th>By</th><th>Date</th>${role === 'Admin' ? '<th>Actions</th>' : ''}</tr></thead>
    <tbody>${reqs.map(r => `<tr>
      <td class="code-cell">${r.request_no}</td>
      <td>${r.item_name}<br><span class="code-cell">${r.item_code}</span></td>
      <td class="num-cell">${r.requested_qty} ${r.unit}</td>
      <td style="font-size:12px;color:var(--text2);max-width:100px">${r.purpose || '-'}</td>
      <td><span class="urgency-${r.urgency}">${r.urgency}</span></td>
      <td>${statusBadge(r.status)}</td>
      <td style="font-size:12px">${r.requested_by}</td>
      <td style="font-size:12px;color:var(--text2)">${fmtDate(r.request_date)}</td>
      ${role === 'Admin' && r.status === 'PENDING' ? `<td>
        <div style="display:flex;gap:6px">
          <button class="btn btn-sm btn-success" onclick="approveRequest(${r.id},'APPROVED')">✅</button>
          <button class="btn btn-sm btn-danger" onclick="approveRequest(${r.id},'REJECTED')">❌</button>
        </div>
      </td>` : role === 'Admin' ? '<td style="font-size:12px;color:var(--text3)">' + (r.approved_by_name || '-') + '</td>' : ''}
    </tr>`).join('')}</tbody>
  </table>`;
  document.getElementById('req-table').innerHTML = html;
}

async function approveRequest(id, action) {
  if (!confirm(`${action === 'APPROVED' ? 'Approve' : 'Reject'} this request?`)) return;
  const res = await api('POST', '/api/requests/approve', { request_id: id, action });
  if (res.success) { toast('success', '✅ Done', res.message); loadRequests(); loadDashboard(); loadInventory(); }
  else toast('error', '❌ Error', res.message);
}

// ─────────────────── USERS ───────────────────
async function loadUsers() {
  const res = await api('GET', '/api/users');
  const users = res.users || [];
  if (!users.length) { document.getElementById('users-table').innerHTML = emptyState('No users'); return; }
  const html = `<table>
    <thead><tr><th>ID</th><th>Username</th><th>Full Name</th><th>Role</th><th>Email</th><th>Status</th><th>Last Login</th><th>Actions</th></tr></thead>
    <tbody>${users.map(u => `<tr>
      <td class="code-cell">#${u.id}</td>
      <td class="code-cell">${u.username}</td>
      <td>${u.full_name}</td>
      <td>${roleBadge(u.role)}</td>
      <td style="font-size:12px;color:var(--text2)">${u.email || '-'}</td>
      <td><span class="badge ${u.is_active ? 'badge-success' : 'badge-danger'}">${u.is_active ? 'Active' : 'Inactive'}</span></td>
      <td style="font-size:12px;color:var(--text2)">${u.last_login ? fmtDate(u.last_login) : 'Never'}</td>
      <td>${u.id !== AUTH.user.id ? `<button class="btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}" onclick="toggleUser(${u.id})">${u.is_active ? '🚫 Deactivate' : '✅ Activate'}</button>` : '<span style="color:var(--text3);font-size:12px">Current</span>'}</td>
    </tr>`).join('')}</tbody>
  </table>`;
  document.getElementById('users-table').innerHTML = html;
}

async function toggleUser(id) {
  const res = await api('POST', '/api/users/toggle', { user_id: id });
  if (res.success) { toast('success', '✅ Updated', res.message); loadUsers(); }
  else toast('error', '❌ Error', res.message);
}

// ─────────────────── REPORTS ───────────────────
async function loadReports() {
  const res = await api('GET', '/api/reports');
  const cats = res.category_stock || [];
  const daily = res.daily_transactions || [];
  const top = res.top_items || [];
  const maxVal = Math.max(...cats.map(c => c.total_value || 0), 1);

  const html = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px">
      <div class="table-card">
        <div class="table-card-header"><div class="table-card-title">📦 Stock by Category</div></div>
        <div style="padding:20px">
          <div class="chart-bar-wrap">
            ${cats.map(c => `
              <div class="chart-bar-row">
                <div class="chart-bar-label" title="${c.name}">${c.name}</div>
                <div class="chart-bar-outer">
                  <div class="chart-bar-inner" style="width:${Math.round((c.total_value||0)/maxVal*100)}%;background:${c.type === 'Raw Material' ? '#3b82f6' : c.type === 'Packing Material' ? '#f59e0b' : '#10b981'}"></div>
                </div>
                <div class="chart-bar-val">₹${(c.total_value||0).toFixed(0)}</div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
      <div class="table-card">
        <div class="table-card-header"><div class="table-card-title">🏆 Top Moving Items</div></div>
        <div class="table-wrap"><table>
          <thead><tr><th>Item</th><th>Transactions</th><th>Total Moved</th></tr></thead>
          <tbody>${top.map((t, i) => `<tr>
            <td>${['🥇','🥈','🥉','4️⃣','5️⃣'][i]} ${t.item_name}</td>
            <td class="num-cell">${t.tx_count}</td>
            <td class="num-cell">${t.total_moved}</td>
          </tr>`).join('')}</tbody>
        </table></div>
      </div>
    </div>
    <div class="table-card">
      <div class="table-card-header"><div class="table-card-title">📅 Last 7 Days — Daily Transactions</div></div>
      <div class="table-wrap"><table>
        <thead><tr><th>Date</th><th>Stock In</th><th>Stock Out</th><th>Total Movements</th></tr></thead>
        <tbody>${daily.map(d => `<tr>
          <td>${d.date}</td>
          <td class="num-cell" style="color:#34d399">+${d.total_in || 0}</td>
          <td class="num-cell" style="color:#fca5a5">-${d.total_out || 0}</td>
          <td class="num-cell">${d.count}</td>
        </tr>`).join('')}
        ${daily.length === 0 ? '<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:20px">No data</td></tr>' : ''}
        </tbody>
      </table></div>
    </div>
  `;
  document.getElementById('reports-content').innerHTML = html;
}

// ─────────────────── ACTIVITY ───────────────────
async function loadActivity() {
  const res = await api('GET', '/api/activity-log');
  const logs = res.logs || [];
  if (logs.length === 0) { document.getElementById('activity-table').innerHTML = emptyState('No activity'); return; }
  const html = `<table>
    <thead><tr><th>#</th><th>User</th><th>Role</th><th>Action</th><th>Details</th><th>Time</th></tr></thead>
    <tbody>${logs.map(l => `<tr>
      <td class="code-cell">${l.id}</td>
      <td>${l.full_name}</td>
      <td>${roleBadge(l.role)}</td>
      <td><span class="badge badge-info">${l.action}</span></td>
      <td style="font-size:12px;color:var(--text2)">${l.details || '-'}</td>
      <td style="font-size:12px;color:var(--text2)">${fmtDate(l.timestamp)}</td>
    </tr>`).join('')}</tbody>
  </table>`;
  document.getElementById('activity-table').innerHTML = html;
}

// ─────────────────── MODALS ───────────────────
function showModal(html) {
  const c = document.getElementById('modal-container');
  c.innerHTML = `<div class="modal-overlay" id="modal-overlay" onclick="e => { if(e.target===this)closeModal(); }">${html}</div>`;
  document.getElementById('modal-overlay').addEventListener('click', function(e) { if(e.target===this) closeModal(); });
}
function closeModal() { document.getElementById('modal-container').innerHTML = ''; }

function showAddItem() {
  const catOptions = categories.map(c => `<option value="${c.id}">${c.name} (${c.type})</option>`).join('');
  showModal(`<div class="modal-box">
    <div class="modal-header">
      <div class="modal-title">➕ Add Inventory Item</div>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="form-label">Item Code *</label><input id="m-code" class="form-input" placeholder="RM-001"></div>
      <div class="form-group"><label class="form-label">Item Name *</label><input id="m-name" class="form-input" placeholder="Item name"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="form-label">Category *</label><select id="m-cat" class="form-input">${catOptions}</select></div>
      <div class="form-group"><label class="form-label">Unit *</label><input id="m-unit" class="form-input" placeholder="kg / pcs / liters"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="form-label">Initial Quantity *</label><input id="m-qty" class="form-input" type="number" min="0" value="0"></div>
      <div class="form-group"><label class="form-label">Unit Price (₹)</label><input id="m-price" class="form-input" type="number" min="0" step="0.01" value="0"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="form-label">Min Stock</label><input id="m-min" class="form-input" type="number" value="10"></div>
      <div class="form-group"><label class="form-label">Max Stock</label><input id="m-max" class="form-input" type="number" value="1000"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="form-label">Location</label><input id="m-loc" class="form-input" placeholder="Warehouse A"></div>
      <div class="form-group"><label class="form-label">Supplier</label><input id="m-sup" class="form-input" placeholder="Supplier name"></div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
      <button class="btn btn-accent" onclick="submitAddItem()">Add Item</button>
    </div>
  </div>`);
}

async function submitAddItem() {
  const data = {
    item_code: document.getElementById('m-code').value.trim(),
    item_name: document.getElementById('m-name').value.trim(),
    category_id: document.getElementById('m-cat').value,
    unit: document.getElementById('m-unit').value.trim(),
    quantity: document.getElementById('m-qty').value,
    unit_price: document.getElementById('m-price').value,
    min_stock: document.getElementById('m-min').value,
    max_stock: document.getElementById('m-max').value,
    location: document.getElementById('m-loc').value.trim(),
    supplier: document.getElementById('m-sup').value.trim(),
  };
  const res = await api('POST', '/api/inventory/add', data);
  if (res.success) { toast('success', '✅ Added', res.message); closeModal(); loadInventory(); loadDashboard(); }
  else toast('error', '❌ Error', res.message);
}

function showStockUpdate() {
  const options = inventoryItems.map(i => `<option value="${i.id}">${i.item_code} — ${i.item_name} (${i.quantity} ${i.unit})</option>`).join('');
  showModal(`<div class="modal-box">
    <div class="modal-header">
      <div class="modal-title">📝 Update Stock</div>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    <div class="form-group"><label class="form-label">Select Item *</label>
      <select id="m-item" class="form-input">${options}</select>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="form-label">Transaction Type *</label>
        <select id="m-tx-type" class="form-input">
          <option value="IN">Stock IN ↑</option>
          <option value="OUT">Stock OUT ↓</option>
          <option value="ADJUST">Adjust (Set Exact)</option>
        </select>
      </div>
      <div class="form-group"><label class="form-label">Quantity *</label>
        <input id="m-upd-qty" class="form-input" type="number" min="0" value="0">
      </div>
    </div>
    <div class="form-group"><label class="form-label">Reason / Notes</label>
      <input id="m-reason" class="form-input" placeholder="Reason for stock update">
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
      <button class="btn btn-accent" onclick="submitStockUpdate()">Update Stock</button>
    </div>
  </div>`);
}

function showStockUpdateFor(id, name, qty) {
  showStockUpdate();
  setTimeout(() => {
    const sel = document.getElementById('m-item');
    if (sel) sel.value = id;
  }, 50);
}

async function submitStockUpdate() {
  const data = {
    item_id: document.getElementById('m-item').value,
    transaction_type: document.getElementById('m-tx-type').value,
    quantity: document.getElementById('m-upd-qty').value,
    reason: document.getElementById('m-reason').value,
  };
  const res = await api('POST', '/api/inventory/update-stock', data);
  if (res.success) { toast('success', '✅ Updated', `Stock updated. Ref: ${res.reference}`); closeModal(); loadInventory(); loadTransactions(); loadDashboard(); }
  else toast('error', '❌ Error', res.message);
}

function showCreateRequest() {
  const options = inventoryItems.map(i => `<option value="${i.id}">${i.item_code} — ${i.item_name} (Stock: ${i.quantity} ${i.unit})</option>`).join('');
  showModal(`<div class="modal-box">
    <div class="modal-header">
      <div class="modal-title">📋 New Material Request</div>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    <div class="form-group"><label class="form-label">Select Item *</label>
      <select id="m-req-item" class="form-input">${options}</select>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="form-label">Quantity Required *</label>
        <input id="m-req-qty" class="form-input" type="number" min="1" value="1">
      </div>
      <div class="form-group"><label class="form-label">Urgency</label>
        <select id="m-req-urgency" class="form-input">
          <option value="Low">Low</option>
          <option value="Normal" selected>Normal</option>
          <option value="High">High</option>
          <option value="Critical">🚨 Critical</option>
        </select>
      </div>
    </div>
    <div class="form-group"><label class="form-label">Purpose / Reason *</label>
      <input id="m-req-purpose" class="form-input" placeholder="Why is this material needed?">
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
      <button class="btn btn-accent" onclick="submitRequest()">Submit Request</button>
    </div>
  </div>`);
}

async function submitRequest() {
  const data = {
    item_id: document.getElementById('m-req-item').value,
    quantity: document.getElementById('m-req-qty').value,
    urgency: document.getElementById('m-req-urgency').value,
    purpose: document.getElementById('m-req-purpose').value,
  };
  const res = await api('POST', '/api/requests/create', data);
  if (res.success) { toast('success', '✅ Submitted', res.message); closeModal(); loadRequests(); loadDashboard(); }
  else toast('error', '❌ Error', res.message);
}

function showAddUser() {
  showModal(`<div class="modal-box">
    <div class="modal-header">
      <div class="modal-title">👤 Add New User</div>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="form-label">Username *</label><input id="m-uname" class="form-input" placeholder="username123"></div>
      <div class="form-group"><label class="form-label">Password *</label><input id="m-upwd" type="password" class="form-input" placeholder="••••••••"></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="form-label">Full Name *</label><input id="m-ufn" class="form-input" placeholder="Full name"></div>
      <div class="form-group"><label class="form-label">Email</label><input id="m-uemail" class="form-input" placeholder="email@company.com"></div>
    </div>
    <div class="form-group"><label class="form-label">Role *</label>
      <select id="m-urole" class="form-input">
        <option value="Admin">🛡️ Admin</option>
        <option value="Raw Material Manager" selected>🏭 Raw Material Manager</option>
        <option value="Packing Supervisor">📦 Packing Supervisor</option>
      </select>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
      <button class="btn btn-accent" onclick="submitAddUser()">Create User</button>
    </div>
  </div>`);
}

async function submitAddUser() {
  const data = {
    username: document.getElementById('m-uname').value.trim(),
    password: document.getElementById('m-upwd').value,
    full_name: document.getElementById('m-ufn').value.trim(),
    email: document.getElementById('m-uemail').value.trim(),
    role: document.getElementById('m-urole').value,
  };
  const res = await api('POST', '/api/users/add', data);
  if (res.success) { toast('success', '✅ Created', res.message); closeModal(); loadUsers(); }
  else toast('error', '❌ Error', res.message);
}

// ─────────────────── HELPERS ───────────────────
function fmtDate(dt) {
  if (!dt) return '-';
  try {
    const d = new Date(dt.replace(' ', 'T'));
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' }) + ' ' +
           d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
  } catch { return dt; }
}

function emptyState(msg) {
  return `<div class="empty-state"><div class="empty-state-icon">📭</div><div class="empty-state-text">${msg}</div></div>`;
}

function statusBadge(status) {
  const map = { PENDING: 'badge-warning', APPROVED: 'badge-success', REJECTED: 'badge-danger', FULFILLED: 'badge-info' };
  return `<span class="badge ${map[status] || 'badge-gray'}">${status}</span>`;
}

function roleBadge(role) {
  const map = { 'Admin': 'badge-purple', 'Raw Material Manager': 'badge-info', 'Packing Supervisor': 'badge-warning' };
  return `<span class="badge ${map[role] || 'badge-gray'}">${role}</span>`;
}

function toast(type, title, msg) {
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const c = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span class="toast-icon">${icons[type]}</span><div class="toast-content"><div class="toast-title">${title}</div><div class="toast-msg">${msg}</div></div>`;
  c.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
</script>
</body>
</html>"""

# ─────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────
PORT = 8765

def start_server():
    server = HTTPServer(("0.0.0.0", PORT), InventoryHandler)
    print(f"\n{'═'*60}")
    print(f"  📦  InvenCore — Role-Based Inventory Management System")
    print(f"{'═'*60}")
    print(f"  🌐  Server : http://localhost:{PORT}")
    print(f"  🗃️  Database: {DB_FILE}")
    print(f"\n  Demo Credentials:")
    print(f"  ┌─────────────────────────────────────────────┐")
    print(f"  │  Role                  │ User     │ Pass    │")
    print(f"  ├─────────────────────────────────────────────┤")
    print(f"  │  🛡️  Admin             │ admin    │ admin123│")
    print(f"  │  🏭  Raw Mat. Manager  │ rawmgr   │ rm123   │")
    print(f"  │  📦  Packing Supv.     │ packsup  │ ps123   │")
    print(f"  └─────────────────────────────────────────────┘")
    print(f"\n  Press Ctrl+C to stop the server")
    print(f"{'═'*60}\n")
    server.serve_forever()

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database ready ✓")

    # Open browser after short delay
    def open_browser():
        import time; time.sleep(1.2)
        webbrowser.open(f"http://localhost:{PORT}")
    threading.Thread(target=open_browser, daemon=True).start()

    try:
        start_server()
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped. Goodbye!\n")
