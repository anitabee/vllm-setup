# CLI Tool Best Practices: A Complete Guide

**The Command Line Interface Guidelines (clig.dev) established the modern foundations of CLI design in 2020, updating UNIX principles for human-first interaction.** This guide synthesizes those principles with battle-tested patterns from production tools into a comprehensive reference covering interface design, I/O contracts, configuration management, distribution, and the subtle art of building tools that feel both powerful and approachable. Whether you're building your first CLI or refining the 50th, these patterns will help you create tools that users trust, remember, and recommend.

---

## Philosophy: Why These Patterns Matter

### Human-first design, machine-second compatibility

Traditional UNIX commands were written assuming they'd be used primarily by other programs—they were essentially functions in a shell scripting language. Today's CLI tools are used primarily by humans, yet many still carry the baggage of that assumption. **Design for humans first, but maintain machine compatibility.**

This doesn't mean abandoning composability. It means that when you have to choose between making something easier for humans or easier for scripts, choose humans—then provide flags like `--plain` or `--json` for scripts.

### The conversational nature of CLI interaction

**Running a CLI tool is a conversation between the user and the program.** This conversation often involves trial and error:
- Run a command, get an error
- Modify the command based on the error message
- Run again, get a different error
- Eventually succeed

Other conversational patterns:
- Multi-step setup (configure tool, then use it)
- Exploration (cd/ls to understand directory structure, git log/show to explore history)
- Dry-run before committing to a destructive action

Acknowledging this conversational nature means:
- **Suggest corrections** when input is invalid ("Did you mean 'commit'?")
- **Show intermediate state** clearly during multi-step processes
- **Confirm before scary actions** ("This will delete 47 files. Continue? [y/N]")
- **Make discovery easy** with examples and progressive help

The user is conversing with your software whether you intended it or not. At worst, it's a hostile conversation that makes them feel stupid. At best, it's a helpful exchange that speeds them along with new knowledge.

