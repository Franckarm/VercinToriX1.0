set -eo pipefail
cd $(cd "$(dirname "$0")/.." && pwd)
python3 vtxc/vocabulaire.py
python3 vtxc/prelude128.py
cd vtx-rs
./target/release/lugus renouveler ../vtxc/vtxc128.vtx | tail -1
cp ../vtxc/vtxc128.mots vtxc128.mots
./target/release/vtx64 renouveler ../vtxc/vtxc64.vtx | tail -1
cp vtxc64.mots ../vtxc/vtxc64.mots
cargo build --release 2>&1 | tail -1
