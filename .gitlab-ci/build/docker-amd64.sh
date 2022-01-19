#!/bin/sh

set -e

if [ "$1" = "setup" ]
then
  set -x
  docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  apk add git
else
  set -x

  ARCH="amd64"

  # Default values
  CI_REGISTRY_IMAGE=${CI_REGISTRY_IMAGE:-"registry.gitlab.com/linaro/kisscache"}-$ARCH

  # Build the docker image
  # Unshallow the git repository to allow git describe to work
  git fetch --unshallow || true
  VERSION=$(git describe)
  docker build -t $CI_REGISTRY_IMAGE:latest . --build-arg VERSION="$VERSION"

  # Push only for tags or master
  if [ "$CI_COMMIT_REF_SLUG" = "master" -o -n "$CI_COMMIT_TAG" ]
  then
    docker push $CI_REGISTRY_IMAGE:latest
  fi
fi
