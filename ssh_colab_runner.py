"""
SSH COLAB RUNNER
================
Automated, non-interactive execution of training scripts on Google Colab T4 GPU
via Cloudflare tunnel proxy using Paramiko.
"""

import sys
import os
import argparse
import paramiko

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def run_ssh_task(hostname: str, password: str, command: str = None):
    print("=" * 65)
    print(f"🚀 CONNECTING TO COLAB GPU VIA CLOUDFLARE TUNNEL")
    print(f"Target Host : {hostname}")
    print(f"Proxy Client: C:/Users/msjan/cloudflared.exe")
    print("=" * 65)

    proxy_cmd = f"C:/Users/msjan/cloudflared.exe access ssh --hostname {hostname}"
    
    try:
        sock = paramiko.ProxyCommand(proxy_cmd)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print("Authenticating with root credentials...")
        client.connect(
            hostname=hostname,
            username="root",
            password=password,
            sock=sock,
            timeout=30,
            banner_timeout=30
        )
        print("✅ SSH Connection Established to Google Colab GPU Environment!\n")

        default_training_cmd = (
            "nvidia-smi && "
            "if [ -d 'vlm-testing' ]; then cd vlm-testing && git pull; else git clone --depth 1 https://github.com/Janakiram-2005/vlm-testing.git && cd vlm-testing; fi && "
            "pip install -q transformers==4.48.3 accelerate==1.3.0 peft==0.14.0 'bitsandbytes>=0.50.0' qwen-vl-utils==0.0.8 sentencepiece tiktoken psutil huggingface-hub>=0.28.0 && "
            "python train_qwen2_vl_lora.py --epochs 3 --batch_size 2 --grad_accum 4 --lr 2e-4"
        )

        exec_cmd = command if command else default_training_cmd
        print(f"[EXECUTING REMOTE TASK]:\n{exec_cmd}\n")
        print("-" * 65)

        stdin, stdout, stderr = client.exec_command(exec_cmd, get_pty=True)

        for line in iter(stdout.readline, ""):
            sys.stdout.write(line)
            sys.stdout.flush()

        exit_status = stdout.channel.recv_exit_status()
        print("-" * 65)
        print(f"\n[REMOTE TASK COMPLETED] Exit Code: {exit_status}")
        client.close()
        return exit_status
    except Exception as e:
        print(f"\n❌ Connection Error: {e}")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger training on Colab via SSH")
    parser.add_argument("--host", type=str, required=True, help="Cloudflare trycloudflare.com hostname")
    parser.add_argument("--password", type=str, required=True, help="Password set in launch_ssh_cloudflared")
    parser.add_argument("--cmd", type=str, default=None, help="Custom bash command to execute")
    args = parser.parse_args()

    sys.exit(run_ssh_task(args.host, args.password, args.cmd))
