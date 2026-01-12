#!/bin/bash

# Pretty git log
# Usage: glog [options]
function glog() {
    git log --oneline --graph --decorate "$@"
}

# Git status
function gst() {
    git status
}

# Git checkout
function gco() {
    git checkout "$@"
}

# Git pull
function gl() {
    git pull
}

# Git push
function gp() {
    git push
}
