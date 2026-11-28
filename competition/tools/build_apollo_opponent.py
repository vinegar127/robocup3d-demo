"""Build pinned Apollo on Windows with transport/build-only compatibility edits.

The original third_party/apollo snapshot is never modified. No decision, world,
motion, formation or model files are changed in the build copy.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import argparse

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--kind',choices=['apollo','my3d'],default='apollo')
args=parser.parse_args()

root = Path(__file__).resolve().parents[1]
source = root / ('third_party/apollo' if args.kind=='apollo' else 'third_party/my3d/runtime/apollo')
provenance_path=root/('third_party/apollo/PROVENANCE.json' if args.kind=='apollo' else 'third_party/my3d/PROVENANCE.json')
provenance=json.loads(provenance_path.read_text())
destination = Path('E:/RoboCup3D/opponents')/args.kind
destination.mkdir(parents=True, exist_ok=True)
for name in ['src', 'assets']:
    shutil.copytree(source / name, destination / name, dirs_exist_ok=True)
for name in ['main.cc', 'LICENSE.md', 'README.md']:
    shutil.copy2(source / name, destination / name)
shutil.copy2(provenance_path,destination/'PROVENANCE.json')
deps = root / 'third_party/build_dependencies'
yaml = deps / 'yaml/yaml-cpp-0.8.0'
ort = deps / 'ort/onnxruntime-win-x64-1.22.0'
shutil.copytree(yaml / 'src', destination / 'cpp_deps/yaml/src', dirs_exist_ok=True)
shutil.copytree(yaml / 'include', destination / 'cpp_deps/yaml/include', dirs_exist_ok=True)
shutil.copytree(ort / 'include', destination / 'cpp_deps/ort/include', dirs_exist_ok=True)
(destination / 'cpp_deps/ort/lib').mkdir(parents=True, exist_ok=True)
for file in (ort / 'lib').iterdir():
    if file.suffix in ('.dll', '.lib'):
        shutil.copy2(file, destination / 'cpp_deps/ort/lib' / file.name)
        if file.suffix == '.dll':
            shutil.copy2(file, destination / file.name)

header = destination / 'src/server/tcp_lpm_client.h'
text = header.read_text(encoding='utf-8').replace('TcpLpmClient(int adopted_socket_fd)', 'TcpLpmClient(std::intptr_t adopted_socket_fd)').replace('int socket_fd_{-1}', 'std::intptr_t socket_fd_{-1}')
header.write_text(text, encoding='utf-8')
transport = destination / 'src/server/tcp_lpm_client.cc'
text = transport.read_text(encoding='utf-8')
start, end = text.index('#include <arpa/inet.h>'), text.index('#include <cerrno>')
text = text[:start] + '#include <winsock2.h>\n#include <ws2tcpip.h>\n\n' + text[end:]
text = text.replace('void send_all(int socket_fd', 'void send_all(std::intptr_t socket_fd').replace('void recv_all(int socket_fd', 'void recv_all(std::intptr_t socket_fd')
text = text.replace('const ssize_t result = ::write(socket_fd, bytes + sent, size - sent);',
                    'const int result = ::send(static_cast<SOCKET>(socket_fd), reinterpret_cast<const char*>(bytes + sent), static_cast<int>(size - sent), 0);')
text = text.replace('const ssize_t result = ::read(socket_fd, bytes + received, size - received);',
                    'const int result = ::recv(static_cast<SOCKET>(socket_fd), reinterpret_cast<char*>(bytes + received), static_cast<int>(size - received), 0);')
text = text.replace('TcpLpmClient::TcpLpmClient(int adopted_socket_fd)', 'TcpLpmClient::TcpLpmClient(std::intptr_t adopted_socket_fd)')
text = text.replace('void TcpLpmClient::connect() {', '''void TcpLpmClient::connect() {
    static const bool winsock_ready = [] { WSADATA data{}; return WSAStartup(MAKEWORD(2,2), &data) == 0; }();
    if (!winsock_ready) throw std::runtime_error("WSAStartup failed");''')
text = text.replace('::socket(AF_INET, SOCK_STREAM, 0)', 'static_cast<std::intptr_t>(::socket(AF_INET, SOCK_STREAM, 0))')
text = text.replace('&enabled, sizeof(enabled)', 'reinterpret_cast<const char*>(&enabled), sizeof(enabled)')
text = text.replace('SHUT_RDWR', 'SD_BOTH').replace('::close(socket_fd_)', '::closesocket(static_cast<SOCKET>(socket_fd_))')
transport.write_text(text, encoding='utf-8')

changed = []
for item in provenance['files']:
    relative=item['path']
    if args.kind=='my3d':
        if not relative.startswith('runtime/apollo/'):
            continue
        relative=relative.removeprefix('runtime/apollo/')
    p = destination / relative
    if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
        changed.append(relative)
assert sorted(changed) == ['src/server/tcp_lpm_client.cc', 'src/server/tcp_lpm_client.h'], changed
(destination / 'WINDOWS_PORT.json').write_text(json.dumps({'base_commit': provenance['commit'], 'changed_files': changed, 'scope': 'Winsock transport and pointer-sized socket handle only; strategy and assets byte-identical'}, indent=2))

cpp = [str(p.relative_to(destination)) for p in sorted((destination / 'src').rglob('*.cc'))]
yaml_cpp = [str(p.relative_to(destination)) for p in sorted((destination / 'cpp_deps/yaml/src').glob('*.cpp'))]
command = ['C:/mingw64/bin/g++.exe', '-std=c++17', '-O2', '-DNOMINMAX', '-DWIN32_LEAN_AND_MEAN',
           '-D_stdcall=__stdcall', '-include', 'cstdint',
           '-DYAML_CPP_STATIC_DEFINE', f'-DAPOLLO_CODE_BASE_PROJECT_SOURCE_DIR="{destination.as_posix()}"',
           '-I.', '-Icpp_deps/yaml/include', '-Icpp_deps/yaml/src', '-Icpp_deps/ort/include',
           'main.cc', *cpp, *yaml_cpp, 'cpp_deps/ort/lib/onnxruntime.lib', '-lws2_32',
           '-static-libgcc', '-static-libstdc++', '-o', 'ApolloCodeBase.exe']
(destination / 'BUILD_COMMAND.json').write_text(json.dumps(command, indent=2))
with (destination / 'build.log').open('w', encoding='utf-8') as log:
    result = subprocess.run(command, cwd=destination, stdout=log, stderr=subprocess.STDOUT)
if result.returncode:
    print((destination / 'build.log').read_text(encoding='utf-8', errors='replace')[-14000:])
    raise SystemExit(result.returncode)
print('Built:', destination / 'ApolloCodeBase.exe')
