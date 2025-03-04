import json
import os
from pathlib import Path

# Constants
ARCHISO_PATH = Path("./archiso")
AIROOTFS_PATH = ARCHISO_PATH / "airootfs"
CONFIG_PATH = Path("./distro/config.json")
RES_PATH = Path("./res")
SYS_LINUX_PATH = ARCHISO_PATH / "syslinux"
EFI_BOOT_PATH = ARCHISO_PATH / "efiboot/loader/entries"

class Utility:
    """Utility functions for file handling and execution."""
    @staticmethod
    def read_file(file_path: Path) -> str:
        with open(file_path, 'r') as f:
            return f.read()

    @staticmethod
    def read_json(file_path: Path) -> dict[str, object]:
        with open(file_path, 'r') as f:
            return json.load(f)

    @staticmethod
    def write_file(file_path: Path, content: str) -> None:
        with open(file_path, 'w') as f:
            f.write(content)

class ExecutablesManager:
    """Handles making files executable within the ISO."""
    executables: list[str] = []

    @staticmethod
    def make_executable(file_path: Path) -> None:
        os.chmod(file_path, 0o755)
        ExecutablesManager.executables.append(str(file_path.relative_to(AIROOTFS_PATH)))
        print(f' * Made executable {file_path}')

def log(start_msg: str = "", end_msg: str = ""):
    """Decorator to log function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if start_msg:
                print(start_msg)
            result = func(*args, **kwargs)
            if end_msg:
                print(end_msg, '\n')
            return result
        return wrapper
    return decorator

class Config:
    """Manages generating configuration files."""
    @staticmethod
    def generate_template(file_path: Path, data: dict[str, object]) -> str:
        content = Utility.read_file(file_path)
        for key, value in data.items():
            content = content.replace(f'{{{key}}}', str(value))
        return content

    @staticmethod
    def get_os_release(data: dict[str, object]) -> str:
        return Config.generate_template(RES_PATH / "os-release", data)

    @staticmethod
    def get_profile_def(data: dict[str, object]) -> str:
        data["id-upper"] = data["id"].upper()
        profile_content = Config.generate_template(RES_PATH / "profiledef.sh", data)
        profile_content += '\n' + '\n'.join(f'  ["{exe}"]="0:0:755"' for exe in ExecutablesManager.executables)
        return profile_content

class Builder:
    """Handles system building tasks."""
    def __init__(self, config: dict[str, object]):
        self.config = config

    @log("Copying releng files")
    def copy_releng(self):
        os.system(f'cp -r /usr/share/archiso/configs/releng {ARCHISO_PATH}')

    @log("Adding packages to live ISO")
    def add_packages(self, packages: list[str]):
        Utility.write_file(ARCHISO_PATH / "packages.x86_64", '\n'.join(packages))

    @log("Rebranding distro")
    def rebrand_distro(self):
        self.add_os_release()
        self.replace_names(SYS_LINUX_PATH)
        self.replace_names(EFI_BOOT_PATH)

    def replace_names(self, directory: Path):
        for file in directory.iterdir():
            if file.name != "splash.png":
                self.replace_name(file)

    def replace_name(self, file_path: Path):
        try:
            content = Utility.read_file(file_path).replace("Arch Linux", self.config["name"])
            Utility.write_file(file_path, content)
            print(f' * Rebranded {file_path}')
        except Exception as e:
            print(f' - Failed to rebrand {file_path}: {e}')

    @log("Setting hostname")
    def set_hostname(self):
        Utility.write_file(AIROOTFS_PATH / "etc/hostname", self.config["liveiso_hostname"])

    @log('Adding ./distro/home to root home')
    def setup_distro_home(self):
        os.makedirs(AIROOTFS_PATH / "root", exist_ok=True)
        os.system(f'cp -r ./distro/home/* {AIROOTFS_PATH / "root"}')
        
        installer_path = (AIROOTFS_PATH / "root/installer")
        if installer_path.exists():
            ExecutablesManager.make_executable(installer_path)

    @log('Adding ./res/home to root home')
    def setup_res_home(self):
        os.makedirs(AIROOTFS_PATH / "root/.config", exist_ok=True)
        os.system(f'cp -r ./res/home/* {AIROOTFS_PATH / "root"}')

        ExecutablesManager.make_executable(AIROOTFS_PATH / "root/.xinitrc")
        ExecutablesManager.make_executable(AIROOTFS_PATH / "root/.zshrc")
        ExecutablesManager.make_executable(AIROOTFS_PATH / "root/.config/i3/config")

    @log("Setting up home directory")
    def setup_home(self):
        self.setup_distro_home()
        self.setup_res_home()

    @log("Adding OS release")
    def add_os_release(self):
        Utility.write_file(AIROOTFS_PATH / "etc/os-release", Config.get_os_release(self.config))

    @log("Adding profile definition")
    def add_profile_def(self):
        Utility.write_file(AIROOTFS_PATH / "root/.profiledef", Config.get_profile_def(self.config))

    @log("====\nBUILDING BASE\n====", "====\nBASE BUILT\n====")
    def build(self, packages: list[str]):
        self.copy_releng()
        self.add_packages(packages)
        self.rebrand_distro()
        self.set_hostname()
        self.setup_home()
        self.add_profile_def()
        print("\nISO is ready with i3 X11 environment, launching installer on boot.\n")

if __name__ == "__main__":
    config_data = Utility.read_json(CONFIG_PATH)
    packages_list = [
        "xorg-server", "xorg-xinit", "xorg-xrandr", "xorg-xsetroot", "xorg-xbacklight", "xorg-xinput", "xterm",
        "i3", "i3status", "dmenu", "lightdm", "lightdm-gtk-greeter", *config_data['packages']
    ]

    builder = Builder(config_data)
    builder.build(packages_list)