*Further reading: [The Anti-Mac User Interface (Don Gentner and Jakob Nielsen)](https://www.nngroup.com/articles/anti-mac-interface/)*

### Composability: Simple parts that work together

**Programs should click together like LEGO bricks.** The original UNIX philosophy emphasized building small, focused tools that can be combined. While shell scripting's role has diminished, large-scale automation through CI/CD and orchestration has flourished.

Standard conventions enable composability:
- **stdin/stdout/stderr** for data flow
- **Exit codes** for success/failure signaling
- **Plain text** for universal parsing
- **JSON** for structured data when needed
- **Signals** for graceful shutdown

Your software will become part of larger systems. The only choice is whether it will be well-behaved.

### Robustness: Both objective and subjective

Software should **be** robust (handle unexpected input gracefully, be idempotent where possible) and **feel** robust (responsive, informative, not fragile).

Subjective robustness requires:
- Keeping users informed about what's happening
- Explaining what common errors mean
- Not printing scary stack traces by default
- Responding within 100ms, even if just to say "working..."

Robustness often comes from simplicity. Lots of special cases make programs fragile.

### Empathy: Exceeding expectations at every turn

Command-line tools are a programmer's creative toolkit—they should be enjoyable to use. This means:
- Being on the user's side, helping them succeed
- Anticipating their problems
- Making the common cases effortless
- Providing escape hatches for edge cases

Delighting users means exceeding their expectations, which starts with empathy and attention to detail.

---

## The Basics: Get These Right or Fail

### Use a CLI argument parsing library

**Never parse arguments manually.** Use your language's built-in parser or a well-maintained third-party library:

- **Go**: Cobra (powers kubectl, Docker, GitHub CLI), cli
- **Rust**: clap (derive API recommended)
- **Python**: Click, Typer (type-hint based), argparse (stdlib)
- **Node.js**: oclif (full-featured), Commander.js (simpler)
- **Java**: picocli
- **Ruby**: TTY
- **Bash**: argbash

These libraries handle:
- Flag parsing (`-v`, `--verbose`)
- Argument validation
- Help text generation
- Shell completion
- Typo suggestions

### Exit codes are your programmatic interface

**Return exit code 0 on success, non-zero on failure.** Scripts depend on this to determine success.

Standard exit codes:
- **0**: Success
- **1**: General error
- **2**: Usage error (invalid arguments)
- **64-78**: BSD sysexits.h codes for specific errors
- **130**: Terminated by SIGINT (Ctrl-C)
- **128+N**: Terminated by signal N

Map non-zero codes to important failure modes when useful.

### The stdout/stderr contract is sacred

**Primary output goes to stdout. Everything else goes to stderr.**

This enables piping and composition:
```bash
# Works because primary output is on stdout
mytool list | grep "error" | sort

# Errors and progress on stderr don't interfere
mytool process file.txt 2>/dev/null  # Suppress diagnostics
```

What goes where:
- **stdout**: Command results, data meant for piping, JSON/CSV output
- **stderr**: Log messages, errors, warnings, progress indicators, prompts

---

## Help: The First Point of Contact

### Display concise help by default, extensive help on --help

When a command is run with missing required arguments, show concise help:

```
$ mytool
mytool - A tool for managing widgets

Usage: mytool [options] <command> [args]

Common commands:
  create    Create a new widget
  list      List all widgets
  delete    Delete a widget

Run 'mytool --help' for full documentation
Run 'mytool <command> --help' for command-specific help
```

When passed `-h` or `--help`, display comprehensive help with all flags, subcommands, and examples.

**Support these help invocations:**
```bash
mytool --help
mytool -h
mytool help
mytool help subcommand
mytool subcommand --help
mytool subcommand -h
```

Adding `-h` to any command should show help, regardless of other flags.

### Lead with examples, not flags

**Users scan for examples first.** Show the most common use cases prominently:

```
$ heroku apps --help
list your apps

EXAMPLES
  $ heroku apps
  === My Apps
  example
  example2

  === Collaborated Apps
  theirapp   other@owner.name

USAGE
  $ heroku apps [options]

OPTIONS
  -A, --all          include apps in all teams
  -p, --personal     list apps in personal account when default team is set
  -s, --space=space  filter by space
  -t, --team=team    team to use
  --json             output in json format
```

If you have many examples, put them in a cheat sheet command or separate documentation page.

### Use formatting to make help scannable

**Bold headings and structure make help readable.** But use terminal-independent formatting (not raw escape codes):

```
USAGE
  mytool [options] <command>

COMMANDS
  create     Create a new widget
  list       List all widgets
  delete     Delete a widget

OPTIONS
  -v, --verbose    Enable verbose output
  -q, --quiet      Suppress all output
  --json           Output in JSON format
```

Most CLI frameworks handle formatting automatically.

### Suggest corrections for typos

**If the user made a typo and you can guess what they meant, suggest it:**

```
$ heroku pss
 ›   Warning: pss is not a heroku command.
Did you mean ps? [y/n]:
```

Use Levenshtein distance to find similar commands. Don't just run the corrected command automatically—the user might have a logical mistake, not a typo.

### Provide a support path

Include a URL in top-level help for feedback and issues:

```
For bugs and feature requests: https://github.com/user/tool/issues
Documentation: https://tool.example.com/docs
```

---

## Arguments, Flags, and Input

### Prefer flags to positional arguments

**Flags are self-documenting and order-independent:**

```bash
# Good: clear what each value means
mytool deploy --app myservice --region us-east-1

# Bad: need to remember order and meaning
mytool deploy myservice us-east-1
```

Use positional arguments only for the single most obvious operand (typically a filename or the primary subject).

Exceptions where positional args work:
- Simple actions on multiple files: `rm file1 file2 file3`
- Very common commands with 2 args: `cp source dest`, `mv old new`

### All flags should have long forms

**Provide both short and long versions:**

```bash
mytool -v --region us-east-1  # Short flag, long flag
mytool --verbose --region us-east-1  # Both long
```

Short flags (`-v`) are for typing speed. Long flags (`--verbose`) are for clarity in scripts and documentation.

### Use standard flag names

**Follow conventions from widely-used tools:**

- `-a`, `--all`: All items/files
- `-d`, `--debug`: Debug output
- `-f`, `--force`: Force operation without confirmation
- `-h`, `--help`: Help text
- `-n`, `--dry-run`: Show what would happen without doing it
- `-o`, `--output`: Output file
- `-p`, `--port`: Network port
- `-q`, `--quiet`: Suppress output
- `-u`, `--user`: Username
- `-v`, `--verbose`: Verbose output (or `--version` if not using for verbose)
- `--version`: Show version
- `--json`: Output in JSON format
- `--no-input`: Non-interactive mode

### Prompt for missing required input

**If a required argument is missing, prompt for it:**

```
$ mytool deploy
App name: █
```

But **always provide a flag alternative** for scripts:

```bash
# Interactive
mytool deploy  # Prompts for app name

# Non-interactive
mytool deploy --app myservice
```

### Never require a prompt

**If stdin is not a TTY, or if `--no-input` is passed, don't prompt—fail with a clear error:**

```
$ mytool deploy --no-input
Error: --app flag is required in non-interactive mode
```

This prevents scripts from hanging when they encounter unexpected prompts.

### Confirm before destructive actions

**Severity levels for confirmation:**

1. **Mild** (deleting a file): Maybe prompt, maybe not
2. **Moderate** (deleting a directory, remote resources): Prompt for `y/yes` or require `--force`
3. **Severe** (deleting entire systems): Require typing the resource name or `--confirm="resource-name"`

Example of moderate confirmation:

```
$ mytool delete-app myservice
This will permanently delete:
  - Application 'myservice'
  - All associated data (3.4 GB)
  - DNS records (2 records)

Type 'yes' to confirm: █
```

### Support stdin with `-` convention

**Use `-` to read from stdin or write to stdout:**

```bash
# Extract tar from stdin
curl https://example.com/file.tar.gz | tar xvf -

# Output to stdout instead of file
mytool generate --output -
```

This enables pipelines without temporary files.

### Don't read secrets from flags

**Secrets in flags leak into `ps` output and shell history:**

```bash
# BAD - password visible in process list
mytool connect --password supersecret

# GOOD - read from file
mytool connect --password-file ~/.config/mytool/password

# GOOD - prompt
mytool connect  # Prompts for password with echo disabled

# GOOD - stdin
echo "supersecret" | mytool connect --password-stdin
```

---

## Output: Clarity for Humans and Machines

### Human-readable output is primary

**Optimize for human readability when stdout is a TTY.** Use formatting, colors, and structure to make information scannable:

```
$ git status
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
        modified:   src/main.rs
        modified:   README.md

no changes added to commit (use "git add" and/or "git commit -a")
```

### Provide machine-readable output with --json

**Support `--json` for structured output:**

```bash
$ mytool list --json
[
  {"id": "app-1", "name": "myservice", "status": "running"},
  {"id": "app-2", "name": "api", "status": "stopped"}
]
```

JSON enables:
- Piping to `jq` for filtering/transformation
- Integration with web APIs
- Complex data structures

For simpler tabular data, also consider `--plain` for unstyled output that works with `grep`/`awk`.

### Display output on success, but keep it brief

**Don't go silent (confusing), but don't be verbose (annoying):**

```bash
# Too silent
$ mytool deploy --app myservice
$  # Did it work??

# Too verbose
$ mytool deploy --app myservice
[INFO] Reading configuration from ./config.toml
[INFO] Validating configuration
[INFO] Configuration valid
[INFO] Connecting to API at https://api.example.com
[INFO] Connection established
[INFO] Uploading bundle (24 files)
...50 more lines...

# Just right
$ mytool deploy --app myservice
✓ Deployed myservice to https://myservice.example.com
  Build: #47 (2m 34s)
```

### Tell users when you change state

**After modifying system state, explain what happened:**

```
$ git push
Enumerating objects: 18, done.
Counting objects: 100% (18/18), done.
Delta compression using up to 8 threads
Compressing objects: 100% (10/10), done.
Writing objects: 100% (10/10), 2.09 KiB | 2.09 MiB/s, done.
Total 10 (delta 8), reused 0 (delta 0)
To github.com:user/repo.git
   6c22c90..a2a5217  main -> main
```

This helps users model system state in their heads.

### Use color with intention, not decoration

**Color should convey meaning:**
- Red for errors
- Yellow for warnings
- Green for success
- Dim gray for secondary information

**Disable color when:**
- stdout/stderr is not a TTY
- `NO_COLOR` environment variable is set (any value)
- `TERM=dumb`
- `--no-color` flag is passed

Example detection (pseudocode):

```python
def should_use_color():
    if os.environ.get('NO_COLOR'):
        return False
    if os.environ.get('TERM') == 'dumb':
        return False
    if not sys.stdout.isatty():
        return False
    return True
```

See [no-color.org](https://no-color.org/) for the standard.

### Use symbols and emoji sparingly

**Visual indicators can improve clarity:**

```
$ yubikey-agent -setup
🔐 The PIN is up to 8 numbers, letters, or symbols.
❌ The key will be lost if the PIN and PUK are locked after 3 incorrect tries.

✅ Done! This YubiKey is secured and ready to go.
🤏 When the YubiKey blinks, touch it to authorize the login.
```

But don't overdo it—too many symbols make output look cluttered.

### Use ASCII art for information density

**Compact representations can be surprisingly scannable:**

```
-rw-r--r-- 1 user user   68 Aug 22 23:20 config.txt
drwxr-xr-x 4 user user 4.0K Jul 20 14:51 data
-rwxr-xr-x 1 user user  12K Mar 15 10:30 script.sh
```

The `ls -l` permissions format is a perfect example—you learn to scan it over time.

---

## Errors: Turn Problems Into Documentation

### Catch and rewrite errors for humans

**Don't expose raw exception messages—translate them:**

```bash
# Bad
Error: ENOENT: no such file or directory, open '/path/to/config.toml'

# Good
Error: Configuration file not found
  Expected location: /path/to/config.toml
  
Try:
  - Create the file with 'mytool init'
  - Specify a different location with --config
```

Every error should answer:
1. **What went wrong** (specific, not generic)
2. **Why it happened** (if determinable)
3. **How to fix it** (concrete steps)
4. **Where to get help** (docs link, issue tracker)

### Keep signal-to-noise ratio high

**The more irrelevant output, the harder to spot the actual problem:**

```bash
# Low signal-to-noise
[ERROR] Failed to process file1.txt: permission denied
[ERROR] Failed to process file2.txt: permission denied
[ERROR] Failed to process file3.txt: permission denied
[ERROR] Failed to process file4.txt: permission denied
[ERROR] Failed to process file5.txt: permission denied

# High signal-to-noise
Error: Permission denied on 5 files
  file1.txt, file2.txt, file3.txt, file4.txt, file5.txt
  
Fix: Run 'chmod +r *.txt' or use sudo
```

### Put important information at the end

**Users look at the bottom of output first** (where the cursor is):

```bash
# Error buried at top (bad)
Error: Missing API key
Traceback (most recent call last):
  File "main.py", line 45, in connect
    response = http.get(url)
  ...50 more lines of stack trace...

# Error at bottom (good)
Traceback (most recent call last):
  File "main.py", line 45, in connect
    response = http.get(url)
  ...stack trace...

Error: Missing API key
  Set the MYTOOL_API_KEY environment variable
  or use --api-key flag

Get an API key: https://example.com/settings/api
```

### Make bug reporting effortless

**Provide a pre-populated bug report URL:**

```
An unexpected error occurred.

Please report this issue:
https://github.com/user/tool/issues/new?title=Crash+in+deploy&body=Version%3A+1.2.3%0AOS%3A+Linux

Attach this file: /tmp/mytool-crash-a1b2c3.txt
```

---

## Configuration: Precedence and Flexibility

### Configuration precedence hierarchy

**Apply configuration in this order (highest to lowest):**

1. Command-line flags
2. Environment variables
3. Project-level config file (`.env`, project-specific config)
4. User-level config file (`~/.config/mytool/config.toml`)
5. System-wide config file (`/etc/mytool/config.toml`)
6. Built-in defaults

This is universal across well-designed CLIs.

### Follow XDG Base Directory Specification

**Use standard locations for config, cache, and state:**

- **Config**: `$XDG_CONFIG_HOME/mytool/` (default: `~/.config/mytool/`)
- **Cache**: `$XDG_CACHE_HOME/mytool/` (default: `~/.cache/mytool/`)
- **Data**: `$XDG_DATA_HOME/mytool/` (default: `~/.local/share/mytool/`)
- **State**: `$XDG_STATE_HOME/mytool/` (default: `~/.local/state/mytool/`)

This keeps home directories clean and is supported by many modern tools (yarn, fish, neovim, tmux).

Example:
```
~/.config/mytool/config.toml      # User config
~/.cache/mytool/downloads/         # Cache
~/.local/share/mytool/data.db      # Persistent data
~/.local/state/mytool/history      # State (logs, history)
```

*Further reading: [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)*

### Make effective configuration introspectable

**Provide a way to see the final, merged configuration:**

```bash
$ mytool config show
api_base: https://api.example.com
  Source: config file (~/.config/mytool/config.toml)
  
timeout: 30s
  Source: default
  
api_key: ***
  Source: environment variable (MYTOOL_API_KEY)
  
region: us-east-1
  Source: flag (--region)
```

This eliminates "works on my machine" issues caused by hidden configuration sources.

### Ask permission before modifying system files

**If you need to modify files outside your program's domain:**

```
$ mytool setup
mytool needs to add itself to /etc/crontab for scheduled tasks.
This requires sudo access.

Proceed? [y/N]: 
```

Prefer creating separate config files (`/etc/cron.d/mytool`) over modifying shared files.

---

## Environment Variables: Context-Aware Behavior

### Use environment variables for context-varying behavior

**Environment variables are for things that change between:**
- Terminal sessions
- Machines
- Projects

Good uses:
- `DEBUG=1 mytool run` — Enable debug output
- `MYTOOL_API_KEY=xxx mytool deploy` — Provide credentials
- `HTTP_PROXY=http://proxy:8080 mytool sync` — Configure networking

Poor uses:
- Complex structured data (use config files)
- Things that should be version-controlled (use project config files)

### Name environment variables properly

**Use UPPERCASE with underscores:**
- `MYTOOL_LOG_LEVEL` ✓
- `mytool_log_level` ✗ (non-portable)
- `MyToolLogLevel` ✗ (non-standard)

Prefix with your tool name to avoid collisions.

### Respect standard environment variables

**Check these when relevant:**

- `NO_COLOR` — Disable color output
- `FORCE_COLOR` — Force color output even when not a TTY
- `DEBUG` — Enable debug mode
- `EDITOR` — User's preferred editor
- `PAGER` — User's preferred pager (less, more)
- `SHELL` — User's shell
- `HOME` — User's home directory
- `TMPDIR` — Temporary file directory
- `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` — Proxy configuration
- `TERM` — Terminal type
- `LINES`, `COLUMNS` — Terminal dimensions

### Support `.env` files for project-specific config

**Read environment variables from `.env` in the current directory:**

```bash
# .env file
MYTOOL_API_KEY=abc123
MYTOOL_REGION=us-east-1
MYTOOL_LOG_LEVEL=debug
```

This allows per-project configuration without polluting the global shell environment.

Many languages have libraries: [dotenv](https://github.com/motdotla/dotenv) (Node), [python-dotenv](https://pypi.org/project/python-dotenv/) (Python), [godotenv](https://github.com/joho/godotenv) (Go).

### Never store secrets in environment variables

**Environment variables are insecure for secrets:**
- Exported to all child processes
- Visible in `ps` output on some systems
- Logged in debug output
- Readable by other users in some contexts

**Instead, use:**
- Credential files with restricted permissions (0600)
- System keychains (macOS Keychain, Windows Credential Manager)
- Secret management services (Vault, AWS Secrets Manager)
- Pipes/stdin for secret input
- OAuth browser flows

---

## Interactivity: TTY Detection and User Control

### Only prompt when stdin is a TTY

**Check if stdin is an interactive terminal before prompting:**

```python
import sys

if sys.stdin.isatty():
    app_name = input("App name: ")
else:
    # Non-interactive, require flag
    print("Error: --app required in non-interactive mode", file=sys.stderr)
    sys.exit(2)
```

This prevents scripts from hanging on unexpected prompts.

### Support `--no-input` flag

**Provide explicit non-interactive mode:**

```bash
# Interactive use
mytool deploy  # Will prompt if needed

# Automated use
mytool deploy --no-input --app myservice --region us-east-1
```

In `--no-input` mode:
- Never prompt
- Fail fast if required input is missing
- Use defaults where appropriate

### Hide passwords when prompting

**Disable echo for password prompts:**

```python
import getpass

password = getpass.getpass("Password: ")
```

Never print passwords to the terminal.

### Let users escape easily

**Always make Ctrl-C work.** Don't trap signals in ways that prevent exit. For programs that wrap other programs (SSH, tmux), document escape sequences clearly.

---

## Subcommands: Organizing Complex Tools

### Use consistent verb-noun or noun-verb ordering

**Pick a pattern and stick to it:**

```bash
# Noun-verb (more common)
docker container create
docker container list
docker image pull

# Verb-noun (also valid)
kubectl create deployment
kubectl get pods
```

Noun-verb seems more popular in modern tools.

### Be consistent across subcommands

- Use the same flag names for the same concepts
- Use similar output formatting
- Follow the same help text structure
- Handle errors the same way

Example: If `--format json` enables JSON output for one subcommand, it should work for all subcommands.

### Don't have ambiguous or similar names

```bash
# Bad - confusing similarity
mytool update   # What does this update?
mytool upgrade  # What does this upgrade?
mytool fetch    # Is this like update?

# Better
mytool refresh-config
mytool upgrade-version
mytool pull-data
```

---

## Robustness: Build Tools That Feel Solid

### Validate early, fail fast

**Check input before doing work:**

```bash
$ mytool deploy --region invalid-region
Error: Invalid region 'invalid-region'
Valid regions: us-east-1, us-west-2, eu-west-1

Run 'mytool regions' to see all available regions
```

Don't wait until halfway through a 10-minute deployment to discover the region is invalid.

### Make operations idempotent

**Running the same operation twice should produce the same result:**

```bash
# First run
$ mytool create-app myservice
✓ Created app 'myservice'

# Second run (idempotent)
$ mytool create-app myservice
✓ App 'myservice' already exists
```

This makes operations safer and more scriptable.

### Make operations resumable

**If a long operation fails, the user should be able to resume:**

```bash
$ mytool sync --all
Syncing 1,247 files...
Error: Connection timeout after file 843

$ mytool sync --all --resume
Resuming from file 843...
Syncing remaining 404 files...
```

Store enough state to pick up where it left off.

### Show meaningful progress

**Users need feedback that something is happening:**

```
$ mytool backup
Creating backup...
[████████████████░░░░] 78% (3.2 GB / 4.1 GB)
Estimated time remaining: 2m 15s
```

Progress indicators:
- **Known work**: Progress bar with percentage
- **Unknown work**: Spinner or pulsing animation
- **Parallel work**: Multiple progress bars (Docker-style)

### Make timeout configurable

**Allow users to override network timeouts:**

```bash
mytool sync --timeout 60s  # Wait up to 60s per request
```

Provide sensible defaults (30s is common) but allow customization for slow connections.

---

## Future-Proofing: Planning for Change

### Keep changes additive

**Prefer adding new flags over changing existing ones:**

```bash
# Rather than changing --format behavior
mytool list --format table  # Old behavior
mytool list --format json   # Add new value

# Better: Keep --format, add --output
mytool list --format table
mytool list --output json  # New flag
```

### Warn before breaking changes

**Give users advance notice:**

```bash
$ mytool deploy --old-flag value
Warning: --old-flag is deprecated and will be removed in v2.0
Use --new-flag instead

Deploying...
```

Give users a migration path before removing functionality.

### Don't create time bombs

**Avoid hard dependencies on external services:**

```bash
# Bad - breaks if example.com goes down
$ mytool init
Downloading config from https://example.com/default.toml...

# Good - include default config in binary
$ mytool init
Created config from built-in template
```

Your tool should work 20 years from now without your maintenance.

### Don't allow arbitrary abbreviations

**Don't accept any prefix as an abbreviation:**

```bash
# Bad - now you can't add "install-deps" command
mytool install → mytool i  # Any prefix works
mytool ins → mytool i
mytool i → mytool i

# Good - explicit aliases only
mytool install
mytool i  # Explicit alias documented in help
```

---

## Distribution: Getting Into Users' Hands

### Distribute as a single binary when possible

**Single binaries are easiest to install and uninstall:**

```bash
# Download and run
curl -o mytool https://example.com/mytool-linux-amd64
chmod +x mytool
./mytool
```

For compiled languages (Go, Rust), this is straightforward. For interpreted languages, use tools like:
- **Python**: PyInstaller, shiv
- **Node.js**: pkg, nexe

### Use native package managers

**Support platform-specific installation:**

```bash
# macOS
brew install mytool

# Linux (via snap, apt, etc.)
snap install mytool

# Windows
choco install mytool

# Language-specific
pip install mytool  # Python
npm install -g mytool  # Node.js
cargo install mytool  # Rust
```

### Make uninstallation easy

**Document uninstall steps in the README:**

```markdown
## Uninstalling

brew uninstall mytool

# Or if installed manually:
rm /usr/local/bin/mytool
rm -rf ~/.config/mytool
```

Put uninstall instructions near install instructions—users often want to uninstall right after trying something.

---

## Analytics and Telemetry: Respect User Privacy

### Do not phone home without consent

**Never send data automatically.** If you collect analytics:

1. **Be explicit** about what you collect
2. **Explain why** you need it
3. **Make opt-in the default** (or very clear opt-out)
4. **Show how to disable** permanently

Example from Homebrew:

```
$ brew install wget
Analytics are enabled. To opt out, run:
  brew analytics off

See what data we collect: https://docs.brew.sh/Analytics
```

### Consider alternatives to telemetry

- **Instrument documentation**: Track docs page views to understand usage
- **Instrument downloads**: Count downloads by OS/version
- **User surveys**: Ask directly
- **GitHub issues**: Encourage feedback

---

## Naming: Making It Memorable

### Make it simple and memorable

**Short, lowercase, easy to type:**

- `git` ✓
- `docker` ✓
- `kubectl` ✓
- `DownloadURL` ✗ (mixed case)
- `url-downloader-pro` ✗ (too long)

### Avoid extremely short names

**Very short names conflict with existing tools:**

- `ls`, `cd`, `ps` — Reserved for core utils
- `go`, `cc`, `dd` — Already taken
- `at`, `bc`, `tr` — POSIX utilities

### Make it easy to type

**Avoid awkward finger positions:**

- `fig` ✓ (alternating hands)
- `plum` ✗ (one hand, awkward)

*Further reading: [The Poetics of CLI Command Names](https://smallstep.com/blog/the-poetics-of-cli-command-names/)*

---

## Conclusion

Building excellent CLI tools requires balancing human-first design with machine compatibility, immediate usability with long-term stability, and helpful guidance with user control. The patterns in this guide—from the stdout/stderr contract to crash-only design, from help text structure to the XDG Base Directory spec—represent decades of accumulated wisdom about what makes command-line tools feel professional, trustworthy, and delightful to use.

The best CLI tools share common traits: they respond instantly, fail gracefully with helpful errors, compose naturally with other tools, work consistently across environments, and guide users toward success through clear documentation and thoughtful defaults. They respect user agency by providing escape hatches, supporting automation through consistent interfaces, and treating configuration as an explicit, introspectable contract.

Modern tools like ripgrep, fd, and bat have raised the bar by demonstrating that following these principles doesn't mean sacrificing innovation. You can have beautiful, colored output *and* respect NO_COLOR. You can have helpful progress indicators *and* clean piped output. You can have intuitive defaults *and* full scriptability.

Use this guide as a checklist when building or refining CLI tools. Not every guideline applies to every tool, but together they form a mental model for creating command-line software that users will trust, remember, and recommend.

---

## References and Further Reading

- [Command Line Interface Guidelines (clig.dev)](https://clig.dev/) — The definitive modern CLI design guide
- [The UNIX Programming Environment](https://en.wikipedia.org/wiki/The_Unix_Programming_Environment) — Kernighan & Pike
- [POSIX Utility Conventions](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap12.html)
- [GNU Coding Standards](https://www.gnu.org/prep/standards/html_node/Program-Behavior.html)
- [12 Factor CLI Apps](https://medium.com/@jdxcode/12-factor-cli-apps-dd3c227a0e46) — Jeff Dickey
- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [NO_COLOR Standard](https://no-color.org/)
- [Crash-only software](https://lwn.net/Articles/191059/)