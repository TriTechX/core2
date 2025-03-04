#Builtin
import os
import sys
import subprocess
import multiprocessing
import shutil
import getpass
import base64
import sys
from datetime import datetime
import time
import select
import math
import requests
import zipfile
import io
import json
#Third-party
from dotenv import load_dotenv
import psutil
from Crypto.Cipher import AES
#Custom
import colours

load_dotenv()

homeDir = os.getcwd()

INSTALL_FOLDER = "cpm"

sysDirs = ["sys", "boot", "opt", "root", "bin", "sbin", "lib32", "home",
           "media", "usr", "dev", "tmp", "srv", "libx32", "lib64", "etc", 
           "var", "lib", "proc", "mnt", "run"]


def clear():
    print("\033[H\033[J", end="")

#Config functions
def get_value(value):
    old = os.getcwd()
    os.chdir(homeDir)
    """Retrieve a value safely from the config file."""
    if os.path.exists("config.txt"):
        with open("config.txt", "r") as f:
            contents = f.readlines()

        for line in contents:
            prefix = line.split(":")[0].strip()
            if value in prefix:
                return line.split(":")[1].strip()

    os.chdir(old)
    return None

def add_value(value_name, value):
    old = os.getcwd()
    os.chdir(homeDir)
    """Add a value safely to the config file."""
    with open("config.txt", "a") as f:
        f.write(f"\n{value_name}: {value}")
    
    os.chdir(old)

def get_or_add_value(value_name, default_value):
    old = os.getcwd()
    os.chdir(homeDir)
    """Retrieve a value from the config, or add it if missing."""
    value = get_value(value_name)
    if not value:
        add_value(value_name, default_value)
    os.chdir(old)
    return get_value(value_name)

def reset_value(value_name, value):
    old = os.getcwd()
    os.chdir(homeDir)
    """Reset the value in the config file."""
    exists = get_value(value_name)
    if exists:
        with open("config.txt", "r") as f:
            lines = f.readlines()

        with open("config.txt", "w") as f:
            for line in lines:
                if value_name not in line:
                    f.write(line)
                else:
                    f.write(f"{value_name}: {value}\n")
        os.chdir(old)
    else:
        os.chdir(old)
        return None

#Configurations
PS1 = get_or_add_value("PS1", "~ €")
USER = get_or_add_value("USER", getpass.getuser())
UWP = get_value("UWP")
name_colour = get_or_add_value("NAMECOLOUR", "\033[35m")
WELCOME = get_or_add_value("WELCOME", "True")
VERSION = get_or_add_value("VERSION", "0.0.1")
REGION = get_or_add_value("REGION", "US")

#Encryption and passwords
def get_secret_key():
    """Retrieve or generate the secret key for encryption."""
    key = os.getenv("CORE_KEY")
    if key:
        return base64.b64decode(key)
    else:
        new_key = os.urandom(32)
        encoded_key = base64.b64encode(new_key).decode()
        with open(".env", "a") as f:
            f.write(f"CORE_KEY={encoded_key}\n")
        return new_key

SECRET_KEY = get_secret_key()

def encrypt(data):
    """Encrypt data using AES encryption."""
    cipher = AES.new(SECRET_KEY, AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode())
    return base64.b64encode(cipher.nonce + tag + ciphertext).decode()

