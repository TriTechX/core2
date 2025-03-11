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
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter
#Third-party
from dotenv import load_dotenv
import psutil
from Crypto.Cipher import AES
#Custom
import colours

load_dotenv()

homeDir = os.getcwd()

INSTALL_FOLDER = "cpm"

if os.path.exists("cpm"):
    pass
else:
    os.mkdir("cpm")

sysDirs = ["sys", "boot", "opt", "root", "bin", "sbin", "lib32", "home",
           "media", "usr", "dev", "tmp", "srv", "libx32", "lib64", "etc", 
           "var", "lib", "proc", "mnt", "run", "cpm"]

sysFiles = [".env", "colours.py", "config.txt", "core.py"]


def clear():
    print("\033c", end="") 

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
shell_ps1 = PS1 + " "
USER = get_or_add_value("USER", getpass.getuser())
UWP = get_value("UWP")
name_colour = get_or_add_value("NAMECOLOUR", "\033[35m")
WELCOME = get_or_add_value("WELCOME", "True")
VERSION = get_or_add_value("VERSION", "0.0.3")
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
        if not connected:
            print(f"{colours.grey()}Offline mode{colours.reset()}")
        print(f"{colours.cyan()}Core{colours.magenta()}2{colours.reset()} Version: {colours.grey()}{VERSION}{colours.reset()}")
        print(f"{colours.cyan()}Date{colours.reset()} and {colours.magenta()}time{colours.reset()}: {current_time}")
        print("------")

#connection test
def check_connection():
    try:
        url = "https://gist.githubusercontent.com/TriTechX/b89f0327f69d518fb71d307e768700a0/raw/216bc948f8e634dd40161b8f44c79e4a555e1447/url.txt"
        content = requests.get(url)

        if content.status_code == 200:
            return True
        else:
            return False
    except:
        return False
    
connected = check_connection()

#cpm
def cpm_install_package(repo_name):
    exists, repo = cpm_locate_package(repo_name)
    
    if not exists:
        try:
            old = os.getcwd()

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
                        package_name = data["package_name"]
                        python = data["python"]

                    dst_folder = f"{homeDir}/cpm/{package_name}"
                    os.makedirs(dst_folder)
                    print("------")
                    for item in os.listdir(os.getcwd()):
                        src_path = os.path.join(os.getcwd(), item)
                        dst_path = os.path.join(dst_folder, item)

                        shutil.move(src_path, dst_path)

                        if os.path.isfile(dst_path):
                            print(f"Extracted: {item} -> {dst_folder}")
                        else:
                            print(f"Extracted: {colours.bold()}{item}{colours.reset()}/ -> {dst_folder}")

                    os.chdir(old)
                    shutil.rmtree(".temp")
                    if python == "True":
                        os.system(f"pip install -r {homeDir}/cpm/{package_name}/{requirements}")

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
                if response.status_code == 404:
                    print(f"{response.status_code}: This repository does not exist.")
                else:
                    print(response.status_code)
        
                return response.status_code
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Package already installed.")
        return None
    
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
        print("------")

        if confirm_response():
            print(f"{colours.red()}Removing '{module_name}'...{colours.reset()}")
            shutil.rmtree(pathName)
            print(f"{colours.green()}'{module_name}' has been removed.{colours.reset()}")
        else:
            print(f"{colours.red()}Action cancelled{colours.reset()}")
        return True
    else:
        print(f"{colours.red()}The module '{module_name}' is not installed.{colours.reset()}")
        return None

def cpm_fix():
    try:
        shutil.rmtree(f"{homeDir}/.temp")
        print("Broken packages cleared.")
    except FileNotFoundError:
        print("You hold no broken packages.")

def cpm_locate_package(packageName):
    installedPackages = os.listdir(f"{homeDir}/cpm")

    if installedPackages:
        for package in installedPackages:
            temp = get_local_meta_value(package, "repo_name")
            if temp == packageName:
                exists = True
                break
            else:
                exists = False
    else:
        exists = False
        temp = None

    return exists, temp

def cpm_purge_all():
    try:
        packageDir = f"{homeDir}/cpm"
        packages = os.listdir(packageDir)

        if packages:
            for item in packages:
                delete_path = os.path.join(packageDir, item)
                print(f"Removed '{delete_path}'")
                shutil.rmtree(delete_path)

            return True
        else:
            print("There were no packages to remove.")
            return False
    except Exception as e:
        print(f"{e}")
        return False

