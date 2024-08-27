import os
import uuid
import netifaces as ni
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging
import requests
import random
import json
import scapy.all as scapy
import argparse
import time
from pyvirtualdisplay import Display
from stem import Signal
from stem.control import Controller
import socket

# Set up logging
logging.basicConfig(level=logging.INFO)

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--interface", help="Network interface to use")
parser.add_argument("--proxy-country", help="Country code for proxy")
args = parser.parse_args()

# Load configuration from file
config = {}
with open("config.json", "r") as f:
    config = json.load(f)

# Set up Chrome options
options = Options()

# Spoof MAC address
mac_address = ":".join(["%02x" % random.randint(0, 255) for _ in range(6)])
options.add_argument(f"--mac-address={mac_address}")

# Spoof IP address
ip_address = ".".join([str(random.randint(0, 255)) for _ in range(4)])
options.add_argument(f"--ip-address={ip_address}")

# Spoof za DPI
options.add_argument("--force-device-scale-factor=1.5")  # Set DPI to 120
options.add_argument("--high-dpi-support=1")

# Set up proxy thingy
proxy_url = f"https://proxylist.org/api/proxy?country={args.proxy_country}&anonymity=elite&ssl=yes"
response = requests.get(proxy_url)

# Check if the response is valid JSON
if response.status_code == 200:
    try:
        proxy_data = response.json()
        proxy_ip = proxy_data["data"][0]["ip"]
        proxy_port = proxy_data["data"][0]["port"]
        options.add_argument(f"--proxy-server=http://{proxy_ip}:{proxy_port}")
    except json.JSONDecodeError:
        logging.error("Failed to parse JSON response from proxylist.org")
        proxy_ip = "127.0.0.1"
        proxy_port = "8080"
        options.add_argument(f"--proxy-server=http://{proxy_ip}:{proxy_port}")
else:
    logging.error("Failed to get proxy list from proxylist.org")
    proxy_ip = "127.0.0.1"
    proxy_port = "8080"
    options.add_argument(f"--proxy-server=http://{proxy_ip}:{proxy_port}")

# Set up user agent and other Stuffs
options.add_argument(f"--user-agent={config['user_agent']}")
options.add_argument(f"--lang={config['lang']}")
options.add_argument(f"--timezone={config['timezone']}")

# Advanced proxy system using Tor
def get_tor_proxy():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate()
        controller.signal(Signal.NEWNYM)
        socks_proxy = "socks5://127.0.0.1:9050"
        return socks_proxy

tor_proxy = get_tor_proxy()
options.add_argument(f"--proxy-server={tor_proxy}")

# Headless browser using PyVirtualDisplay
display = Display(visible=0, size=(1024, 768))
display.start()

# Create a new Chrome driver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Anti-detection techniques
def anti_detection_techniques():
    # Disable Chrome's built-in anti-bot measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--enable-automation")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")

    # Randomize browser window size and position
    window_size = (random.randint(800, 1920), random.randint(600, 1080))
    window_position = (random.randint(0, 100), random.randint(0, 100))
    driver.set_window_size(*window_size)
    driver.set_window_position(*window_position)

    # Randomize browser zoom level
    zoom_level = random.uniform(0.5, 1.5)
    driver.execute_script(f"document.body.style.zoom = '{zoom_level}'")

anti_detection_techniques()

# Spoof packets
def spoof_packets(interface, src_ip, dst_ip, src_port, dst_port):
    packet = scapy.IP(src=src_ip, dst=dst_ip) / scapy.TCP(sport=src_port, dport=dst_port)
    scapy.send(packet, iface=interface, verbose=False)

# Spoof MAC address needs root perms
def spoof_mac(interface, mac_address):
    subprocess.run(["ip", "link", "set", interface, "address", mac_address])
# Get network interface
interface = args.interface
if not interface:
    interface = ni.gateways()['default'][ni.AF_INET][1]

# Spoof MAC address
spoof_mac(interface, mac_address)

# Start the browser
driver.get("https://example.com")

# Perform some actions on the website
driver.find_element_by_name("q").send_keys("Hello, World!")
driver.find_element_by_name("q").submit()

# Wait for 10 seconds
time.sleep(10)

# Spoof packets every 10 seconds
while True:
    spoof_packets(interface, "192.168.1.100", "8.8.8.8", 1234, 5678)
    time.sleep(10)

# Close the browser
driver.quit()

# Stop the display
display.stop()
