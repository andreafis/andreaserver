#!/usr/bin/env python3
"""Console AndreaServer - dashboard web leggera (solo libreria standard).

Raccoglie i dati in RAM e li serve su http://<server>:8088
Accesso consentito solo da LAN e VPN. I pulsanti richiedono la password
in /etc/console-andreaserver/password.
"""
import glob, hmac, ipaddress, json, os, re, subprocess, threading, time, urllib.request
from collections import deque
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = 8088
HERE = os.path.dirname(os.path.abspath(__file__))
PWFILE = "/etc/console-andreaserver/password"
ALLOWED = [ipaddress.ip_network(n) for n in
           ("127.0.0.0/8", "@@LAN_NET@@", "10.9.0.0/24", "10.8.0.0/24", "::1/128")]
MOUNTS = {"Sistema": "/", "Media": "@@MEDIA_MOUNT@@",
          "Indice": "@@INDEX_MOUNT@@"}
DISKS = {"@@DISK_SYS@@": "Sistema", "@@DISK_MEDIA@@": "Media", "@@DISK_INDEX@@": "Indice"}
NICS = ("@@NIC@@", "wg0", "tun0")
SERVICES = [("pihole-FTL", "Pi-hole"), ("jellyfin", "Jellyfin"), ("smbd", "Samba"),
            ("openvpn@server", "OpenVPN"), ("wg-quick@wg0", "WireGuard"),
            ("dropbear", "SSH"), ("cron", "Cron"), ("smartmontools", "SMART")]
BACKUP_DIR = "@@INDEX_MOUNT@@/backup-server"
HIST = 180                     # campioni veloci (2 s) = 6 minuti
LAT, LON = @@LAT@@, @@LON@@

VENTI = ["Tramontana", "Grecale", "Grecale", "Levante", "Levante", "Scirocco", "Scirocco",
         "Gallipolino", "Ostro (Mezzogiorno)", "Libeccio", "Libeccio", "Calabrese",
         "Ponente", "Ponente", "Maestrale", "Maestrale"]
SIGLE = "N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split()

lock = threading.Lock()
state = {"fast": {}, "slow": {}, "meteo": {}, "hist": {}}
hist = {k: deque(maxlen=HIST) for k in
        ["cpu", "temp", "ram"] + [f"{n}_rx" for n in NICS] + [f"{n}_tx" for n in NICS]
        + [f"{d}_r" for d in DISKS] + [f"{d}_w" for d in DISKS]}


def sh(cmd, timeout=10):
    try:
        return subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                              text=True, timeout=timeout).stdout
    except Exception:
        return ""


def read(path, default=""):
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return default


# ---------------------------------------------------------------- campioni veloci
def cpu_times():
    out = {}
    for line in read("/proc/stat").splitlines():
        if line.startswith("cpu"):
            p = line.split()
            v = list(map(int, p[1:8]))
            out[p[0]] = (sum(v), v[3] + v[4])
    return out


def net_bytes():
    out = {}
    for line in read("/proc/net/dev").splitlines()[2:]:
        name, data = line.split(":", 1)
        name = name.strip()
        if name in NICS:
            f = data.split()
            out[name] = (int(f[0]), int(f[8]))
    return out


def disk_sectors():
    out = {}
    for line in read("/proc/diskstats").splitlines():
        f = line.split()
        if len(f) > 9 and f[2] in DISKS:
            out[f[2]] = (int(f[5]), int(f[9]))
    return out


def temps():
    t = {}
    for h in glob.glob("/sys/class/hwmon/hwmon*"):
        name = read(h + "/name").strip()
        for inp in sorted(glob.glob(h + "/temp*_input")):
            try:
                v = int(read(inp)) / 1000
            except ValueError:
                continue
            if v <= 1:
                continue
            label = read(inp.replace("_input", "_label")).strip() or name
            t[label] = round(v, 1)
    return t


def meminfo():
    m = {}
    for line in read("/proc/meminfo").splitlines():
        k, v = line.split(":", 1)
        m[k] = int(v.split()[0]) * 1024
    used = m["MemTotal"] - m["MemAvailable"]
    return {"total": m["MemTotal"], "used": used, "cache": m.get("Cached", 0) + m.get("Buffers", 0),
            "swap_total": m.get("SwapTotal", 0), "swap_used": m.get("SwapTotal", 0) - m.get("SwapFree", 0)}


