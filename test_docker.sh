docker build -t my-ubuntu-image .
docker run -it -v $(pwd):/workspace --workdir /workspace my-ubuntu-image /bin/bash