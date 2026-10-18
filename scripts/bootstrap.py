"""Download pinned public root research source and build local TV payloads."""

from pathlib import Path
import io
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "4ad2c4d3b0d0e0da4b5b7ebe4a787e94596f416b"
URL = "https://codeload.github.com/chris-ritsen/samsung-tv-root/zip/" + COMMIT
local = ROOT / ".local"
local.mkdir(mode=0o700, exist_ok=True)
upstream = local / "upstream"
if not upstream.exists():
    data = urllib.request.urlopen(URL, timeout=60).read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            relative = Path(*Path(name).parts[1:])
            if not relative.parts:
                continue
            if relative.is_absolute() or ".." in relative.parts:
                raise SystemExit("Unexpected source archive path")
            dest = upstream / relative
            if name.endswith("/"):
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.read(name))
    (upstream / ".source-commit").write_text(COMMIT + "\n")
elif (
    not (upstream / ".source-commit").exists()
    or (upstream / ".source-commit").read_text().strip() != COMMIT
):
    raise SystemExit(
        "Existing upstream directory is not this pinned source; preserve it and use a fresh .local/upstream"
    )
source = upstream / "src/samsung_tv_root/archive_root.py"
s = source.read_text()
old = '    runtimes = _capture(client, "/usr/bin/dotnet --list-runtimes")\n'
replacement = """    try:
        runtimes = _capture(client, "/usr/bin/dotnet --list-runtimes")
    except ArchiveRootError as error:
        if "Unknown option --list-runtimes" not in str(error):
            raise
        runtime_path = _capture(client, "readlink -f /usr/share/dotnet.tizen/netcoreapp")
        if runtime_path != "/usr/share/dotnet/shared/Microsoft.NETCore.App/3.1.3":
            raise ArchiveRootError("unrecognized Samsung runtime path") from error
        _capture(client, "test -f /usr/share/dotnet/shared/Microsoft.NETCore.App/3.1.3/libcoreclr.so")
        runtimes = "Microsoft.NETCore.App 3.1.3 [/usr/share/dotnet/shared/Microsoft.NETCore.App]"
"""
if "unrecognized Samsung runtime path" not in s:
    if s.count(old) != 1:
        raise SystemExit("Unexpected upstream source; adaptation refused")
    source.write_text(s.replace(old, replacement))
for name in ("SamsungTvArchiveRoot", "SamsungTvRootAgent"):
    folder = local / "payload-projects" / name
    folder.mkdir(parents=True, exist_ok=True)
    # Relative source paths keep local host names out of generated project files.
    project = folder / (name + ".csproj")
    project.write_text(
        f"""<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netcoreapp3.1</TargetFramework><OutputType>Exe</OutputType><AssemblyName>{name}</AssemblyName><UseAppHost>false</UseAppHost><EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup><ItemGroup><Compile Include="../../upstream/payloads/common/{name}.cs" /></ItemGroup></Project>"""
    )
    # payload-projects/NAME is two levels below .local.
    subprocess.run(
        ["dotnet", "build", str(project), "-o", str(local / "payloads"), "--nologo"],
        check=True,
    )
print("Pinned source and locally built payloads ready. No TV connection was made.")
