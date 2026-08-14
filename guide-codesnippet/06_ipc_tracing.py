import os
import queue
import socket
import threading
import time

from proctrace.ipc import ipc_report, trace_ipc, trace_pipe, trace_socket


# ── 1. Queue tracing ──────────────────────────────────────────────

print("=== queue tracing ===")

raw_q: queue.Queue = queue.Queue()
q = trace_ipc(raw_q, name="work-queue", ring_capacity=256)

def producer() -> None:
    for i in range(20):
        q.put(f"item-{i}")
        time.sleep(0.002)

def consumer() -> None:
    for _ in range(20):
        q.get()
        time.sleep(0.005)

t1 = threading.Thread(target=producer)
t2 = threading.Thread(target=consumer)
t1.start(); t2.start()
t1.join();  t2.join()

print(ipc_report())
print()


# ── 2. OS pipe tracing ────────────────────────────────────────────

print("=== OS pipe tracing ===")

r_fd, w_fd = os.pipe()
pipe = trace_pipe(r_fd, w_fd, name="data-pipe", ring_capacity=128)

def writer() -> None:
    for _ in range(10):
        pipe.write(b"hello-world")
        time.sleep(0.003)
    os.close(w_fd)

def reader() -> None:
    try:
        while True:
            data = pipe.read(64)
            if not data:
                break
            time.sleep(0.005)
    except OSError:
        pass

t3 = threading.Thread(target=writer)
t4 = threading.Thread(target=reader)
t3.start(); t4.start()
t3.join();  t4.join()
os.close(r_fd)

print(ipc_report())
print()


# ── 3. Unix socket tracing ────────────────────────────────────────

print("=== socket tracing ===")

server_sock, client_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
traced_client = trace_socket(client_sock, name="client-side")

def server_echo() -> None:
    data = server_sock.recv(1024)
    server_sock.sendall(data)
    server_sock.close()

srv = threading.Thread(target=server_echo)
srv.start()

traced_client.sendall(b"ping!" * 100)
response = traced_client.recv(1024)
traced_client.close()
srv.join()

print(ipc_report())
