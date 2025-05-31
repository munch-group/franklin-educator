#!/usr/bin/env bash

# export PIXI_EXE="/home/vscode/bin/pixi"
# echo "export PIXI_EXE=/home/vscode/bin/pixi" >> /home/vscode/.bashrc

export PIXI_HOME="/home/vscode"
echo "export PIXI_HOME=/home/vscode" >> /home/vscode/.bashrc

export PIXI_PROJECT_MANIFEST="$PWD/pixi.toml"
echo "export PIXI_PROJECT_MANIFEST="pixi.toml"" >> /home/vscode/.bashrc

curl -fsSL https://pixi.sh/install.sh | bash

bash