def cpm_scan_packages():
    try:
        old = os.getcwd()
        packageDir = f"{homeDir}/cpm"

        packageList = os.listdir(packageDir)

        if packageList:
            packages = []

            for package in packageList:
                packages.append(get_local_meta_value(package, "repo_name"))

            return packages
        else:
            return False
    except:
        return False

def confirm_response():
    temp = input("(y/n) " + shell_ps1)

    if temp.lower().strip(" ") in ["y", "yes"]:
        return True
    else:
        return False
        
def retrieve_config_values():
    PS1 = get_value("PS1")
    shell_ps1 = PS1 + " "
    UWP = get_value("UWP")
    PASSENC = get_value("PASSENC")
    NAMECOLOUR = get_value("NAMECOLOUR")
    WELCOME = get_value("WELCOME")
    VERSION = get_value("VERSION")
    REGION = get_value("REGION")
    USER = get_value("USER")

    return PS1, shell_ps1, UWP, PASSENC, NAMECOLOUR, WELCOME, VERSION, REGION, USER


def retrieve_messages():
    try:
        url = "https://gist.github.com/TriTechX/2c0c13e83870f52b10d7b7f92277671b/raw"
        message = requests.get(url)
        messageContent = message.content.decode().strip(" ").strip("\n")

        print(messageContent)
    except Exception as e:
        print(f"Error: {e}")

def read_contents(path, highlighted):

    try:
        if path.split(".")[1] == "py":
            python = True
        else:
            python = False
    except:
        python = False

    try:
        f = open(path,"r")
        contents=  f.read().strip("\n")
        f.close()

        if contents == "":
            return "empty"
        else:
            if python and highlighted:
                highlighted_code = highlight(contents, PythonLexer(), TerminalFormatter())
                return highlighted_code
            else:
                return contents
    except:
        return False

def delete(filename, showmessage):
    try:
        if os.path.exists(filename):
            if os.path.isfile(filename):
                os.remove(filename)
            else:
                shutil.rmtree(filename)

            if showmessage == True:
                print(f"Deleted '{filename}' successfully.")
            
            return True
        else:
            if showmessage == True:
                print(f"Path '{filename}' does not exist.")
            return False
    except:
        if showmessage == True:
            print(f"An error occurred removing '{filename}'.")
        return None

show_welcome()
### COMMAND SECTION ###
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

        if confirm_response():
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
    """Changes the directory"""
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
    """Prints the time until interrupted"""
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
    """Converts file sizes to their appropriate prefix alternatives"""
    try:
        power = math.log(bytes, 1024)
        suffixes = ["B", "kB", "MB", "GB", "TB"]

        power = math.floor(power)
        suffix = suffixes[power]

        if power > 0:
            size = round(bytes/1024**power,1)
        else:
            size = bytes
        
        output = str(size) + " " + suffix
    except: #does not have permission
        output = "0 B"

    return output

def dir_size(path):
    """Calculates the size of a directory"""
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
    """Output of the ls command"""
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
        if contents:
            buffer = []
            for item in contents:
                if os.path.isfile(item):
                    size = convert_size(os.path.getsize(item))
                    
                    if item not in sysFiles:
                        buffer.append("🗎 - " + colours.cyan() + item + colours.reset() + f" - {size}")
                    else:
                        buffer.append("🗎 - " + colours.cyan() + colours.greenBg() + item + colours.reset() + f" - {size}")
                else:
                    size = convert_size(dir_size(item))
                    if item not in sysDirs:
                        buffer.append("🗀  - " + colours.bold() + colours.magenta() + item + colours.reset() + f" - {size}")
                    else:
                        buffer.append("🗀  - " + colours.bold() + colours.magenta() + colours.dgreenBg() + item + colours.reset() + f" - {size}")
            output = "\n".join(buffer)
            print(output)
        else:
            print(f"{colours.grey()}This folder is empty.{colours.reset()}")
        print("------")
    except:
        print(f"The directory '{colours.bold()}{hostDir}{colours.reset()}' does not exist.")


def use_pip():
    """pip through the console"""
    if args:
        argsStr = " ".join(args)
        os.system(f"pip {argsStr}")
    else:
        print("USAGE: pip <args> <package>\nInstalls packages for use with Python applications.")

def use_cpm():
    """Core package manager runner"""
    old = os.getcwd()
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
        
        elif args[0] == "purge":

            if len(args) == 1:
                print("This will remove all packages installed with cpm.")
                if confirm_response():
                    cpm_purge_all()
                else:
                    print(f"{colours.red()}Action cancelled.{colours.reset()}")
            else:
                print("USAGE: cpm <args> <package>\nInstalls packages using the Core package manager repository.")
        
        elif args[0] == "list":
            list = cpm_scan_packages()

            if list:
                for item in list:
                    print(item)
            else:
                print("There are no installed packages.")
            
        else:
            print("USAGE: cpm <args> <package>\nInstalls packages using the Core package manager repository.")
    else:
        print("USAGE: cpm <args> <package>\nInstalls packages using the Core package manager repository.")