def fast_loop():
    prev_c, prev_n, prev_d, prev_t = cpu_times(), net_bytes(), disk_sectors(), time.time()
    while True:
        time.sleep(2)
        c, n, d, t = cpu_times(), net_bytes(), disk_sectors(), time.time()
        dt = t - prev_t
        cores = {}
        for k, (tot, idle) in c.items():
            pt, pi = prev_c.get(k, (tot, idle))
            dtot = tot - pt
            cores[k] = round(100 * (dtot - (idle - pi)) / dtot, 1) if dtot else 0
        rates = {}
        for k, (rx, tx) in n.items():
            prx, ptx = prev_n.get(k, (rx, tx))
            rates[k] = {"rx": max(0, (rx - prx) / dt), "tx": max(0, (tx - ptx) / dt),
                        "rx_tot": rx, "tx_tot": tx}
        io = {}
        for k, (r, w) in d.items():
            pr, pw = prev_d.get(k, (r, w))
            io[k] = {"r": max(0, (r - pr) * 512 / dt), "w": max(0, (w - pw) * 512 / dt)}
        tt = temps()
        mem = meminfo()
        cpu_t = max([v for k, v in tt.items() if k.startswith("Core")] or [0])
        with lock:
            hist["cpu"].append(cores.get("cpu", 0))
            hist["temp"].append(cpu_t)
            hist["ram"].append(round(100 * mem["used"] / mem["total"], 1))
            for k in NICS:
                hist[f"{k}_rx"].append(rates.get(k, {}).get("rx", 0))
                hist[f"{k}_tx"].append(rates.get(k, {}).get("tx", 0))
            for k in DISKS:
                hist[f"{k}_r"].append(io.get(k, {}).get("r", 0))
                hist[f"{k}_w"].append(io.get(k, {}).get("w", 0))
            state["fast"] = {"cpu": cores.get("cpu", 0),
                             "cores": [cores[k] for k in sorted(cores) if k != "cpu"],
                             "temps": tt, "mem": mem, "net": rates, "io": io,
                             "load": read("/proc/loadavg").split()[:3], "ts": t}
        prev_c, prev_n, prev_d, prev_t = c, n, d, t


# ---------------------------------------------------------------- campioni lenti
def pihole_api(path):
    try:
        return json.loads(sh(["pihole", "api", path], timeout=15) or "{}")
    except Exception:
        return {}


def wg_names():
    names, pending = {}, None
    for line in read("/etc/wireguard/wg0.conf").splitlines():
        s = line.strip()
        if s.startswith("#"):
            pending = s.lstrip("# ").strip()
        elif s.startswith("AllowedIPs"):
            ip = s.split("=", 1)[1].strip().split("/")[0]
            names[ip] = pending or ip
            pending = None
    return names


def wireguard():
    names, now, peers = wg_names(), time.time(), []
    for line in sh(["wg", "show", "wg0", "dump"]).splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 8:
            continue
        ip = f[3].split("/")[0]
        hs = int(f[4])
        peers.append({"name": names.get(ip, ip), "ip": ip,
                      "endpoint": "" if f[2] == "(none)" else f[2].rsplit(":", 1)[0],
                      "handshake": hs, "ago": int(now - hs) if hs else None,
                      "online": bool(hs and now - hs < 180), "rx": int(f[5]), "tx": int(f[6])})
    peers.sort(key=lambda p: (not p["online"], -(p["handshake"] or 0)))
    return peers


def disks():
    out = []
    for name, mnt in MOUNTS.items():
        try:
            st = os.statvfs(mnt)
            tot, free = st.f_blocks * st.f_frsize, st.f_bavail * st.f_frsize
            out.append({"name": name, "total": tot, "used": tot - free, "free": free})
        except Exception:
            out.append({"name": name, "total": 0, "used": 0, "free": 0})
    smart = read("/run/banner-smart").split()
    sm = {"temp": smart[2], "health": smart[3], "ts": int(smart[0])} if len(smart) == 4 else None
    return out, sm


def updates():
    items = []
    n = read("/run/banner-updates").strip()
    if n.isdigit() and int(n) > 0:
        items.append({"what": f"Sistema: {n} pacchetti", "cmd": "apt upgrade"})
    v = dict(re.findall(r"^(\w+)=(.*)$", read("/etc/pihole/versions"), re.M))
    for comp in ("CORE", "WEB", "FTL"):
        if v.get(f"{comp}_VERSION") and v.get(f"{comp}_VERSION") != v.get(f"GITHUB_{comp}_VERSION"):
            items.append({"what": f"Pi-hole {comp.title()} {v.get('GITHUB_' + comp + '_VERSION')}",
                          "cmd": "pihole -up"})
    if read("/run/dietpi/.update_available").strip():
        items.append({"what": "DietPi " + read("/run/dietpi/.update_available").strip(),
                      "cmd": "dietpi-update"})
    if os.path.exists("/run/reboot-required"):
        items.append({"what": "Riavvio richiesto", "cmd": "reboot"})
    dv = dict(re.findall(r"^G_DIETPI_VERSION_(\w+)=(\d+)", read("/boot/dietpi/.version"), re.M))
    versions = {"DietPi": f"v{dv.get('CORE')}.{dv.get('SUB')}.{dv.get('RC')}",
                "Pi-hole": f"Core {v.get('CORE_VERSION')} · Web {v.get('WEB_VERSION')} · FTL {v.get('FTL_VERSION')}",
                "Kernel": os.uname().release}
    return items, versions