def decrypt(data):
    """Decrypt data using AES encryption."""
    raw = base64.b64decode(data)
    nonce, tag, ciphertext = raw[:16], raw[16:32], raw[32:]
    cipher = AES.new(SECRET_KEY, AES.MODE_EAX, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode()

clear()

#Password decryption and validation
if UWP == "True":
    PASSDEC = decrypt(get_value("PASSENC"))
    print("A password is set up for this user.")
    print("------")

    valid = False
    while not valid:
        attempt = getpass.getpass(PS1 + " ")
        if attempt == PASSDEC:
            valid = True
            clear()
        else:
            print("Incorrect.")
else:
    pass

#Show welcome message
def show_welcome():
    """Display the welcome message."""
    if WELCOME == "True":
        if REGION == "GB":
            current_time = datetime.now().strftime("%d/%m/%Y %H:%M")
        else:
            current_time = datetime.now().strftime("%m/%d/%Y %H:%M")
        print(f"Hello, {name_colour}{USER}{colours.reset()}!")
        print("------")
        print(f"Core 2 Version: v{VERSION}")
        print(f"Date and time: {current_time}")
        print("------")

def cpm_install_package(repo_name):
    old = os.getcwd()

    dst_folder = f"{homeDir}/cpm/{repo_name}"
    os.makedirs(dst_folder)

    url = f"https://github.com/TriTechX/{repo_name}/archive/refs/heads/main.zip"
    response = requests.get(url)

    if response.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(".temp")

        os.chdir(f".temp/{repo_name}-main")

        contents = os.listdir(os.getcwd())

        if "meta.json" in contents:
            with open("meta.json", "r") as f:
                data = json.load(f)

                requirements = data["requirements"]
                linuxRequirements = data["linuxrequirements"]
            print(os.getcwd())
            for item in os.listdir(os.getcwd()):
                src_path = os.path.join(os.getcwd(), item)
                dst_path = os.path.join(dst_folder, item)

                shutil.move(src_path, dst_path)
                
            os.chdir(old)
            shutil.rmtree(".temp")

            os.system(f"pip install -r {homeDir}/cpm/{repo_name}/{requirements}")

            if linuxRequirements:
                os.system("sudo apt update")
                for item in linuxRequirements:
                    os.system(f"sudo apt install {item} -y")
            print("------")
            print(f"{colours.green()}Package '{repo_name}' installed successfully!{colours.reset()}")     
            print("------")
            return True
        else:
            os.chdir(old)
            return None
    else:
        os.chdir(old)
        return response.status_code

def cpm_get_meta(repo_name):
    try:
        url = f"https://raw.githubusercontent.com/TriTechX/{repo_name}/main/meta.json"
        response = requests.get(url)

        if response.status_code == 200:
            return response.text
        else:
            return response.status_code
    except:
        return response.status_code
    
def get_local_meta_value(module_name, value):

    with open(f"{homeDir}/cpm/{module_name}/meta.json", "r") as f:
        data = json.load(f)

    if data:
        return data[value]
    else:
        return None

def cpm_uninstall_package(module_name):
    print("Checking paths...")
    old = os.getcwd()
    
    pathName = f"{homeDir}/cpm/{module_name}"

    if os.path.exists(pathName):
        print("------")
        print(f"'{module_name}' will be uninstalled.")

        temp = input(shell_ps1)

        if temp.lower() in ["y", "yes"]:
            print(f"{colours.red()}Removing '{module_name}'...{colours.reset()}")
            shutil.rmtree(pathName)
            print(f"{colours.green()}'{module_name}' has been removed.{colours.reset()}")
        return True
    else:
        print(f"{colours.red()}The module '{module_name}' is not installed.{colours.reset()}")
        return None

def cpm_fix():
    shutil.rmtree(f"{homeDir}/.temp")
    print("Broken packages cleared.")
        
show_welcome()

shell_ps1 = PS1 + " "

commands = {
    "clear": lambda: clear_terminal(),
    "cls": lambda: clear_terminal(),
    "cl": lambda: clear_terminal(),
    "c": lambda: clear_terminal(),
    "chpass": lambda: change_password(),
    "rmpass": lambda: remove_password(),
    "welcome": lambda: toggle_welcome_message(),
    "cd": lambda: change_directory(),
    "quit": lambda: sys.exit(),
    "exit": lambda: sys.exit(),
    "clock": lambda: clock(),
    "ls": lambda: list_directory(),
    "dir": lambda: list_directory(),
    "pip": lambda: use_pip(),
    "cpm": lambda: use_cpm()
}

def clear_terminal():
    clear()
    show_welcome()

def change_password():
    """Change the user's password."""
    print("Please type your new password:")
    print("------")
    new_pass = input(shell_ps1)
    reset_value("PASSENC", encrypt(new_pass))
    reset_value("UWP", "True")
    print("Password set successfully.")

def remove_password():
    """Remove the user's password."""
    if UWP == "True":
        print(f"Are you sure you want to remove the password?")

        temp = input(shell_ps1)
        if temp.lower().strip() in ["y", "yes"]:
            reset_value("PASSENC", "None")
            reset_value("UWP", "False")
            print("Password deactivated.")
        else:
            print("Action cancelled.")
    else:
        print("The user has no password.")

def toggle_welcome_message():
    """Toggle the welcome message setting."""
    if WELCOME == "True":
        reset_value("WELCOME", "False")
        print("Welcome message disabled.")
    else:
        reset_value("WELCOME", "True")
        print("Welcome message enabled.")

def change_directory():
    if not args:
        print("Please type the name of the directory.")
        temp = input(shell_ps1)
    else:
        temp = args[0]
    if os.path.exists(temp):
        os.chdir(temp)
    else:
        print(f"The directory '{colours.bold()}{temp}{colours.reset()}' does not exist.")

def clock():
    while True:
        current_time = datetime.now().strftime("%H:%M:%S")
        sys.stdout.write(f'\r{current_time}')
        sys.stdout.flush()

        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            clear()

        time.sleep(1)

        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            clear()

def convert_size(bytes):
    try:
        power = math.log(bytes, 1024)
        suffixes = ["B", "kB", "MB", "GB", "TB"]

        power = math.floor(power)
        suffix = suffixes[power]

        if power > 0:
            size = round(bytes/1024*power,1)
        else:
            size = bytes
        
        output = str(size) + " " + suffix
    except: #does not have permission
        output = "0 B"

    return output

def dir_size(path):
    try:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if not os.path.islink(filepath):
                    total_size += os.path.getsize(filepath)
    except: #does not have permission
        total_size = 0

    return total_size


def list_directory():
    try:
        if args:
            hostDir = args[0]
        else:
            hostDir = os.getcwd()
        contents = os.listdir(hostDir)
        print("------")

        if hostDir == "/":
            hostDirName = "/"
        elif hostDir == ".":
            hostDir = os.getcwd()
            hostDirName = hostDir.split("/")[-1]
        else:
            hostDirName = hostDir.split("/")[-1]
        

        print(f"🗀  Directory: '{colours.green()}{colours.bold()}{hostDirName}{colours.reset()}'")
        print("------")
        buffer = []
        for item in contents:
            if os.path.isfile(item):
                size = convert_size(os.path.getsize(item))
                buffer.append("🗎 - " + colours.cyan() + item + colours.reset() + f" - {size}")
            else:
                size = convert_size(dir_size(item))
                if item not in sysDirs:
                    buffer.append("🗀  - " + colours.bold() + colours.magenta() + item + colours.reset() + f" - {size}")
                else:
                    buffer.append("🗀  - " + colours.bold() + colours.magenta() + colours.dgreenBg() + item + colours.reset() + f" - {size}")
        output = "\n".join(buffer)
        print(output)
        print("------")
    except:
        print(f"The directory '{colours.bold()}{hostDir}{colours.reset()}' does not exist.")


def use_pip():
    if args:
        argsStr = " ".join(args)
        os.system(f"pip {argsStr}")
    else:
        print("USAGE: pip <args> <package>\nInstalls packages for use with Python applications.")

def use_cpm():
    if args:
        if args[0] == "install":
            if len(args) > 1:
                cpm_install_package(args[1]) 
            else:
                print("USAGE: cpm <args> <package>\nInstalls packages using the Core package manager repository.")
        
        elif args[0] == "uninstall" or args[0] == "remove":
            if len(args) > 1:
                cpm_uninstall_package(args[1])
            else:
                print("USAGE: cpm <args> <package>\nInstalls packages using the Core package manager repository.")
        
        elif args[0] == "meta":
            if len(args) > 1:
                try:
                    print(cpm_get_meta(args[1]).strip("\n"))
                except:
                    print("Request failed.")
            else:
                print("USAGE: cpm <args> <package>\nInstalls packages using the Core package manager repository.")
        
        elif args[0] == "fix":
            cpm_fix()
        else:
            print("USAGE: cpm <args> <package>\nInstalls packages using the Core package manager repository.")
    else:
        print("USAGE: cpm <args> <package>\nInstalls packages using the Core package manager repository.")

while True:
    args = None

    WELCOME = get_or_add_value("WELCOME", "True")
    cwd = os.getcwd()
    temp = input(colours.bold() + colours.cyan() + cwd + " " + colours.reset() + shell_ps1)
    commandList = temp.strip().split(" ")
    commandcap = commandList[0]
    command = commandList[0].lower()
    args = commandList[1:len(commandList)]

    if command in commands:
        try:
            oldDir = cwd
            commands[command]()
        except KeyboardInterrupt:
            os.chdir(oldDir)
            print(f"\n{colours.red()}Action cancelled.{colours.reset()}")
        
    else:
        try:
            old = os.getcwd()
            externals = os.listdir(f"{homeDir}/cpm")
            if commandcap in externals:
                execPath = f"{homeDir}/cpm/{commandcap}"
                mainLocation = get_local_meta_value(commandcap, "main")
                
                try:
                    externalPath = f"{execPath}/{mainLocation.split("/")[0]}"
                    os.chdir(externalPath)
                    print(os.getcwd())
                    print(os.listdir())
                    subprocess.run(["chmod", "+x", mainLocation.split("/")[1]])
                    subprocess.run([f"./{mainLocation.split("/")[1]}"])
                except KeyboardInterrupt:
                    print(f"{colours.red()}Action cancelled{colours.reset()}")
        except Exception as e:
            print(str(e))
            pass #command not found
