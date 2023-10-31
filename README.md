# MovableQ

MovableQ is a service meant to automatically connect people who need their 3DS console's `movable.sed` bruteforced with volunteers that can offer the computing power to do so. Currently `movable.sed` mining, Mii LFCS mining, and friend exchange LFCS dumping jobs are supported.


## Server Setup (Website)

### Requirements

- [Python 3.10+](https://www.python.org/)
- [Pipenv](https://pypi.org/project/pipenv/)

### Instructions

1. Clone this GitHub repository and install the depedencies with pipenv:
```bash
git clone --recursive https://github.com/cm-360/MovableQ.git
cd MovableQ
pipenv install
```
1. Configure host settings and admin credentials in `.env`
1. Run the server:
```bash
pipenv run python3 server.py
```


## Client Setup (Miner)

### Requirements

- [Python 3.10+](https://www.python.org/)
- [requests](https://pypi.org/project/requests/)

### Instructions

1. Download and extract the latest release of [danny8376's Seedminer](https://github.com/danny8376/seedminer/releases) for your operating system.
1. Download the [mining client script](https://cm360.xyz/movableq/get_mining_client) from the MovableQ website. Place it inside the extracted Seedminer directory, in the same place as `seedminer_launcher_3.py`.
1. Install the `requests` package if you haven't already:
```bash
pip install requests
```
1. Run the mining client and allow it to generate a default configuration file:
```bash
python3 mining_client.py
```
1. Open `mining_client.cfg` in a text editor to change the `miner_name` variable and give yourself a username.
1. Run the mining client again. If everything was set up correctly and the benchmark passes, it should start checking for jobs.

**NOTE**: If you download the script directly from GitHub instead of the website, you will also need to adjust the `client_version` and `base_url` variables.


## About

### What is `movable.sed`?
`movable.sed` (sometimes shortened to just "movable" or "msed") refers to a console-unique file on a 3DS system's NAND containing important encryption keys. These keys can be used to encrypt/decrypt contents on the SD card, allowing us to perform several useful exploits, such as [BannerBomb3](https://github.com/zoogie/Bannerbomb3). Check [this presentation](https://zoogie.github.io/web/34%E2%85%95c3/) for more information.

### What is "Mii Mining"?
Mii Mining is a process to bruteforce a 3DS console's LocalFriendCodeSeed (LFCS) and complete the Seedminer process. The LFCS can normally be obtained during a friend exchange, but the [11.16.0-48 system update](https://yls8.mtheall.com/ninupdates/titlelist.php?date=2022-08-30_00-00-33&sys=ctr) updated the friend list module, leaving consoles on system version 11.15 or lower without access. Luckily, an exported Mii QR code contains a hash of the LFCS, which we can then bruteforce.