def last_backup():
    files = sorted(glob.glob(BACKUP_DIR + "/andreaserver_*.tar.gz"), key=os.path.getmtime)
    if not files:
        return None
    f = files[-1]
    return {"file": os.path.basename(f), "ts": int(os.path.getmtime(f)),
            "size": os.path.getsize(f), "count": len(files)}


def processes():
    out = []
    for line in sh(["ps", "-eo", "pid,comm,%cpu,%mem,rss", "--sort=-%cpu", "--no-headers"]).splitlines()[:10]:
        p = line.split(None, 4)
        if len(p) == 5 and p[1] not in ("ps",):
            out.append({"pid": p[0], "name": p[1], "cpu": float(p[2]), "mem": float(p[3]),
                        "rss": int(p[4]) * 1024})
    return out[:8]


def slow_loop():
    while True:
        try:
            now = int(time.time())
            summ = pihole_api("stats/summary")
            top = pihole_api("stats/top_domains?count=8").get("domains", [])
            topb = pihole_api("stats/top_domains?blocked=true&count=8").get("domains", [])
            ph_hist = pihole_api("history").get("history", [])
            q = pihole_api(f"queries?from={now - 600}&length=5000").get("queries", [])
            clients = {}
            for x in q:
                ip = x.get("client", {}).get("ip")
                if ip in (None, "127.0.0.1", "::1"):
                    continue
                c = clients.setdefault(ip, {"ip": ip, "name": x["client"].get("name") or "",
                                            "count": 0, "blocked": 0})
                c["count"] += 1
                if x.get("status") in ("GRAVITY", "REGEX", "DENYLIST", "EXTERNAL_BLOCKED_IP",
                                       "GRAVITY_CNAME", "REGEX_CNAME", "DENYLIST_CNAME"):
                    c["blocked"] += 1
            wgn = wg_names()
            for c in clients.values():
                c["net"] = "WireGuard" if c["ip"].startswith("10.9.0.") else \
                           "OpenVPN" if c["ip"].startswith("10.8.0.") else "LAN"
                if not c["name"] and c["ip"] in wgn:
                    c["name"] = wgn[c["ip"]]
            services = [{"unit": u, "name": n,
                         "active": sh(["systemctl", "is-active", u]).strip() == "active"}
                        for u, n in SERVICES]
            dk, smart = disks()
            upd, versions = updates()
            up = float(read("/proc/uptime").split()[0])
            ffmpeg = sum(1 for p in glob.glob("/proc/[0-9]*/comm") if read(p).strip() == "ffmpeg")
            data = {
                "pihole": {
                    "total": summ.get("queries", {}).get("total", 0),
                    "blocked": summ.get("queries", {}).get("blocked", 0),
                    "percent": round(summ.get("queries", {}).get("percent_blocked", 0), 1),
                    "cached": summ.get("queries", {}).get("cached", 0),
                    "forwarded": summ.get("queries", {}).get("forwarded", 0),
                    "unique": summ.get("queries", {}).get("unique_domains", 0),
                    "gravity": summ.get("gravity", {}).get("domains_being_blocked", 0),
                    "clients_total": summ.get("clients", {}).get("total", 0),
                    "top": [d for d in top if d.get("domain") != "local.api.ftl"][:7],
                    "top_blocked": topb[:7],
                    "history": [[h["timestamp"], h["total"], h["blocked"]] for h in ph_hist],
                },
                "clients": sorted(clients.values(), key=lambda c: -c["count"]),
                "wg": wireguard(), "services": services, "disks": dk, "smart": smart,
                "updates": upd, "versions": versions, "backup": last_backup(),
                "procs": processes(), "uptime": up, "transcodes": ffmpeg,
                "hostname": os.uname().nodename,
                "cpu_model": next((l.split(":", 1)[1].strip() for l in read("/proc/cpuinfo").splitlines()
                                   if l.startswith("model name")), ""),
                "ips": {"lan": "@@LAN_IP@@", "wan": state["slow"].get("ips", {}).get("wan", "")},
            }
            if now % 600 < 25 or not data["ips"]["wan"]:
                try:
                    data["ips"]["wan"] = urllib.request.urlopen("https://api.ipify.org", timeout=4).read().decode()
                except Exception:
                    pass
            with lock:
                state["slow"] = data
        except Exception as e:
            print("slow_loop:", e, flush=True)
        time.sleep(20)


