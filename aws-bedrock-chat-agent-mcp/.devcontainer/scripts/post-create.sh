set -e

mkdir -p ~/.oh-my-zsh/completions
tenv completion zsh > ~/.oh-my-zsh/completions/_tenv
tenv completion bash > ~/.tenv.completion.bash
echo "source \$HOME/.tenv.completion.bash" >> ~/.bashrc
cat .devcontainer/scripts/.bashrc >> ~/.bashrc
