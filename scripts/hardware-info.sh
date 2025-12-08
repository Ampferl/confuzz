#!/bin/bash

GREEN='\033[0;32m'
RESET='\033[0m'

echo -e "${GREEN}==========================================${RESET}"
echo -e "${GREEN}          Hardware-Informationen          ${RESET}"
echo -e "${GREEN}==========================================${RESET}"

echo -e "\n[Operating System]"
if [ -f /etc/os-release ]; then
    grep -E '^(PRETTY_NAME)' /etc/os-release | cut -d'"' -f2
else
    echo "OS-Release file not found."
fi
echo "Kernel: $(uname -r)"

# 2. CPU Informationen
echo -e "\n[CPU]"
lscpu | grep -E "Model name|Socket\(s\)|Core\(s\) per socket|Thread\(s\) per core"

# 3. System Memory
echo -e "\n[RAM (System Memory)]"
free -h | grep "Mem:" | awk '{print "Total: " $2, "| Used: " $3, "| Free: " $4}'

# 4. GPU Informationen
echo -e "\n[GPU (NVIDIA)]"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,driver_version,pstate --format=csv,noheader

    echo -e "\n[CUDA Version]"
    nvidia-smi | grep "CUDA Version" | awk '{print $8 $9}'
else
    echo "Keine NVIDIA GPU gefunden oder 'nvidia-smi' ist nicht installiert."
    echo "Versuche lspci:"
    lspci | grep -i vga
fi

# 5. Storage
echo -e "\n[Storage (Root Partition)]"
df -h / | awk 'NR==2 {print "Total: " $2, "| Avail: " $4}'

echo -e "\n${GREEN}==========================================${RESET}"