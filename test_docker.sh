# docker build -t my-ubuntu-image .
cmd_to_run="uv run --with rich https://raw.githubusercontent.com/anhvth/vex/ecf3b5a700fccf36bcfa7f41a566217eaded6069/pyve/cli.py"
docker run -it -v $(pwd):/workspace --workdir /workspace my-ubuntu-image /bin/sh -c "$cmd_to_run"