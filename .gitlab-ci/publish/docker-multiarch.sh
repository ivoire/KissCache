#!/bin/sh

set -e

if [ "$1" = "setup" ]
then
  set -x
  docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  apk add git
else
  set -x

  # Default values
  CI_REGISTRY_IMAGE=${CI_REGISTRY_IMAGE:-"registry.gitlab.com/linaro/kisscache"}

  docker manifest create $CI_REGISTRY_IMAGE:latest $CI_REGISTRY_IMAGE-amd64:latest $CI_REGISTRY_IMAGE-arm64:latest
  # Push only for tags or master
  if [ "$CI_COMMIT_REF_SLUG" = "master" -o -n "$CI_COMMIT_TAG" ]
  then
    docker manifest push $CI_REGISTRY_IMAGE:latest
  fi
fi
