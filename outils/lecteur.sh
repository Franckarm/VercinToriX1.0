# 0.62 : recompile le lecteur d'ADN écrit en vtx (chimie/adn.vtx) et l'embarque dans Lugus (vtx-rs/lecteur_adn.mots),
# à lancer après toute retouche du lecteur (le catalogue, la carte, la vibration…)
set -eo pipefail
cd $(cd "$(dirname "$0")/.." && pwd)/vtx-rs
./target/release/lugus compiler ../chimie/adn.vtx lecteur_adn.mots | tail -1
cargo build --release 2>&1 | tail -1
