// atelier : le même exécutable que vtx, sous ce nom. Sous Windows, il ouvre la fenêtre de l'atelier (sans console) ;
// ailleurs, l'atelier en console.
#![cfg_attr(windows, windows_subsystem = "windows")]
include!("main.rs");
