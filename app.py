from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import json, html, uuid
from datetime import date

BASE = Path(__file__).parent
DATA_FILE = BASE / "tasks.json"
TEMPLATES = BASE / "templates"
STATIC = BASE / "static"

DEFAULT_TASKS = [
    {"id":"1","title":"Computer Networks Assignment","subject":"Computer Networks","deadline":"2026-09-10","priority":"High","status":"Pending","description":"Complete the CN assignment questions."},
    {"id":"2","title":"Dynamic Programming Revision","subject":"Algorithms","deadline":"2026-09-08","priority":"Medium","status":"Pending","description":"Revise change-making and matrix chain multiplication."},
    {"id":"3","title":"Python Practical","subject":"Python","deadline":"2026-09-05","priority":"Low","status":"Completed","description":"Finish and test the Python practical programs."}
]

def load_tasks():
    if not DATA_FILE.exists():
        save_tasks(DEFAULT_TASKS)
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

def save_tasks(tasks):
    DATA_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")

def esc(value):
    return html.escape(str(value or ""), quote=True)

def render(name, **context):
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    for key, value in context.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text

def page_shell(content, active="dashboard"):
    return render(
        "base.html",
        content=content,
        dashboard_active=("active" if active == "dashboard" else ""),
        tasks_active=("active" if active == "tasks" else ""),
        add_active=("active" if active == "add" else "")
    )

def task_rows(tasks):
    if not tasks:
        return '<tr><td colspan="6" class="empty">No tasks found.</td></tr>'
    rows = []
    for t in tasks:
        status_class = "completed" if t["status"] == "Completed" else "pending"
        priority_class = t["priority"].lower()
        rows.append(f"""
        <tr>
          <td><strong>{esc(t["title"])}</strong><div class="muted">{esc(t.get("description",""))}</div></td>
          <td>{esc(t["subject"])}</td>
          <td>{esc(t["deadline"])}</td>
          <td><span class="badge {priority_class}">{esc(t["priority"])}</span></td>
          <td><span class="badge {status_class}">{esc(t["status"])}</span></td>
          <td>
            <a class="btn small" href="/edit?id={esc(t["id"])}">Edit</a>
            <a class="btn small danger" href="/delete?id={esc(t["id"])}" onclick="return confirm('Delete this task?')">Delete</a>
          </td>
        </tr>""")
    return "".join(rows)

def dashboard():
    tasks = load_tasks()
    total = len(tasks)
    completed = sum(t["status"] == "Completed" for t in tasks)
    pending = total - completed
    today = date.today().isoformat()
    overdue = sum(t["status"] != "Completed" and t["deadline"] < today for t in tasks)
    recent = sorted(tasks, key=lambda x: x["deadline"] or "9999-99-99")[:5]

    content = f"""
    <section class="hero">
      <div>
        <p class="eyebrow">STUDENT PRODUCTIVITY</p>
        <h1>Stay on top of your academic work.</h1>
        <p>Organize assignments, track deadlines and keep your semester under control.</p>
      </div>
      <a class="primary" href="/add">+ Add New Task</a>
    </section>
    <section class="stats">
      <div class="stat"><span>Total Tasks</span><strong>{total}</strong></div>
      <div class="stat"><span>Pending</span><strong>{pending}</strong></div>
      <div class="stat"><span>Completed</span><strong>{completed}</strong></div>
      <div class="stat"><span>Overdue</span><strong>{overdue}</strong></div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div><h2>Upcoming Tasks</h2><p>Sorted by deadline</p></div>
        <a class="btn" href="/tasks">View all</a>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Task</th><th>Subject</th><th>Deadline</th><th>Priority</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>{task_rows(recent)}</tbody>
        </table>
      </div>
    </section>"""
    return page_shell(content, "dashboard")

