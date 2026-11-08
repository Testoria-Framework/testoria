"""A self-contained, stateful demo REST API (users, products, orders, auth).

It implements the contract used by the bundled Python, JavaScript and Java example suites,
so every suite can run against real HTTP without external services:

    testoria demo-api --port 8080

Public: /health, /version, /docs, POST /auth/login. Everything else needs `Authorization: Bearer <token>`.
Accepted tokens: those returned by /auth/login plus the fixed dev tokens in DEV_TOKENS.
"""

from __future__ import annotations

import copy
import datetime as _dt
import json
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlsplit

DEV_TOKENS = {"test_token", "valid_token", "valid-token"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ORDER_STATUSES = {"pending", "processing", "shipped", "delivered", "cancelled"}

SEED = {
    "users": [
        {"id": 1, "name": "John Doe", "email": "john.doe@example.com", "phone": "+1234567890",
         "created_at": "2023-01-01T10:00:00Z", "updated_at": "2023-01-01T10:00:00Z"},
        {"id": 2, "name": "Jane Smith", "email": "jane.smith@example.com", "phone": "+1987654321",
         "created_at": "2023-01-02T11:00:00Z", "updated_at": "2023-01-02T11:00:00Z"},
    ],
    "products": [
        {"id": "P001", "name": "Smartphone X", "description": "Latest smartphone with advanced features",
         "price": 999.99, "category": "electronics", "stock": 50, "sku": "PHONE-X-001",
         "created_at": "2023-01-01T10:00:00Z", "updated_at": "2023-01-01T10:00:00Z"},
        {"id": "P002", "name": "Laptop Pro", "description": "Powerful laptop for professionals",
         "price": 1499.99, "category": "electronics", "stock": 25, "sku": "LAPTOP-PRO-001",
         "created_at": "2023-01-02T10:00:00Z", "updated_at": "2023-01-02T10:00:00Z"},
        {"id": "P003", "name": "Coffee Maker", "description": "Programmable coffee maker",
         "price": 79.99, "category": "home", "stock": 100, "sku": "COFFEE-001",
         "created_at": "2023-01-03T10:00:00Z", "updated_at": "2023-01-03T10:00:00Z"},
    ],
    "orders": [
        {"id": "ORD-001", "customer_id": 1, "items": [{"product_id": "P003", "quantity": 2, "price": 79.99}],
         "total": 159.98, "status": "shipped", "created_at": "2023-01-10T09:30:00Z", "updated_at": "2023-01-11T14:20:00Z"},
        {"id": "ORD-002", "customer_id": 2, "items": [{"product_id": "P001", "quantity": 1, "price": 999.99}],
         "total": 999.99, "status": "pending", "created_at": "2023-01-15T11:45:00Z", "updated_at": "2023-01-15T11:45:00Z"},
    ],
}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ApiError(Exception):
    def __init__(self, status: int, body: Any):
        super().__init__(str(body))
        self.status = status
        self.body = body


class DemoStore:
    def __init__(self, rate_limit: int = 1000):
        self.lock = threading.RLock()
        self.rate_limit = rate_limit
        self.reset()

    def reset(self) -> None:
        with self.lock:
            self.users: List[Dict[str, Any]] = copy.deepcopy(SEED["users"])
            self.products: List[Dict[str, Any]] = copy.deepcopy(SEED["products"])
            self.orders: List[Dict[str, Any]] = copy.deepcopy(SEED["orders"])
            self.tokens: Dict[str, str] = {}
            self.seq = {"user": 2, "product": 3, "order": 2}
            self.hits: Dict[str, int] = {}

    # ---------------------------------------------------------------- auth
    def login(self, body: Dict[str, Any]) -> Dict[str, Any]:
        user = str(body.get("username") or body.get("email") or "")
        pwd = str(body.get("password") or "")
        if not user or not pwd or pwd in ("wrong", "invalid", "wrong_password", "wrongpassword"):
            raise ApiError(401, {"error": "Invalid credentials"})
        token = secrets.token_hex(16)
        self.tokens[token] = user
        return {"token": token, "access_token": token, "token_type": "Bearer", "expires_in": 3600}

    def check_auth(self, headers: Dict[str, str]) -> str:
        auth = headers.get("authorization", "")
        if not auth:
            raise ApiError(401, {"error": "Authentication required"})
        m = re.match(r"Bearer\s+(.+)$", auth, re.I)
        if not m:
            raise ApiError(401, {"error": "Unsupported authorization scheme"})
        tok = m.group(1).strip()
        if tok in DEV_TOKENS:
            return "dev"
        if tok in self.tokens:
            return self.tokens[tok]
        raise ApiError(401, {"error": "Invalid or expired token"})

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _find(coll: List[Dict[str, Any]], item_id: Any) -> Optional[Dict[str, Any]]:
        return next((x for x in coll if str(x["id"]) == str(item_id)), None)

    @staticmethod
    def _no_markup(value: Any, field: str, errors: List[Dict[str, str]]) -> None:
        if isinstance(value, str) and re.search(r"[<>]|javascript:", value, re.I):
            errors.append({"field": field, "message": f"{field} contains forbidden characters"})

    # ---------------------------------------------------------------- users
    def _validate_user(self, body: Dict[str, Any], partial: bool) -> None:
        errors: List[Dict[str, str]] = []
        if not partial or "name" in body:
            if not isinstance(body.get("name"), str) or not body.get("name", "").strip():
                errors.append({"field": "name", "message": "Name is required"})
            self._no_markup(body.get("name"), "name", errors)
        if not partial or "email" in body:
            if not isinstance(body.get("email"), str) or not EMAIL_RE.match(body.get("email", "")):
                errors.append({"field": "email", "message": "Invalid email format"})
        if errors:
            raise ApiError(400, {"errors": errors})

    @staticmethod
    def _derive_name(body: Dict[str, Any]) -> Dict[str, Any]:
        """Accept first_name/last_name or username as an alternative to name."""
        if "name" not in body:
            full = " ".join(str(body[k]) for k in ("first_name", "last_name") if body.get(k))
            if full or body.get("username"):
                body = {**body, "name": full or str(body["username"])}
        return body

    def create_user(self, body: Dict[str, Any]) -> Dict[str, Any]:
        body = self._derive_name(body)
        self._validate_user(body, partial=False)
        if any(u["email"].lower() == body["email"].lower() for u in self.users):
            raise ApiError(409, {"error": "Email already exists"})
        self.seq["user"] += 1
        now = _now()
        user = {"id": self.seq["user"], "name": body["name"].strip(), "email": body["email"],
                "phone": body.get("phone", ""), "created_at": now, "updated_at": now}
        for k, v in body.items():
            if k not in user and k != "password":
                user[k] = v
        self.users.append(user)
        return user

    def get_user(self, raw_id: str) -> Dict[str, Any]:
        if not raw_id.isdigit():
            raise ApiError(400, {"error": "Invalid user ID format"})
        u = self._find(self.users, raw_id)
        if not u:
            raise ApiError(404, {"error": "User not found"})
        return u

    def update_user(self, raw_id: str, body: Dict[str, Any], partial: bool) -> Dict[str, Any]:
        u = self.get_user(raw_id)
        if not partial and any(k in body for k in ("first_name", "last_name", "username")):
            body = self._derive_name(body)
        self._validate_user(body, partial=True)
        for k, v in body.items():
            if k not in ("id", "created_at", "password"):
                u[k] = v
        u["updated_at"] = _now()
        return u

    # ---------------------------------------------------------------- products
    def _validate_product(self, body: Dict[str, Any], partial: bool) -> None:
        errors: List[Dict[str, str]] = []
        if not partial or "name" in body:
            if not isinstance(body.get("name"), str) or not body.get("name", "").strip():
                errors.append({"field": "name", "message": "Name is required"})
            self._no_markup(body.get("name"), "name", errors)
        if not partial or "price" in body:
            p = body.get("price")
            if not isinstance(p, (int, float)) or isinstance(p, bool):
                errors.append({"field": "price", "message": "Price is required"})
            elif p < 0:
                errors.append({"field": "price", "message": "Price must be greater than or equal to 0"})
        if "stock" in body:
            s = body.get("stock")
            if not isinstance(s, int) or isinstance(s, bool) or s < 0:
                errors.append({"field": "stock", "message": "Stock must be a non-negative integer"})
        if errors:
            raise ApiError(400, {"errors": errors})

    def create_product(self, body: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_product(body, partial=False)
        self.seq["product"] += 1
        now = _now()
        prod = {"id": f"P{self.seq['product']:03d}", "name": body["name"], "description": body.get("description", ""),
                "price": body["price"], "category": body.get("category", "general"), "stock": body.get("stock", 0),
                "sku": body.get("sku") or f"SKU-{self.seq['product']:05d}", "created_at": now, "updated_at": now}
        self.products.append(prod)
        return prod

    def get_product(self, pid: str) -> Dict[str, Any]:
        p = self._find(self.products, pid)
        if not p:
            raise ApiError(404, {"error": "Product not found"})
        return p

    def update_product(self, pid: str, body: Dict[str, Any], partial: bool) -> Dict[str, Any]:
        p = self.get_product(pid)
        self._validate_product(body, partial=partial)
        for k, v in body.items():
            if k not in ("id", "created_at"):
                p[k] = v
        p["updated_at"] = _now()
        return p

    # ---------------------------------------------------------------- orders
    def create_order(self, body: Dict[str, Any]) -> Dict[str, Any]:
        errors: List[Dict[str, str]] = []
        if body.get("customer_id") in (None, ""):
            errors.append({"field": "customer_id", "message": "Customer ID is required"})
        items = body.get("items")
        if not isinstance(items, list) or not items:
            errors.append({"field": "items", "message": "Order must contain at least one item"})
        else:
            for i, it in enumerate(items):
                if not isinstance(it, dict) or not it.get("product_id"):
                    errors.append({"field": f"items[{i}].product_id", "message": "Product ID is required"})
                elif not isinstance(it.get("quantity"), int) or it["quantity"] <= 0:
                    errors.append({"field": f"items[{i}].quantity", "message": "Quantity must be a positive integer"})
        if errors:
            raise ApiError(400, {"errors": errors})
        lines = []
        for it in items:
            prod = self._find(self.products, it["product_id"])
            price = it.get("price", prod["price"] if prod else 0)
            if prod is not None:
                if prod.get("stock", 0) < it["quantity"]:
                    raise ApiError(400, {"errors": [{"field": "items", "message": f"Insufficient stock for {prod['id']}"}]})
            lines.append({**it, "price": price})
        for it in lines:
            prod = self._find(self.products, it["product_id"])
            if prod is not None:
                prod["stock"] -= it["quantity"]
        self.seq["order"] += 1
        now = _now()
        order = {"id": f"ORD-{self.seq['order']:03d}", "customer_id": body["customer_id"], "items": lines,
                 "total": round(sum(float(i["price"]) * i["quantity"] for i in lines), 2), "status": "pending",
                 "created_at": now, "updated_at": now}
        for k in ("shipping_address", "payment_method", "notes"):
            if k in body:
                order[k] = body[k]
        self.orders.append(order)
        return order

    def get_order(self, oid: str) -> Dict[str, Any]:
        o = self._find(self.orders, oid)
        if not o:
            raise ApiError(404, {"error": "Order not found"})
        return o

    def update_order(self, oid: str, body: Dict[str, Any]) -> Dict[str, Any]:
        o = self.get_order(oid)
        if "status" in body and body["status"] not in ORDER_STATUSES:
            raise ApiError(400, {"errors": [{"field": "status", "message": f"Status must be one of {sorted(ORDER_STATUSES)}"}]})
        for k, v in body.items():
            if k not in ("id", "created_at", "items", "total"):
                o[k] = v
        o["updated_at"] = _now()
        return o

    def cancel_order(self, oid: str, body: Dict[str, Any]) -> Dict[str, Any]:
        o = self.get_order(oid)
        if o["status"] in ("shipped", "delivered"):
            raise ApiError(409, {"error": f"Cannot cancel an order that is {o['status']}"})
        if o["status"] != "cancelled":
            for it in o["items"]:
                prod = self._find(self.products, it["product_id"])
                if prod is not None:
                    prod["stock"] += it["quantity"]
        o["status"] = "cancelled"
        o["cancellation_reason"] = body.get("cancellation_reason") or body.get("reason", "")
        o["cancelled_at"] = o["updated_at"] = _now()
        return o

    # ---------------------------------------------------------------- routing
    def route(self, method: str, path: str, query: Dict[str, List[str]], headers: Dict[str, str],
              body: Any) -> Tuple[int, Any]:
        parts = [unquote(p) for p in path.strip("/").split("/") if p]
        with self.lock:
            if method == "GET" and parts == ["health"]:
                return 200, {"status": "ok", "time": _now()}
            if method == "GET" and parts == ["version"]:
                return 200, {"name": "testoria-demo-api", "version": "2.0.0"}
            if method == "GET" and parts == ["docs"]:
                return 200, {"endpoints": ["/health", "/version", "POST /auth/login", "/users", "/users/{id}",
                                           "/users/{id}/orders", "/users/me", "/products", "/products/{id}",
                                           "/orders", "/orders/{id}", "PATCH /orders/{id}/cancel"]}
            if parts == ["auth", "login"] and method == "POST":
                return 200, self.login(body if isinstance(body, dict) else {})
            if parts == ["__reset"] and method == "POST":
                self.reset()
                return 200, {"status": "reset"}

            user = self.check_auth(headers)
            if body is _INVALID_JSON:
                raise ApiError(400, {"error": "Request body is not valid JSON"})
            b = body if isinstance(body, dict) else {}
            if method in ("POST", "PUT", "PATCH") and body is not None and not isinstance(body, dict):
                raise ApiError(400, {"error": "Request body must be a JSON object"})

            if parts == ["protected-resource"] and method == "GET":
                return 200, {"message": "You have access", "user": user}
            if not parts:
                raise ApiError(404, {"error": "Not found"})
            res = parts[0]
            if res == "users":
                if len(parts) == 1:
                    if method == "GET":
                        items = self.users
                        if "email" in query:
                            items = [u for u in items if u["email"] == query["email"][0]]
                        return 200, _paginate(items, query)
                    if method == "POST":
                        return 201, self.create_user(b)
                elif parts[1] == "me" and len(parts) == 2 and method == "GET":
                    return 200, {"id": 0 if user == "dev" else 1, "username": user, "role": "admin"}
                elif len(parts) == 2:
                    if method == "GET":
                        return 200, self.get_user(parts[1])
                    if method in ("PUT", "PATCH"):
                        return 200, self.update_user(parts[1], b, partial=method == "PATCH")
                    if method == "DELETE":
                        u = self.get_user(parts[1])
                        self.users.remove(u)
                        return 204, None
                elif len(parts) == 3 and parts[2] == "orders" and method == "GET":
                    self.get_user(parts[1])
                    return 200, [o for o in self.orders if str(o["customer_id"]) == parts[1]]
            if res == "products":
                if len(parts) == 1:
                    if method == "GET":
                        items = self.products
                        if "category" in query:
                            items = [p for p in items if p["category"] == query["category"][0]]
                        return 200, _paginate(items, query)
                    if method == "POST":
                        return 201, self.create_product(b)
                elif len(parts) == 2 and parts[1] != "admin":
                    if method == "GET":
                        return 200, self.get_product(parts[1])
                    if method in ("PUT", "PATCH"):
                        return 200, self.update_product(parts[1], b, partial=method == "PATCH")
                    if method == "DELETE":
                        self.products.remove(self.get_product(parts[1]))
                        return 204, None
                elif parts[1:] == ["admin"]:
                    if user != "admin":
                        raise ApiError(403, {"error": "Admin role required"})
                    return 200, {"products": len(self.products)}
            if res == "orders":
                if len(parts) == 1:
                    if method == "GET":
                        items = self.orders
                        for key in ("status", "customer_id"):
                            if key in query:
                                items = [o for o in items if str(o.get(key)) == query[key][0]]
                        return 200, _paginate(items, query)
                    if method == "POST":
                        return 201, self.create_order(b)
                elif len(parts) == 2:
                    if method == "GET":
                        return 200, self.get_order(parts[1])
                    if method in ("PUT", "PATCH"):
                        return 200, self.update_order(parts[1], b)
                    if method == "DELETE":
                        self.orders.remove(self.get_order(parts[1]))
                        return 204, None
                elif len(parts) == 3 and parts[2] == "cancel" and method in ("PATCH", "POST", "PUT"):
                    return 200, self.cancel_order(parts[1], b)
            raise ApiError(404, {"error": "Not found"})


def _paginate(items: List[Dict[str, Any]], query: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    if "limit" in query or "page" in query:
        try:
            limit = int(query.get("limit", ["20"])[0])
            page = int(query.get("page", ["1"])[0])
        except ValueError:
            raise ApiError(400, {"error": "page and limit must be integers"}) from None
        return items[(page - 1) * limit: page * limit]
    return items


_INVALID_JSON = object()


def make_handler(store: DemoStore, verbose: bool = False):
    class Handler(BaseHTTPRequestHandler):
        server_version = "TestoriaDemoAPI/2.0"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            if verbose:
                super().log_message(fmt, *args)

        def _send(self, status: int, body: Any, extra: Optional[Dict[str, str]] = None):
            payload = b"" if body is None or status == 204 else json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if payload and self.command != "HEAD":
                self.wfile.write(payload)

        def _handle(self):
            split = urlsplit(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
            body: Any = None
            if raw.strip():
                try:
                    body = json.loads(raw)
                except ValueError:
                    body = _INVALID_JSON
            headers = {k.lower(): v for k, v in self.headers.items()}
            client = headers.get("authorization", self.client_address[0])
            with store.lock:
                store.hits[client] = store.hits.get(client, 0) + 1
                remaining = max(0, store.rate_limit - store.hits[client])
            rl = {"X-RateLimit-Limit": str(store.rate_limit), "X-RateLimit-Remaining": str(remaining)}
            if remaining <= 0:
                return self._send(429, {"error": "Too many requests"}, {**rl, "Retry-After": "1"})
            try:
                status, out = store.route(self.command.upper(), split.path, parse_qs(split.query), headers, body)
            except ApiError as e:
                status, out = e.status, e.body
            except Exception as e:  # noqa: BLE001
                status, out = 500, {"error": "Internal server error", "type": type(e).__name__}
            extra = dict(rl)
            if status == 401:
                extra["WWW-Authenticate"] = 'Bearer realm="testoria-demo"'
            self._send(status, out, extra)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _handle

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Allow", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
            self.send_header("Content-Length", "0")
            self.end_headers()

    return Handler


def create_server(host: str = "127.0.0.1", port: int = 0, rate_limit: int = 1000,
                  verbose: bool = False) -> Tuple[ThreadingHTTPServer, DemoStore]:
    store = DemoStore(rate_limit=rate_limit)
    server = ThreadingHTTPServer((host, port), make_handler(store, verbose))
    server.daemon_threads = True
    return server, store


def start_background(host: str = "127.0.0.1", port: int = 0, **kw) -> Tuple[ThreadingHTTPServer, DemoStore]:
    server, store = create_server(host, port, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, store
