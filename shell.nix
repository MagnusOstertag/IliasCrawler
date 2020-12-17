{ pkgs ? import <nixpkgs> {} }:
with pkgs;
let
  python-ilias-downloader = python-packages: with python-packages; [
    requests
    beautifulsoup4
    ipython
  ];
  python-for-ilias-downloader = python37.withPackages python-ilias-downloader;
in pkgs.mkShell {
  nativeBuildInputs = [ ffmpeg python-for-ilias-downloader ];
  shellHook = ''
    exec zsh
  '';
}
