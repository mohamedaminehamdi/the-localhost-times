"""Tiny stdlib HTTP helpers shared by sources and deliveries."""
import json
import urllib.request
import uuid

UA = "TheLocalhostTimes/1.0 (+https://github.com/mohamedaminehamdi/the-localhost-times)"


def request(url, data=None, headers=None, method=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def get_json(url, headers=None, timeout=30):
    return json.loads(request(url, headers=headers, timeout=timeout))


def post_json(url, payload, headers=None, timeout=60):
    body = request(url, json.dumps(payload).encode(), {"Content-Type": "application/json", **(headers or {})}, timeout=timeout)
    return json.loads(body) if body.strip() else None


def post_multipart(url, fields, files, timeout=120):
    """fields: {name: str}; files: {name: (filename, bytes, content_type)}."""
    boundary = uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, (filename, data, ctype) in files.items():
        head = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n'
        chunks.append(head.encode() + data + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return request(url, b"".join(chunks), {"Content-Type": f"multipart/form-data; boundary={boundary}"}, timeout=timeout)