def task_form(task=None):
    editing = task is not None
    action = "/edit" if editing else "/add"
    title = "Edit Task" if editing else "Add New Task"
    task = task or {"title":"","subject":"","deadline":"","priority":"Medium","status":"Pending","description":""}

    priority_options = "".join(
        f'<option {"selected" if p == task["priority"] else ""}>{p}</option>'
        for p in ["Low", "Medium", "High"]
    )
    status_options = "".join(
        f'<option {"selected" if s == task["status"] else ""}>{s}</option>'
        for s in ["Pending", "Completed"]
    )
    hidden_id = f'<input type="hidden" name="id" value="{esc(task.get("id",""))}">' if editing else ""

    content = f"""
    <section class="form-page">
      <div class="panel narrow">
        <p class="eyebrow">TASK MANAGEMENT</p>
        <h1>{title}</h1>
        <form method="POST" action="{action}">
          {hidden_id}
          <label>Task Title
            <input name="title" required value="{esc(task["title"])}" placeholder="e.g. DBMS Assignment">
          </label>
          <div class="grid2">
            <label>Subject / Category
              <input name="subject" required value="{esc(task["subject"])}" placeholder="e.g. Database">
            </label>
            <label>Deadline
              <input type="date" name="deadline" required value="{esc(task["deadline"])}">
            </label>
          </div>
          <div class="grid2">
            <label>Priority<select name="priority">{priority_options}</select></label>
            <label>Status<select name="status">{status_options}</select></label>
          </div>
          <label>Description
            <textarea name="description" rows="5" placeholder="Add notes about this task...">{esc(task["description"])}</textarea>
          </label>
          <div class="form-actions">
            <a class="btn" href="/tasks">Cancel</a>
            <button class="primary" type="submit">Save Task</button>
          </div>
        </form>
      </div>
    </section>"""
    return page_shell(content, "add")

def tasks_page():
    tasks = load_tasks()
    content = f"""
    <section class="page-title">
      <div><p class="eyebrow">MY WORK</p><h1>All Tasks</h1><p>Manage every assignment in one place.</p></div>
      <a class="primary" href="/add">+ Add Task</a>
    </section>
    <section class="panel">
      <div class="table-wrap">
        <table>
          <thead><tr><th>Task</th><th>Subject</th><th>Deadline</th><th>Priority</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>{task_rows(tasks)}</tbody>
        </table>
      </div>
    </section>"""
    return page_shell(content, "tasks")

class Handler(BaseHTTPRequestHandler):
    def send_html(self, body, status=200):
        raw = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/":
            self.send_html(dashboard())
        elif path == "/tasks":
            self.send_html(tasks_page())
        elif path == "/add":
            self.send_html(task_form())
        elif path == "/edit":
            task_id = qs.get("id", [""])[0]
            task = next((t for t in load_tasks() if t["id"] == task_id), None)
            self.send_html(task_form(task) if task else "Task not found", 200 if task else 404)
        elif path == "/delete":
            task_id = qs.get("id", [""])[0]
            save_tasks([t for t in load_tasks() if t["id"] != task_id])
            self.redirect("/tasks")
        elif path == "/static/style.css":
            raw = (STATIC / "style.css").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/css")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif path == "/static/script.js":
            raw = (STATIC / "script.js").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        else:
            self.send_html("404 - Page not found", 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length).decode("utf-8")
        form = {k: v[0] for k, v in parse_qs(data).items()}

        required = ["title", "subject", "deadline", "priority", "status", "description"]
        if any(not form.get(k, "").strip() for k in required):
            self.send_html("Please fill all required fields.", 400)
            return

        tasks = load_tasks()
        item = {k: form.get(k, "").strip() for k in required}

        if parsed.path == "/add":
            item["id"] = uuid.uuid4().hex[:8]
            tasks.append(item)
        elif parsed.path == "/edit":
            task_id = form.get("id", "")
            for task in tasks:
                if task["id"] == task_id:
                    task.update(item)
                    break

        save_tasks(tasks)
        self.redirect("/tasks")

if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 8000))

    print("Student Task Management System")
    print(f"Server running on port {port}")

    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
