#!/usr/bin/env python3

import argparse
import json
import logging
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import time

import distro as pydistro

from app.helper import helper
from app.pretty import pretty

with open("config.json", "r", encoding="utf-8") as config_file:
    defaults = json.load(config_file)

parser = argparse.ArgumentParser()
parser.add_argument(
    "-d", "--debug", help="Enables debugging mode", default=False, action="store_true"
)
parser.add_argument(
    "-s", "--ssh", help="Runs git in SSH mode", default=False, action="store_true"
)

logging.basicConfig(
    filename="installer.log",
    filemode="w",
    format="[+] Crafty Installer: %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

args = parser.parse_args()

if args.debug:
    defaults["debug_mode"] = True
if defaults["debug_mode"]:
    logger.setLevel(logging.DEBUG)
    pretty.info("Debug mode turned on")
    logger.info("Debug mode turned on")

if args.ssh:
    defaults["clone_method"] = "ssh"
    pretty.info("Git will try to clone using SSH")
    logger.info("Git will try to clone using SSH")


# our pretty header
def do_header():
    time.sleep(2)

    if not defaults["debug_mode"]:
        helper.clear_screen()

    msg = "-" * 25
    msg += "# \t \t Crafty Controller 4.0 Linux Installer \t \t #"
    msg += "-" * 25
    msg += "\n \t\t\t This program will install Crafty Controller 4.0 on your Linux Machine"
    msg += "\n \t\t\t This program isn't perfect, but it will do it's best to get you up and running"

    msg += "\n"
    pretty.header(msg)


# here we can define other distro shell scripts for even better support
def do_distro_install(target_distro):
    real_dir = os.path.abspath(os.curdir)

    pretty.warning(
        "This install could take a long time depending on how old your system is."
    )
    pretty.warning(
        "Please be patient and do not exit the installer otherwise things may break"
    )

    pretty.info("We are updating python3 and pip")
    script = os.path.join(real_dir, "app", target_distro)

    logger.info("Running %s}", script)

    try:
        # Going to ensure our script has full permissions.
        os.chmod(script, 0o0775)
        p = subprocess.Popen(script, stdout=subprocess.PIPE)
        while True:
            line = p.stdout.readline()
            if not line:
                break
            sys.stdout.write(line.decode("utf-8"))
        rc = p.poll()
        if rc != 0:
            raise RuntimeError(f"script exited with code {rc}")

    except Exception as e:
        pretty.critical(f"Error installing dependencies: {e}")
        logger.exception("Error installing dependencies: %s", exc_info=e)
        sys.exit(1)


# creates the venv and clones the git repo
def setup_repo(target_directory: pathlib.Path):
    do_header()

    # create new virtual environment
    pretty.info("Creating New Virtual Environment")

    venv_dir = pathlib.Path(target_directory, ".venv")

    # changing to install dir
    os.chdir(target_directory)
    pretty.info(f"Jumping into install directory: {os.path.abspath(os.curdir)}")
    logger.info("Changed directory to: %s", os.path.abspath(os.curdir))

    # creating venv
    try:
        subprocess.check_output([sys.executable, "-m", "venv", venv_dir], text=True)
    except subprocess.CalledProcessError as e:
        pretty.critical(
            "Unable to create virtual environment - venv creation failed (see log)"
        )
        logger.critical(
            "venv subprocess returned abnormally with code %i and output:\n%s",
            e.returncode,
            e.output,
        )
        helper.cleanup_bad_install(target_directory)
        sys.exit(1)
    except Exception as e:
        pretty.critical(f"Unable to create virtual environment - {e}")
        logger.exception("Unable to create virtual environment!", exc_info=e)
        helper.cleanup_bad_install(target_directory)
        sys.exit(1)

    clone_method = defaults["clone_method"]

    # cloning the repo
    pretty.info("Cloning the Git Repo...this could take a few moments")
    if clone_method == "ssh":
        clone_repo_ssh(target_directory)
    else:
        clone_repo_https(target_directory)


def confirm_ssh_key_location(key_location, tries=0):
    pretty.info(f"Attempts: {tries}")
    if key_location is None:
        key_location = helper.get_user_open_input(
            "Unable to detect ssh key - Please input the full path to your ssh key, or 'https' to fallback to https"
        )

    if key_location == "https" or tries > 2:
        pretty.info("Falling back to https")
        return "https"

    if not helper.check_file_exists(key_location):
        pretty.warning("The specified key does not exist!")
        return confirm_ssh_key_location(None, tries + 1)

    key_confirm = helper.get_user_valid_input(
        f"SSH key selected from {key_location}. Would you like to use this key?",
        ["y", "n"],
    )

    if key_confirm == "y":
        return key_location
    else:
        key_location = helper.get_user_open_input(
            "Please specify the full path of the ssh key you wish to use"
        )
        return confirm_ssh_key_location(key_location, tries + 1)


def clone_repo_ssh(target_directory: pathlib.Path):
    invoking_user = os.getenv("SUDO_USER", "root")
    user_ssh_dir = f"/home/{invoking_user}/.ssh/"
    if helper.check_file_exists(user_ssh_dir + "id_ed25519"):
        ssh_key_loc = confirm_ssh_key_location(user_ssh_dir + "id_ed25519")
    elif helper.check_file_exists(user_ssh_dir + "id_rsa"):
        ssh_key_loc = confirm_ssh_key_location(user_ssh_dir + "id_rsa")
    else:
        ssh_key_loc = confirm_ssh_key_location(None)

    if ssh_key_loc == "https":
        return clone_repo_https(target_directory)

    try:
        embed_ssh_command = "ssh -i '{ssh_key_loc}'"
        subprocess.check_output(
            [
                "git",
                "clone",
                "git@gitlab.com:crafty-controller/crafty-4.git",
                "--config",
                f'core.sshCommand="{embed_ssh_command}"',
            ],
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.critical(
            "git clone returned abnormally with code %i and output:\n%s",
            e.returncode,
            e.output,
        )
        logger.critical("Git clone failed! Did you specify the correct key?")
        pretty.critical("Failed to clone. Falling back to HTTPS.")
        clone_repo_https(target_directory)
    except Exception as e:
        logger.exception("Error: %s", exc_info=e)
        helper.cleanup_bad_install(target_directory)
        sys.exit(1)


def clone_repo_https(target_directory: pathlib.Path):
    try:
        subprocess.check_output(
            ["git", "clone", "https://gitlab.com/crafty-controller/crafty-4.git"]
        )
    except Exception as e:
        logger.critical("Git clone failed!")
        logger.exception("Error:", exc_info=e)
        pretty.critical("Unable to clone. Please check the install.log for details!")
        pretty.warning("Cleaning up partial install and exiting...")
        helper.cleanup_bad_install(target_directory)
        sys.exit(1)


# this switches to the branch chosen and does the pip install and such
def do_virt_dir_install(
    starting_directory: pathlib.Path, target_directory: pathlib.Path
):
    do_header()

    # choose your destiny
    pretty.info("Choose your destiny:")
    pretty.info("Crafty comes in different branches:")
    pretty.info("Master - Kinda Stable, a few bugs present")
    pretty.info("Dev - Highly Unstable, full of bugs and new features")

    # unattended
    if not defaults["unattended"]:
        branch = helper.get_user_valid_input(
            "Which branch of Crafty would you like to run?", ["master", "dev"]
        )

    else:
        branch = defaults["branch"]

    crafty_directory = pathlib.Path(target_directory, "crafty-4").resolve()
    # changing to git repo dir
    pretty.info(f"Jumping into repo directory: {crafty_directory}")
    logger.info("Changed directory to: %s", crafty_directory)
    os.chdir(crafty_directory)

    logger.info("User choose %s branch", branch)

    # branch selection
    if branch == "master":
        pretty.info("Slow and Stable it is")

    elif branch == "dev":
        pretty.info("Way to saddle up cowboy!")

    # create a quick script / execute pip install
    do_pip_install(branch, starting_directory, target_directory)


# installs pip requirements via shell script
def do_pip_install(
    branch: str, starting_directory: pathlib.Path, target_directory: pathlib.Path
):
    os.chmod(pathlib.Path(starting_directory, "app", "pip_install_req.sh"), 0o0775)
    pip_install_script_src = pathlib.Path(
        starting_directory, "app", "pip_install_req.sh"
    )
    pip_install_script_dst = pathlib.Path(target_directory, "pip_install_req.sh")

    logger.info("Copying PIP install script")
    shutil.copyfile(pip_install_script_src, pip_install_script_dst)

    pip_command = [pip_install_script_dst, target_directory, branch]

    logger.info("Ensuring exec on file %s", pip_install_script_dst)
    helper.chmod_add_exec(pip_install_script_dst)

    logger.info("Running Pip: %s", pip_command)
    pretty.warning(
        "We are now going to install all the python modules for Crafty - This process can take awhile "
        "depending on your internet connection"
    )

    time.sleep(3)

    try:
        p = subprocess.Popen(pip_command, stdout=subprocess.PIPE)
        while True:
            line = p.stdout.readline()
            if not line:
                break
            sys.stdout.write(line.decode("utf-8"))
        rc = p.poll()
        if rc != 0:
            raise RuntimeError(f"abnormal exit code {rc}")

    except Exception as e:
        logger.error("Pip failed due to error: %s", e)
        sys.exit(1)

    if not defaults["debug_mode"]:
        os.remove(pip_install_script_dst)


# Creates the run_crafty.sh
def make_startup_script(target_directory: pathlib.Path):
    os.chdir(target_directory)
    logger.info("Changing to %s", os.path.abspath(os.curdir))

    txt = "#!/bin/bash\n"
    txt += f"cd {target_directory}\n"
    txt += "source .venv/bin/activate \n"
    txt += "cd crafty-4 \n"
    txt += f"exec python{sys.version_info.major} main.py \n"
    with open("run_crafty.sh", "w", encoding="utf-8") as run_crafty_sh_file:
        run_crafty_sh_file.write(txt)
        run_crafty_sh_file.close()
    helper.chmod_add_exec(pathlib.Path("run_crafty.sh"))


# Creates the update_crafty.sh
def make_update_script(target_directory: pathlib.Path):
    os.chdir(target_directory)
    logger.info("Changing to %s", os.path.abspath(os.curdir))

    txt = "#!/bin/bash\n"
    txt += f"cd {target_directory}\n"
    txt += "source .venv/bin/activate \n"
    txt += "cd crafty-4 \n"
    txt += "\n"
    txt += "if [[ -v 1 ]]; then\n"
    txt += '    yn="$1"\n'
    txt += "fi\n"
    txt += "\n"
    txt += "while true; do\n"
    txt += "    if [[ ! -v yn ]]; then\n"
    txt += "        read -p 'Can we overwrite any local codebase changes? (Y/N)' yn\n"
    txt += "    fi\n"
    txt += "    \n"
    txt += "    case $yn in\n"
    txt += "        [yY] | -y )\n"
    txt += "            git reset --hard origin/master\n"
    txt += "            break;;\n"
    txt += "        [nN] | -n )\n"
    txt += "            break;;\n"
    txt += "        * )\n"
    txt += "            unset yn\n"
    txt += "            echo 'Please use Y or N to reply.';;\n"
    txt += "    esac\n"
    txt += "done\n"
    txt += "\n"
    txt += "git pull \n"
    txt += "python3 -m ensurepip --upgrade \n"
    txt += "pip3 install --upgrade pip --no-cache-dir\n"
    txt += "pip3 install -r requirements.txt --no-cache-dir \n"
    with open("update_crafty.sh", "w", encoding="utf-8") as update_crafty_sh_file:
        update_crafty_sh_file.write(txt)
        update_crafty_sh_file.close()

    helper.chmod_add_exec(pathlib.Path("update_crafty.sh"))


# Creates the run as a service.sh
def make_service_script(target_directory: pathlib.Path):
    os.chdir(target_directory)
    logger.info("Changing to %s", os.path.abspath(os.curdir))

    txt = "#!/bin/bash\n"
    txt += f"cd {target_directory}\n"
    txt += "source .venv/bin/activate \n"
    txt += "cd crafty-4 \n"
    txt += f"python{sys.version_info.major} main.py -d\n"
    with open(
        "run_crafty_service.sh", "w", encoding="utf-8"
    ) as run_crafty_service_file:
        run_crafty_service_file.write(txt)
        run_crafty_service_file.close()

    helper.chmod_add_exec(pathlib.Path("run_crafty_service.sh"))


def make_service_file(target_directory: pathlib.Path):
    os.chdir(target_directory)
    logger.info("Changing to %s", os.path.abspath(os.curdir))
    txt = f"""
[Unit]
Description=Crafty 4
After=network.target

[Service]
Type=simple

User=crafty
WorkingDirectory={target_directory}

ExecStart=/usr/bin/bash {target_directory}/run_crafty_service.sh

Restart=on-failure
# Other restart options: always, on-abort, etc

# The install section is needed to use
# `systemctl enable` to start on boot
# For a user service that you want to enable
# and start automatically, use `default.target`
# For system level services, use `multi-user.target`
[Install]
WantedBy=multi-user.target
"""

    with open("crafty.service", "w", encoding="utf-8") as crafty_service_file:
        crafty_service_file.write(txt)
        crafty_service_file.close()

    shutil.copy2(
        pathlib.Path(target_directory, "crafty.service"), "/etc/systemd/system/"
    )


# get distro
def get_distro():
    distro_id = pydistro.id()
    version = pydistro.version()
    with open("linux_versions.json", "r", encoding="utf-8") as linux_versions_file:
        linux_versions = json.load(linux_versions_file)
    sys.stdout.write(f"We detected your os is: {distro_id} - Version: {version}\n")

    distro_file = None

    if distro_id == "arch" or distro_id == "archarm" or distro_id == "manjaro":
        logger.info("%s version %s Dectected", distro_id, version)
        return "arch.sh"

    current_distro = distro_id
    user_version = str(version).replace(".", "_")
    if current_distro not in linux_versions:
        # Panic on Distro
        distros = linux_versions.keys()
        logger.critical("Unsupported Distro - We only support %s", distros)
        return
    if version not in linux_versions[current_distro]["versions"]:
        # Panic on Distro Version
        versions = linux_versions[current_distro]["versions"]
        logger.critical(
            "Unsupported Version - We only support %s, %s", current_distro, versions
        )
        return

    logger.info("%s %s Detected!", current_distro, user_version)

    if helper.check_file_exists(
        os.path.join("app", f"{current_distro}_{user_version}.sh")
    ):
        distro_file = f"{current_distro}_{user_version}.sh"
    elif helper.check_file_exists(os.path.join("app", f"{current_distro}.sh")):
        distro_file = f"{current_distro}.sh"
    if distro_file is None:
        logger.critical(
            "Unable to determine distro: ID:%s - Version:%s", distro_id, version
        )
        logger.debug("File is: %s", distro_file)
    return distro_file


if __name__ == "__main__":
    logger.info("Installer Started")

    starting_dir = pathlib.Path(os.path.curdir).resolve()
    temp_dir = pathlib.Path(starting_dir, "temp")

    do_header()

    # are we on linux?
    if platform.system() != "Linux":
        pretty.critical("This script requires Linux")
        logger.critical("This script requires Linux")
        sys.exit(1)

    pretty.info("Linux Check Success")
    pretty.info(
        f"Python Version Check - {sys.version_info.major}.{sys.version_info.minor}"
    )

    user_distro = get_distro()
    if not user_distro:
        pretty.critical("Your distro is not supported.")
        logger.critical("Unable to find distro information")
        sys.exit(1)

    # default py_check
    py_check = False

    # are we at least on 3.8?
    if not (sys.version_info.major == 3 and sys.version_info.minor >= 9):
        pretty.critical("This script requires Python 3.9 or higher!")
        pretty.critical(
            f"You are using Python {sys.version_info.major}.{sys.version_info.minor}."
        )
        logger.critical(
            "Python Version < 3.9: %i.%i was found",
            sys.version_info.major,
            sys.version_info.minor,
        )
        time.sleep(1)
        pretty.warning(
            "Your python version didn't check out - do you want us to fix this for you?"
        )
    else:
        py_check = True

    # unattended
    if not defaults["unattended"]:
        install_requirements = helper.get_user_valid_input(
            f"Install {user_distro} requirements?", ["y", "n"]
        )
    else:
        install_requirements = "y"

    if install_requirements == "y":
        pretty.info(
            f"Installing required packages for {user_distro} - Please enter sudo password when prompted"
        )
        do_distro_install(user_distro)
    else:
        if not py_check:
            pretty.critical("This script requires Python 3.9 or higher!")
            helper.cleanup_bad_install()
            sys.exit(1)

    do_header()

    # do we want to install to default dir?
    pretty.info(
        f"Crafty's Default install directory is set to: {defaults['install_dir']}"
    )

    # unattended
    if not defaults["unattended"]:
        install_use_default = helper.get_user_yesno(
            f"Install Crafty to this directory? {defaults['install_dir']}"
        )
    else:
        install_use_default = True

    do_header()

    if not install_use_default:
        install_dir = pathlib.Path(
            helper.get_user_open_input("Where would you like Crafty to install to?")
        ).resolve()
    else:
        install_dir = pathlib.Path(defaults["install_dir"]).resolve()

    pretty.info(f"Installing Crafty to {install_dir}")
    logger.info("Installing Crafty to %s", install_dir)

    # does the install directory exist?
    if not install_dir.is_dir():
        logger.debug("Installation directory %s does not yet exist", install_dir)
        try:
            install_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
            shutil.chown(install_dir, user="crafty", group="crafty")
        except OSError as e:
            logger.critical(
                "Unable to create install directory %s with error %s", install_dir, e
            )
            pretty.critical(
                "Unable to create install directory {install_dir}. Terminating program"
            )
            if os.geteuid() != 0:
                logger.critical(
                    "This action likely require root/sudo - elevating this script may solve the above issue"
                )
                pretty.critical(
                    "This action likely require root/sudo - elevating this script may solve the above issue"
                )
            sys.exit(1)

    logger.debug("Checking if installation directory has correct ownership")
    install_dir_stat = install_dir.stat()
    logger.debug(
        "Installation directory has ownership of %s:%s with mode %s (expected crafty:crafty 0755)",
        install_dir.owner(),
        install_dir.group(),
        oct(install_dir_stat.st_mode),
    )
    if not (
        install_dir.owner() == "crafty"
        and install_dir.group() == "crafty"
        and (install_dir_stat.st_mode & 0o777) == 0o755
    ):
        logger.debug("Installation directory did not match ownership/mode check")
        if helper.get_user_yesno(
            "Installation directory has an unexpected user, group, or mode - should we attempt to fix this?"
        ):
            shutil.chown(install_dir, user="crafty", group="crafty")
            install_dir.chmod(0o755)

    # is this a fresh install?
    files = os.listdir(install_dir)

    time.sleep(1)

    do_header()

    logger.info("Looking for old crafty install in: %s", install_dir)

    if len(files) > 0:
        logger.warning("Old Crafty install detected: %s", install_dir)
        pretty.warning(
            "Old Crafty Install Detected. Please move all files out of the install"
            + " directory and run this script again."
        )

        time.sleep(10)
        sys.exit()

    setup_repo(install_dir)

    do_virt_dir_install(starting_dir, install_dir)

    do_header()

    logger.info("Creating Shell Scripts")
    pretty.info("Making start and update scripts for you")

    make_startup_script(install_dir)
    make_update_script(install_dir)

    if not defaults["unattended"]:
        service_answer = helper.get_user_yesno(
            "Would you like to make a service file for Crafty?"
        )
        if service_answer:
            make_service_script(install_dir)
            make_service_file(install_dir)
    else:
        make_service_script(install_dir)
        make_service_file(install_dir)

    # fixing permission issues
    logger.info("Fixing ownership issues on %s", install_dir)
    for installed_file in install_dir.glob("**"):
        logger.debug("Changing ownership of %s", installed_file)
        shutil.chown(installed_file, user="crafty", group="crafty")

    time.sleep(1)
    do_header()

    pretty.info("Cleaning up temp dir")
    helper.ensure_dir_exists(temp_dir)

    if not defaults["debug_mode"]:
        shutil.rmtree(temp_dir)

    pretty.info("Congrats! Crafty is now installed!")
    pretty.info(
        "We created a user called 'crafty' for you to run crafty as. (DO NOT RUN CRAFTY WITH ROOT OR SUDO) Switch to crafty user with 'sudo su crafty -'"
    )
    pretty.info(f"Your install is located here: {install_dir}")
    pretty.info(
        f"You can run crafty by running {os.path.join(install_dir, 'run_crafty.sh')}"
    )
    pretty.info(
        f"You can update crafty by running {os.path.join(install_dir, 'update_crafty.sh')}"
    )
    if service_answer:
        pretty.info(
            "A service unit file has been saved in /etc/systemd/system/crafty.service"
        )
        pretty.info(
            "run this command to enable crafty as a service- 'sudo systemctl enable crafty.service' "
        )
        pretty.info(
            "run this command to start the crafty service- 'sudo systemctl start crafty.service' "
        )