def read_file():
    print("------")

    if args:
        contentsExists = os.path.exists(args[0])
        if contentsExists:
            if len(args) > 1:
                if args[1].lower() == "h":
                    contents = read_contents(args[0], True)
                else:
                    contents = read_contents(args[0], False)
            else:
                contents = read_contents(args[0], False)


            if contents:
                print(contents)
            else:
                print("File does not exist.")
        else:
            print("File does not exist.")
        
    else:
        print("Which file do you want to read?")
        list_directory()

        valid = False

        while not valid:
            filename = input(shell_ps1)

            if os.path.exists(filename):
                contents = read_contents(filename)
                print(contents)
                valid = True
            else:
                print("File does not exist.")
    print("------")

def remove_file():
    if args:
        delete(args[0], True)
    else:
        print("Which file do you want to delete?")
        list_directory()

        valid = False

        while not valid:
            filename = input(shell_ps1)

            if not os.path.exists(filename):
                print("Path does not exist.")
            else:
                valid = True

        delete(filename, True)

def create_file():
    if args:
        filename = args[0].strip()
    else:
        filename = input(f"What should the new file be called?\n{shell_ps1}").strip()

    if filename in os.listdir():
        print(f"File '{filename}' already exists.")
        return

    # Check if filename has an extension
    if "." in filename and filename.rsplit(".", 1)[1]:  # Ensures there's an extension after "."
        newFilename = filename
    else:
        newFilename = filename + ".txt"

    if newFilename in os.listdir():
        print(f"File '{newFilename}' already exists.")
    else:
        open(newFilename, "w").close()
        print(f"File '{newFilename}' created successfully.")

def core_help():
    buffer = []
    buffer.append(f"{colours.bold()}------{colours.reset()}")
    buffer.append(f"{colours.bold()}{colours.italics()}Terminal commands{colours.reset()}:")
    buffer.append(f"{colours.bold()}------{colours.reset()}")
    buffer.append(f"welcome - toggle the welcome message.")
    buffer.append("---")
    buffer.append(f"clear - clears the terminal.")
    buffer.append("---")
    buffer.append("clock - display the current time until cancelled.")
    buffer.append("---")
    buffer.append("message - buffer.append the message from the developer.")
    buffer.append("---")
    buffer.append(f"{colours.bold()}sys{colours.reset()} - interact with your system's terminal")
    buffer.append("---")
    buffer.append(f"{colours.grey()}quit{colours.reset()} - quit Core2")
    buffer.append(f"{colours.bold()}------{colours.reset()}")
    buffer.append(f"{colours.bold()}{colours.italics()}{colours.red()}User management{colours.reset()}:")
    buffer.append("---")
    buffer.append(f"{colours.red()}chpass{colours.reset()} - changes the user password, creates if it doesn't exist.")
    buffer.append("---")
    buffer.append(f"{colours.red()}rmpass{colours.reset()} - remove the user password.")
    buffer.append(f"{colours.bold()}------{colours.reset()}")
    buffer.append(f"{colours.green()}{colours.bold()}{colours.italics()}Directory management{colours.reset()}:")
    buffer.append("---")
    buffer.append(f"{colours.green()}cd <dir>{colours.reset()} - changes the current working directory.")
    buffer.append("---")
    buffer.append(f"{colours.green()}ls <dir>{colours.reset()} - list the directory.")
    buffer.append(f"{colours.bold()}------{colours.reset()}")
    buffer.append(f"{colours.bold()}{colours.italics()}{colours.cyan()}Package management{colours.reset()}:")
    buffer.append("---")
    buffer.append(f"{colours.yellow()}pip{colours.reset()} - use Python's package manager, works as expected.")
    buffer.append("---")
    buffer.append(f"{colours.cyan()}cpm <arg> <packageName>{colours.reset()} - use Core2's package manager.")
    buffer.append(f"{colours.bold()}------{colours.reset()}")
    buffer.append(f"{colours.orange()}{colours.bold()}{colours.italics()}File management{colours.reset()}:")
    buffer.append("---")
    buffer.append(f"{colours.orange()}read <h>{colours.reset()} - read a file.")
    buffer.append("---")
    buffer.append(f"{colours.orange()}rm <file>{colours.reset()} - delete a file.")
    buffer.append("---")
    buffer.append(f"{colours.orange()}make <file>{colours.reset()} - make a file.")
    buffer.append(f"{colours.bold()}------{colours.reset()}")


    print("\n".join(buffer))