def meteo_loop():
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,"
           "wind_speed_10m,wind_direction_10m,wind_gusts_10m,pressure_msl"
           "&hourly=precipitation_probability,temperature_2m&forecast_hours=12"
           "&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset&forecast_days=1"
           "&timezone=auto") % (LAT, LON)
    while True:
        try:
            d = json.loads(urllib.request.urlopen(url, timeout=8).read())
            c = d["current"]
            ws, wd = round(c["wind_speed_10m"]), c["wind_direction_10m"]
            i = int(((wd * 100 + 1125) % 36000) // 2250)
            nome = VENTI[i]
            if ws >= 40 and nome in ("Tramontana", "Grecale"):
                nome = "Scorcicapre"
            elif ws >= 40 and nome == "Scirocco":
                nome = "Sciroccone"
            if ws < 2:
                nome = "Calma"
            with lock:
                state["meteo"] = {
                    "temp": c["temperature_2m"], "feels": c["apparent_temperature"],
                    "hum": c["relative_humidity_2m"], "code": c["weather_code"],
                    "pressure": round(c["pressure_msl"]), "wind": ws, "gust": round(c["wind_gusts_10m"]),
                    "dir": wd, "sigla": SIGLE[i], "vento": nome,
                    "rain": list(zip([t[11:16] for t in d["hourly"]["time"]],
                                     d["hourly"]["precipitation_probability"],
                                     d["hourly"]["temperature_2m"])),
                    "tmax": d["daily"]["temperature_2m_max"][0], "tmin": d["daily"]["temperature_2m_min"][0],
                    "sunrise": d["daily"]["sunrise"][0][11:16], "sunset": d["daily"]["sunset"][0][11:16],
                    "ts": int(time.time())}
            time.sleep(600)
        except Exception as e:
            print("meteo_loop:", e, flush=True)
            time.sleep(60)


# ---------------------------------------------------------------- azioni (pulsanti)
ACTIONS = {
    "jellyfin_stop":    (["systemctl", "stop", "jellyfin"], "Jellyfin fermato"),
    "jellyfin_start":   (["systemctl", "start", "jellyfin"], "Jellyfin avviato"),
    "jellyfin_restart": (["systemctl", "restart", "jellyfin"], "Jellyfin riavviato"),
    "backup":           (["/usr/local/bin/backup-server"], "Backup completato"),
    "gravity":          (["pihole", "-g"], "Liste Pi-hole aggiornate"),
}
action_lock = threading.Lock()


def check_password(given):
    real = read(PWFILE).strip()
    return bool(real) and hmac.compare_digest(real.encode(), (given or "").encode())


class Handler(BaseHTTPRequestHandler):
    server_version = "ConsoleAndreaServer"

    def log_message(self, *a):
        pass

    def allowed(self):
        try:
            ip = ipaddress.ip_address(self.client_address[0].replace("::ffff:", ""))
            return any(ip in n for n in ALLOWED)
        except ValueError:
            return False

    def send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.allowed():
            return self.send(403, {"error": "accesso solo da LAN/VPN"})
        if self.path in ("/", "/index.html"):
            return self.send(200, read(os.path.join(HERE, "index.html")), "text/html")
        if self.path == "/api/data":
            with lock:
                d = {"fast": state["fast"], "slow": state["slow"], "meteo": state["meteo"],
                     "hist": {k: list(v) for k, v in hist.items()}, "now": time.time()}
            return self.send(200, d)
        self.send(404, {"error": "non trovato"})

    def do_POST(self):
        if not self.allowed():
            return self.send(403, {"error": "accesso solo da LAN/VPN"})
        if self.path != "/api/action":
            return self.send(404, {"error": "non trovato"})
        try:
            n = min(int(self.headers.get("Content-Length", 0)), 4096)
            req = json.loads(self.rfile.read(n) or "{}")
        except Exception:
            return self.send(400, {"error": "richiesta non valida"})
        if not check_password(self.headers.get("X-Password")):
            time.sleep(1.5)
            return self.send(401, {"error": "password errata"})
        act = ACTIONS.get(req.get("action"))
        if not act:
            return self.send(400, {"error": "azione sconosciuta"})
        if not action_lock.acquire(blocking=False):
            return self.send(409, {"error": "un'altra azione è in corso"})
        try:
            r = subprocess.run(act[0], capture_output=True, text=True, timeout=600)
            ok = r.returncode == 0
            out = re.sub(r"\x1b\[[0-9;]*[A-Za-z]|\[K", "", (r.stdout + r.stderr))[-600:]
            return self.send(200 if ok else 500, {"ok": ok, "message": act[1] if ok else "Errore", "output": out})
        except Exception as e:
            return self.send(500, {"ok": False, "message": "Errore", "output": str(e)})
        finally:
            action_lock.release()


if __name__ == "__main__":
    for fn in (fast_loop, slow_loop, meteo_loop):
        threading.Thread(target=fn, daemon=True).start()
    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
