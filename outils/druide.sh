# 0.846 : recompile le Druide conseiller écrit en vtx (druide/conseiller.vtx) et l'embarque dans Lugus et Ogmios
# (vtx-rs/druide_conseiller.mots) ; à lancer après toute retouche du conseiller
set -eo pipefail
cd $(cd "$(dirname "$0")/.." && pwd)/vtx-rs
./target/release/lugus compiler ../druide/conseiller.vtx druide_conseiller.mots | tail -1
cargo build --release 2>&1 | tail -1