def manual():
    manual = {
        "clear":"This command clears the screen. Alternatives include 'cls', 'cl', and 'c'.",
        "chpass":"This command is used to change the user password, or create a new one if it does not exist. This command does not take arguments, but does ask for parameters, and is therefore not a smart command.",
        "rmpass":"This command removes the current user password if it exists.",
        "welcome":"This command is a boolean command that toggles the opening welcome message at the top of the screen upon clearing and starting up.",
        "cd":"This command can be used to change the current working directory of the terminal. This command is a smart command.",
        "quit":"This command quits Core2 and returns you back to your original environment. 'exit' may also be used.",
        "clock":"This command is rather janky and needs some fixing, but it prints the current time to your screen until cancelled with [CTRL]+[C].",
        "ls":"This command lists the contents of a directory. This command is a smart command.",
        "pip":"This command interacts with the terminal Core2 is running within to use pip, Python's module/package manager.",
        "cpm":"This is Core2's package manager.\n------\nValid arguments include:\n  install - install a cpm package\n  uninstall/remove - delete a cpm package\n  purge - remove ALL installed cpm packages\n  meta - get the meta.json contents for a cpm package\n  fix - remove any temporary or broken cpm packages\n---\n'cpm install corebench' - installs the corebench module, and can be executed through the terminal by typing 'corebench'\n'cpm uninstall corebench' - removes the package from the environment. Can be reinstalled again.\n'cpm meta totked' - gets the contents of the meta file for 'totked'\n------",
        "read":"This command extracts the raw contents of a file and prints them to the screen. Recommended for use with text and code files. Add the argument 'h' to the end of the command to prind the contents of a file with Python syntax highlighting.\n---\nexample: 'read core.py h'\n------",
        "rm":"This command deletes a file from a given path. This command is a smart command.",
        "make":"This command makes a file. If no file extension is provided, it will default to '.txt'. This command is a smart command.",
        "man":"Haha. Very funny. You typed 'man man' in the terminal because you thought it would break. It's not that complicated anymore. What's funny is that this doesn't use any importlib or bin folder with functions. It just sits in a dictionary. I gave up. It was too jank."
    }

    manualCommands = manual.keys()

    if args:
        commandName = args[0]
        if commandName in manualCommands:
            print(manual[commandName])
        else:
            print(f"Command '{args[0]}' does not exist.")
    else:
        valid = False

        print("Which command do you want the manual for?")
        while not valid:
            commandName = input(shell_ps1)

            if commandName in manualCommands:
                print(manual[commandName])
                valid = True
            else:
                print(f"Command '{commandName}' does not exist.")
                valid = False

def use_nano():
    os.system(f"nano {" ".join(args)}")

def use_system():
    os.system(f"{" ".join(args)}")

commands = {
    "clear": clear_terminal,
    "cls": clear_terminal,
    "cl": clear_terminal,
    "c": clear_terminal,

    "chpass": change_password,
    "rmpass": remove_password,

    "welcome": toggle_welcome_message,

    "cd": change_directory,

    "quit": sys.exit,
    "exit": sys.exit,

    "clock": clock,

    "ls": list_directory,
    "dir": list_directory,

    "pip": use_pip,

    "cpm": use_cpm,

    "message":retrieve_messages,

    "read":read_file,
    "rm":remove_file, #takes argument 'h' to return highlighted syntax

    "make":create_file,

    "help":core_help,
    "man":manual,

    "nano":use_nano,
    "sys":use_system,

}

while True:
    connected = check_connection()

    args = None

    PS1, shell_ps1, UWP, PASSENC, NAMECOLOUR, temp, VERSION, REGION, USER = retrieve_config_values()

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
        
    else: #look for externals
        try:
            old = os.getcwd()
            externals = os.listdir(f"{homeDir}/cpm")
            if commandcap in externals:
                execPath = f"{homeDir}/cpm/{commandcap}"
                mainLocation = get_local_meta_value(commandcap, "main")
                
                try:
                    externalPath = f"{execPath}/{mainLocation.split("/")[0]}"
                    os.chdir(externalPath)
                    subprocess.run(["chmod", "+x", mainLocation.split("/")[1]])
                    subprocess.run([f"./{mainLocation.split("/")[1]}"])
                except KeyboardInterrupt:
                    print(f"{colours.red()}Action cancelled{colours.reset()}")
            else:
                print("Command not installed.")
        except Exception as e:
            print(str(e))
            pass #command not found
