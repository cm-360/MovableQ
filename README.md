# MovableQ

MovableQ is a service meant to automatically connect people who need their 3DS console's `movable.sed` bruteforced with people that can offer the computing power to do so. Currently only "mii mining" is supported, though adding support for normal "seedminer" jobs is planned.

## Requirements

- [Python 3](https://www.python.org/)
- [Pipenv](https://pypi.org/project/pipenv/)

## Setup

1. Clone this GitHub repository and install the depedencies with pipenv:
```bash
git clone --recursive https://github.com/cm-360/MovableQ.git
cd MovableQ
pipenv install
```
2. Configure host settings and admin credentials in `.env`
3. Run the server:
```bash
pipenv run python3 server.py
```

## About

### 