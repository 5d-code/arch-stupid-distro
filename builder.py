import json
import os

executables = []

def logruns(logmsg: str = None, endmsg: str = None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if logmsg: print(logmsg)
            x = func(*args, **kwargs)
            if endmsg: print(endmsg, '\n')
            return x
        return wrapper
    return decorator

def make_executable(fn: str):
    os.chmod(fn, 0o755)
    executables.append(fn.removesuffix('./archiso/airootfs'))
    print(' * made executable', fn)

def load_file(fn: str) -> str:
    with open(fn, 'r') as f:
        return f.read()

def load_json(fn: str) -> dict:
    with open(fn, 'r') as f:
        x = json.load(f)
        return x

@logruns()
def load_os_release(dat: dict = None) -> str:
    if not dat: return load_file('./res/os-release')
    f = load_os_release()
    for k, v in dat.items():
        f = f.replace('{' + k + '}', f'{v}')
    return f

@logruns()
def load_profiledef(dat: dict = None) -> str:
    if not dat: return load_file('./res/profiledef.sh')
    f = load_profiledef()
    dat['id-upper'] = dat['id'].upper()
    for k, v in dat.items():    
        f = f.replace('{' + k + '}', f'{v}')
    
    lines = f.split('\n')[:-1]
    for i in executables:
        lines.append(f'  ["{i}"]="0:0:755"')
    
    f = '\n'.join(lines)

    print()
    print('[profiledef.sh]')
    print(f)
    print()

    return f

@logruns()
def load_config() -> dict:
    return load_json('./distro/config.json')

config = load_config()
print('[config]')
print(json.dumps(config, indent=4))
print()

packages = [
    'xorg-server',
    'xorg-xinit',
    'xorg-xrandr',
    'xorg-xsetroot',
    'xorg-xbacklight',
    'xorg-xinput',
    'xterm',
    'i3',
    'i3status',
    'dmenu',
    'lightdm',
    'lightdm-gtk-greeter',
    *config['packages']
]

@logruns('copying releng files')
def copy_releng_files():
    os.system('cp -r /usr/share/archiso/configs/releng ./archiso')

@logruns('adding packages to live iso')
def add_packages():
    for i in packages: print(f' * {i}')
    with open('./archiso/packages.x86_64', 'a') as f:
        f.write('\n'.join(packages))
    print('packages added')
    print()

@logruns('enabling autologin')
def enable_autologin():
    with open('./archiso/airootfs/etc/systemd/system/getty@tty1.service.d/autologin.conf', 'w') as f:
        f.write(load_file('./res/autologin.conf'))

@logruns('adding xinitrc')
def add_xinitrc():
    p = './archiso/airootfs/root/.xinitrc'
    with open(p, 'w') as f:
        f.write(load_file('./res/xinitrc'))
        make_executable(p)

@logruns('adding zshrc')
def add_zshrc():
    p = './archiso/airootfs/root/.zshrc'
    with open(p, 'w') as f:
        f.write(load_file('./res/zshrc'))
        make_executable(p)

@logruns('adding i3 config')
def add_i3config():
    p = './archiso/airootfs/root/.config/i3/config'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(load_file('./res/i3config'))

@logruns('adding splash')
def add_splash():
    os.system('cp ./distro/splash.png ./archiso/syslinux/splash.png')

def replace_distro_name(fn: str):
    try:
        with open(f'./archiso/syslinux/{fn}', 'r') as f:
            dat = f.read()
        with open(f'./archiso/syslinux/{fn}', 'w') as f:
            f.write(dat.replace('Arch Linux', config['name']))
        print(' * replaced Arch Linux with distro name on', fn)
    except Exception as e:
        print(' - failed to replace Arch Linux with distro name on', fn)

@logruns('rebranding Arch Linux', 'rebranded Arch Linux')
def replace_all_distro_names(d: str = './archiso/syslinux'):
    for i in os.listdir(d):
        if i == 'splash.png': continue
        replace_distro_name(i)

@logruns('rebranding Arch Linux on boot entries')
def replace_efi_boot_entries():
    replace_all_distro_names('./archiso/efiboot/loader/entries')

@logruns('setting iso hostname')
def set_iso_hostname():
    with open('./archiso/airootfs/etc/hostname', 'w') as f:
        f.write(config['liveiso_hostname'])

@logruns('add installer')
def add_installer():
    p = './archiso/airootfs/root/installer'
    os.system(f'cp ./distro/installer {p}')
    make_executable(p)

@logruns('add os-release')
def add_os_release():
    with open('./archiso/airootfs/etc/os-release', 'w') as f:
        f.write(load_os_release(config))

@logruns('add profiledef')
def add_profiledef():
    with open('./archiso/airootfs/root/.profiledef', 'w') as f:
        f.write(load_profiledef(config))

@logruns('====\nBUILDING BASE\n====', '====\nBASE BUILT\n====')
def build_base():
    print()

    copy_releng_files()
    add_packages()
    replace_all_distro_names()
    replace_efi_boot_entries()
    set_iso_hostname()
    enable_autologin()
    add_xinitrc()
    add_zshrc()
    add_i3config()
    add_splash()
    add_installer()
    add_os_release()
    add_profiledef()

    print()
    print('ISO now has an i3 X11 install enviroment, that will execute installer on boot.')
    print()

build_base()
