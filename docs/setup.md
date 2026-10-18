# Setup and device access

## Requirements

- A TV matching the [documented original assembly hashes](compatibility.md), and permission to modify it.
- A computer and TV on the same reachable local network. Wired Ethernet is also usable; Wi-Fi is not a special protocol requirement.
- Python 3.12 or newer, the .NET 10.0.402 SDK (pinned by `global.json`), OpenSSL, and Samsung's SDB executable from [Tizen Studio](https://developer.tizen.org/development/tizen-studio/download).
- The host firewall must allow the TV to connect back to the computer for the temporary authenticated command session. Guest-network isolation, a VPN, or the wrong interface can prevent this.

Use macOS for the documented device workflow. Linux supports offline CI checks; its complete device workflow has not been qualified. Windows is unsupported. Commands below use a POSIX shell. Do not install an obsolete .NET 3.1 host runtime: the build targets the runtime already present on the TV.

The host patchers target .NET 10 LTS. Download the pinned SDK from [Microsoft](https://dotnet.microsoft.com/en-us/download/dotnet/10.0). If installed in `$HOME/.dotnet`, select it in the current shell before building:

```sh
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
dotnet --version
```

The expected version is `10.0.402`. The TV payloads retain their `netcoreapp3.1` target; this does not change the TV runtime. See [testing](CI.md) for automated checks.

Download the project source archive, extract it, and open a terminal in the project directory.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
cp config.example.json config.json
```

Edit `config.json`: set `host` to your TV's IPv4 address and `sdb` to the absolute path to Samsung's executable. Record the actual model name; it is metadata, while exact source hashes gate customization. The example address `192.0.2.50` is a documentation placeholder. Leave `callback_host` null unless automatic routing chooses the wrong local interface; if needed, set it to the computer's LAN IPv4 address.

The tools are intended to run from this editable source workspace. Keep `config.json`, `.local/`, and `.venv/` private. There is no hosted account or cloud login for Tizen Dock.

## Enable TV Developer Mode

On the tested TV, open **Apps**, enter **12345** using the remote's number controls to open Developer Mode, enable it, and enter the **computer's** LAN address as the allowed host. Restart the TV. Depending on the remote, a full numeric IR remote or the on-screen number pad may be required. Other model menus can differ.

If the connection still fails after a normal restart, the tested TV needed a full unplug/reconnect before Developer Mode became reachable. Use the TV's on-screen software information to record its complete model and version before proceeding. Standby, a Home-app restart, and a full system boot are different; see [restart behavior](restart-and-persistence.md). Use the computer's address for initial development access. The [startup installer](restart-and-persistence.md) later changes it to loopback for autonomous restoration.

## Prepare temporary root tooling

```sh
python scripts/bootstrap.py
tizen-dock doctor
tizen-dock connect
tizen-dock status
```

`bootstrap.py` downloads a pinned public research source archive into `.local/upstream`, applies the documented Samsung runtime check adaptation, and builds two payloads into `.local/payloads`. It makes no TV connection. The .NET build restores its target reference packages as needed; those dependencies remain local.

`doctor` validates local configuration and dependency paths. `connect` establishes SDB access. `status` reads architecture, Tizen release information, and the Home process. These do not qualify the firmware files for patching.

## Login and root access

There is no default SSH username/password or password-based root login in this workflow. Developer Mode whitelists the computer, SDB provides the initial connection, and the pinned research adapter obtains a temporary authenticated root command channel.

```sh
tizen-dock root --command 'id'
```

On the development device, the route returned UID/GID 0 and the expected effective capabilities. The adapter uses a private mount namespace for its temporary launcher setup and checks restoration of its sensitive temporary mounts. The administrator command channel is short-lived. Install the current device-authorized TV startup helper using [restart and persistence](restart-and-persistence.md); it uses the same v4 build manifest.

On the supported runtime, `/usr/bin/dotnet` is a Samsung launcher that rejects `--list-runtimes`. The local adaptation only accepts its observed 3.1.3 runtime symlink and existing runtime library. If those checks differ, stop; the adaptation is not permission to bypass another compatibility error.

Read [backups and recovery](backups-and-recovery.md) before changing app state or loading overlays. Never forward SDB or a development command listener to the public internet.

## Multiple TVs

Keep one private configuration per TV and select it explicitly, for example
`tizen-dock --config .local/tv-config.json connect`. Use the same selected
configuration for status, backup, apply and restoration. There is one installer
implementation, with separate device data rather than model-specific session scripts.
`connect` requires a registered device before reporting success.
