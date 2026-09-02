# Nand2Tetris Student Starter Repository

Welcome! This repository contains the starter files for the [Nand2Tetris](https://www.nand2tetris.org/) coursework. 

Nand2Tetris software requires you to have Java installed. It's likely you already have Java installed, but check out their own instructions for [installing the software](https://www.nand2tetris.org/software).

I like the **[VS Code](https://code.visualstudio.com/)** *integrated development environment (IDE)* for working in the course, and also for AI integration. Check out [Antigravity](https://antigravity.google/download) (with personal gmail) or its [vscode integration](https://antigravity.google/docs/ide/extensions/vscode).

The instructions below are principally about allowing you to work with git version control. 

---

## First Up: Download the software package

See the [instructions](https://drive.google.com/file/d/1IkIR8Pwq3PY49QgXpUJOkUUVht-TKIET/view) to download the zip package. When you unzip the contents you'll see a folder structure like:

```
__MACOSX
nand2tetris:
    -projects
    -tools
```

The `tools` subfolder is where all the simulation software can be found. We will not change any of these contents.

The `projects` subfolder contains all the provided assignment and test files for completing the course. Below you will reproduce this folder in your own github space as a private git repository. This will allow for easy control and assessment as we progress through the course.


## Quick Start: Creating Your Private GitHub Workspace

Do **not** edit code directly inside a clone of this public repository. Instead, follow these steps to push your starter files to your own **private** repository.

### 1. Create your remote repository on GitHub
1. Go to [github.com/new](https://github.com/new).
2. Name the repository `nand2tetris-projects`.
3. Select **Private**.
4. **Do NOT check** "Add a README file", ".gitignore", or "License" (leave it completely blank).
5. Click **Create repository**.

### 2. Run These Commands in Your Terminal

Open your terminal, copy and run the block below (remember to replace `YOUR-GITHUB-USERNAME` with your actual GitHub username):

```bash
# Clone this starter repository locally
git clone git@github.com:profstough/nand2tetris_26F.git nand2tetris-projects
cd nand2tetris-projects

# Rename the template remote to "upstream" so you can still pull future updates from it
git remote rename origin upstream

# Add YOUR new private GitHub repo as "origin"
git remote add origin git@github.com:YOUR-GITHUB-USERNAME/nand2tetris-projects.git

# Push the starter files to your private repo
git branch -M main
git push --set-upstream origin main
```

Of note, the above assumes you have [set up an ssh key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) for github access:
* **SSH:** `git@github.com:profstough/nand2tetris_26F.git`
* **HTTPS:** `https://github.com/profstough/nand2tetris_26F.git`

> **Already followed the old instructions and don't have an `upstream` remote?** No problem — just add it back:
> ```bash
> git remote add upstream git@github.com:profstough/nand2tetris_26F.git
> ```

## Getting Updates From the Template

Occasionally I may push fixes or new files (a corrected grading script, a missing test fixture, etc.) to the template repository. To pull those into your own repo **without losing any of your own committed work**:

```bash
git fetch upstream
git merge upstream/main
```

This only changes files that were updated upstream. If you happen to have edited one of those exact same files yourself, Git will pause and ask you to resolve the conflict by hand (it marks the conflicting lines in the file) — it will never silently discard your commits. Once resolved, `git add` the file and `git commit` to finish the merge, then `git push` as usual to update your own private repo.



## MAC/Linux Setup Guide

### 1. Add Hardware Simulator Tools to Your PATH
To run `HardwareSimulator.sh` from your terminal without typing the full path every time:

**For Bash users** (add to `~/.bashrc`):
```bash
export PATH="$PATH:/path/to/nand2tetris/tools"
```

**For Zsh users** (add to `~/.zshrc`):
```bash
export PATH="$PATH:/path/to/nand2tetris/tools"
```

Replace `/path/to/nand2tetris/tools` with the actual path to your extracted `tools` folder (e.g., `$HOME/nand2tetris/tools`).

After editing your shell configuration file, reload it:
```bash
# For Bash
source ~/.bashrc

# For Zsh
source ~/.zshrc
```

Now you can run the simulator directly:
```bash
HardwareSimulator.sh DMux4Way.tst
```


## Windows Setup Guide

Windows users are encouraged to use **Git Bash** so that all terminal commands match the macOS/Linux instructions.

### 1. Install Git Bash & VS Code
1. Download and install **[Git for Windows](https://gitforwindows.org/)** (this installs Git Bash).
2. Download and install **[VS Code](https://code.visualstudio.com/)**.

### 2. Set Git Bash as Your Default Terminal in VS Code
1. Open VS Code.
2. Press `Ctrl + Shift + P` and type: **Terminal: Select Default Profile**.
3. Select **Git Bash** from the list.
4. Open a new terminal in VS Code (`Ctrl + ~`). You are now running a Linux-style Bash terminal on Windows!

### 3. Add Hardware Simulator Tools to Your Windows PATH
To run `HardwareSimulator.sh` from Git Bash without typing the full path every time:

1. Press `Win + R`, type `sysdm.cpl`, and press **Enter** (opens System Properties).
2. Go to the **Advanced** tab $\rightarrow$ click **Environment Variables**.
3. Under **User variables**, select `Path` and click **Edit**.
4. Click **New** and add the path to your extracted `tools` folder (e.g., `C:\nand2tetris-tools\tools`).
5. Click **OK** on all windows, then restart VS Code.

> **Note for Windows:** In Git Bash, you can run `.sh` scripts directly:
> ```bash
> HardwareSimulator.sh DMux4Way.tst
> ```
> *(If `HardwareSimulator.sh` isn't recognized, you can also run `HardwareSimulator.bat DMux4Way.tst` natively).*