FROM gitpod/workspace-full

USER gitpod

# Install custom tools, runtime, etc. using apt-get
# For example, the command below would install "bastet" - a command line tetris clone:
#
RUN sudo apt-get -q update && sudo apt-get install -y python3-libtorrent && sudo apt-get build-dep python-libtorrent
#
# More information: https://www.gitpod.io/docs/config-docker/
