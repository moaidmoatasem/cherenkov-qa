---
title: Shell Completions
description: Install tab-completion for the CHERENKOV CLI in bash, zsh, or fish.
---

# Shell Completions

CHERENKOV supports tab-completion for commands, subcommands, and flags via Click's completion system.

## Install Completions

=== "bash"

    ```bash
    # Add to ~/.bashrc
    eval "$(_CHERENKOV_COMPLETE=bash_source cherenkov)"
    ```

    Or generate a static file for faster startup:

    ```bash
    _CHERENKOV_COMPLETE=bash_source cherenkov > ~/.cherenkov-complete.bash
    echo ". ~/.cherenkov-complete.bash" >> ~/.bashrc
    ```

=== "zsh"

    ```bash
    # Add to ~/.zshrc
    eval "$(_CHERENKOV_COMPLETE=zsh_source cherenkov)"
    ```

=== "fish"

    ```bash
    # Add to ~/.config/fish/config.fish
    eval (env _CHERENKOV_COMPLETE=fish_source cherenkov)
    ```

## What Gets Completed

After installation, pressing `TAB` completes:

```
cherenkov <TAB>
validate   generate   eject   dashboard   hitl   knowledge
teleport   routine    doctor  examples    memory  --help

cherenkov validate --<TAB>
--spec   --target   --fail-on-drift   --output   --json   --quiet
```
