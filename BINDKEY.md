To get the complete list of key bindings in Zsh, including the `bindkey` commands, you can use the following methods:

### 1. **View Current Key Bindings**
   You can list all the current key bindings in your Zsh session by running:
   ```zsh
   bindkey
   ```
   This will display all the key sequences and the functions or widgets they are bound to.

### 2. **View Custom Key Bindings in Your Configuration Files**
   If you've customized your key bindings (like your example with `bindkey '˚' optionk`), you can find them in your Zsh configuration files, typically `~/.zshrc` or `~/.zshenv`. You can search for `bindkey` commands using `grep`:
   ```zsh
   grep bindkey ~/.zshrc
   ```

### 3. **List All Widgets**
   You can list all Zsh widgets (functions bound to key sequences) using:
   ```zsh
   zle -l
   ```
   This will list the names of all widgets that you can bind to keys.

### 4. **Get Documentation for `bindkey`**
   You can read the Zsh manual for detailed information on `bindkey` and key binding syntax by running:
   ```zsh
   man zshzle
   ```
   In the manual, search for `bindkey` to get detailed usage instructions.

### 5. **Get Key Codes**
   If you're unsure about the key code for a specific key (like `˚` in your example), you can press `Ctrl+v` followed by the key in your terminal. This will show the key sequence that you can use in the `bindkey` command.

For example:
- Press `Ctrl+v` and then `˚`, and you'll see the key code output.
- You can then use this key code in your `bindkey` command like so:
  ```zsh
  bindkey 'key_code' optionk
  ```

By using these methods, you can view, customize, and manage key bindings in Zsh effectively.