#!/bin/sh

set -e

if [ "$1" = "setup" ]
then
  set -x
  docker login -u gitlab-ci-token -p $CI_JOB_TOKEN $CI_REGISTRY
  apk add git
else
  set -x

  # Default values
  CI_REGISTRY_IMAGE=${CI_REGISTRY_IMAGE:-"hub.lavasoftware.org/ivoire/kisscache"}

  # Build the docker image
  VERSION=$(git describe)
  docker build -t $CI_REGISTRY_IMAGE:latest . --build-arg VERSION="$VERSION"

  # Push only for tags or master
  if [ "$CI_COMMIT_REF_SLUG" = "master" -o -n "$CI_COMMIT_TAG" ]
  then
    docker push $CI_REGISTRY_IMAGE:latest
  fi
fi
