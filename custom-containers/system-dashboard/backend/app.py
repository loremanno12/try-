from flask import Flask, jsonify
from flask_cors import CORS
import psutil
import docker
import requests
import os
import time
import subprocess
from datetime import datetime
from collections import deque

app = Flask(__name__)
CORS(app)

# Configurazione Pi-hole
PIHOLE_URL = os.getenv('PIHOLE_URL', 'http://localhost:80')
PIHOLE_API_KEY = os.getenv('PIHOLE_API_KEY', '')

# Client Docker
docker_client = None
try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"Docker non disponibile: {e}")

# Storico per grafici (mantiene gli ultimi 60 valori)
history_size = 60
cpu_history = deque(maxlen=history_size)
memory_history = deque(maxlen=history_size)
network_rx_history = deque(maxlen=history_size)
network_tx_history = deque(maxlen=history_size)
temp_history = deque(maxlen=history_size)

# Ultimo valore di rete per calcolare il rate
last_network = None


def get_cpu_temperature():
    """Ottiene la temperatura CPU del Raspberry Pi"""
    try:
        # Prova vcgencmd (metodo ufficiale Raspberry Pi)
        result = subprocess.run(
            ['vcgencmd', 'measure_temp'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            temp_str = result.stdout.strip()
            temp = float(temp_str.replace('temp=', '').replace("'C", ''))
            return temp
    except Exception:
        pass

    # Fallback: leggi da /sys
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = int(f.read().strip()) / 1000.0
            return temp
    except Exception:
        pass

    return None


def get_pi_throttling_status():
    """Ottiene lo stato di throttling del Raspberry Pi"""
    try:
        result = subprocess.run(
            ['vcgencmd', 'get_throttled'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            hex_value = result.stdout.strip().split('=')[1]
            value = int(hex_value, 16)

            # Estrai flag bits
            return {
                'raw': hex_value,
                'undervoltage': bool(value & 0x1),
                'freq_capped': bool(value & 0x2),
                'throttled': bool(value & 0x4),
                'soft_temp_limited': bool(value & 0x8),
                'undervoltage_occurred': bool(value & 0x10000),
                'freq_capped_occurred': bool(value & 0x20000),
                'throttled_occurred': bool(value & 0x40000),
                'soft_temp_occurred': bool(value & 0x80000),
            }
    except Exception:
        pass

    return None


def get_pi_voltage():
    """Ottiene i voltaggi del Raspberry Pi"""
    voltages = {}
    try:
        for label in ['core', 'sdram_c', 'sdram_i', 'sdram_p']:
            result = subprocess.run(
                ['vcgencmd', 'measure_volts', label],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                volts = result.stdout.strip().replace('volt=', '').replace('V', '')
                voltages[label] = float(volts)
    except Exception:
        pass

    return voltages if voltages else None


def get_pi_clock():
    """Ottiene le frequenze del clock del Raspberry Pi"""
    clocks = {}
    try:
        for domain in ['arm', 'core', 'h264', 'isp', 'v3d', 'uart', 'pwm', 'emmc', 'pixel', 'hdmi']:
            result = subprocess.run(
                ['vcgencmd', 'measure_clock', domain],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                freq = result.stdout.strip().split('=')[1]
                clocks[domain] = int(freq)
    except Exception:
        pass

    return clocks if clocks else None


def get_network_rate():
    """Calcola il rate di rete (bytes/sec)"""
    global last_network

    net_io = psutil.net_io_counters()
    current = {
        'bytes_sent': net_io.bytes_sent,
        'bytes_recv': net_io.bytes_recv,
        'timestamp': time.time()
    }

    if last_network is None:
        last_network = current
        return {'rx_rate': 0, 'tx_rate': 0}

    time_delta = current['timestamp'] - last_network['timestamp']
    if time_delta > 0:
        rx_rate = (current['bytes_recv'] - last_network['bytes_recv']) / time_delta
        tx_rate = (current['bytes_sent'] - last_network['bytes_sent']) / time_delta
    else:
        rx_rate, tx_rate = 0, 0

    last_network = current
    return {'rx_rate': rx_rate, 'tx_rate': tx_rate}


def format_bytes(bytes_value):
    """Formatta bytes in unità leggibili"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint per verificare lo stato del server"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.1.0',
        'device': 'Raspberry Pi 5'
    })


@app.route('/api/cpu', methods=['GET'])
def cpu_usage():
    """Endpoint per statistiche CPU con storico"""
    cpu_percent = psutil.cpu_percent(interval=0.5, percpu=False)
    cpu_percent_per_core = psutil.cpu_percent(interval=0.5, percpu=True)
    cpu_freq = psutil.cpu_freq()

    # Aggiungi allo storico
    timestamp = datetime.now().isoformat()
    cpu_history.append({'time': timestamp, 'value': cpu_percent, 'timestamp': time.time()})

    return jsonify({
        'overall': cpu_percent,
        'per_core': cpu_percent_per_core,
        'core_count': psutil.cpu_count(),
        'physical_cores': psutil.cpu_count(logical=False),
        'frequency': {
            'current': cpu_freq.current if cpu_freq else 0,
            'min': cpu_freq.min if cpu_freq else 0,
            'max': cpu_freq.max if cpu_freq else 0
        },
        'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
        'history': list(cpu_history)
    })


@app.route('/api/memory', methods=['GET'])
def memory_usage():
    """Endpoint per statistiche RAM con storico"""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Aggiungi allo storico
    timestamp = datetime.now().isoformat()
    memory_history.append({
        'time': timestamp,
        'value': mem.percent,
        'used': mem.used,
        'available': mem.available,
        'timestamp': time.time()
    })

    return jsonify({
        'ram': {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'percent': mem.percent,
            'total_formatted': format_bytes(mem.total),
            'used_formatted': format_bytes(mem.used),
            'available_formatted': format_bytes(mem.available),
            'free': mem.free
        },
        'swap': {
            'total': swap.total,
            'used': swap.used,
            'free': swap.free,
            'percent': swap.percent,
            'total_formatted': format_bytes(swap.total),
            'used_formatted': format_bytes(swap.used)
        },
        'history': list(memory_history)
    })


@app.route('/api/pi', methods=['GET'])
def pi_stats():
    """Endpoint specifico per statistiche Raspberry Pi"""
    temp = get_cpu_temperature()
    throttling = get_pi_throttling_status()
    voltage = get_pi_voltage()
    clocks = get_pi_clock()
    cpu_freq = psutil.cpu_freq()

    # Aggiungi temperatura allo storico
    if temp is not None:
        temp_history.append({
            'time': datetime.now().isoformat(),
            'value': temp,
            'timestamp': time.time()
        })

    return jsonify({
        'temperature': {
            'value': temp,
            'unit': '°C',
            'warning_threshold': 80,
            'critical_threshold': 85,
            'history': list(temp_history)
        },
        'throttling': throttling,
        'voltage': voltage,
        'clock': {
            'arm': clocks.get('arm') if clocks else None,
            'core': clocks.get('core') if clocks else None,
            'arm_formatted': f"{clocks.get('arm', 0) / 1_000_000:.2f} GHz" if clocks and clocks.get('arm') else None,
            'core_formatted': f"{clocks.get('core', 0) / 1_000_000:.2f} GHz" if clocks and clocks.get('core') else None
        },
        'cpu_frequency': {
            'current': cpu_freq.current if cpu_freq else 0,
            'min': cpu_freq.min if cpu_freq else 0,
            'max': cpu_freq.max if cpu_freq else 0,
            'current_mhz': cpu_freq.current if cpu_freq else 0,
            'max_ghz': f"{cpu_freq.max / 1000:.2f} GHz" if cpu_freq and cpu_freq.max else None
        },
        'model': {
            'detected': True,
            'type': 'Raspberry Pi 5'
        }
    })


@app.route('/api/network', methods=['GET'])
def network_usage():
    """Endpoint per statistiche di rete con rate"""
    net = psutil.net_io_counters()
    rate = get_network_rate()

    # Aggiungi allo storico
    timestamp = datetime.now().isoformat()
    network_rx_history.append({
        'time': timestamp,
        'value': rate['rx_rate'],
        'timestamp': time.time()
    })
    network_tx_history.append({
        'time': timestamp,
        'value': rate['tx_rate'],
        'timestamp': time.time()
    })

    return jsonify({
        'current': {
            'bytes_sent': net.bytes_sent,
            'bytes_recv': net.bytes_recv,
            'packets_sent': net.packets_sent,
            'packets_recv': net.packets_recv,
            'errin': net.errin,
            'errout': net.errout,
            'dropin': net.dropin,
            'dropout': net.dropout
        },
        'rate': {
            'rx_rate': rate['rx_rate'],
            'tx_rate': rate['tx_rate'],
            'rx_rate_formatted': format_bytes(rate['rx_rate']) + '/s',
            'tx_rate_formatted': format_bytes(rate['tx_rate']) + '/s'
        },
        'formatted': {
            'bytes_sent': format_bytes(net.bytes_sent),
            'bytes_recv': format_bytes(net.bytes_recv)
        },
        'history': {
            'rx': list(network_rx_history),
            'tx': list(network_tx_history)
        }
    })


@app.route('/api/disk', methods=['GET'])
def disk_usage():
    """Endpoint per statistiche disco"""
    partitions = psutil.disk_partitions()
    disks = []

    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disks.append({
                'device': partition.device,
                'mountpoint': partition.mountpoint,
                'fstype': partition.fstype,
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent,
                'total_formatted': format_bytes(usage.total),
                'used_formatted': format_bytes(usage.used),
                'free_formatted': format_bytes(usage.free)
            })
        except PermissionError:
            continue
        except Exception:
            continue

    # Aggiungi statistiche I/O disco se disponibili
    disk_io = None
    try:
        io = psutil.disk_io_counters()
        if io:
            disk_io = {
                'read_count': io.read_count,
                'write_count': io.write_count,
                'read_bytes': io.read_bytes,
                'write_bytes': io.write_bytes,
                'read_bytes_formatted': format_bytes(io.read_bytes),
                'write_bytes_formatted': format_bytes(io.write_bytes)
            }
    except Exception:
        pass

    return jsonify({
        'disks': disks,
        'io_stats': disk_io
    })


@app.route('/api/docker/containers', methods=['GET'])
def docker_containers():
    """Endpoint per container Docker"""
    if not docker_client:
        return jsonify({
            'available': False,
            'error': 'Docker non disponibile',
            'containers': []
        })

    try:
        containers = docker_client.containers.list(all=True)
        container_list = []

        for container in containers:
            container_info = container.attrs
            container_list.append({
                'id': container.short_id,
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else container.image.short_id,
                'created': container_info.get('Created', ''),
                'ports': container.ports,
                'state': container_info.get('State', {})
            })

        return jsonify({
            'available': True,
            'count': len(container_list),
            'containers': container_list
        })
    except Exception as e:
        return jsonify({
            'available': False,
            'error': str(e),
            'containers': []
        })


@app.route('/api/docker/stats', methods=['GET'])
def docker_stats():
    """Endpoint per statistiche Docker in tempo reale"""
    if not docker_client:
        return jsonify({
            'available': False,
            'error': 'Docker non disponibile',
            'stats': []
        })

    try:
        containers = docker_client.containers.list()
        stats_list = []

        for container in containers:
            try:
                stats = container.stats(stream=False)
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                num_cpus = stats['cpu_stats'].get('online_cpus', 1)
                cpu_percent = (cpu_delta / system_delta * num_cpus * 100.0) if system_delta > 0 else 0

                mem_usage = stats['memory_stats'].get('usage', 0)
                mem_limit = stats['memory_stats'].get('limit', 1)
                mem_percent = (mem_usage / mem_limit * 100.0) if mem_limit > 0 else 0

                # Calcola I/O blocco
                block_stats = stats.get('blkio_stats', {}).get('io_service_bytes_recursive', [])
                block_read = block_stats[0].get('value', 0) if len(block_stats) > 0 else 0
                block_write = block_stats[1].get('value', 0) if len(block_stats) > 1 else 0

                stats_list.append({
                    'id': container.short_id,
                    'name': container.name,
                    'status': container.status,
                    'cpu_percent': round(cpu_percent, 2),
                    'memory_usage': mem_usage,
                    'memory_limit': mem_limit,
                    'memory_percent': round(mem_percent, 2),
                    'memory_usage_formatted': format_bytes(mem_usage),
                    'network_rx': stats.get('networks', {}).get('eth0', {}).get('rx_bytes', 0),
                    'network_tx': stats.get('networks', {}).get('eth0', {}).get('tx_bytes', 0),
                    'block_read': block_read,
                    'block_write': block_write,
                    'block_read_formatted': format_bytes(block_read),
                    'block_write_formatted': format_bytes(block_write)
                })
            except Exception:
                continue

        return jsonify({
            'available': True,
            'count': len(stats_list),
            'stats': stats_list
        })
    except Exception as e:
        return jsonify({
            'available': False,
            'error': str(e),
            'stats': []
        })


@app.route('/api/pihole', methods=['GET'])
def pihole_stats():
    """Endpoint per statistiche Pi-hole"""
    try:
        url = f"{PIHOLE_URL}/admin/api.php"
        params = {}
        if PIHOLE_API_KEY:
            params['auth'] = PIHOLE_API_KEY

        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'available': True,
                'connected': True,
                'data': {
                    'domains_being_blocked': data.get('domains_being_blocked', 0),
                    'dns_queries_today': data.get('dns_queries_today', 0),
                    'ads_blocked_today': data.get('ads_blocked_today', 0),
                    'ads_percentage_today': data.get('ads_percentage_today', 0),
                    'unique_domains': data.get('unique_domains', 0),
                    'forwarded': data.get('queries_forwarded', 0),
                    'cached': data.get('queries_cached', 0),
                    'status': data.get('status', 'unknown')
                }
            })
        else:
            return jsonify({
                'available': True,
                'connected': False,
                'error': f'HTTP {response.status_code}'
            })
    except requests.exceptions.ConnectionError:
        return jsonify({
            'available': True,
            'connected': False,
            'error': 'Connessione rifiutata'
        })
    except requests.exceptions.Timeout:
        return jsonify({
            'available': True,
            'connected': False,
            'error': 'Timeout connessione'
        })
    except Exception as e:
        return jsonify({
            'available': False,
            'connected': False,
            'error': str(e)
        })


@app.route('/api/system', methods=['GET'])
def system_info():
    """Endpoint per informazioni generali di sistema"""
    boot_time = psutil.boot_time()
    uptime = time.time() - boot_time

    return jsonify({
        'platform': {
            'system': os.uname().sysname,
            'node': os.uname().nodename,
            'release': os.uname().release,
            'version': os.uname().version,
            'machine': os.uname().machine
        },
        'boot_time': datetime.fromtimestamp(boot_time).isoformat(),
        'uptime_seconds': int(uptime),
        'uptime_formatted': f"{int(uptime // 86400)}d {int((uptime % 86400) // 3600)}h {int((uptime % 3600) // 60)}m",
        'device': 'Raspberry Pi 5'
    })


@app.route('/api/all', methods=['GET'])
def all_stats():
    """Endpoint aggregato per tutti i dati di sistema"""
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'cpu': cpu_usage().get_json(),
        'memory': memory_usage().get_json(),
        'pi': pi_stats().get_json(),
        'network': network_usage().get_json(),
        'disk': disk_usage().get_json(),
        'docker': docker_containers().get_json(),
        'docker_stats': docker_stats().get_json(),
        'pihole': pihole_stats().get_json(),
        'system': system_info().get_json()
    })


if __name__ == '__main__':
    print("=" * 60)
    print("  System Dashboard API - Raspberry Pi 5 Optimized")
    print("=" * 60)
    print(f"  CPU Cores: {psutil.cpu_count()} ({psutil.cpu_count(logical=False)} physical)")
    print(f"  RAM Total: {format_bytes(psutil.virtual_memory().total)}")
    print(f"  CPU Temp: {get_cpu_temperature()}°C" if get_cpu_temperature() else "  CPU Temp: N/A")
    print(f"  Docker: {'Disponibile' if docker_client else 'Non disponibile'}")
    print("=" * 60)
    print("  Server avviato su http://0.0.0.0:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
