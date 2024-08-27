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
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3")
options.add_argument("--lang=en-US")
options.add_argument("--timezone=America/New_York")

# Spoof packets
def spoof_packets(interface, src_ip, dst_ip, src_port, dst_port):
    packet = scapy.IP(src=src_ip, dst=dst_ip) / scapy.TCP(sport=src_port, dport=dst_port)
    scapy.send(packet, iface=interface, verbose=False)

# Spoof MAC address needs root perms
def spoof_mac(interface, mac_address):
    subprocess.run(["ip", "link", "set", interface, "address", mac_address])

# Spoof IP address needs root perms
def spoof_ip(interface, ip_address):
    subprocess.run(["ip", "addr", "add", f"{ip_address}/24", "brd", "+", "dev", interface])

# Get the interface name
interface = ni.interfaces()[0]

# Spoof MAC address
spoof_mac(interface, mac_address)

# Spoof IP address
spoof_ip(interface, ip_address)

# Create za Chrome service
service = Service(ChromeDriverManager().install())

# Create a new Chrome driver
driver = webdriver.Chrome(service=service, options=options)

try:
    # Go to Google search
    driver.get("https://www.google.com")

    # Spoof packets at 10 packets per second for 10 seconds
    for i in range(100):
        spoof_packets(interface, ip_address, "8.8.8.8", 1234, 80)
        time.sleep(0.1)  # Send packets at 10 packets per second

finally:
    # Close the browser
    driver.quit()