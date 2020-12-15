{ pkgs ? import <nixpkgs> {} }:
with pkgs;
let
  python-ilias-downloader = python-packages: with python-packages; [
    requests
    beautifulsoup4
  ];
  python-for-ilias-downloader = python37.withPackages python-ilias-downloader;
in pkgs.mkShell {
  nativeBuildInputs = [ python-for-ilias-downloader ];
  shellHook = ''
    exec zsh
  '';
}
