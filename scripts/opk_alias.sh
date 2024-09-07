optionk() {
    local install_path="{INSTALL_PATH}"
    local query="$BUFFER"
    local result=$("$install_path/venv/bin/python" "$install_path/client/opk.py" "$query" --quick)
    BUFFER="$result"
    zle end-of-line
}

zle -N optionk
bindkey '˚' optionk